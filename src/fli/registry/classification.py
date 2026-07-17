"""Resumable structural-kind classification for provisional X entities.

The model sees only identity-bearing profile fields and returns exactly a
classification plus a short reason. Operational metadata stays in SQLite.
Accepted results can be promoted into the canonical ``entities.kind`` field
as a separate, atomic operation.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fli import llm_responses, store
from fli.ingestion import sources
from fli.registry import channels
from fli.registry import store as registry

PROMPT_VERSION = "entity-kind-v5"
SCHEMA_VERSION = "entity-kind-output-v1"
DEFAULT_MODEL = llm_responses.DEFAULT_EFFICIENT_MODEL
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_WORKERS = 100
DEFAULT_POST_WORKERS = 10
DEFAULT_POST_LIMIT = 20
DEFAULT_MIN_FOLLOWERS = 1_000
DEFAULT_WEB_MAX_TOOL_CALLS = 4
DEFAULT_SECRET_PATH = Path.home() / ".secrets" / "litellm" / "env"
CLASSIFICATIONS = frozenset({"person", "organization", "unsure"})
TRAILING_MARKDOWN_CITATION_RE = re.compile(
    r"\s*(?:\(\s*)?\[[^\]]+\]\(https?://[^)]+\)(?:\s*\))?\s*$"
)
PROTECTED_ACCOUNT_REASON_CODE = "protected_x_account"
PROTECTED_ACCOUNT_REASON = (
    "The X account has protected posts, so its public output cannot be collected."
)

# Frozen fallback for the accepted classifier contract, verified 2026-07-10.
# LiteLLM's reported response cost is the operational source of truth. This
# snapshot exists only to preserve local estimates when the proxy omits cost.
DEFAULT_MODEL_PRICING_USD_PER_TOKEN = (
    1.00 / 1_000_000,
    6.00 / 1_000_000,
)

ENTITY_KIND_INSTRUCTIONS = """Classify what one X account represents.

The goal is to determine the structural actor speaking through the account,
not whether the account is relevant, prominent, trustworthy, or popular.

Return person when the account represents one individual human, including a
pseudonymous human. Return organization when it represents a company, lab,
nonprofit, team, product, publication, newsletter, community, project, or
other collective or institutional actor. Return unsure when the supplied
evidence is insufficient or contradictory.

Use the account's own voice, not merely the subjects it discusses. A person
may promote a company, project, newsletter, or show and still be a person when
the account speaks as that individual. Repeated first-person singular voice,
personal experiences, and personal work support person. Institutional voice,
team language, publication branding, and product or service announcements
support organization. Do not use follower count, fame, outside knowledge, or
assumptions based on a recognizable handle. Do not infer identity from topic
alone, and do not force a binary answer when the evidence remains weak.

On the profile-only turn, require evidence that actually identifies the actor.
A full personal name or an explicitly personal biography can support person,
but a lone given name, generic display name, opaque handle, or empty biography
does not establish that the account represents one human. Return unsure in
those cases so later authored posts can provide the missing evidence.

Return exactly classification and reason through the required schema. Keep
the reason to one short sentence grounded only in the supplied profile or
posts. Do not mention confidence, relevance, prominence, ranking, or these
instructions.
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

SCHEMA = """
CREATE TABLE IF NOT EXISTS entity_kind_classification_runs (
    id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
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
    reported_cost_usd REAL NOT NULL DEFAULT 0,
    reported_cost_count INTEGER NOT NULL DEFAULT 0,
    request_tags TEXT NOT NULL DEFAULT '[]',
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
    reasoning_effort TEXT NOT NULL,
    response_model TEXT,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    response_id TEXT,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    estimated_cost_usd REAL NOT NULL,
    reported_cost_usd REAL,
    run_id INTEGER NOT NULL REFERENCES entity_kind_classification_runs (id),
    classified_at TEXT NOT NULL,
    PRIMARY KEY (
        entity_id, input_sha256, model, reasoning_effort, prompt_version
    )
);
CREATE INDEX IF NOT EXISTS idx_entity_kind_classifications_label
ON entity_kind_classifications (classification);
CREATE INDEX IF NOT EXISTS idx_entity_kind_classifications_entity_label_latest
ON entity_kind_classifications (
    entity_id, classification, classified_at DESC, run_id DESC
);

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

CREATE TABLE IF NOT EXISTS entity_kind_web_enrichments (
    entity_id INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    input_sha256 TEXT NOT NULL,
    classification TEXT NOT NULL
        CHECK (classification IN ('person', 'organization', 'unsure')),
    reason TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    response_model TEXT,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    response_id TEXT,
    actions_json TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    estimated_cost_usd REAL NOT NULL,
    reported_cost_usd REAL,
    run_id INTEGER NOT NULL REFERENCES entity_kind_classification_runs (id),
    enriched_at TEXT NOT NULL,
    PRIMARY KEY (
        entity_id, input_sha256, model, reasoning_effort, prompt_version
    )
);
CREATE INDEX IF NOT EXISTS idx_entity_kind_web_label
ON entity_kind_web_enrichments (classification);

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
    reported_cost_usd: float | None


@dataclass(frozen=True)
class WebEnrichmentResult:
    result: ClassificationResult
    actions: tuple[dict[str, Any], ...]
    sources: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PostEnrichmentResult:
    entity: EntityInput
    profile_result: ClassificationResult
    followup_result: ClassificationResult | None
    web_result: WebEnrichmentResult | None
    recent_posts: tuple[dict[str, Any], ...]
    evidence_sha256: str

    @property
    def final_result(self) -> ClassificationResult:
        if self.web_result is not None:
            return self.web_result.result
        return self.followup_result or self.profile_result

    @property
    def turns(self) -> tuple[ClassificationResult, ...]:
        turns = [self.profile_result]
        if self.followup_result is not None:
            turns.append(self.followup_result)
        if self.web_result is not None:
            turns.append(self.web_result.result)
        return tuple(turns)

    @property
    def input_tokens(self) -> int:
        return sum(turn.input_tokens for turn in self.turns)

    @property
    def output_tokens(self) -> int:
        return sum(turn.output_tokens for turn in self.turns)

    @property
    def estimated_cost_usd(self) -> float:
        return sum(turn.estimated_cost_usd for turn in self.turns)

    @property
    def reported_cost_usd(self) -> float | None:
        costs = [
            turn.reported_cost_usd
            for turn in self.turns
            if turn.reported_cost_usd is not None
        ]
        return sum(costs) if costs else None


@dataclass(frozen=True)
class RegistryRejection:
    entity: EntityInput
    reason_code: str
    reason: str
    source: str
    evidence_url: str


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


def _read_inputs_for_kind(
    conn: sqlite3.Connection,
    *,
    kind: str,
) -> list[EntityInput]:
    """Read deterministic identity-only inputs for one canonical kind."""
    if kind not in {"unknown", "unsure"}:
        raise ValueError(f"unsupported input kind: {kind!r}")
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
           WHERE e.kind = ?
           ORDER BY e.id, c.id""",
        (kind,),
    ).fetchall()
    seen: set[int] = set()
    inputs: list[EntityInput] = []
    for row in rows:
        if row["entity_id"] in seen:
            raise RuntimeError(
                f"{kind} entity {row['entity_id']} has multiple X channels; "
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


def read_unknown_inputs(conn: sqlite3.Connection) -> list[EntityInput]:
    """Read deterministic identity-only inputs for current unknown X entities."""
    return _read_inputs_for_kind(conn, kind="unknown")


def read_unsure_inputs(conn: sqlite3.Connection) -> list[EntityInput]:
    """Read deterministic identity-only inputs for current unsure X entities."""
    return _read_inputs_for_kind(conn, kind="unsure")


def read_entity_input(conn: sqlite3.Connection, *, entity_id: int) -> EntityInput:
    """Read one X-backed entity regardless of its current lifecycle kind."""
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
           WHERE e.id = ?
           ORDER BY c.id""",
        (entity_id,),
    ).fetchall()
    if not rows:
        raise ValueError(f"entity {entity_id} does not have an X channel")
    if len(rows) > 1:
        raise RuntimeError(
            f"entity {entity_id} has multiple X channels; channel merging "
            "is outside this classifier"
        )
    row = rows[0]
    return EntityInput(
        entity_id=row["entity_id"],
        handle=row["handle"],
        display_name=row["display_name"],
        bio=row["bio"] or None,
        profile_url=row["profile_url"],
    )


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
    return classification, reason


def _without_trailing_web_citation(reason: str) -> str:
    """Remove a hosted-search citation from the runner-owned reason field."""
    cleaned = TRAILING_MARKDOWN_CITATION_RE.sub("", reason).strip()
    return cleaned or reason


def _usage_value(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(field) or 0)
    return int(getattr(usage, field, 0) or 0)


def default_reasoning_effort(model: str) -> str:
    """Return the evaluated effort for the accepted model contract."""
    if model != DEFAULT_MODEL:
        raise ValueError(
            f"no evaluated reasoning effort for {model!r}; pass one explicitly"
        )
    return DEFAULT_REASONING_EFFORT


def request_tags(
    *,
    scope: str,
    run_id: int,
    job: str = "entity-kind-classification",
    prompt_version: str = PROMPT_VERSION,
) -> tuple[str, ...]:
    """Return stable, queryable LiteLLM spend tags for one classifier run."""
    return (
        "app:frontier-lab-intelligence",
        "pipeline:entity-kind-classification",
        f"job:{job}",
        f"scope:{scope}",
        f"prompt:{prompt_version}",
        f"run:{run_id}",
    )


def _reported_cost(headers: Any) -> float | None:
    if headers is None:
        return None
    raw_cost = headers.get("x-litellm-response-cost")
    if raw_cost in (None, ""):
        return None
    try:
        return float(raw_cost)
    except (TypeError, ValueError):
        return None


def classify_one(
    client: Any,
    entity: EntityInput,
    *,
    model: str,
    effort: str,
    tags: tuple[str, ...],
    input_cost_per_token: float,
    output_cost_per_token: float,
) -> ClassificationResult:
    request = dict(
        model=model,
        instructions=ENTITY_KIND_INSTRUCTIONS,
        input=json.dumps(
            entity.model_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        text={"format": CLASSIFICATION_FORMAT},
        reasoning={"effort": effort},
        max_output_tokens=200,
        store=False,
        extra_body={"metadata": {"tags": list(tags)}},
        extra_headers={"x-litellm-tags": ",".join(tags)},
    )
    raw_api = getattr(client.responses, "with_raw_response", None)
    if raw_api is None:
        response = client.responses.create(**request)
        reported_cost_usd = None
    else:
        raw_response = raw_api.create(**request)
        response = raw_response.parse()
        reported_cost_usd = _reported_cost(raw_response.headers)
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
        reported_cost_usd=reported_cost_usd,
    )


def _profile_workflow_input(entity: EntityInput) -> list[dict[str, str]]:
    bio = entity.bio.strip() if entity.bio else "No bio observed."
    prompt = "\n".join(
        (
            "Classify this X account from its profile alone.",
            "",
            f"Handle: @{entity.handle}",
            f"Display name: {entity.display_name}",
            f"Bio: {bio}",
            f"Profile: {entity.profile_url}",
        )
    )
    return [
        {"role": "developer", "content": ENTITY_KIND_INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]


def _posts_followup_input(
    posts: tuple[dict[str, Any], ...],
) -> list[dict[str, str]]:
    blocks = [
        "The profile alone was not enough to classify this account.",
        "",
        (
            "Here are recent posts written by the same account. Replies and "
            "retweets have been excluded. Re-evaluate the account using the "
            "profile and these posts together."
        ),
    ]
    for index, post in enumerate(posts, start=1):
        created_at = post.get("created_at") or "date unavailable"
        post_type = post.get("post_type") or "original"
        blocks.extend(
            (
                "",
                f"Post {index} ({post_type}, {created_at}):",
                str(post.get("text") or ""),
            )
        )
    return [{"role": "user", "content": "\n".join(blocks)}]


def _web_followup_input(entity: EntityInput) -> list[dict[str, str]]:
    prompt = "\n".join(
        (
            "The profile and recent authored posts were still insufficient.",
            "",
            (
                "Use web search to identify what this exact X account "
                f"(@{entity.handle}) represents. Match the handle to the "
                "real-world actor; do not merely find a similarly named or "
                "famous person."
            ),
            (
                "Prefer first-party identity evidence such as official company "
                "pages, official blogs, regulatory filings, employer pages, "
                "or the actor's own site. Use reputable secondary sources only "
                "when first-party evidence is unavailable."
            ),
            (
                "Re-evaluate the same account using the profile, posts, and "
                "searched evidence together. Return unsure if the exact-handle "
                "identity still cannot be established."
            ),
        )
    )
    return [{"role": "user", "content": prompt}]


def _web_evidence(
    response_data: dict[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Extract observable hosted-search actions and deduplicated sources."""
    actions: list[dict[str, Any]] = []
    sources_by_url: dict[str, dict[str, Any]] = {}

    def add_source(
        *,
        url: Any,
        title: Any = None,
        source_type: Any = None,
        cited: bool = False,
    ) -> None:
        if not isinstance(url, str) or not url:
            return
        source = sources_by_url.setdefault(
            url,
            {"url": url, "title": None, "type": None, "cited": False},
        )
        if isinstance(title, str) and title:
            source["title"] = title
        if isinstance(source_type, str) and source_type:
            source["type"] = source_type
        source["cited"] = source["cited"] or cited

    for item in response_data.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "web_search_call":
            action = item.get("action") or {}
            if not isinstance(action, dict):
                action = {}
            actions.append(
                {
                    key: action[key]
                    for key in ("type", "query", "queries", "url", "pattern")
                    if action.get(key) is not None
                }
            )
            for source in action.get("sources") or []:
                if isinstance(source, dict):
                    add_source(
                        url=source.get("url"),
                        title=source.get("title"),
                        source_type=source.get("type"),
                    )
        if item.get("type") == "message":
            for content in item.get("content") or []:
                if not isinstance(content, dict):
                    continue
                for annotation in content.get("annotations") or []:
                    if (
                        isinstance(annotation, dict)
                        and annotation.get("type") == "url_citation"
                    ):
                        add_source(
                            url=annotation.get("url"),
                            title=annotation.get("title"),
                            source_type="url_citation",
                            cited=True,
                        )
    if not actions:
        raise OutputContractError("response completed without a web search call")
    return tuple(actions), tuple(sources_by_url.values())


def _post_workflow_turn(
    client: Any,
    entity: EntityInput,
    *,
    input_items: list[dict[str, str]],
    model: str,
    effort: str,
    tags: tuple[str, ...],
    input_cost_per_token: float,
    output_cost_per_token: float,
    previous_response_id: str | None = None,
) -> ClassificationResult:
    request: dict[str, Any] = {
        "model": model,
        "input": input_items,
        "text": {"format": CLASSIFICATION_FORMAT},
        "reasoning": {"effort": effort},
        "max_output_tokens": 800,
        "store": True,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    if previous_response_id is not None:
        request["previous_response_id"] = previous_response_id
    raw_api = getattr(client.responses, "with_raw_response", None)
    if raw_api is None:
        response = client.responses.create(**request)
        reported_cost_usd = None
    else:
        raw_response = raw_api.create(**request)
        response = raw_response.parse()
        reported_cost_usd = _reported_cost(raw_response.headers)
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
        reported_cost_usd=reported_cost_usd,
    )


def _web_workflow_turn(
    client: Any,
    entity: EntityInput,
    *,
    previous_response_id: str,
    model: str,
    effort: str,
    tags: tuple[str, ...],
    input_cost_per_token: float,
    output_cost_per_token: float,
    max_tool_calls: int = DEFAULT_WEB_MAX_TOOL_CALLS,
) -> WebEnrichmentResult:
    """Run the final, required hosted-search escalation for one abstention."""
    request: dict[str, Any] = {
        "model": model,
        "input": _web_followup_input(entity),
        "previous_response_id": previous_response_id,
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "tool_choice": "required",
        "include": ["web_search_call.action.sources"],
        "max_tool_calls": max_tool_calls,
        "text": {"format": CLASSIFICATION_FORMAT},
        "reasoning": {"effort": effort},
        "max_output_tokens": 800,
        "store": True,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    raw_api = getattr(client.responses, "with_raw_response", None)
    if raw_api is None:
        response = client.responses.create(**request)
        reported_cost_usd = None
    else:
        raw_response = raw_api.create(**request)
        response = raw_response.parse()
        reported_cost_usd = _reported_cost(raw_response.headers)
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
    reason = _without_trailing_web_citation(reason)
    actions, web_sources = _web_evidence(response_data)
    usage = getattr(response, "usage", None) or response_data.get("usage")
    input_tokens = _usage_value(usage, "input_tokens")
    output_tokens = _usage_value(usage, "output_tokens")
    result = ClassificationResult(
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
        reported_cost_usd=reported_cost_usd,
    )
    return WebEnrichmentResult(
        result=result,
        actions=actions,
        sources=web_sources,
    )


def enrich_one_with_posts(
    client: Any,
    post_client: Any,
    entity: EntityInput,
    *,
    model: str,
    effort: str,
    tags: tuple[str, ...],
    input_cost_per_token: float,
    output_cost_per_token: float,
    post_limit: int = DEFAULT_POST_LIMIT,
    profile: dict[str, Any] | None = None,
) -> PostEnrichmentResult:
    """Run profile, authored-post, then hosted-web escalation as needed."""
    profile_result = _post_workflow_turn(
        client,
        entity,
        input_items=_profile_workflow_input(entity),
        model=model,
        effort=effort,
        tags=tags,
        input_cost_per_token=input_cost_per_token,
        output_cost_per_token=output_cost_per_token,
    )
    recent_posts: tuple[dict[str, Any], ...] = ()
    followup_result: ClassificationResult | None = None
    web_result: WebEnrichmentResult | None = None
    if profile_result.classification == "unsure":
        recent_posts = post_client.fetch_recent_authored_posts(
            username=entity.handle,
            limit=post_limit,
            profile=profile,
        )
        if recent_posts:
            followup_result = _post_workflow_turn(
                client,
                entity,
                input_items=_posts_followup_input(recent_posts),
                model=model,
                effort=effort,
                tags=tags,
                input_cost_per_token=input_cost_per_token,
                output_cost_per_token=output_cost_per_token,
                previous_response_id=profile_result.response_id,
            )
    latest_result = followup_result or profile_result
    if latest_result.classification == "unsure":
        if latest_result.response_id is None:
            raise OutputContractError(
                "cannot continue to web search without a previous response ID"
            )
        web_result = _web_workflow_turn(
            client,
            entity,
            previous_response_id=latest_result.response_id,
            model=model,
            effort=effort,
            tags=tags,
            input_cost_per_token=input_cost_per_token,
            output_cost_per_token=output_cost_per_token,
        )
    evidence_payload = {
        "profile": entity.model_payload,
        "recent_posts": recent_posts,
        "web_actions": web_result.actions if web_result is not None else (),
        "web_sources": web_result.sources if web_result is not None else (),
    }
    evidence_sha256 = hashlib.sha256(
        json.dumps(
            evidence_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return PostEnrichmentResult(
        entity=entity,
        profile_result=profile_result,
        followup_result=followup_result,
        web_result=web_result,
        recent_posts=recent_posts,
        evidence_sha256=evidence_sha256,
    )


def _classify_safely(
    client: Any,
    entity: EntityInput,
    *,
    model: str,
    effort: str,
    tags: tuple[str, ...],
    input_cost_per_token: float,
    output_cost_per_token: float,
) -> tuple[ClassificationResult | None, list[ClassificationError]]:
    try:
        return (
            classify_one(
                client,
                entity,
                model=model,
                effort=effort,
                tags=tags,
                input_cost_per_token=input_cost_per_token,
                output_cost_per_token=output_cost_per_token,
            ),
            [],
        )
    except Exception as exc:
        return None, [
            ClassificationError(
                entity=entity,
                attempt=1,
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
                terminal=True,
            )
        ]


def _post_enrich_safely(
    client: Any,
    post_client: Any,
    entity: EntityInput,
    *,
    model: str,
    effort: str,
    tags: tuple[str, ...],
    input_cost_per_token: float,
    output_cost_per_token: float,
    post_limit: int,
    profile: dict[str, Any] | None = None,
) -> tuple[
    PostEnrichmentResult | None,
    list[ClassificationError],
    RegistryRejection | None,
]:
    try:
        profile = profile or post_client.fetch_user(username=entity.handle)
        if sources.is_protected_profile(profile):
            return (
                None,
                [],
                RegistryRejection(
                    entity=entity,
                    reason_code=PROTECTED_ACCOUNT_REASON_CODE,
                    reason=PROTECTED_ACCOUNT_REASON,
                    source=sources.PROVIDER,
                    evidence_url=entity.profile_url,
                ),
            )
        return (
            enrich_one_with_posts(
                client,
                post_client,
                entity,
                model=model,
                effort=effort,
                tags=tags,
                input_cost_per_token=input_cost_per_token,
                output_cost_per_token=output_cost_per_token,
                post_limit=post_limit,
                profile=profile,
            ),
            [],
            None,
        )
    except Exception as exc:
        return (
            None,
            [
                ClassificationError(
                    entity=entity,
                    attempt=1,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:500],
                    terminal=True,
                )
            ],
            None,
        )


def _already_classified(
    conn: sqlite3.Connection,
    entity: EntityInput,
    *,
    model: str,
    effort: str,
) -> bool:
    return bool(
        conn.execute(
            """SELECT 1 FROM entity_kind_classifications
               WHERE entity_id = ? AND input_sha256 = ?
                 AND model = ? AND reasoning_effort = ?
                 AND prompt_version = ?""",
            (
                entity.entity_id,
                entity.input_sha256,
                model,
                effort,
                PROMPT_VERSION,
            ),
        ).fetchone()
    )


def run_classification(
    conn: sqlite3.Connection,
    inputs: list[EntityInput],
    *,
    client: Any,
    model: str = DEFAULT_MODEL,
    workers: int = DEFAULT_WORKERS,
    scope: str = "custom",
    reasoning_effort_override: str | None = None,
    pricing: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Classify a deterministic batch, skipping already completed inputs."""
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if pricing is None:
        if model != DEFAULT_MODEL:
            raise ValueError(
                f"no local pricing snapshot for {model!r}; pass pricing explicitly"
            )
        pricing = DEFAULT_MODEL_PRICING_USD_PER_TOKEN
    ensure_schema(conn)
    effort = reasoning_effort_override or default_reasoning_effort(model)
    pending = [
        entity
        for entity in inputs
        if not _already_classified(conn, entity, model=model, effort=effort)
    ]
    started_at = _now()
    prompt_sha256 = hashlib.sha256(ENTITY_KIND_INSTRUCTIONS.encode()).hexdigest()
    cursor = conn.execute(
        """INSERT INTO entity_kind_classification_runs
           (model, reasoning_effort, prompt_version, schema_version,
            prompt_sha256, scope,
            requested_count, skipped_count, status, started_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?)""",
        (
            model,
            effort,
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
    tags = request_tags(scope=scope, run_id=run_id)
    conn.execute(
        """UPDATE entity_kind_classification_runs
           SET request_tags = ? WHERE id = ?""",
        (json.dumps(tags), run_id),
    )
    conn.commit()

    results: list[ClassificationResult] = []
    errors: list[ClassificationError] = []
    if pending:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    _classify_safely,
                    client,
                    entity,
                    model=model,
                    effort=effort,
                    tags=tags,
                    input_cost_per_token=pricing[0],
                    output_cost_per_token=pricing[1],
                )
                for entity in pending
            ]
            for future in concurrent.futures.as_completed(futures):
                result, item_errors = future.result()
                errors.extend(item_errors)
                if result:
                    results.append(result)
                classified_at = _now()
                if result:
                    conn.execute(
                        """INSERT OR IGNORE INTO entity_kind_classifications
                           (entity_id, input_sha256, classification, reason,
                            model, reasoning_effort, response_model,
                            prompt_version, schema_version, response_id,
                            input_tokens, output_tokens, estimated_cost_usd,
                            reported_cost_usd, run_id, classified_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            result.entity.entity_id,
                            result.entity.input_sha256,
                            result.classification,
                            result.reason,
                            model,
                            effort,
                            result.response_model,
                            PROMPT_VERSION,
                            SCHEMA_VERSION,
                            result.response_id,
                            result.input_tokens,
                            result.output_tokens,
                            result.estimated_cost_usd,
                            result.reported_cost_usd,
                            run_id,
                            classified_at,
                        ),
                    )
                for error in item_errors:
                    conn.execute(
                        """INSERT INTO entity_kind_classification_errors
                           (run_id, entity_id, input_sha256, attempt,
                            error_type, error_message, terminal, occurred_at)
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
                # Persist every completed entity so an interrupted full run can
                # resume without repeating earlier paid requests.
                conn.commit()

    classified_at = _now()
    failure_count = len(pending) - len(results)
    input_tokens = sum(result.input_tokens for result in results)
    output_tokens = sum(result.output_tokens for result in results)
    estimated_cost_usd = sum(result.estimated_cost_usd for result in results)
    reported_costs = [
        result.reported_cost_usd
        for result in results
        if result.reported_cost_usd is not None
    ]
    reported_cost_usd = sum(reported_costs)
    status = "completed" if failure_count == 0 else "partial"
    conn.execute(
        """UPDATE entity_kind_classification_runs
           SET success_count = ?, failure_count = ?, input_tokens = ?,
               output_tokens = ?, estimated_cost_usd = ?,
               reported_cost_usd = ?, reported_cost_count = ?, status = ?,
               completed_at = ?
           WHERE id = ?""",
        (
            len(results),
            failure_count,
            input_tokens,
            output_tokens,
            estimated_cost_usd,
            reported_cost_usd,
            len(reported_costs),
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
        "reasoning_effort": effort,
        "request_tags": tags,
        "requested": len(inputs),
        "skipped": len(inputs) - len(pending),
        "classified": len(results),
        "failed": failure_count,
        "counts": counts,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "reported_cost_usd": reported_cost_usd,
        "reported_cost_count": len(reported_costs),
        "status": status,
    }


def _post_turn_record(
    stage: str,
    result: ClassificationResult,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "classification": result.classification,
        "reason": result.reason,
        "response_id": result.response_id,
        "response_model": result.response_model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "estimated_cost_usd": result.estimated_cost_usd,
        "reported_cost_usd": result.reported_cost_usd,
    }


def run_post_enrichment(
    conn: sqlite3.Connection,
    inputs: list[EntityInput],
    *,
    client: Any,
    post_client: Any,
    model: str = DEFAULT_MODEL,
    workers: int = DEFAULT_POST_WORKERS,
    scope: str = "posts-custom",
    reasoning_effort_override: str | None = None,
    pricing: tuple[float, float] | None = None,
    post_limit: int = DEFAULT_POST_LIMIT,
    persist: bool = False,
    promote: bool = False,
    allow_unknown: bool = False,
    profiles: dict[int, dict[str, Any]] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run the profile/posts/web lifecycle for current abstentions."""
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if post_limit < 1:
        raise ValueError("post_limit must be at least 1")
    if promote and not persist:
        raise ValueError("promote requires persist")
    if pricing is None:
        if model != DEFAULT_MODEL:
            raise ValueError(
                f"no local pricing snapshot for {model!r}; pass pricing explicitly"
            )
        pricing = DEFAULT_MODEL_PRICING_USD_PER_TOKEN
    ensure_schema(conn)
    effort = reasoning_effort_override or default_reasoning_effort(model)
    current_unsure_ids = {entity.entity_id for entity in read_unsure_inputs(conn)}
    eligible_ids = set(current_unsure_ids)
    if allow_unknown:
        eligible_ids.update(
            entity.entity_id for entity in read_unknown_inputs(conn)
        )
    invalid_ids = [
        entity.entity_id
        for entity in inputs
        if entity.entity_id not in eligible_ids
    ]
    if invalid_ids:
        raise ValueError(
            "entity-kind enrichment accepts only current abstentions; "
            f"invalid IDs: {invalid_ids[:10]}"
        )
    pending = inputs
    if persist and not force:
        pending = [
            entity
            for entity in inputs
            if not conn.execute(
                """SELECT 1 FROM entity_kind_classifications
                   WHERE entity_id = ? AND model = ?
                     AND reasoning_effort = ? AND prompt_version = ?
                   LIMIT 1""",
                (entity.entity_id, model, effort, PROMPT_VERSION),
            ).fetchone()
        ]
        cursor = conn.execute(
            """INSERT INTO entity_kind_classification_runs
               (model, reasoning_effort, prompt_version, schema_version,
                prompt_sha256, scope, requested_count, skipped_count,
                status, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?)""",
            (
                model,
                effort,
                PROMPT_VERSION,
                SCHEMA_VERSION,
                hashlib.sha256(ENTITY_KIND_INSTRUCTIONS.encode()).hexdigest(),
                scope,
                len(inputs),
                len(inputs) - len(pending),
                _now(),
            ),
        )
        run_id = cursor.lastrowid
    else:
        run_id = int(datetime.now(timezone.utc).timestamp() * 1000)
    tags = request_tags(
        scope=scope,
        run_id=run_id,
        job="entity-kind-post-enrichment",
        prompt_version=PROMPT_VERSION,
    )
    if persist:
        conn.execute(
            """UPDATE entity_kind_classification_runs
               SET request_tags = ? WHERE id = ?""",
            (json.dumps(tags), run_id),
        )
        conn.commit()

    results: list[PostEnrichmentResult] = []
    errors: list[ClassificationError] = []
    rejections: list[RegistryRejection] = []
    if pending:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    _post_enrich_safely,
                    client,
                    post_client,
                    entity,
                    model=model,
                    effort=effort,
                    tags=tags,
                    input_cost_per_token=pricing[0],
                    output_cost_per_token=pricing[1],
                    post_limit=post_limit,
                    profile=(profiles or {}).get(entity.entity_id),
                )
                for entity in pending
            ]
            for future in concurrent.futures.as_completed(futures):
                result, item_errors, rejection = future.result()
                errors.extend(item_errors)
                if result:
                    results.append(result)
                if rejection:
                    rejections.append(rejection)
                if persist:
                    completed_at = _now()
                    if result:
                        final = result.final_result
                        conn.execute(
                            """INSERT OR IGNORE INTO entity_kind_classifications
                               (entity_id, input_sha256, classification, reason,
                                model, reasoning_effort, response_model,
                                prompt_version, schema_version, response_id,
                                input_tokens, output_tokens,
                                estimated_cost_usd, reported_cost_usd, run_id,
                                classified_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                result.entity.entity_id,
                                result.evidence_sha256,
                                final.classification,
                                final.reason,
                                model,
                                effort,
                                final.response_model,
                                PROMPT_VERSION,
                                SCHEMA_VERSION,
                                final.response_id,
                                result.input_tokens,
                                result.output_tokens,
                                result.estimated_cost_usd,
                                result.reported_cost_usd,
                                run_id,
                                completed_at,
                            ),
                        )
                        if result.web_result is not None:
                            web = result.web_result
                            web_turn = web.result
                            conn.execute(
                                """INSERT OR REPLACE INTO entity_kind_web_enrichments
                                   (entity_id, input_sha256, classification,
                                    reason, model, reasoning_effort,
                                    response_model, prompt_version,
                                    schema_version, response_id, actions_json,
                                    sources_json, input_tokens, output_tokens,
                                    estimated_cost_usd, reported_cost_usd,
                                    run_id, enriched_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    result.entity.entity_id,
                                    result.evidence_sha256,
                                    web_turn.classification,
                                    web_turn.reason,
                                    model,
                                    effort,
                                    web_turn.response_model,
                                    PROMPT_VERSION,
                                    SCHEMA_VERSION,
                                    web_turn.response_id,
                                    json.dumps(web.actions, ensure_ascii=False),
                                    json.dumps(web.sources, ensure_ascii=False),
                                    web_turn.input_tokens,
                                    web_turn.output_tokens,
                                    web_turn.estimated_cost_usd,
                                    web_turn.reported_cost_usd,
                                    run_id,
                                    completed_at,
                                ),
                            )
                        if promote:
                            conn.execute(
                                """UPDATE entities
                                   SET kind = ?, updated_at = ?
                                   WHERE id = ?""",
                                (
                                    final.classification,
                                    completed_at,
                                    result.entity.entity_id,
                                ),
                            )
                    if rejection:
                        registry.reject_entity(
                            conn,
                            entity_id=rejection.entity.entity_id,
                            reason_code=rejection.reason_code,
                            reason=rejection.reason,
                            source=rejection.source,
                            evidence_url=rejection.evidence_url,
                            rejected_at=completed_at,
                        )
                    for error in item_errors:
                        conn.execute(
                            """INSERT INTO entity_kind_classification_errors
                               (run_id, entity_id, input_sha256, attempt,
                                error_type, error_message, terminal,
                                occurred_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                run_id,
                                error.entity.entity_id,
                                error.entity.input_sha256,
                                error.attempt,
                                error.error_type,
                                error.error_message,
                                int(error.terminal),
                                completed_at,
                            ),
                        )
                    conn.commit()
    results.sort(key=lambda item: item.entity.entity_id)
    errors.sort(key=lambda item: item.entity.entity_id)
    rejections.sort(key=lambda item: item.entity.entity_id)
    failure_count = len(pending) - len(results) - len(rejections)
    input_tokens = sum(result.input_tokens for result in results)
    output_tokens = sum(result.output_tokens for result in results)
    estimated_cost_usd = sum(result.estimated_cost_usd for result in results)
    reported_costs = [
        turn.reported_cost_usd
        for result in results
        for turn in result.turns
        if turn.reported_cost_usd is not None
    ]
    reported_cost_usd = sum(reported_costs)
    status = "completed" if failure_count == 0 else "partial"
    if persist:
        conn.execute(
            """UPDATE entity_kind_classification_runs
               SET success_count = ?, failure_count = ?, input_tokens = ?,
                   output_tokens = ?, estimated_cost_usd = ?,
                   reported_cost_usd = ?, reported_cost_count = ?, status = ?,
                   completed_at = ?
               WHERE id = ?""",
            (
                len(results) + len(rejections),
                failure_count,
                input_tokens,
                output_tokens,
                estimated_cost_usd,
                reported_cost_usd,
                len(reported_costs),
                status,
                _now(),
                run_id,
            ),
        )
        conn.commit()
    counts = {classification: 0 for classification in sorted(CLASSIFICATIONS)}
    for result in results:
        counts[result.final_result.classification] += 1
    return {
        "run_id": run_id,
        "scope": scope,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": PROMPT_VERSION,
        "request_tags": tags,
        "requested": len(inputs),
        "skipped": len(inputs) - len(pending),
        "enriched": len(results),
        "rejected": len(rejections),
        "failed": failure_count,
        "counts": counts,
        "profile_only": sum(
            len(result.turns) == 1 for result in results
        ),
        "followups": sum(
            result.followup_result is not None for result in results
        ),
        "recent_posts": sum(len(result.recent_posts) for result in results),
        "web_followups": sum(
            result.web_result is not None for result in results
        ),
        "web_search_actions": sum(
            len(result.web_result.actions)
            for result in results
            if result.web_result is not None
        ),
        "web_sources": sum(
            len(result.web_result.sources)
            for result in results
            if result.web_result is not None
        ),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "reported_cost_usd": reported_cost_usd,
        "reported_cost_count": len(reported_costs),
        "persisted": len(results) if persist else 0,
        "rejections_persisted": len(rejections) if persist else 0,
        "promoted": len(results) if promote else 0,
        "items": [
            {
                "entity_id": result.entity.entity_id,
                "handle": result.entity.handle,
                "profile": _post_turn_record(
                    "profile",
                    result.profile_result,
                ),
                "followup": (
                    _post_turn_record("recent_posts", result.followup_result)
                    if result.followup_result is not None
                    else None
                ),
                "web": (
                    {
                        **_post_turn_record(
                            "web_search",
                            result.web_result.result,
                        ),
                        "actions": result.web_result.actions,
                        "sources": result.web_result.sources,
                    }
                    if result.web_result is not None
                    else None
                ),
                "classification": result.final_result.classification,
                "reason": result.final_result.reason,
                "recent_post_count": len(result.recent_posts),
                "evidence_sha256": result.evidence_sha256,
            }
            for result in results
        ],
        "rejections": [
            {
                "entity_id": rejection.entity.entity_id,
                "handle": rejection.entity.handle,
                "reason_code": rejection.reason_code,
                "reason": rejection.reason,
                "source": rejection.source,
                "evidence_url": rejection.evidence_url,
            }
            for rejection in rejections
        ],
        "errors": [
            {
                "entity_id": error.entity.entity_id,
                "handle": error.entity.handle,
                "type": error.error_type,
                "message": error.error_message,
            }
            for error in errors
        ],
        "status": status,
    }


def _latest_entity_classification(
    conn: sqlite3.Connection,
    *,
    entity_id: int,
    prompt_version: str | None = None,
) -> sqlite3.Row | None:
    prompt_clause = "AND prompt_version = ?" if prompt_version else ""
    params: tuple[Any, ...] = (
        (entity_id, prompt_version)
        if prompt_version
        else (entity_id,)
    )
    return conn.execute(
        f"""SELECT * FROM entity_kind_classifications
            WHERE entity_id = ? {prompt_clause}
            ORDER BY classified_at DESC, run_id DESC
            LIMIT 1""",
        params,
    ).fetchone()


def run_x_account_lifecycle(
    conn: sqlite3.Connection,
    *,
    handle: str,
    client: Any,
    post_client: Any,
    model: str = DEFAULT_MODEL,
    reasoning_effort_override: str | None = None,
    pricing: tuple[float, float] | None = None,
    post_limit: int = DEFAULT_POST_LIMIT,
    min_followers: int = DEFAULT_MIN_FOLLOWERS,
    force: bool = False,
) -> dict[str, Any]:
    """Run one X handle through the complete, idempotent Registry lifecycle."""
    if min_followers < 0:
        raise ValueError("min_followers must be non-negative")
    normalized = sources.normalize_x_handle(handle)
    profile = post_client.fetch_user(username=normalized)
    followers_count = sources.profile_followers_count(profile)
    if followers_count is None:
        raise sources.SourceCliError(
            code="E_FOLLOWER_COUNT_MISSING",
            message=f"@{normalized} profile has no follower count.",
            hint="Do not admit the account until the eligibility floor can be checked.",
            exit_code=4,
            retryable=False,
        )
    if followers_count < min_followers:
        return {
            "status": "completed",
            "outcome": "rejected",
            "stage": "follower_floor",
            "handle": normalized,
            "followers_count": followers_count,
            "min_followers": min_followers,
            "persisted": False,
            "reason_code": "below_follower_floor",
            "reason": (
                f"The X account has {followers_count:,} followers, below the "
                f"current {min_followers:,}-follower floor."
            ),
        }

    materialized = sources.persist_x_profile(conn, profile=profile)
    entity_id = int(materialized["entity_id"])
    entity = read_entity_input(conn, entity_id=entity_id)
    if sources.is_protected_profile(profile):
        registry.reject_entity(
            conn,
            entity_id=entity_id,
            reason_code=PROTECTED_ACCOUNT_REASON_CODE,
            reason=PROTECTED_ACCOUNT_REASON,
            source=sources.PROVIDER,
            evidence_url=entity.profile_url,
        )
        conn.commit()
        return {
            "status": "completed",
            "outcome": "rejected",
            "stage": "protected_account",
            "handle": normalized,
            "entity_id": entity_id,
            "followers_count": followers_count,
            "persisted": True,
            "reason_code": PROTECTED_ACCOUNT_REASON_CODE,
            "reason": PROTECTED_ACCOUNT_REASON,
        }

    registry.clear_rejection(conn, entity_id=entity_id)
    conn.commit()
    current_kind = conn.execute(
        "SELECT kind FROM entities WHERE id = ?",
        (entity_id,),
    ).fetchone()[0]
    if current_kind in {"person", "organization"} and not force:
        existing = _latest_entity_classification(conn, entity_id=entity_id)
        return {
            "status": "completed",
            "outcome": "existing",
            "stage": "existing_classification",
            "handle": normalized,
            "entity_id": entity_id,
            "followers_count": followers_count,
            "classification": current_kind,
            "reason": existing["reason"] if existing else None,
            "persisted": True,
            "model_calls": 0,
        }

    workflow = run_post_enrichment(
        conn,
        [entity],
        client=client,
        post_client=post_client,
        model=model,
        workers=1,
        scope="x-account-lifecycle",
        reasoning_effort_override=reasoning_effort_override,
        pricing=pricing,
        post_limit=post_limit,
        persist=True,
        promote=True,
        allow_unknown=True,
        profiles={entity_id: profile},
        force=force,
    )
    if workflow["failed"]:
        return {
            "status": "partial",
            "outcome": "failed",
            "stage": "classification",
            "handle": normalized,
            "entity_id": entity_id,
            "followers_count": followers_count,
            "workflow": workflow,
        }
    item = workflow["items"][0] if workflow["items"] else None
    if item is None:
        existing = _latest_entity_classification(
            conn,
            entity_id=entity_id,
            prompt_version=PROMPT_VERSION,
        )
        if existing is None:
            raise RuntimeError(
                f"@{normalized} was skipped without a stored {PROMPT_VERSION} result"
            )
        return {
            "status": "completed",
            "outcome": "existing",
            "stage": "resume",
            "handle": normalized,
            "entity_id": entity_id,
            "followers_count": followers_count,
            "classification": existing["classification"],
            "reason": existing["reason"],
            "persisted": True,
            "model_calls": 0,
        }
    final_stage = "web_search" if item["web"] else (
        "recent_posts" if item["followup"] else "profile"
    )
    return {
        "status": "completed",
        "outcome": "classified",
        "stage": final_stage,
        "handle": normalized,
        "entity_id": entity_id,
        "followers_count": followers_count,
        "classification": item["classification"],
        "reason": item["reason"],
        "persisted": True,
        "workflow": workflow,
    }


def promote_classifications(
    conn: sqlite3.Connection,
    *,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str | None = None,
    prompt_version: str = PROMPT_VERSION,
) -> dict[str, Any]:
    """Atomically promote accepted results into canonical entity kinds.

    Only current ``unknown`` entities are eligible. Every eligible entity must
    have a result for its current identity input and the exact accepted
    model/effort/prompt contract, otherwise nothing is changed.
    """
    ensure_schema(conn)
    effort = reasoning_effort or default_reasoning_effort(model)
    inputs = read_unknown_inputs(conn)
    decisions: list[tuple[str, str, int]] = []
    missing: list[int] = []
    promoted_at = _now()
    for entity in inputs:
        row = conn.execute(
            """SELECT classification
               FROM entity_kind_classifications
               WHERE entity_id = ? AND input_sha256 = ?
                 AND model = ? AND reasoning_effort = ?
                 AND prompt_version = ?
               ORDER BY classified_at DESC, run_id DESC
               LIMIT 1""",
            (
                entity.entity_id,
                entity.input_sha256,
                model,
                effort,
                prompt_version,
            ),
        ).fetchone()
        if row is None:
            missing.append(entity.entity_id)
            continue
        decisions.append((row["classification"], promoted_at, entity.entity_id))
    if missing:
        preview = ", ".join(str(entity_id) for entity_id in missing[:10])
        raise RuntimeError(
            f"cannot promote: {len(missing)} unknown entities lack an accepted "
            f"classification for their current input (first IDs: {preview})"
        )

    with conn:
        conn.executemany(
            """UPDATE entities SET kind = ?, updated_at = ?
               WHERE id = ? AND kind = 'unknown'""",
            decisions,
        )
    counts = {
        row["kind"]: row["n"]
        for row in conn.execute(
            "SELECT kind, COUNT(*) AS n FROM entities GROUP BY kind"
        ).fetchall()
    }
    return {
        "promoted": len(decisions),
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": prompt_version,
        "counts": counts,
    }


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[], Any] = create_litellm_client,
    post_client_factory: Callable[[], Any] = sources.create_twitterapi_io_client,
) -> int:
    parser = argparse.ArgumentParser(prog="fli entity-kinds")
    parser.add_argument(
        "action",
        choices=["run", "enrich", "onboard", "summary", "promote"],
    )
    parser.add_argument("--db", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--handle")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--post-limit", type=int, default=DEFAULT_POST_LIMIT)
    parser.add_argument("--min-followers", type=int, default=DEFAULT_MIN_FOLLOWERS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high", "xhigh", "max"],
    )
    args = parser.parse_args(argv)

    conn = connect(args.db) if args.db else connect()
    if args.action == "onboard":
        if not args.handle:
            parser.error("onboard requires --handle")
        summary = run_x_account_lifecycle(
            conn,
            handle=args.handle,
            client=client_factory(),
            post_client=post_client_factory(),
            model=args.model,
            reasoning_effort_override=args.reasoning_effort,
            post_limit=args.post_limit,
            min_followers=args.min_followers,
            force=args.force,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0 if summary["status"] == "completed" else 1
    if args.action == "promote":
        summary = promote_classifications(
            conn,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0
    if args.action == "summary":
        unknown_inputs = read_unknown_inputs(conn)
        unsure_inputs = read_unsure_inputs(conn)
        row = conn.execute(
            """SELECT COUNT(*) AS classified,
                      COALESCE(SUM(estimated_cost_usd), 0) AS cost
               FROM entity_kind_classifications"""
        ).fetchone()
        print(
            json.dumps(
                {
                    "unknown_inputs": len(unknown_inputs),
                    "unsure_inputs": len(unsure_inputs),
                    "stored_classifications": row["classified"],
                    "estimated_cost_usd": row["cost"],
                },
                sort_keys=True,
            )
        )
        return 0

    inputs = (
        read_unsure_inputs(conn)
        if args.action == "enrich"
        else read_unknown_inputs(conn)
    )
    selected = inputs
    scope_prefix = "posts" if args.action == "enrich" else "profile"
    scope = f"{scope_prefix}-full" if args.limit is None else f"{scope_prefix}-limited"
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be at least 1")
        selected = selected[: args.limit]
    if args.action == "enrich":
        summary = run_post_enrichment(
            conn,
            selected,
            client=client_factory(),
            post_client=post_client_factory(),
            model=args.model,
            workers=args.workers or DEFAULT_POST_WORKERS,
            scope=scope,
            reasoning_effort_override=args.reasoning_effort,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0 if summary["failed"] == 0 else 1
    summary = run_classification(
        conn,
        selected,
        client=client_factory(),
        model=args.model,
        workers=args.workers or DEFAULT_WORKERS,
        scope=scope,
        reasoning_effort_override=args.reasoning_effort,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
