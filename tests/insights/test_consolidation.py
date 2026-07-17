from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from fli.insights import consolidation
from fli.routing import runs as routing_runs


class FakeEmbeddings:
    def __init__(self, vectors):
        self.vectors = vectors
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        data = [
            SimpleNamespace(index=index, embedding=self.vectors[index])
            for index in reversed(range(len(self.vectors)))
        ]
        return SimpleNamespace(
            data=data,
            usage=SimpleNamespace(total_tokens=123),
        )


class FailingEmbeddings:
    def create(self, **kwargs):
        raise AssertionError(f"cached embeddings should be reused: {kwargs}")


def _routing_db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(routing_runs.RUN_SCHEMA)
    conn.execute(
        """INSERT INTO run_meta VALUES (
               1, 'routing-test', '2026-07-15', 'gpt-5.4-mini', 'high',
               'prompt-v1', 'prompt-sha', 'schema-v1', 'event-run', 'feed-run',
               'artifacts.db', 'top_ranked', 3, NULL, 'cohort-sha', 3,
               '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00')"""
    )
    packets = [
        {
            "sources": [
                {
                    "source_type": "x_post",
                    "relation": "root",
                    "author": "alice",
                    "text": "Inkling reasons across several modalities.",
                }
            ]
        },
        {
            "sources": [
                {
                    "source_type": "x_post",
                    "relation": "root",
                    "author": "bob",
                    "text": "Inkling is a new multimodal reasoning system.",
                },
                {
                    "source_type": "artifact",
                    "relation": "linked_artifact",
                    "title": "Inkling release",
                    "text": "Technical release details.",
                    "url": "https://example.com/inkling",
                },
            ]
        },
        {
            "sources": [
                {
                    "source_type": "x_post",
                    "relation": "root",
                    "author": "carol",
                    "text": "A separate reaction linking the same release.",
                },
                {
                    "source_type": "artifact",
                    "relation": "linked_artifact",
                    "title": "Inkling release",
                    "text": "Technical release details.",
                    "url": "https://example.com/inkling",
                },
            ]
        },
    ]
    for rank, packet in enumerate(packets, start=1):
        conn.execute(
            """INSERT INTO routing_item (
                   event_id, feed_rank, root_url, snapshot_content_sha256,
                   packet_json, evidence_sha256, input_text, input_sha256,
                   status, updated_at)
               VALUES (?, ?, ?, 'snapshot', ?, ?, 'input', 'input-sha',
                       'complete', '2026-07-15T00:00:00+00:00')""",
            (
                f"event-{rank}",
                rank,
                f"https://x.com/example/status/{rank}",
                json.dumps(packet),
                f"evidence-{rank}",
            ),
        )
    conn.commit()
    conn.close()
    return path


def test_long_embedding_input_includes_posts_and_artifact_excerpts():
    rendered = consolidation.render_embedding_input(
        {
            "sources": [
                {
                    "source_type": "x_post",
                    "relation": "root",
                    "author": "alice",
                    "text": "A   launch\npost",
                },
                {
                    "source_type": "artifact",
                    "relation": "linked_artifact",
                    "title": "Release note",
                    "text": "Full details",
                },
            ]
        }
    )

    assert "root x_post alice: A launch post" in rendered
    assert "linked_artifact artifact title: Release note text: Full details" in rendered


def test_index_is_stored_by_event_and_reused_without_another_embedding_call(tmp_path):
    routing_db = _routing_db(tmp_path / "routing.db")
    embeddings = FakeEmbeddings([[1.0, 0.0], [0.99, 0.1], [0.0, 1.0]])

    first = consolidation.build_index(
        routing_db=routing_db,
        day="2026-07-15",
        insights_db=tmp_path / "missing-insights.db",
        threshold=0.80,
        client=SimpleNamespace(embeddings=embeddings),
    )

    assert first["embedded_event_count"] == 3
    assert first["reused_embedding_count"] == 0
    assert first["group_count"] == 1
    assert first["candidate_edge_count"] == 2
    assert first["groups"][0]["feed_ranks"] == [1, 2, 3]
    assert first["groups"][0]["method"] == "exact_artifact+cosine"
    assert embeddings.calls[0]["model"] == "text-embedding-3-large"
    assert "pipeline:insight-consolidation" in embeddings.calls[0]["extra_body"][
        "metadata"
    ]["tags"]

    conn = sqlite3.connect(routing_db)
    stored = conn.execute(
        "SELECT event_id, dimensions, length(vector_f32) FROM event_embedding ORDER BY event_id"
    ).fetchall()
    members = conn.execute(
        "SELECT feed_rank FROM event_similarity_member ORDER BY feed_rank"
    ).fetchall()
    edge_reasons = conn.execute(
        """SELECT exact_artifact, cosine_similarity
           FROM event_similarity_edge ORDER BY left_event_id, right_event_id"""
    ).fetchall()
    conn.close()

    assert stored == [("event-1", 2, 8), ("event-2", 2, 8), ("event-3", 2, 8)]
    assert members == [(1,), (2,), (3,)]
    assert edge_reasons[0][0] == 0
    assert edge_reasons[1][0] == 1

    second = consolidation.build_index(
        routing_db=routing_db,
        day="2026-07-15",
        insights_db=tmp_path / "missing-insights.db",
        threshold=0.80,
        client=SimpleNamespace(embeddings=FailingEmbeddings()),
    )

    assert second["embedded_event_count"] == 0
    assert second["reused_embedding_count"] == 3
    assert second["groups"] == first["groups"]
