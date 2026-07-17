"""Provider-backed retrieval of verbatim X Article bodies.

X Article URLs are catalog identities, but TwitterAPI.io retrieves an article
by the ID of its publishing post.  The artifact catalog preserves that mapping
from the source envelope.  This adapter fails closed when the mapping is absent
or ambiguous and never promotes title or preview metadata into body evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

import httpx

from fli.evidence.artifacts import fetch as artifact_fetch
from fli.evidence.artifacts import store as artifacts
from fli.ingestion import sources


FETCH_POLICY = "twitterapi-io-x-article-v1"
SELECTION_POLICY = "x-article-catalog-v1"
ENDPOINT = f"{sources.TWITTERAPI_IO_BASE_URL}/twitter/article"
EXTRACTOR_CONTRACT = "twitterapi-io-x-article-body-v1"
EXTRACTOR_VERSION = "1"
PROVIDER_CREDITS_PER_REQUEST = 100
ARTICLE_PATH = re.compile(r"^/i/article/(?P<article_id>\d+)/?$", re.IGNORECASE)
ARTIFACT_ID = re.compile(r"^[0-9a-f]{64}$")
PROVENANCE_SCHEMA_VERSION = "x-article-provider-provenance-v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _article_identity(url: str) -> tuple[str, str] | None:
    match = ARTICLE_PATH.match(urlsplit(url).path)
    if match is None:
        return None
    article_id = match.group("article_id")
    return article_id, f"https://x.com/i/article/{article_id}"


def _normalized_body(contents: list[Any]) -> str | None:
    """Return body-block text in provider order, excluding all preview fields."""
    blocks: list[str] = []
    for content in contents:
        if not isinstance(content, dict) or not isinstance(content.get("text"), str):
            continue
        value = unicodedata.normalize(
            "NFC", content["text"].replace("\r\n", "\n").replace("\r", "\n")
        )
        value = "\n".join(line.rstrip() for line in value.split("\n")).strip()
        if value:
            blocks.append(value)
    if not blocks:
        return None
    return "\n\n".join(blocks) + "\n"


def _validated_artifact_ids(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip().lower()
        if ARTIFACT_ID.fullmatch(value) is None:
            raise ValueError(
                f"artifact_id must be a 64-character hexadecimal digest: {raw!r}"
            )
        if value in seen:
            raise ValueError(f"artifact_id was provided more than once: {value}")
        seen.add(value)
        normalized.append(value)
    return tuple(sorted(normalized))


def _selection_rows(
    conn: Any,
    *,
    limit: int | None,
    artifact_ids: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT artifact.artifact_id, artifact.canonical_url,
                  candidate.source_external_id, candidate.envelope_day,
                  candidate.event_id AS source_event_id, candidate.source_rank,
                  candidate.day_candidate_count, candidate.relation,
                  candidate.decision
           FROM artifact
           LEFT JOIN artifact_import_candidate candidate
             ON candidate.artifact_id = artifact.artifact_id
            AND candidate.decision = 'accepted'
           WHERE lower(artifact.host) IN (
                     'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'
                 )
             AND lower(artifact.canonical_url) LIKE '%/i/article/%'
           ORDER BY artifact.canonical_url, candidate.source_rank,
                    candidate.event_id, candidate.source_external_id"""
    ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        artifact_id = str(row["artifact_id"])
        item = grouped.setdefault(
            artifact_id,
            {
                "artifact_id": artifact_id,
                "canonical_url": str(row["canonical_url"]),
                "mappings": set(),
                "source_day": None,
                "source_rank": None,
                "normalized_rank": None,
                "source_event_id": None,
                "source_key": None,
            },
        )
        if row["source_event_id"] is not None:
            source_rank = int(row["source_rank"])
            normalized_rank = (source_rank - 1) / max(
                int(row["day_candidate_count"]) - 1, 1
            )
            source_key = (
                normalized_rank,
                source_rank,
                str(row["source_event_id"]),
            )
            if item["source_key"] is None or source_key < item["source_key"]:
                item["source_day"] = str(row["envelope_day"])
                item["source_rank"] = source_rank
                item["normalized_rank"] = normalized_rank
                item["source_event_id"] = str(row["source_event_id"])
                item["source_key"] = source_key
        if row["relation"] == "self_publishes" and row["source_external_id"]:
            item["mappings"].add(str(row["source_external_id"]))

    selection: list[dict[str, Any]] = []
    for item in grouped.values():
        item.pop("source_key")
        identity = _article_identity(item["canonical_url"])
        if identity is None:
            # The catalog query is intentionally broad enough to surface a bad
            # X Article URL as a durable terminal state rather than hide it.
            article_id = hashlib.sha256(item["canonical_url"].encode()).hexdigest()
            canonical_article_url = item["canonical_url"]
            mapping_error = "x_article_identity_invalid"
        else:
            article_id, canonical_article_url = identity
            mapping_error = None
        mappings = sorted(item.pop("mappings"))
        request_post_id = mappings[0] if len(mappings) == 1 else None
        if mapping_error is None and not mappings:
            mapping_error = "x_article_post_id_missing"
        elif mapping_error is None and len(mappings) > 1:
            mapping_error = "x_article_post_id_ambiguous"
        elif mapping_error is None and not str(request_post_id).isdigit():
            mapping_error = "x_article_post_id_invalid"
            request_post_id = None
        item.update(
            {
                "request_post_id": request_post_id,
                "canonical_article_id": article_id,
                "canonical_article_url": canonical_article_url,
                "mapping_error": mapping_error,
                "source_day": item["source_day"] or "unknown",
                "source_rank": item["source_rank"] or 2_147_483_647,
                "normalized_rank": (
                    item["normalized_rank"]
                    if item["normalized_rank"] is not None
                    else 1.0
                ),
                "source_event_id": item["source_event_id"]
                or f"missing:{item['artifact_id']}",
            }
        )
        selection.append(item)
    selection.sort(
        key=lambda item: (
            item["normalized_rank"],
            item["source_rank"],
            item["canonical_article_url"],
        )
    )
    if artifact_ids is not None:
        requested = set(artifact_ids)
        found = {item["artifact_id"] for item in selection}
        missing = sorted(requested - found)
        if missing:
            raise ValueError(
                "artifact_id is not a catalogued X Article: " + ", ".join(missing)
            )
        selection = [item for item in selection if item["artifact_id"] in requested]
    elif limit is not None:
        selection = selection[:limit]
    for rank, item in enumerate(selection, 1):
        item["selection_rank"] = rank
    return selection


def _provenance_snapshot(
    reference: Any,
    digest: Any,
    *,
    label: str,
) -> tuple[str | None, str | None, bytes | None]:
    """Read and hash one immutable snapshot without mutating catalog state."""
    if reference is None and digest is None:
        return None, None, None
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError(f"{label} snapshot reference is missing")
    if not isinstance(digest, str) or ARTIFACT_ID.fullmatch(digest) is None:
        raise ValueError(f"{label} snapshot SHA-256 is invalid")
    path = Path(reference)
    if not path.is_absolute():
        path = artifacts.REPO_ROOT / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"{label} snapshot does not exist: {path}")
    body = path.read_bytes()
    if _sha256_bytes(body) != digest:
        raise ValueError(f"{label} snapshot hash drift")
    return reference, digest, body


def _require_binding(
    row: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    drift = [field for field, value in expected.items() if row[field] != value]
    if drift:
        raise ValueError(f"{label} binding drift: {', '.join(drift)}")


def _validate_response_projection(
    row: Mapping[str, Any],
    *,
    label: str,
    raw: bytes | None,
    text: bytes | None,
) -> None:
    """Bind response-derived columns to the exact raw and text snapshots."""
    status = str(row["status"])
    if status == "in_progress":
        if row["completed_at"] is not None:
            raise ValueError(f"{label} in-progress attempt is marked complete")
        if any(
            row[field] is not None
            for field in (
                "error_code",
                "error_message",
                "retryable",
                "provider_status",
                "provider_message",
                "response_fetched_at",
                "content_block_count",
                "content_blocks_json",
                "content_blocks_sha256",
            )
        ):
            raise ValueError(f"{label} in-progress attempt has terminal metadata")
        return

    if row["completed_at"] is None:
        raise ValueError(f"{label} terminal attempt lacks completed_at")
    expected_retryable = int(status == "failed_retryable")
    if row["retryable"] != expected_retryable:
        raise ValueError(f"{label} retryable flag does not match status")
    if status == "success":
        if row["error_code"] is not None or row["error_message"] is not None:
            raise ValueError(f"{label} successful attempt has error metadata")
    elif not row["error_code"] or not row["error_message"]:
        raise ValueError(f"{label} failed attempt lacks explicit error metadata")

    if raw is None:
        if text is not None:
            raise ValueError(f"{label} has text without a raw response")
        if any(
            row[field] is not None
            for field in (
                "provider_status",
                "provider_message",
                "response_fetched_at",
                "content_block_count",
                "content_blocks_json",
                "content_blocks_sha256",
            )
        ):
            raise ValueError(f"{label} has provider response data without a snapshot")
        return

    if row["http_status"] is None:
        raise ValueError(f"{label} raw response lacks an HTTP status")
    if row["response_fetched_at"] is None:
        raise ValueError(f"{label} raw response lacks provider fetch time")
    response = httpx.Response(int(row["http_status"]), content=raw)
    (
        expected_status,
        provider_status,
        provider_message,
        title,
        contents,
        normalized_text,
        error_code,
        error_message,
    ) = _response_outcome(response)
    expected_blocks_json = _canonical_json(contents) if contents is not None else None
    expected_blocks_sha256 = (
        _sha256_bytes(expected_blocks_json.encode())
        if expected_blocks_json is not None
        else None
    )
    expected_block_count = len(contents) if contents is not None else None
    _require_binding(
        row,
        {
            "status": expected_status,
            "provider_status": provider_status,
            "provider_message": provider_message,
            "extracted_title": title,
            "content_block_count": expected_block_count,
            "content_blocks_json": expected_blocks_json,
            "content_blocks_sha256": expected_blocks_sha256,
            "error_code": error_code,
            "error_message": error_message,
        },
        label=label,
    )
    if normalized_text is None:
        if text is not None:
            raise ValueError(f"{label} has text for a response without a body")
    else:
        if text is None or text.decode("utf-8") != normalized_text:
            raise ValueError(f"{label} text snapshot does not match provider blocks")


def validate_x_article_provenance(
    *,
    db_path: Path | str = artifacts.DEFAULT_DB,
    artifact_ids: Iterable[str],
) -> dict[str, Any]:
    """Return an exact read-only provider binding for catalogued X Articles.

    The returned projection is deterministic and JSON-safe.  It binds the
    current catalog mapping to every stored fetch/provider attempt and proves
    that response-derived status, errors, content blocks, and snapshots still
    match the raw provider response.  The function never creates or resumes a
    fetch and is therefore safe for production reconciliation.
    """
    selected_ids = _validated_artifact_ids(tuple(artifact_ids))
    if not selected_ids:
        raise ValueError("artifact_ids must contain at least one X Article")
    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        selection = _selection_rows(
            conn,
            limit=None,
            artifact_ids=selected_ids,
        )
        items: list[dict[str, Any]] = []
        for selected in sorted(selection, key=lambda item: item["artifact_id"]):
            artifact_id = str(selected["artifact_id"])
            attempts = conn.execute(
                """SELECT fetch.fetch_id, fetch.fetch_run_id,
                          fetch.artifact_id AS fetch_artifact_id,
                          fetch.fetch_policy, fetch.requested_url,
                          fetch.status, fetch.attempt_number, fetch.started_at,
                          fetch.completed_at, fetch.final_url, fetch.http_status,
                          fetch.content_length, fetch.raw_sha256,
                          fetch.raw_snapshot_ref, fetch.extractor_contract,
                          fetch.extractor_version, fetch.extracted_title,
                          fetch.text_sha256, fetch.text_snapshot_ref,
                          fetch.text_char_count, fetch.text_truncated,
                          fetch.declared_canonical_url, fetch.error_code,
                          fetch.error_message, fetch.retryable,
                          provider.fetch_id AS provider_fetch_id,
                          provider.artifact_id AS provider_artifact_id,
                          provider.provider, provider.endpoint,
                          provider.request_post_id,
                          provider.canonical_article_id,
                          provider.canonical_article_url,
                          provider.request_made,
                          provider.estimated_provider_credits,
                          provider.provider_status, provider.provider_message,
                          provider.response_fetched_at,
                          provider.content_block_count,
                          provider.content_blocks_json,
                          provider.content_blocks_sha256,
                          provider.created_at AS provider_created_at
                   FROM artifact_fetch AS fetch
                   LEFT JOIN artifact_x_article_fetch AS provider
                     ON provider.fetch_id = fetch.fetch_id
                   WHERE fetch.artifact_id = ? AND fetch.fetch_policy = ?
                   ORDER BY fetch.attempt_number, fetch.fetch_id""",
                (artifact_id, FETCH_POLICY),
            ).fetchall()
            orphan_count = int(
                conn.execute(
                    """SELECT COUNT(*)
                       FROM artifact_x_article_fetch AS provider
                       LEFT JOIN artifact_fetch AS fetch
                         ON fetch.fetch_id = provider.fetch_id
                       WHERE provider.artifact_id = ?
                         AND (fetch.fetch_id IS NULL OR fetch.fetch_policy != ?)""",
                    (artifact_id, FETCH_POLICY),
                ).fetchone()[0]
            )
            if orphan_count:
                raise ValueError(
                    f"X Article {artifact_id} has provider rows outside {FETCH_POLICY}"
                )
            numbers = [int(row["attempt_number"]) for row in attempts]
            if numbers != list(range(1, len(attempts) + 1)):
                raise ValueError(
                    f"X Article {artifact_id} attempt numbers are not contiguous"
                )

            attempt_projection: list[dict[str, Any]] = []
            expected_request_made = int(selected["mapping_error"] is None)
            expected_credits = (
                PROVIDER_CREDITS_PER_REQUEST if expected_request_made else 0
            )
            for row_value in attempts:
                row = dict(row_value)
                label = f"X Article {artifact_id} attempt {row['attempt_number']}"
                if row["provider_fetch_id"] is None:
                    raise ValueError(f"{label} lacks provider provenance")
                _require_binding(
                    row,
                    {
                        "fetch_artifact_id": artifact_id,
                        "fetch_policy": FETCH_POLICY,
                        "requested_url": selected["canonical_url"],
                        "provider_fetch_id": row["fetch_id"],
                        "provider_artifact_id": artifact_id,
                        "provider": "twitterapi_io",
                        "endpoint": ENDPOINT,
                        "request_post_id": selected["request_post_id"],
                        "canonical_article_id": selected["canonical_article_id"],
                        "canonical_article_url": selected["canonical_article_url"],
                        "request_made": expected_request_made,
                        "estimated_provider_credits": expected_credits,
                    },
                    label=label,
                )
                raw_ref, raw_sha, raw = _provenance_snapshot(
                    row["raw_snapshot_ref"],
                    row["raw_sha256"],
                    label=f"{label} raw",
                )
                text_ref, text_sha, text = _provenance_snapshot(
                    row["text_snapshot_ref"],
                    row["text_sha256"],
                    label=f"{label} text",
                )
                if raw is not None and row["content_length"] != len(raw):
                    raise ValueError(f"{label} raw content length drift")
                if text is not None and row["text_char_count"] != len(
                    text.decode("utf-8")
                ):
                    raise ValueError(f"{label} text character count drift")
                if raw is not None:
                    _require_binding(
                        row,
                        {
                            "final_url": selected["canonical_article_url"],
                            "declared_canonical_url": selected[
                                "canonical_article_url"
                            ],
                            "extractor_contract": EXTRACTOR_CONTRACT,
                            "extractor_version": EXTRACTOR_VERSION,
                            "text_truncated": 0,
                            "request_made": 1,
                        },
                        label=label,
                    )
                if row["status"] == "success":
                    if raw is None or text is None:
                        raise ValueError(f"{label} success lacks raw or text snapshot")
                if not expected_request_made:
                    _require_binding(
                        row,
                        {
                            "status": "failed_terminal",
                            "error_code": selected["mapping_error"],
                            "retryable": 0,
                        },
                        label=label,
                    )
                    if raw is not None or text is not None:
                        raise ValueError(
                            f"{label} mapping failure has response evidence"
                        )
                _validate_response_projection(
                    row,
                    label=label,
                    raw=raw,
                    text=text,
                )
                attempt_projection.append(
                    {
                        "fetch_id": str(row["fetch_id"]),
                        "fetch_run_id": str(row["fetch_run_id"]),
                        "attempt_number": int(row["attempt_number"]),
                        "status": str(row["status"]),
                        "started_at": str(row["started_at"]),
                        "completed_at": row["completed_at"],
                        "requested_url": str(row["requested_url"]),
                        "final_url": row["final_url"],
                        "http_status": row["http_status"],
                        "raw_sha256": raw_sha,
                        "raw_snapshot_ref": raw_ref,
                        "content_length": row["content_length"],
                        "extractor_contract": row["extractor_contract"],
                        "extractor_version": row["extractor_version"],
                        "extracted_title": row["extracted_title"],
                        "text_sha256": text_sha,
                        "text_snapshot_ref": text_ref,
                        "text_char_count": row["text_char_count"],
                        "text_truncated": row["text_truncated"],
                        "declared_canonical_url": row[
                            "declared_canonical_url"
                        ],
                        "error_code": row["error_code"],
                        "error_message": row["error_message"],
                        "retryable": row["retryable"],
                        "provider": str(row["provider"]),
                        "endpoint": str(row["endpoint"]),
                        "request_post_id": row["request_post_id"],
                        "canonical_article_id": str(row["canonical_article_id"]),
                        "canonical_article_url": str(row["canonical_article_url"]),
                        "request_made": int(row["request_made"]),
                        "estimated_provider_credits": int(
                            row["estimated_provider_credits"]
                        ),
                        "provider_status": row["provider_status"],
                        "provider_message": row["provider_message"],
                        "response_fetched_at": row["response_fetched_at"],
                        "content_block_count": row["content_block_count"],
                        "content_blocks_sha256": row["content_blocks_sha256"],
                        "provider_created_at": str(row["provider_created_at"]),
                    }
                )
            items.append(
                {
                    "artifact_id": artifact_id,
                    "selection_rank": int(selected["selection_rank"]),
                    "canonical_url": str(selected["canonical_url"]),
                    "canonical_article_id": str(selected["canonical_article_id"]),
                    "canonical_article_url": str(
                        selected["canonical_article_url"]
                    ),
                    "request_post_id": selected["request_post_id"],
                    "mapping_error": selected["mapping_error"],
                    "source_day": str(selected["source_day"]),
                    "source_rank": int(selected["source_rank"]),
                    "normalized_rank": float(selected["normalized_rank"]),
                    "source_event_id": str(selected["source_event_id"]),
                    "attempts": attempt_projection,
                }
            )
        digest = _sha256_bytes(_canonical_json(items).encode())
        return {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "artifact_db": str(path),
            "artifact_count": len(items),
            "binding_sha256": digest,
            "items": items,
        }
    finally:
        conn.close()


def _create_run(
    conn: Any, selection: list[dict[str, Any]]
) -> tuple[str | None, bool]:
    if not selection:
        return None, True
    manifest = [
        [
            item["artifact_id"],
            item["canonical_article_id"],
            item["request_post_id"],
            item["mapping_error"],
        ]
        for item in selection
    ]
    fingerprint = hashlib.sha256(_canonical_json(manifest).encode()).hexdigest()
    fetch_run_id = hashlib.sha256(
        _canonical_json([FETCH_POLICY, SELECTION_POLICY, fingerprint]).encode()
    ).hexdigest()
    run_items = [
        (
            fetch_run_id,
            item["artifact_id"],
            item["selection_rank"],
            "x_article",
            item["canonical_url"],
            item["source_day"],
            item["source_rank"],
            item["normalized_rank"],
            item["source_event_id"],
        )
        for item in selection
    ]
    existing = conn.execute(
        "SELECT status FROM artifact_fetch_run WHERE fetch_run_id = ?",
        (fetch_run_id,),
    ).fetchone()
    if existing is not None:
        if artifact_fetch.restore_pruned_run_items(
            conn,
            fetch_run_id=fetch_run_id,
            run_items=run_items,
        ):
            return fetch_run_id, False
        if str(existing["status"]) == "in_progress":
            return fetch_run_id, False
        pending = conn.execute(
            """SELECT 1
               FROM artifact_fetch_run_item item
               WHERE item.fetch_run_id = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM artifact_fetch fetch
                     WHERE fetch.artifact_id = item.artifact_id
                       AND fetch.fetch_policy = ?
                       AND fetch.status IN ('success', 'failed_terminal')
                 )
                 AND COALESCE((
                     SELECT MAX(fetch.attempt_number)
                     FROM artifact_fetch fetch
                     WHERE fetch.artifact_id = item.artifact_id
                       AND fetch.fetch_policy = ?
                 ), 0) < ?
               LIMIT 1""",
            (
                fetch_run_id,
                FETCH_POLICY,
                FETCH_POLICY,
                artifact_fetch.MAX_ATTEMPTS,
            ),
        ).fetchone()
        if pending is None:
            return fetch_run_id, True
        with conn:
            conn.execute(
                """UPDATE artifact_fetch_run
                   SET status = 'in_progress', completed_at = NULL
                   WHERE fetch_run_id = ?""",
                (fetch_run_id,),
            )
        return fetch_run_id, False

    now = artifact_fetch._now()
    with conn:
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                status)
               VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, 'in_progress')""",
            (
                fetch_run_id,
                artifacts.SCHEMA_VERSION,
                FETCH_POLICY,
                SELECTION_POLICY,
                fingerprint,
                len(selection),
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO artifact_fetch_run_item
               (fetch_run_id, artifact_id, selection_rank, stratum,
                selected_url, source_day, source_rank, normalized_rank,
                source_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            run_items,
        )
    return fetch_run_id, False


def _record_request(
    conn: Any,
    *,
    fetch_id: str,
    item: dict[str, Any],
    request_made: bool,
) -> None:
    with conn:
        conn.execute(
            """INSERT INTO artifact_x_article_fetch
               (fetch_id, artifact_id, provider, endpoint, request_post_id,
                canonical_article_id, canonical_article_url, request_made,
                estimated_provider_credits, created_at)
               VALUES (?, ?, 'twitterapi_io', ?, ?, ?, ?, ?, ?, ?)""",
            (
                fetch_id,
                item["artifact_id"],
                ENDPOINT,
                item["request_post_id"],
                item["canonical_article_id"],
                item["canonical_article_url"],
                int(request_made),
                PROVIDER_CREDITS_PER_REQUEST if request_made else 0,
                artifact_fetch._now(),
            ),
        )


def _finish_response(
    conn: Any,
    *,
    fetch_id: str,
    item: dict[str, Any],
    response: httpx.Response,
    status: str,
    provider_status: str | None,
    provider_message: str | None,
    title: str | None = None,
    contents: list[Any] | None = None,
    text: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    now = artifact_fetch._now()
    body = response.content
    raw_sha = _sha256_bytes(body)
    raw_ref = artifact_fetch._write_snapshot(
        artifact_fetch.RAW_ROOT, raw_sha, ".json", body
    )
    text_sha = None
    text_ref = None
    if text is not None:
        text_bytes = text.encode("utf-8")
        text_sha = _sha256_bytes(text_bytes)
        text_ref = artifact_fetch._write_snapshot(
            artifact_fetch.TEXT_ROOT, text_sha, ".txt", text_bytes
        )
    blocks_json = _canonical_json(contents) if contents is not None else None
    blocks_sha = (
        _sha256_bytes(blocks_json.encode("utf-8"))
        if blocks_json is not None
        else None
    )
    retryable = int(status == "failed_retryable")
    headers = {
        **artifact_fetch._safe_headers(response),
        "retrieval-provider": "twitterapi_io",
        "provider-endpoint": ENDPOINT,
        "estimated-provider-credits": str(PROVIDER_CREDITS_PER_REQUEST),
    }
    with conn:
        conn.execute(
            """UPDATE artifact_fetch
               SET status = ?, completed_at = ?, lease_expires_at = NULL,
                   final_url = ?, redirect_chain_json = '[]', http_status = ?,
                   response_headers_json = ?, content_type = 'application/json',
                   charset = 'utf-8', content_length = ?, raw_sha256 = ?,
                   raw_snapshot_ref = ?, extractor_contract = ?,
                   extractor_version = ?, extracted_title = ?, text_sha256 = ?,
                   text_snapshot_ref = ?, text_char_count = ?, text_truncated = 0,
                   declared_canonical_url = ?, error_code = ?, error_message = ?,
                   retryable = ?
               WHERE fetch_id = ? AND status = 'in_progress'""",
            (
                status,
                now,
                item["canonical_article_url"],
                response.status_code,
                _canonical_json(headers),
                len(body),
                raw_sha,
                raw_ref,
                EXTRACTOR_CONTRACT,
                EXTRACTOR_VERSION,
                title,
                text_sha,
                text_ref,
                len(text) if text is not None else None,
                item["canonical_article_url"],
                error_code,
                error_message,
                retryable,
                fetch_id,
            ),
        )
        conn.execute(
            """UPDATE artifact_x_article_fetch
               SET provider_status = ?, provider_message = ?,
                   response_fetched_at = ?, content_block_count = ?,
                   content_blocks_json = ?, content_blocks_sha256 = ?
               WHERE fetch_id = ?""",
            (
                provider_status,
                provider_message,
                now,
                len(contents) if contents is not None else None,
                blocks_json,
                blocks_sha,
                fetch_id,
            ),
        )
        if title:
            conn.execute(
                """UPDATE artifact SET title = ?, title_fetch_id = ?, updated_at = ?
                   WHERE artifact_id = ?""",
                (title, fetch_id, now, item["artifact_id"]),
            )


def _response_outcome(
    response: httpx.Response,
) -> tuple[
    str,
    str | None,
    str | None,
    str | None,
    list[Any] | None,
    str | None,
    str | None,
    str | None,
]:
    if response.status_code in artifact_fetch.RETRYABLE_HTTP:
        code = f"x_article_http_{response.status_code}"
        return (
            "failed_retryable",
            None,
            None,
            None,
            None,
            None,
            code,
            f"TwitterAPI.io returned HTTP {response.status_code}",
        )
    if not 200 <= response.status_code < 300:
        code = f"x_article_http_{response.status_code}"
        return (
            "failed_terminal",
            None,
            None,
            None,
            None,
            None,
            code,
            f"TwitterAPI.io returned HTTP {response.status_code}",
        )
    try:
        payload = response.json()
    except ValueError:
        return (
            "failed_retryable",
            None,
            None,
            None,
            None,
            None,
            "x_article_invalid_json",
            "TwitterAPI.io returned invalid JSON",
        )
    if not isinstance(payload, dict):
        return (
            "failed_terminal",
            None,
            None,
            None,
            None,
            None,
            "x_article_invalid_payload",
            "TwitterAPI.io returned a non-object payload",
        )
    provider_status = str(payload.get("status") or "").strip() or None
    provider_message = str(payload.get("message") or "").strip() or None
    if provider_status != "success":
        return (
            "failed_terminal",
            provider_status,
            provider_message,
            None,
            None,
            None,
            "x_article_provider_failed",
            provider_message or "TwitterAPI.io did not report success",
        )
    article = payload.get("article")
    if not isinstance(article, dict):
        return (
            "failed_terminal",
            provider_status,
            provider_message,
            None,
            None,
            None,
            "x_article_missing",
            "TwitterAPI.io response has no article object",
        )
    title = str(article.get("title") or "").strip() or None
    contents = article.get("contents")
    if not isinstance(contents, list):
        return (
            "failed_terminal",
            provider_status,
            provider_message,
            title,
            None,
            None,
            "x_article_contents_missing",
            "Article response has no ordered contents array",
        )
    text = _normalized_body(contents)
    if text is None:
        return (
            "failed_terminal",
            provider_status,
            provider_message,
            title,
            contents,
            None,
            "x_article_body_missing",
            "Article contents contain no body text; title and preview were not used",
        )
    issue = artifact_fetch.extracted_text_issue(text)
    if issue is not None:
        error_code, error_message = issue
        return (
            "failed_terminal",
            provider_status,
            provider_message,
            title,
            contents,
            None,
            error_code,
            error_message,
        )
    return (
        "success",
        provider_status,
        provider_message,
        title,
        contents,
        text,
        None,
        None,
    )


def _result_telemetry(conn: Any, fetch_run_id: str) -> dict[str, int]:
    row = conn.execute(
        """SELECT COUNT(*) AS request_attempts,
                  COALESCE(SUM(estimated_provider_credits), 0) AS credits
           FROM artifact_x_article_fetch provider
           JOIN artifact_fetch fetch ON fetch.fetch_id = provider.fetch_id
           WHERE fetch.fetch_run_id = ? AND provider.request_made = 1""",
        (fetch_run_id,),
    ).fetchone()
    return {
        "provider_request_attempts": int(row["request_attempts"]),
        "estimated_provider_credits": int(row["credits"]),
    }


def fetch_x_articles(
    *,
    db_path: Path | str = artifacts.DEFAULT_DB,
    limit: int | None = None,
    artifact_ids: list[str] | tuple[str, ...] | None = None,
    api_key: str | None = None,
    key_file: Path = sources.DEFAULT_TWITTERAPI_IO_KEY_FILE,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Fetch a deterministic, resumable X Article catalog cohort."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero")
    if artifact_ids is not None and limit is not None:
        raise ValueError("limit and artifact_ids are mutually exclusive")
    selected_ids = (
        _validated_artifact_ids(artifact_ids) if artifact_ids is not None else None
    )
    conn = artifacts.connect(db_path)
    try:
        selection = _selection_rows(
            conn, limit=limit, artifact_ids=selected_ids
        )
    except Exception:
        conn.close()
        raise
    fetch_run_id, already_complete = _create_run(conn, selection)
    if fetch_run_id is None:
        conn.close()
        return {
            "fetch_run_id": None,
            "expected_count": 0,
            "success": 0,
            "failed_retryable": 0,
            "failed_terminal": 0,
            "provider_request_attempts": 0,
            "estimated_provider_credits": 0,
            "provider_request_attempts_this_call": 0,
            "estimated_provider_credits_this_call": 0,
            "reused": True,
        }
    if already_complete:
        row = conn.execute(
            "SELECT * FROM artifact_fetch_run WHERE fetch_run_id = ?",
            (fetch_run_id,),
        ).fetchone()
        assert row is not None
        result = {
            "fetch_run_id": fetch_run_id,
            "expected_count": int(row["expected_count"]),
            "success": int(row["success_count"]),
            "failed_retryable": int(row["failed_retryable_count"]),
            "failed_terminal": int(row["failed_terminal_count"]),
            **_result_telemetry(conn, fetch_run_id),
            "provider_request_attempts_this_call": 0,
            "estimated_provider_credits_this_call": 0,
            "reused": True,
        }
        conn.close()
        return result

    prior_telemetry = _result_telemetry(conn, fetch_run_id)
    needs_key = any(item["mapping_error"] is None for item in selection)
    resolved_key = api_key
    if needs_key and resolved_key is None:
        try:
            resolved_key = sources._read_api_key(key_file)
        except Exception:
            conn.close()
            raise
    client = httpx.Client(
        trust_env=False,
        timeout=httpx.Timeout(30.0, connect=10.0, read=30.0, write=10.0, pool=10.0),
        headers={"X-API-Key": resolved_key or "", "Accept": "application/json"},
        transport=transport,
    )
    try:
        for item in selection:
            fetch_id = artifact_fetch._claim(
                conn,
                fetch_run_id=fetch_run_id,
                artifact_id=item["artifact_id"],
                requested_url=item["canonical_url"],
                fetch_policy=FETCH_POLICY,
            )
            if fetch_id is None:
                continue
            request_made = item["mapping_error"] is None
            _record_request(
                conn,
                fetch_id=fetch_id,
                item=item,
                request_made=request_made,
            )
            if item["mapping_error"] is not None:
                artifact_fetch._finish_failure(
                    conn,
                    fetch_id,
                    artifact_fetch.FetchFailure(
                        item["mapping_error"],
                        "X Article has no unique publishing-post mapping",
                        retryable=False,
                    ),
                )
                continue
            try:
                response = client.get(
                    ENDPOINT, params={"tweet_id": item["request_post_id"]}
                )
            except httpx.TimeoutException as exc:
                artifact_fetch._finish_failure(
                    conn,
                    fetch_id,
                    artifact_fetch.FetchFailure(
                        "x_article_timeout", str(exc), retryable=True
                    ),
                )
                continue
            except httpx.TransportError as exc:
                artifact_fetch._finish_failure(
                    conn,
                    fetch_id,
                    artifact_fetch.FetchFailure(
                        "x_article_transport_error", str(exc), retryable=True
                    ),
                )
                continue
            (
                status,
                provider_status,
                provider_message,
                title,
                contents,
                text,
                error_code,
                error_message,
            ) = _response_outcome(response)
            _finish_response(
                conn,
                fetch_id=fetch_id,
                item=item,
                response=response,
                status=status,
                provider_status=provider_status,
                provider_message=provider_message,
                title=title,
                contents=contents,
                text=text,
                error_code=error_code,
                error_message=error_message,
            )
    finally:
        client.close()
    result = artifact_fetch._complete_run(
        conn, fetch_run_id, fetch_policy=FETCH_POLICY
    )
    result.update(_result_telemetry(conn, fetch_run_id))
    result["provider_request_attempts_this_call"] = (
        result["provider_request_attempts"]
        - prior_telemetry["provider_request_attempts"]
    )
    result["estimated_provider_credits_this_call"] = (
        result["estimated_provider_credits"]
        - prior_telemetry["estimated_provider_credits"]
    )
    result["reused"] = False
    conn.close()
    return result
