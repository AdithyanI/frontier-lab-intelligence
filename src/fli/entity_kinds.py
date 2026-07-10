"""Resumable structural-kind classification for provisional X entities.

The model sees only identity-bearing profile fields and returns exactly a
classification plus a short reason. Operational metadata stays in SQLite, and
the canonical ``entities.kind`` vocabulary remains unchanged until its
separate migration is implemented.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shlex
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fli import channels, store

PROMPT_VERSION = "entity-kind-v2"
SCHEMA_VERSION = "entity-kind-output-v1"
DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_SECRET_PATH = Path.home() / ".secrets" / "litellm" / "env"
CLASSIFICATIONS = frozenset({"person", "organization", "unsure"})

# Verified against the local LiteLLM /model/info endpoint on 2026-07-10.
MODEL_PRICING_USD_PER_TOKEN = {
    "gpt-5-nano": (0.05 / 1_000_000, 0.40 / 1_000_000),
    "gpt-5-mini": (0.25 / 1_000_000, 2.00 / 1_000_000),
}

CLASSIFIER_INSTRUCTIONS = """Classify what the supplied X profile represents.

Return person when the account represents one individual human.
Return organization when it represents a company, lab, nonprofit, team,
product, publication, community, or project rather than one individual.
Return unsure when the identity evidence is missing, contradictory, or too
weak. A full personal name is evidence for person, but a lone given name or
generic display name with an empty biography and opaque handle is unsure. Do
not invent identity from an opaque handle or use outside knowledge. Keep the
reason to one short sentence grounded only in the supplied fields; do not call
an actor "known." Do not discuss relevance, prominence, affiliation, ranking,
confidence, or channel merging.
"""

CLASSIFICATION_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "entity_kind_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["person", "organization", "unsure"],
            },
            "reason": {"type": "string"},
        },
        "required": ["classification", "reason"],
        "additionalProperties": False,
    },
}

CALIBRATION_HANDLES = (
    "karpathy",  # obvious person, five sources
    "huggingface",  # obvious organization, multiple sources
    "arena",  # organization/community, multiple sources
    "dwarkesh_sp",  # individual who hosts a publication
    "alecrad",  # recognizable personal name, missing bio
    "rpoo",  # ambiguous handle/name, missing bio
    "tgale96",  # graph-only individual
    "tinkerapi",  # single-source product
    "claude_code",  # single-source community account
    "geminiapp",  # single-source product/brand
    "theaitimeline",  # publication-style account
    "vibagor44145276",  # opaque pseudonymous account
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS entity_kind_classification_runs (
    id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    scope TEXT NOT NULL,
    requested_count INTEGER NOT NULL,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS entity_kind_classifications (
    entity_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    input_sha256 TEXT NOT NULL,
    classification TEXT NOT NULL
        CHECK (classification IN ('person', 'organization', 'unsure')),
    reason TEXT NOT NULL,
    model TEXT NOT NULL,
    response_model TEXT,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    response_id TEXT,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    estimated_cost_usd REAL NOT NULL,
    run_id INTEGER NOT NULL REFERENCES entity_kind_classification_runs (id),
    classified_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, input_sha256, model, prompt_version)
);
CREATE INDEX IF NOT EXISTS idx_entity_kind_classifications_label
ON entity_kind_classifications (classification);

CREATE TABLE IF NOT EXISTS entity_kind_classification_errors (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES entity_kind_classification_runs (id),
    entity_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    input_sha256 TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    terminal INTEGER NOT NULL CHECK (terminal IN (0, 1)),
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entity_kind_errors_run
ON entity_kind_classification_errors (run_id, entity_id);
"""


@dataclass(frozen=True)
class EntityInput:
    entity_id: int
    handle: str
    display_name: str
    bio: str | None
    profile_url: str

    @property
    def model_payload(self) -> dict[str, str | None]:
        return {
            "handle": self.handle,
            "display_name": self.display_name,
            "bio": self.bio or None,
            "profile_url": self.profile_url,
        }

    @property
    def input_sha256(self) -> str:
        encoded = json.dumps(
            self.model_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ClassificationResult:
    entity: EntityInput
    classification: str
    reason: str
    response_id: str | None
    response_model: str | None
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


@dataclass(frozen=True)
class ClassificationError:
    entity: EntityInput
    attempt: int
    error_type: str
    error_message: str
    terminal: bool


class OutputContractError(ValueError):
    """The provider response did not satisfy the accepted output contract."""


class ModelRefusalError(RuntimeError):
    """The model refused the classification request."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema(conn: sqlite3.Connection) -> None:
    channels.ensure_schema(conn)
    conn.executescript(SCHEMA)


def connect(db_path: Path | str = store.DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = channels.connect(db_path)
    ensure_schema(conn)
    return conn


def read_unknown_inputs(conn: sqlite3.Connection) -> list[EntityInput]:
    """Read deterministic identity-only inputs for current unknown X entities."""
    ensure_schema(conn)
    rows = conn.execute(
        """SELECT e.id AS entity_id,
                  c.key AS handle,
                  COALESCE(c.label, e.name) AS display_name,
                  (SELECT o.value FROM channel_observations o
                   WHERE o.channel_id = c.id
                     AND o.source = 'x_profile'
                     AND o.metric = 'bio'
                   ORDER BY o.observed_at DESC LIMIT 1) AS bio,
                  COALESCE(c.url, 'https://x.com/' || c.key) AS profile_url
           FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           JOIN channels c ON c.id = ec.channel_id AND c.kind = 'x'
           WHERE e.kind = 'unknown'
           ORDER BY e.id, c.id"""
    ).fetchall()
    seen: set[int] = set()
    inputs: list[EntityInput] = []
    for row in rows:
        if row["entity_id"] in seen:
            raise RuntimeError(
                f"unknown entity {row['entity_id']} has multiple X channels; "
                "channel merging is outside this classifier"
            )
        seen.add(row["entity_id"])
        inputs.append(
            EntityInput(
                entity_id=row["entity_id"],
                handle=row["handle"],
                display_name=row["display_name"],
                bio=row["bio"] or None,
                profile_url=row["profile_url"],
            )
        )
    return inputs


def calibration_inputs(inputs: list[EntityInput]) -> list[EntityInput]:
    by_handle = {item.handle.lower(): item for item in inputs}
    missing = [handle for handle in CALIBRATION_HANDLES if handle not in by_handle]
    if missing:
        raise RuntimeError(f"calibration handles missing from input universe: {missing}")
    return [by_handle[handle] for handle in CALIBRATION_HANDLES]


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"LiteLLM machine-secret file not found: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ")
        key, separator, raw_value = line.partition("=")
        if separator and key in {"LLM_API_ENDPOINT", "LLM_API_KEY"}:
            parsed = shlex.split(raw_value, posix=True)
            if len(parsed) != 1:
                raise ValueError(f"invalid value for {key} in {path}")
            values[key] = parsed[0]
    return values


def litellm_credentials(
    secret_path: Path = DEFAULT_SECRET_PATH,
) -> tuple[str, str]:
    values = _load_env_file(secret_path)
    endpoint = os.environ.get("LLM_API_ENDPOINT") or values.get("LLM_API_ENDPOINT")
    api_key = os.environ.get("LLM_API_KEY") or values.get("LLM_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError(
            "LLM_API_ENDPOINT and LLM_API_KEY must come from the shared "
            f"machine-secret setup at {secret_path}"
        )
    return endpoint.rstrip("/"), api_key


def create_litellm_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI SDK is required; install the project dependencies first."
        ) from exc
    endpoint, api_key = litellm_credentials()
    return OpenAI(base_url=endpoint, api_key=api_key)


def _response_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    return {}


def _find_refusal(value: Any) -> str | None:
    if isinstance(value, dict):
        if value.get("type") == "refusal" and value.get("refusal"):
            return str(value["refusal"])
        for child in value.values():
            refusal = _find_refusal(child)
            if refusal:
                return refusal
    elif isinstance(value, list):
        for child in value:
            refusal = _find_refusal(child)
            if refusal:
                return refusal
    return None


def _validate_output(output_text: str) -> tuple[str, str]:
    try:
        payload = json.loads(output_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise OutputContractError("response was not valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"classification", "reason"}:
        raise OutputContractError(
            "response must contain exactly classification and reason"
        )
    classification = payload["classification"]
    reason = payload["reason"]
    if classification not in CLASSIFICATIONS:
        raise OutputContractError(f"invalid classification: {classification!r}")
    if not isinstance(reason, str) or not reason.strip():
        raise OutputContractError("reason must be a non-empty string")
    reason = " ".join(reason.split())
    if len(reason) > 240:
        raise OutputContractError("reason exceeds 240 characters")
    return classification, reason


def _usage_value(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(field) or 0)
    return int(getattr(usage, field, 0) or 0)


def classify_one(
    client: Any,
    entity: EntityInput,
    *,
    model: str,
    input_cost_per_token: float,
    output_cost_per_token: float,
) -> ClassificationResult:
    response = client.responses.create(
        model=model,
        instructions=CLASSIFIER_INSTRUCTIONS,
        input=json.dumps(
            entity.model_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        text={"format": CLASSIFICATION_FORMAT},
        reasoning={"effort": "minimal"},
        max_output_tokens=200,
        store=False,
    )
    response_data = _response_dict(response)
    refusal = _find_refusal(response_data)
    if refusal:
        raise ModelRefusalError(refusal)
    status = getattr(response, "status", None) or response_data.get("status")
    if status and status != "completed":
        raise OutputContractError(f"response status was {status!r}")
    output_text = getattr(response, "output_text", None)
    if output_text is None:
        output_text = response_data.get("output_text")
    classification, reason = _validate_output(output_text)
    usage = getattr(response, "usage", None) or response_data.get("usage")
    input_tokens = _usage_value(usage, "input_tokens")
    output_tokens = _usage_value(usage, "output_tokens")
    return ClassificationResult(
        entity=entity,
        classification=classification,
        reason=reason,
        response_id=getattr(response, "id", None) or response_data.get("id"),
        response_model=(
            getattr(response, "model", None) or response_data.get("model")
        ),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=(
            input_tokens * input_cost_per_token
            + output_tokens * output_cost_per_token
        ),
    )


def _classify_with_retries(
    client: Any,
    entity: EntityInput,
    *,
    model: str,
    input_cost_per_token: float,
    output_cost_per_token: float,
    max_attempts: int,
) -> tuple[ClassificationResult | None, list[ClassificationError]]:
    errors: list[ClassificationError] = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = classify_one(
                client,
                entity,
                model=model,
                input_cost_per_token=input_cost_per_token,
                output_cost_per_token=output_cost_per_token,
            )
            return result, errors
        except Exception as exc:  # provider and contract errors share retry policy
            errors.append(
                ClassificationError(
                    entity=entity,
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:500],
                    terminal=attempt == max_attempts,
                )
            )
    return None, errors


def _already_classified(
    conn: sqlite3.Connection,
    entity: EntityInput,
    *,
    model: str,
) -> bool:
    return bool(
        conn.execute(
            """SELECT 1 FROM entity_kind_classifications
               WHERE entity_id = ? AND input_sha256 = ?
                 AND model = ? AND prompt_version = ?""",
            (entity.entity_id, entity.input_sha256, model, PROMPT_VERSION),
        ).fetchone()
    )


def run_classification(
    conn: sqlite3.Connection,
    inputs: list[EntityInput],
    *,
    client: Any,
    model: str = DEFAULT_MODEL,
    workers: int = 3,
    max_attempts: int = 2,
    scope: str = "custom",
    pricing: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Classify a deterministic batch, skipping already completed inputs."""
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if pricing is None:
        if model not in MODEL_PRICING_USD_PER_TOKEN:
            raise ValueError(f"no verified pricing configured for model {model!r}")
        pricing = MODEL_PRICING_USD_PER_TOKEN[model]
    ensure_schema(conn)
    pending = [
        entity
        for entity in inputs
        if not _already_classified(conn, entity, model=model)
    ]
    started_at = _now()
    prompt_sha256 = hashlib.sha256(CLASSIFIER_INSTRUCTIONS.encode()).hexdigest()
    cursor = conn.execute(
        """INSERT INTO entity_kind_classification_runs
           (model, prompt_version, schema_version, prompt_sha256, scope,
            requested_count, skipped_count, status, started_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)""",
        (
            model,
            PROMPT_VERSION,
            SCHEMA_VERSION,
            prompt_sha256,
            scope,
            len(inputs),
            len(inputs) - len(pending),
            started_at,
        ),
    )
    run_id = cursor.lastrowid
    conn.commit()

    results: list[ClassificationResult] = []
    errors: list[ClassificationError] = []
    if pending:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    _classify_with_retries,
                    client,
                    entity,
                    model=model,
                    input_cost_per_token=pricing[0],
                    output_cost_per_token=pricing[1],
                    max_attempts=max_attempts,
                )
                for entity in pending
            ]
            for future in concurrent.futures.as_completed(futures):
                result, item_errors = future.result()
                errors.extend(item_errors)
                if result:
                    results.append(result)

    classified_at = _now()
    for result in results:
        conn.execute(
            """INSERT OR IGNORE INTO entity_kind_classifications
               (entity_id, input_sha256, classification, reason, model,
                response_model, prompt_version, schema_version, response_id,
                input_tokens, output_tokens, estimated_cost_usd, run_id,
                classified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.entity.entity_id,
                result.entity.input_sha256,
                result.classification,
                result.reason,
                model,
                result.response_model,
                PROMPT_VERSION,
                SCHEMA_VERSION,
                result.response_id,
                result.input_tokens,
                result.output_tokens,
                result.estimated_cost_usd,
                run_id,
                classified_at,
            ),
        )
    for error in errors:
        conn.execute(
            """INSERT INTO entity_kind_classification_errors
               (run_id, entity_id, input_sha256, attempt, error_type,
                error_message, terminal, occurred_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                error.entity.entity_id,
                error.entity.input_sha256,
                error.attempt,
                error.error_type,
                error.error_message,
                int(error.terminal),
                classified_at,
            ),
        )
    failure_count = len(pending) - len(results)
    input_tokens = sum(result.input_tokens for result in results)
    output_tokens = sum(result.output_tokens for result in results)
    estimated_cost_usd = sum(result.estimated_cost_usd for result in results)
    status = "completed" if failure_count == 0 else "partial"
    conn.execute(
        """UPDATE entity_kind_classification_runs
           SET success_count = ?, failure_count = ?, input_tokens = ?,
               output_tokens = ?, estimated_cost_usd = ?, status = ?,
               completed_at = ?
           WHERE id = ?""",
        (
            len(results),
            failure_count,
            input_tokens,
            output_tokens,
            estimated_cost_usd,
            status,
            classified_at,
            run_id,
        ),
    )
    conn.commit()
    counts = {classification: 0 for classification in sorted(CLASSIFICATIONS)}
    for result in results:
        counts[result.classification] += 1
    return {
        "run_id": run_id,
        "scope": scope,
        "model": model,
        "requested": len(inputs),
        "skipped": len(inputs) - len(pending),
        "classified": len(results),
        "failed": failure_count,
        "counts": counts,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "status": status,
    }


def estimate_full_run(
    *,
    calibration_summary: dict[str, Any],
    full_count: int,
) -> dict[str, float | int]:
    classified = int(calibration_summary["classified"])
    if classified < 1:
        raise ValueError("at least one calibration result is required")
    return {
        "entities": full_count,
        "estimated_input_tokens": round(
            calibration_summary["input_tokens"] / classified * full_count
        ),
        "estimated_output_tokens": round(
            calibration_summary["output_tokens"] / classified * full_count
        ),
        "estimated_cost_usd": (
            calibration_summary["estimated_cost_usd"] / classified * full_count
        ),
    }


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[], Any] = create_litellm_client,
) -> int:
    parser = argparse.ArgumentParser(prog="fli entity-kinds")
    parser.add_argument("action", choices=["run", "summary"])
    parser.add_argument("--db", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--calibration", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args(argv)

    conn = connect(args.db) if args.db else connect()
    inputs = read_unknown_inputs(conn)
    if args.action == "summary":
        row = conn.execute(
            """SELECT COUNT(*) AS classified,
                      COALESCE(SUM(estimated_cost_usd), 0) AS cost
               FROM entity_kind_classifications"""
        ).fetchone()
        print(
            json.dumps(
                {
                    "unknown_inputs": len(inputs),
                    "stored_classifications": row["classified"],
                    "estimated_cost_usd": row["cost"],
                },
                sort_keys=True,
            )
        )
        return 0

    if args.calibration:
        selected = calibration_inputs(inputs)
        scope = "calibration"
    else:
        selected = inputs
        scope = "full" if args.limit is None else "limited"
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be at least 1")
        selected = selected[: args.limit]
    summary = run_classification(
        conn,
        selected,
        client=client_factory(),
        model=args.model,
        workers=args.workers,
        max_attempts=args.max_attempts,
        scope=scope,
    )
    if args.calibration and summary["classified"]:
        summary["full_run_estimate"] = estimate_full_run(
            calibration_summary=summary,
            full_count=len(inputs),
        )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
