"""Small reusable cosine-index spike for cross-Event Insight consolidation.

The module deliberately writes auxiliary tables into one derived routing
database. It does not change Event identity, routing results, Insight records,
or the live API/UI.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

import numpy as np

from fli import llm_responses
from fli.insights import runs as insight_runs
from fli.insights import view as insight_view
from fli.registry import classification as entity_kinds


INPUT_CONTRACT = "routing-packet-long-v1"
DEFAULT_MODEL = "text-embedding-3-large"
DEFAULT_THRESHOLD = 0.66
EMBEDDING_BATCH_SIZE = 16

AUXILIARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS event_embedding (
    event_id TEXT PRIMARY KEY REFERENCES routing_item(event_id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    input_contract TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    vector_f32 BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_similarity_run (
    run_id TEXT PRIMARY KEY,
    day TEXT NOT NULL,
    source_cohort_sha256 TEXT NOT NULL,
    model TEXT NOT NULL,
    input_contract TEXT NOT NULL,
    cosine_threshold REAL NOT NULL,
    event_count INTEGER NOT NULL,
    pair_count INTEGER NOT NULL,
    candidate_edge_count INTEGER NOT NULL,
    group_count INTEGER NOT NULL,
    grouped_event_count INTEGER NOT NULL,
    embedded_event_count INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    reported_cost_usd REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_similarity_group (
    run_id TEXT NOT NULL REFERENCES event_similarity_run(run_id) ON DELETE CASCADE,
    group_id TEXT NOT NULL,
    lead_feed_rank INTEGER NOT NULL,
    method TEXT NOT NULL,
    PRIMARY KEY (run_id, group_id)
);

CREATE TABLE IF NOT EXISTS event_similarity_member (
    run_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    event_id TEXT NOT NULL REFERENCES routing_item(event_id) ON DELETE CASCADE,
    feed_rank INTEGER NOT NULL,
    PRIMARY KEY (run_id, group_id, event_id),
    FOREIGN KEY (run_id, group_id)
        REFERENCES event_similarity_group(run_id, group_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_similarity_edge (
    run_id TEXT NOT NULL REFERENCES event_similarity_run(run_id) ON DELETE CASCADE,
    left_event_id TEXT NOT NULL REFERENCES routing_item(event_id) ON DELETE CASCADE,
    right_event_id TEXT NOT NULL REFERENCES routing_item(event_id) ON DELETE CASCADE,
    cosine_similarity REAL NOT NULL,
    exact_artifact INTEGER NOT NULL CHECK (exact_artifact IN (0, 1)),
    shared_artifact_urls_json TEXT NOT NULL,
    PRIMARY KEY (run_id, left_event_id, right_event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_similarity_member_event
    ON event_similarity_member(event_id, run_id);
CREATE INDEX IF NOT EXISTS idx_event_similarity_edge_left
    ON event_similarity_edge(left_event_id, run_id);
CREATE INDEX IF NOT EXISTS idx_event_similarity_edge_right
    ON event_similarity_edge(right_event_id, run_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: object | None) -> str:
    return " ".join(str(value or "").split())


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def render_embedding_input(packet: dict[str, Any]) -> str:
    """Render root/thread text plus artifact titles and excerpts."""
    sections: list[str] = []
    sources = packet.get("sources", [])
    if not isinstance(sources, list):
        return ""
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_type = _clean(source.get("source_type"))
        relation = _clean(source.get("relation"))
        author = _clean(source.get("author"))
        title = _clean(source.get("title"))
        text = _clean(source.get("text"))
        if source_type == "artifact":
            section = f"{relation} artifact"
            if title:
                section += f" title: {title}"
            if text:
                section += f" text: {text[:1800]}"
        else:
            section = f"{relation} {source_type}"
            if author:
                section += f" {author}"
            if text:
                section += f": {text[:2400]}"
        if section.strip():
            sections.append(section.strip())
    return "\n".join(sections)[:7200]


def _artifact_urls(packet: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    sources = packet.get("sources", [])
    if not isinstance(sources, list):
        return urls
    for source in sources:
        if not isinstance(source, dict) or source.get("source_type") != "artifact":
            continue
        url = _clean(source.get("url"))
        if url:
            urls.add(url)
    return urls


def _load_routing_rows(
    conn: sqlite3.Connection, *, day: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    meta_row = conn.execute("SELECT * FROM run_meta WHERE singleton = 1").fetchone()
    if meta_row is None:
        raise ValueError("routing database has no run metadata")
    meta = dict(meta_row)
    if str(meta["day"]) != day:
        raise ValueError(
            f"routing database day is {meta['day']!r}, not requested day {day!r}"
        )
    db_rows = conn.execute(
        """SELECT event_id, feed_rank, root_url, packet_json, evidence_sha256
           FROM routing_item WHERE status = 'complete'
           ORDER BY feed_rank, event_id"""
    ).fetchall()
    expected_count = int(meta["expected_count"])
    if len(db_rows) != expected_count:
        raise ValueError(
            f"routing cohort is incomplete: expected {expected_count}, found {len(db_rows)}"
        )
    rows: list[dict[str, Any]] = []
    for row in db_rows:
        packet = json.loads(str(row["packet_json"]))
        if not isinstance(packet, dict):
            raise ValueError(f"routing packet is not an object: {row['event_id']}")
        input_text = render_embedding_input(packet)
        if not input_text:
            raise ValueError(f"routing packet has no embeddable text: {row['event_id']}")
        rows.append(
            {
                "event_id": str(row["event_id"]),
                "feed_rank": int(row["feed_rank"]),
                "root_url": str(row["root_url"]),
                "evidence_sha256": str(row["evidence_sha256"]),
                "artifact_urls": sorted(_artifact_urls(packet)),
                "input_text": input_text,
                "input_sha256": _sha256(input_text),
            }
        )
    return meta, rows


def _stored_embeddings(
    conn: sqlite3.Connection, rows: list[dict[str, Any]], *, model: str
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    stored_rows = conn.execute(
        """SELECT event_id, model, input_contract, input_sha256,
                  dimensions, vector_f32
           FROM event_embedding"""
    ).fetchall()
    stored = {str(row["event_id"]): row for row in stored_rows}
    vectors: dict[str, np.ndarray] = {}
    stale: list[dict[str, Any]] = []
    for row in rows:
        cached = stored.get(str(row["event_id"]))
        if (
            cached is None
            or str(cached["model"]) != model
            or str(cached["input_contract"]) != INPUT_CONTRACT
            or str(cached["input_sha256"]) != str(row["input_sha256"])
        ):
            stale.append(row)
            continue
        vector = np.frombuffer(cached["vector_f32"], dtype=np.float32).copy()
        if vector.size != int(cached["dimensions"]):
            stale.append(row)
            continue
        vectors[str(row["event_id"])] = vector
    return vectors, stale


def _embed(
    client: Any,
    rows: list[dict[str, Any]],
    *,
    model: str,
    tags: tuple[str, ...],
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if not rows:
        return {}, {"input_tokens": 0, "reported_cost_usd": 0.0}
    vectors: dict[str, np.ndarray] = {}
    input_tokens = 0
    reported_costs: list[float] = []
    request_count = 0
    for start in range(0, len(rows), EMBEDDING_BATCH_SIZE):
        batch = rows[start : start + EMBEDDING_BATCH_SIZE]
        request = {
            "model": model,
            "input": [str(row["input_text"]) for row in batch],
            "extra_body": {"metadata": {"tags": list(tags)}},
            "extra_headers": {"x-litellm-tags": ",".join(tags)},
        }
        raw_api = getattr(client.embeddings, "with_raw_response", None)
        if raw_api is None:
            response = client.embeddings.create(**request)
            reported_cost = None
        else:
            raw_response = raw_api.create(**request)
            response = raw_response.parse()
            reported_cost = llm_responses.reported_cost(raw_response.headers)
        request_count += 1
        ordered = sorted(response.data, key=lambda item: int(item.index))
        indices = [int(item.index) for item in ordered]
        if indices != list(range(len(batch))):
            raise RuntimeError(
                "embedding response did not provide complete indexed coverage "
                f"for batch {request_count}: expected {list(range(len(batch)))}, "
                f"found {indices}"
            )
        matrix = np.asarray([item.embedding for item in ordered], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise RuntimeError("embedding response contained a zero-length vector")
        matrix /= norms
        vectors.update(
            {
                str(row["event_id"]): matrix[index]
                for index, row in enumerate(batch)
            }
        )
        usage = getattr(response, "usage", None)
        input_tokens += int(getattr(usage, "total_tokens", 0) or 0)
        if reported_cost is not None:
            reported_costs.append(float(reported_cost))
    return (
        vectors,
        {
            "input_tokens": input_tokens,
            "reported_cost_usd": (
                round(sum(reported_costs), 10) if reported_costs else None
            ),
            "request_count": request_count,
        },
    )


def _persist_embeddings(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
    vectors: dict[str, np.ndarray],
    *,
    model: str,
) -> None:
    created_at = _now()
    for row in rows:
        event_id = str(row["event_id"])
        vector = vectors[event_id]
        conn.execute(
            """INSERT INTO event_embedding (
                   event_id, model, input_contract, input_sha256,
                   dimensions, vector_f32, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(event_id) DO UPDATE SET
                   model = excluded.model,
                   input_contract = excluded.input_contract,
                   input_sha256 = excluded.input_sha256,
                   dimensions = excluded.dimensions,
                   vector_f32 = excluded.vector_f32,
                   created_at = excluded.created_at""",
            (
                event_id,
                model,
                INPUT_CONTRACT,
                str(row["input_sha256"]),
                int(vector.size),
                vector.astype(np.float32, copy=False).tobytes(),
                created_at,
            ),
        )


def _candidate_edges(
    rows: list[dict[str, Any]],
    vectors: dict[str, np.ndarray],
    *,
    threshold: float,
) -> list[dict[str, Any]]:
    matrix = np.stack([vectors[str(row["event_id"])] for row in rows])
    similarity = matrix @ matrix.T
    edges: list[dict[str, Any]] = []
    for left in range(len(rows)):
        left_urls = set(rows[left]["artifact_urls"])
        for right in range(left + 1, len(rows)):
            score = float(similarity[left, right])
            shared_urls = sorted(left_urls & set(rows[right]["artifact_urls"]))
            if score < threshold and not shared_urls:
                continue
            edges.append(
                {
                    "left": left,
                    "right": right,
                    "cosine_similarity": round(score, 6),
                    "exact_artifact": bool(shared_urls),
                    "shared_artifact_urls": shared_urls,
                }
            )
    return edges


def _components(size: int, edges: list[dict[str, Any]]) -> list[list[int]]:
    neighbors = [set() for _ in range(size)]
    for edge in edges:
        left, right = int(edge["left"]), int(edge["right"])
        neighbors[left].add(right)
        neighbors[right].add(left)
    seen: set[int] = set()
    result: list[list[int]] = []
    for node in range(size):
        if node in seen or not neighbors[node]:
            continue
        seen.add(node)
        stack = [node]
        component: list[int] = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in neighbors[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        result.append(sorted(component))
    return sorted(result, key=lambda value: (-len(value), value[0]))


def _groups(
    rows: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    threshold: float,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for component in _components(len(rows), edges):
        indices = set(component)
        group_edges = [
            edge
            for edge in edges
            if int(edge["left"]) in indices and int(edge["right"]) in indices
        ]
        member_ids = sorted(str(rows[index]["event_id"]) for index in component)
        group_id = hashlib.sha256("|".join(member_ids).encode()).hexdigest()[:16]
        has_exact = any(bool(edge["exact_artifact"]) for edge in group_edges)
        has_cosine = any(
            float(edge["cosine_similarity"]) >= threshold for edge in group_edges
        )
        method = "+".join(
            value
            for value, enabled in (
                ("exact_artifact", has_exact),
                ("cosine", has_cosine),
            )
            if enabled
        )
        members = [
            {
                "event_id": str(rows[index]["event_id"]),
                "feed_rank": int(rows[index]["feed_rank"]),
                "root_url": str(rows[index]["root_url"]),
            }
            for index in sorted(
                component,
                key=lambda value: (
                    int(rows[value]["feed_rank"]),
                    str(rows[value]["event_id"]),
                ),
            )
        ]
        groups.append(
            {
                "group_id": group_id,
                "method": method,
                "members": members,
                "edges": group_edges,
            }
        )
    groups.sort(key=lambda group: int(group["members"][0]["feed_rank"]))
    return groups


def _run_id(
    *, cohort_sha256: str, model: str, threshold: float
) -> str:
    identity = f"{cohort_sha256}|{model}|{INPUT_CONTRACT}|{threshold:.6f}"
    return f"insight-similarity-{_sha256(identity)[:16]}"


def _persist_groups(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    day: str,
    cohort_sha256: str,
    model: str,
    threshold: float,
    rows: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    embedded_event_count: int,
    usage: dict[str, Any],
) -> None:
    conn.execute("DELETE FROM event_similarity_run WHERE run_id = ?", (run_id,))
    conn.execute(
        """INSERT INTO event_similarity_run (
               run_id, day, source_cohort_sha256, model, input_contract,
               cosine_threshold, event_count, pair_count, candidate_edge_count,
               group_count, grouped_event_count, embedded_event_count,
               input_tokens, reported_cost_usd, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            day,
            cohort_sha256,
            model,
            INPUT_CONTRACT,
            threshold,
            len(rows),
            len(rows) * (len(rows) - 1) // 2,
            len(edges),
            len(groups),
            sum(len(group["members"]) for group in groups),
            embedded_event_count,
            int(usage["input_tokens"]),
            usage["reported_cost_usd"],
            _now(),
        ),
    )
    group_by_index: dict[int, str] = {}
    event_to_index = {
        str(row["event_id"]): index for index, row in enumerate(rows)
    }
    for group in groups:
        group_id = str(group["group_id"])
        conn.execute(
            """INSERT INTO event_similarity_group
               (run_id, group_id, lead_feed_rank, method)
               VALUES (?, ?, ?, ?)""",
            (
                run_id,
                group_id,
                int(group["members"][0]["feed_rank"]),
                str(group["method"]),
            ),
        )
        for member in group["members"]:
            event_id = str(member["event_id"])
            group_by_index[event_to_index[event_id]] = group_id
            conn.execute(
                """INSERT INTO event_similarity_member
                   (run_id, group_id, event_id, feed_rank)
                   VALUES (?, ?, ?, ?)""",
                (run_id, group_id, event_id, int(member["feed_rank"])),
            )
    for edge in edges:
        left, right = int(edge["left"]), int(edge["right"])
        if group_by_index.get(left) != group_by_index.get(right):
            raise RuntimeError("candidate edge endpoints were assigned to different groups")
        conn.execute(
            """INSERT INTO event_similarity_edge (
                   run_id, left_event_id, right_event_id, cosine_similarity,
                   exact_artifact, shared_artifact_urls_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                str(rows[left]["event_id"]),
                str(rows[right]["event_id"]),
                float(edge["cosine_similarity"]),
                int(bool(edge["exact_artifact"])),
                json.dumps(edge["shared_artifact_urls"], separators=(",", ":")),
            ),
        )


def _longest_investment_insight(
    members: list[dict[str, Any]], kept_by_event: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    candidates = [
        kept_by_event[str(member["event_id"])]
        for member in members
        if str(member["event_id"]) in kept_by_event
    ]
    if not candidates:
        return None
    fields = ("title", "summary", "why_it_matters", "action")
    selected = max(
        candidates,
        key=lambda item: (
            sum(len(str(item.get(field) or "")) for field in fields),
            -int(item["feed_rank"]),
        ),
    )
    return {
        "event_id": str(selected["event_id"]),
        "feed_rank": int(selected["feed_rank"]),
        "title": str(selected["title"]),
        "summary": selected.get("summary"),
        "why_it_matters": selected.get("why_it_matters"),
        "watchpoint": selected.get("action"),
    }


def build_index(
    *,
    routing_db: Path,
    day: str,
    insights_db: Path = insight_runs.DEFAULT_DB,
    model: str = DEFAULT_MODEL,
    threshold: float = DEFAULT_THRESHOLD,
    client: Any | None = None,
) -> dict[str, Any]:
    """Upsert per-envelope embeddings and candidate groups into a routing DB."""
    if not routing_db.is_file():
        raise FileNotFoundError(routing_db)
    if not 0 < threshold < 1:
        raise ValueError("cosine threshold must be between 0 and 1")
    conn = sqlite3.connect(routing_db, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(AUXILIARY_SCHEMA)
    try:
        meta, rows = _load_routing_rows(conn, day=day)
        vectors, stale_rows = _stored_embeddings(conn, rows, model=model)
        tags = (
            "app:fli",
            "pipeline:insight-consolidation",
            "job:daily-cosine-index",
            f"scope:{day}",
            f"prompt:{INPUT_CONTRACT}",
            f"run:{meta['run_id']}",
        )
        embedding_client = (
            (client or entity_kinds.create_litellm_client())
            if stale_rows
            else None
        )
        new_vectors, usage = _embed(
            embedding_client,
            stale_rows,
            model=model,
            tags=tags,
        )
        vectors.update(new_vectors)
        _persist_embeddings(conn, stale_rows, new_vectors, model=model)
        edges = _candidate_edges(rows, vectors, threshold=threshold)
        groups = _groups(rows, edges, threshold=threshold)
        run_id = _run_id(
            cohort_sha256=str(meta["cohort_sha256"]),
            model=model,
            threshold=threshold,
        )
        _persist_groups(
            conn,
            run_id=run_id,
            day=day,
            cohort_sha256=str(meta["cohort_sha256"]),
            model=model,
            threshold=threshold,
            rows=rows,
            groups=groups,
            edges=edges,
            embedded_event_count=len(stale_rows),
            usage=usage,
        )
        conn.commit()
    finally:
        conn.close()

    insights = insight_view.insights_payload(
        audience="investment",
        day=day,
        status="kept",
        db_path=insights_db,
    )
    kept_by_event = {
        str(item["event_id"]): item for item in insights.get("items", [])
    }
    group_report = []
    for group in groups:
        report = {
            "group_id": group["group_id"],
            "method": group["method"],
            "feed_ranks": [member["feed_rank"] for member in group["members"]],
            "event_ids": [member["event_id"] for member in group["members"]],
            "kept_investment_count": sum(
                str(member["event_id"]) in kept_by_event
                for member in group["members"]
            ),
            "representative_investment_insight": _longest_investment_insight(
                group["members"], kept_by_event
            ),
        }
        group_report.append(report)
    return {
        "run_id": run_id,
        "day": day,
        "routing_db": str(routing_db),
        "embedding_model": model,
        "input_contract": INPUT_CONTRACT,
        "cosine_threshold": threshold,
        "event_count": len(rows),
        "pair_count": len(rows) * (len(rows) - 1) // 2,
        "embedded_event_count": len(stale_rows),
        "reused_embedding_count": len(rows) - len(stale_rows),
        "candidate_edge_count": len(edges),
        "group_count": len(groups),
        "grouped_event_count": sum(len(group["members"]) for group in groups),
        "usage": usage,
        "groups": group_report,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m fli.insights.consolidation",
        description="Index one routing cohort for exact-link and cosine groups.",
    )
    parser.add_argument("--routing-db", type=Path, required=True)
    parser.add_argument("--day", required=True)
    parser.add_argument("--insights-db", type=Path, default=insight_runs.DEFAULT_DB)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cosine-threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--plain", action="store_true")
    return parser


def _plain(payload: dict[str, Any]) -> str:
    lines = [
        f"{payload['day']} · {payload['event_count']} envelopes · "
        f"{payload['group_count']} groups · {payload['candidate_edge_count']} candidate edges",
        f"{payload['embedded_event_count']} embedded · "
        f"{payload['reused_embedding_count']} reused · "
        f"threshold {payload['cosine_threshold']:.2f}",
    ]
    for group in payload["groups"]:
        representative = group["representative_investment_insight"]
        title = representative["title"] if representative else "no kept Investment Insight"
        lines.append(f"{group['feed_ranks']} · {group['method']} · {title}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = build_index(
        routing_db=args.routing_db,
        day=args.day,
        insights_db=args.insights_db,
        model=args.model,
        threshold=args.cosine_threshold,
    )
    print(_plain(payload) if args.plain else json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
