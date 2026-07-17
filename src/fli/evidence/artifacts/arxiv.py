"""Batch arXiv metadata and abstract extraction for catalogued papers."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

import httpx

from fli.evidence.artifacts import fetch as artifact_fetch
from fli.evidence.artifacts import store as artifacts


FETCH_POLICY = "arxiv-metadata-v1"
SELECTION_POLICY = "catalogued-arxiv-without-text-v1"
API_URL = "https://export.arxiv.org/api/query"
BATCH_SIZE = 100
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _arxiv_id(url: str) -> str | None:
    match = re.fullmatch(r"/(?:abs|pdf)/([^/]+?)(?:\.pdf)?", urlsplit(url).path)
    if match is None:
        return None
    return re.sub(r"v\d+$", "", match.group(1))


def _text(node: ElementTree.Element, name: str) -> str | None:
    value = node.findtext(name)
    return " ".join(str(value or "").split()) or None


def _parse_feed(body: bytes) -> dict[str, dict[str, Any]]:
    root = ElementTree.fromstring(body)
    parsed: dict[str, dict[str, Any]] = {}
    for entry in root.findall(f"{ATOM}entry"):
        entry_url = _text(entry, f"{ATOM}id") or ""
        identifier = _arxiv_id(entry_url)
        if identifier is None:
            continue
        authors = [
            value
            for author in entry.findall(f"{ATOM}author")
            if (value := _text(author, f"{ATOM}name"))
        ]
        categories = [
            str(category.attrib.get("term") or "").strip()
            for category in entry.findall(f"{ATOM}category")
            if str(category.attrib.get("term") or "").strip()
        ]
        parsed[identifier] = {
            "title": _text(entry, f"{ATOM}title"),
            "summary": _text(entry, f"{ATOM}summary"),
            "published": _text(entry, f"{ATOM}published"),
            "updated": _text(entry, f"{ATOM}updated"),
            "comment": _text(entry, f"{ARXIV}comment"),
            "authors": authors,
            "categories": categories,
        }
    return parsed


def _render_text(record: dict[str, Any]) -> str:
    sections = [str(record.get("title") or "Untitled arXiv paper")]
    if record.get("authors"):
        sections.append("Authors: " + ", ".join(record["authors"]))
    if record.get("published"):
        sections.append("Published: " + str(record["published"]))
    if record.get("updated"):
        sections.append("Updated: " + str(record["updated"]))
    if record.get("categories"):
        sections.append("Categories: " + ", ".join(record["categories"]))
    if record.get("summary"):
        sections.append("Abstract\n\n" + str(record["summary"]))
    if record.get("comment"):
        sections.append("Comment\n\n" + str(record["comment"]))
    return "\n\n".join(sections).strip() + "\n"


def _create_run(
    conn: Any, selection: list[dict[str, Any]]
) -> tuple[str | None, bool]:
    if not selection:
        return None, True
    payload = [[item["artifact_id"], item["selected_url"]] for item in selection]
    fingerprint = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
    run_id = hashlib.sha256(
        _canonical_json([FETCH_POLICY, SELECTION_POLICY, fingerprint]).encode()
    ).hexdigest()
    run_items = [
        (
            run_id,
            item["artifact_id"],
            rank,
            "paper",
            item["selected_url"],
            item["envelope_day"],
            item["source_rank"],
            item["normalized_rank"],
            item["event_id"],
        )
        for rank, item in enumerate(selection, start=1)
    ]
    existing = conn.execute(
        "SELECT status FROM artifact_fetch_run WHERE fetch_run_id = ?", (run_id,)
    ).fetchone()
    if existing is not None:
        if artifact_fetch.restore_pruned_run_items(
            conn,
            fetch_run_id=run_id,
            run_items=run_items,
        ):
            return run_id, False
        return run_id, str(existing["status"]) == "complete"
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
                run_id,
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
    return run_id, False


def fetch_arxiv_metadata(
    *,
    db_path: Path | str = artifacts.DEFAULT_DB,
    transport: httpx.BaseTransport | None = None,
    batch_sleep_seconds: float = 3.0,
) -> dict[str, Any]:
    """Fetch title, authors, categories, dates, and abstract in API batches."""
    conn = artifacts.connect(db_path)
    candidate_ids = [
        str(row["artifact_id"])
        for row in conn.execute(
            """SELECT artifact_id FROM artifact
               WHERE host = 'arxiv.org'
                 AND NOT EXISTS (
                     SELECT 1 FROM artifact_fetch fetch
                     WHERE fetch.artifact_id = artifact.artifact_id
                       AND fetch.status = 'success'
                       AND fetch.text_snapshot_ref IS NOT NULL
                 )
               ORDER BY artifact_id"""
        )
    ]
    if not candidate_ids:
        conn.close()
        return {
            "fetch_run_id": None,
            "expected_count": 0,
            "success": 0,
            "failed_retryable": 0,
            "failed_terminal": 0,
            "api_requests": 0,
            "reused": True,
        }
    selection = artifact_fetch.select_explicit_artifacts(
        conn, artifact_ids=candidate_ids
    )
    run_id, reused = _create_run(conn, selection)
    assert run_id is not None
    if reused:
        row = conn.execute(
            "SELECT * FROM artifact_fetch_run WHERE fetch_run_id = ?", (run_id,)
        ).fetchone()
        assert row is not None
        result = {
            "fetch_run_id": run_id,
            "expected_count": int(row["expected_count"]),
            "success": int(row["success_count"]),
            "failed_retryable": int(row["failed_retryable_count"]),
            "failed_terminal": int(row["failed_terminal_count"]),
            "api_requests": 0,
            "reused": True,
        }
        conn.close()
        return result

    client = httpx.Client(
        trust_env=False,
        timeout=httpx.Timeout(45.0, connect=10.0),
        headers={"User-Agent": artifact_fetch.USER_AGENT},
        transport=transport,
    )
    api_requests = 0
    try:
        for offset in range(0, len(selection), BATCH_SIZE):
            batch = selection[offset : offset + BATCH_SIZE]
            id_to_item = {
                identifier: item
                for item in batch
                if (identifier := _arxiv_id(str(item["canonical_url"]))) is not None
            }
            try:
                response = client.get(
                    API_URL,
                    params={
                        "id_list": ",".join(id_to_item),
                        "max_results": len(id_to_item),
                    },
                )
                api_requests += 1
                response.raise_for_status()
                records = _parse_feed(response.content)
            except (httpx.HTTPError, ElementTree.ParseError) as exc:
                records = {}
                batch_failure = artifact_fetch.FetchFailure(
                    "arxiv_api_error", str(exc), retryable=True
                )
            else:
                batch_failure = None
            for identifier, item in id_to_item.items():
                artifact_id = str(item["artifact_id"])
                requested_url = str(item["canonical_url"])
                fetch_id = artifact_fetch._claim(
                    conn,
                    fetch_run_id=run_id,
                    artifact_id=artifact_id,
                    requested_url=requested_url,
                    fetch_policy=FETCH_POLICY,
                )
                if fetch_id is None:
                    continue
                if batch_failure is not None:
                    artifact_fetch._finish_failure(conn, fetch_id, batch_failure)
                    continue
                record = records.get(identifier)
                if record is None:
                    artifact_fetch._finish_failure(
                        conn,
                        fetch_id,
                        artifact_fetch.FetchFailure(
                            "arxiv_record_missing",
                            f"arXiv API returned no record for {identifier}",
                            retryable=False,
                        ),
                    )
                    continue
                artifact_fetch._finish_retrieved(
                    conn,
                    fetch_id=fetch_id,
                    source_artifact_id=artifact_id,
                    retrieved=artifact_fetch.Retrieved(
                        final_url=requested_url,
                        status_code=200,
                        redirect_chain=[],
                        headers={"retrieval-provider": "arxiv_api"},
                        content_type="application/atom+xml",
                        charset="utf-8",
                        body=response.content,
                    ),
                    extraction=artifact_fetch.Extraction(
                        success=True,
                        extractor_contract="arxiv-atom-metadata-v1",
                        extractor_version="1",
                        title=record.get("title"),
                        text=_render_text(record),
                        declared_canonical_url=requested_url,
                    ),
                )
            if offset + BATCH_SIZE < len(selection) and batch_sleep_seconds > 0:
                time.sleep(batch_sleep_seconds)
    finally:
        client.close()
    result = artifact_fetch._complete_run(
        conn, run_id, fetch_policy=FETCH_POLICY
    )
    result.update({"api_requests": api_requests, "reused": False})
    conn.close()
    return result
