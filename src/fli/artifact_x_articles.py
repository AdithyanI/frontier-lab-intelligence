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
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from fli import artifact_fetch, artifacts, sources


FETCH_POLICY = "twitterapi-io-x-article-v1"
SELECTION_POLICY = "x-article-catalog-v1"
ENDPOINT = f"{sources.TWITTERAPI_IO_BASE_URL}/twitter/article"
EXTRACTOR_CONTRACT = "twitterapi-io-x-article-body-v1"
EXTRACTOR_VERSION = "1"
PROVIDER_CREDITS_PER_REQUEST = 100
ARTICLE_PATH = re.compile(r"^/i/article/(?P<article_id>\d+)/?$", re.IGNORECASE)
ARTIFACT_ID = re.compile(r"^[0-9a-f]{64}$")


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
    existing = conn.execute(
        "SELECT status FROM artifact_fetch_run WHERE fetch_run_id = ?",
        (fetch_run_id,),
    ).fetchone()
    if existing is not None:
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
               VALUES (?, ?, ?, 'x_article', ?, ?, ?, ?, ?)""",
            [
                (
                    fetch_run_id,
                    item["artifact_id"],
                    item["selection_rank"],
                    item["canonical_url"],
                    item["source_day"],
                    item["source_rank"],
                    item["normalized_rank"],
                    item["source_event_id"],
                )
                for item in selection
            ],
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
            "reused": True,
        }
        conn.close()
        return result

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
    result["reused"] = False
    conn.close()
    return result
