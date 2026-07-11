"""Web-grounded Registry relevance audit with no canonical mutation path."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fli import entity_kinds, llm_responses

PROMPT_VERSION = "registry-relevance-v1"
SCHEMA_VERSION = "registry-relevance-output-v1"
DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_WORKERS = 8
PROMPT_CACHE_SHARDS = 64
PROMPT_PATH = Path(__file__).with_name("prompts") / "registry_relevance_v1.txt"

DECISIONS = frozenset({"keep", "remove", "review"})
RELEVANCE_BASES = frozenset(
    {
        "lab_activity",
        "frontier_research",
        "evaluation_and_safety",
        "ai_native_technology",
        "specialist_intelligence",
        "out_of_scope",
        "uncertain",
    }
)
AUDIENCES = frozenset({"ai_team", "investment_team", "both", "neither"})
CONFIDENCES = frozenset({"high", "medium", "low"})

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "registry_relevance_audit",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "entity_id": {"type": "integer"},
            "decision": {"type": "string", "enum": sorted(DECISIONS)},
            "relevance_basis": {
                "type": "string",
                "enum": sorted(RELEVANCE_BASES),
            },
            "audience": {"type": "string", "enum": sorted(AUDIENCES)},
            "reason": {"type": "string"},
            "current_connection": {"type": "string"},
            "confidence": {"type": "string", "enum": sorted(CONFIDENCES)},
            "evidence_urls": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 5,
            },
        },
        "required": [
            "entity_id",
            "decision",
            "relevance_basis",
            "audience",
            "reason",
            "current_connection",
            "confidence",
            "evidence_urls",
        ],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class RelevanceInput:
    entity_id: int
    structural_kind: str
    name: str
    slug: str
    is_curated_lab: bool
    channels: tuple[dict[str, Any], ...]

    @property
    def model_payload(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "structural_kind": self.structural_kind,
            "name": self.name,
            "slug": self.slug,
            "is_curated_lab": self.is_curated_lab,
            "channels": list(self.channels),
        }

    @property
    def input_sha256(self) -> str:
        payload = json.dumps(
            self.model_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def instructions() -> str:
    return PROMPT_PATH.read_text().strip()


def prompt_cache_key(entity_id: int) -> str:
    """Route repeated prompt prefixes without overloading one cache key."""
    digest = hashlib.sha256(str(entity_id).encode()).digest()
    shard = int.from_bytes(digest[:8], "big") % PROMPT_CACHE_SHARDS
    return f"fli:registry-relevance:{PROMPT_VERSION}:shard-{shard:02d}"


def read_active_inputs(conn: sqlite3.Connection) -> list[RelevanceInput]:
    """Return active people/organizations without follower-count evidence."""
    entity_kinds.ensure_schema(conn)
    entities = conn.execute(
        """SELECT e.id, e.kind, e.name, e.slug,
                  EXISTS (SELECT 1 FROM labs l WHERE l.slug = e.slug)
                      AS is_curated_lab
           FROM entities e
           WHERE e.kind IN ('person', 'organization')
             AND NOT EXISTS (
                 SELECT 1 FROM entity_registry_rejections r
                 WHERE r.entity_id = e.id
             )
           ORDER BY e.id"""
    ).fetchall()
    results: list[RelevanceInput] = []
    for entity in entities:
        channel_rows = conn.execute(
            """SELECT c.kind, c.key, c.label, c.url, ec.relationship,
                      a.display_name, a.bio
               FROM entity_channels ec
               JOIN channels c ON c.id = ec.channel_id
               LEFT JOIN accounts a
                 ON c.kind = 'x' AND a.platform = 'x'
                AND lower(a.handle) = lower(c.key)
               WHERE ec.entity_id = ?
               ORDER BY c.kind, c.key""",
            (entity["id"],),
        ).fetchall()
        channels = tuple(
            {
                key: row[key]
                for key in (
                    "kind",
                    "key",
                    "label",
                    "url",
                    "relationship",
                    "display_name",
                    "bio",
                )
                if row[key] is not None
            }
            for row in channel_rows
        )
        results.append(
            RelevanceInput(
                entity_id=entity["id"],
                structural_kind=entity["kind"],
                name=entity["name"],
                slug=entity["slug"],
                is_curated_lab=bool(entity["is_curated_lab"]),
                channels=channels,
            )
        )
    return results


def _usage_value(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(field) or 0)
    return int(getattr(usage, field, 0) or 0)


def _validate_output(output_text: str, entity_id: int) -> dict[str, Any]:
    payload = json.loads(output_text)
    required = set(OUTPUT_FORMAT["schema"]["required"])
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("response does not match the exact relevance schema")
    if payload["entity_id"] != entity_id:
        raise ValueError("response entity_id does not match input")
    decision = payload["decision"]
    basis = payload["relevance_basis"]
    audience = payload["audience"]
    if decision == "keep" and (
        basis in {"out_of_scope", "uncertain"} or audience == "neither"
    ):
        raise ValueError("keep decision has inconsistent basis or audience")
    if decision == "remove" and (basis != "out_of_scope" or audience != "neither"):
        raise ValueError("remove decision must be out_of_scope / neither")
    if decision == "review" and (basis != "uncertain" or audience != "neither"):
        raise ValueError("review decision must be uncertain / neither")
    if not payload["reason"].strip() or not payload["current_connection"].strip():
        raise ValueError("reason and current_connection must be non-empty")
    if not all(url.startswith("https://") for url in payload["evidence_urls"]):
        raise ValueError("evidence URLs must use https")
    return payload


def request_tags(*, run: str) -> tuple[str, ...]:
    return (
        "app:frontier-lab-intelligence",
        "pipeline:registry-relevance-audit",
        "job:web-grounded-relevance",
        "scope:single-entity",
        f"prompt:{PROMPT_VERSION}",
        f"run:{run}",
    )


def _load_checkpoint(
    path: Path,
    *,
    by_id: dict[int, RelevanceInput],
    model: str,
    effort: str,
) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    """Load valid completed results and the latest unresolved errors."""
    results: dict[int, dict[str, Any]] = {}
    errors: dict[int, dict[str, Any]] = {}
    if not path.exists():
        return results, errors
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid checkpoint JSON at {path}:{line_number}"
            ) from exc
        record_type = record.get("type")
        item = record.get("item")
        if not isinstance(item, dict) or not isinstance(item.get("entity_id"), int):
            raise ValueError(f"invalid checkpoint record at {path}:{line_number}")
        entity_id = item["entity_id"]
        entity = by_id.get(entity_id)
        if entity is None:
            continue
        if record_type == "result":
            if (
                item.get("input_sha256") == entity.input_sha256
                and item.get("model") == model
                and item.get("reasoning_effort") == effort
                and item.get("prompt_version") == PROMPT_VERSION
            ):
                results[entity_id] = item
                errors.pop(entity_id, None)
        elif record_type == "error" and entity_id not in results:
            errors[entity_id] = item
        else:
            raise ValueError(f"invalid checkpoint record type at {path}:{line_number}")
    return results, errors


def _append_checkpoint(stream: Any, record_type: str, item: dict[str, Any]) -> None:
    stream.write(
        json.dumps({"type": record_type, "item": item}, ensure_ascii=False)
        + "\n"
    )
    stream.flush()
    os.fsync(stream.fileno())


def audit_one(
    client: Any,
    entity: RelevanceInput,
    *,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_REASONING_EFFORT,
    run: str,
) -> dict[str, Any]:
    tags = request_tags(run=run)
    request = {
        "model": model,
        "instructions": instructions(),
        "input": json.dumps(entity.model_payload, ensure_ascii=False),
        "prompt_cache_key": prompt_cache_key(entity.entity_id),
        "tools": [
            {
                "type": "web_search",
                "search_context_size": "high",
                "return_token_budget": "unlimited",
            }
        ],
        "tool_choice": llm_responses.required_web_search_tool_choice(model),
        "include": ["web_search_call.action.sources"],
        "reasoning": {"effort": effort},
        "text": {"format": OUTPUT_FORMAT},
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }
    raw_api = getattr(client.responses, "with_raw_response", None)
    if raw_api is None:
        response = client.responses.create(**request)
        reported_cost = None
    else:
        raw_response = raw_api.create(**request)
        response = raw_response.parse()
        reported_cost = entity_kinds._reported_cost(raw_response.headers)
    response_data = llm_responses.as_dict(response)
    if response_data.get("status") not in (None, "completed"):
        raise ValueError(
            f"response status was {response_data.get('status')!r}: "
            f"{response_data.get('incomplete_details')!r}"
        )
    payload = _validate_output(
        llm_responses.output_text(response_data), entity.entity_id
    )
    actions, sources = llm_responses.web_evidence(
        response_data, cited_urls=payload["evidence_urls"]
    )
    usage = getattr(response, "usage", None) or response_data.get("usage")
    return {
        **payload,
        "entity_name": entity.name,
        "structural_kind": entity.structural_kind,
        "is_curated_lab": entity.is_curated_lab,
        "input_sha256": entity.input_sha256,
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "response_id": getattr(response, "id", None) or response_data.get("id"),
        "response_model": getattr(response, "model", None)
        or response_data.get("model"),
        "input_tokens": _usage_value(usage, "input_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
        "reported_cost_usd": reported_cost,
        "web_actions": actions,
        "consulted_sources": sources,
        "request_tags": list(tags),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli relevance-audit")
    parser.add_argument("action", choices=["run"])
    parser.add_argument("--db", default=None)
    parser.add_argument("--entity-id", type=int, action="append", default=[])
    parser.add_argument("--exclude-entity-id", type=int, action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args(argv)
    if args.all == bool(args.entity_id):
        parser.error("choose exactly one of --all or one/more --entity-id")
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    conn = entity_kinds.connect(args.db) if args.db else entity_kinds.connect()
    inputs = read_active_inputs(conn)
    by_id = {entity.entity_id: entity for entity in inputs}
    if args.all:
        excluded = set(args.exclude_entity_id)
        selected = [entity for entity in inputs if entity.entity_id not in excluded]
    else:
        if args.exclude_entity_id:
            parser.error("--exclude-entity-id requires --all")
        missing = [entity_id for entity_id in args.entity_id if entity_id not in by_id]
        if missing:
            parser.error(f"unknown or inactive entity IDs: {missing}")
        selected = [by_id[entity_id] for entity_id in args.entity_id]
    checkpoint = args.checkpoint or args.output.with_suffix(
        args.output.suffix + ".partial.jsonl"
    )
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    completed_by_id, prior_errors = _load_checkpoint(
        checkpoint,
        by_id=by_id,
        model=args.model,
        effort=args.reasoning_effort,
    )
    selected_ids = {entity.entity_id for entity in selected}
    completed_by_id = {
        entity_id: result
        for entity_id, result in completed_by_id.items()
        if entity_id in selected_ids
    }
    pending = [
        entity for entity in selected if entity.entity_id not in completed_by_id
    ]
    client = entity_kinds.create_litellm_client()
    latest_errors = {
        entity_id: error
        for entity_id, error in prior_errors.items()
        if entity_id in selected_ids and entity_id not in completed_by_id
    }
    with checkpoint.open("a", encoding="utf-8") as checkpoint_stream:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_entity = {
                executor.submit(
                    audit_one,
                    client,
                    entity,
                    model=args.model,
                    effort=args.reasoning_effort,
                    run=args.run,
                ): entity
                for entity in pending
            }
            for completed_count, future in enumerate(
                concurrent.futures.as_completed(future_to_entity), start=1
            ):
                entity = future_to_entity[future]
                try:
                    result = future.result()
                    completed_by_id[entity.entity_id] = result
                    latest_errors.pop(entity.entity_id, None)
                    _append_checkpoint(checkpoint_stream, "result", result)
                except Exception as exc:  # preserve per-identity failures
                    error = {
                        "entity_id": entity.entity_id,
                        "entity_name": entity.name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                    latest_errors[entity.entity_id] = error
                    _append_checkpoint(checkpoint_stream, "error", error)
                if completed_count % 25 == 0 or completed_count == len(pending):
                    print(
                        json.dumps(
                            {
                                "progress": completed_count,
                                "pending_at_start": len(pending),
                                "stored_total": len(completed_by_id),
                                "errors": len(latest_errors),
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
    results = sorted(completed_by_id.values(), key=lambda item: item["entity_id"])
    errors = sorted(latest_errors.values(), key=lambda item: item["entity_id"])
    artifact = {
        "run": args.run,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "prompt_version": PROMPT_VERSION,
        "requested": len(selected),
        "completed": len(results),
        "failed": len(errors),
        "reported_cost_usd": sum(
            result["reported_cost_usd"] or 0 for result in results
        ),
        "results": results,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: artifact[key] for key in (
        "run", "requested", "completed", "failed", "reported_cost_usd"
    )}, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
