import json
import sqlite3

import pytest

from fli import registry_evaluation, registry_evaluation_runs


def make_registry(tmp_path):
    conn = sqlite3.connect(tmp_path / "registry.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY, kind TEXT, slug TEXT, name TEXT
        );
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY, kind TEXT, key TEXT, label TEXT, url TEXT
        );
        CREATE TABLE entity_channels (entity_id INTEGER, channel_id INTEGER);
        CREATE TABLE accounts (
            platform TEXT, handle TEXT, display_name TEXT, bio TEXT,
            followers_count INTEGER
        );
        CREATE TABLE entity_registry_rejections (entity_id INTEGER PRIMARY KEY);

        INSERT INTO entities VALUES (1, 'person', 'x-alice', 'Alice');
        INSERT INTO entities VALUES (2, 'organization', 'acme', 'Acme');
        INSERT INTO entities VALUES (3, 'person', 'x-rejected', 'Rejected');
        INSERT INTO channels VALUES (11, 'x', 'alice', 'Alice', 'https://x.com/alice');
        INSERT INTO channels VALUES (21, 'x', 'acme', 'Acme', 'https://x.com/acme');
        INSERT INTO channels VALUES (22, 'x', 'acmeproduct', 'Acme Product', 'https://x.com/acmeproduct');
        INSERT INTO channels VALUES (31, 'x', 'rejected', 'Rejected', 'https://x.com/rejected');
        INSERT INTO entity_channels VALUES (1, 11);
        INSERT INTO entity_channels VALUES (2, 21);
        INSERT INTO entity_channels VALUES (2, 22);
        INSERT INTO entity_channels VALUES (3, 31);
        INSERT INTO accounts VALUES ('x', 'alice', 'Alice A', 'Researcher', 2000);
        INSERT INTO accounts VALUES ('x', 'acme', 'Acme', 'AI company', 1000);
        INSERT INTO accounts VALUES ('x', 'acmeproduct', 'Acme Product', 'Product', 5000);
        INSERT INTO accounts VALUES ('x', 'rejected', 'Rejected', 'No', 5000);
        INSERT INTO entity_registry_rejections VALUES (3);
        """
    )
    return conn


def freeze(tmp_path):
    registry = make_registry(tmp_path)
    run = registry_evaluation_runs.connect_run(tmp_path / "run.db", check_same_thread=False)
    count = registry_evaluation_runs.freeze_run(
        registry,
        run,
        run_id="test-run",
        model="gpt-5.4-mini",
        effort="high",
    )
    return registry, run, count


def test_freeze_uses_one_representative_channel_and_excludes_rejected(tmp_path):
    registry, run, count = freeze(tmp_path)

    assert count == 2
    rows = run.execute(
        "SELECT entity_id, handle FROM evaluation_item ORDER BY entity_id"
    ).fetchall()
    assert [(row["entity_id"], row["handle"]) for row in rows] == [
        (1, "alice"),
        (2, "acme"),
    ]
    assert registry_evaluation_runs.status(run)["total"] == 2

    with pytest.raises(ValueError, match="model"):
        registry_evaluation_runs.freeze_run(
            registry,
            run,
            run_id="test-run",
            model="different-model",
            effort="high",
        )


class FakePostClient:
    def __init__(self):
        self.calls = []

    def fetch_recent_authored_posts(self, *, username, limit, profile):
        self.calls.append((username, limit, profile))
        return (
            {
                "id": f"{username}-1",
                "text": f"Post by {username}",
                "created_at": "2026-07-12",
                "post_type": "original",
            },
        )


def test_evidence_is_persisted_and_reused(tmp_path):
    _, run, _ = freeze(tmp_path)
    client = FakePostClient()

    first = registry_evaluation_runs.collect_evidence(
        run,
        post_client=client,
        workers=2,
        requests_per_second=10_000,
    )
    second = registry_evaluation_runs.collect_evidence(
        run,
        post_client=client,
        workers=2,
        requests_per_second=10_000,
    )

    assert first == {"pending_at_start": 2, "complete": 2, "failed": 0}
    assert second == {"pending_at_start": 0, "complete": 0, "failed": 0}
    assert [call[0] for call in client.calls] == ["alice", "acme"]
    assert run.execute(
        "SELECT COUNT(*) FROM evaluation_item WHERE evidence_sha256 IS NOT NULL"
    ).fetchone()[0] == 2


def test_completed_model_results_are_resumable(tmp_path):
    _, run, _ = freeze(tmp_path)
    registry_evaluation_runs.collect_evidence(
        run,
        post_client=FakePostClient(),
        workers=2,
        requests_per_second=10_000,
    )
    calls = []

    def evaluator(client, entity, *, run, model, effort):
        calls.append(entity.handle)
        decision = "keep" if entity.handle == "alice" else "remove"
        return {
            "entity_id": entity.entity_id,
            "handle": entity.handle,
            "input_sha256": entity.input_sha256,
            "kind": "person" if entity.handle == "alice" else "organization",
            "kind_reason": "Known actor.",
            "registry_decision": decision,
            "registry_decision_reason": "Test decision.",
            "model": model,
            "reasoning_effort": effort,
            "prompt_version": registry_evaluation.PROMPT_VERSION,
            "schema_version": registry_evaluation.SCHEMA_VERSION,
            "prompt_sha256": registry_evaluation.prompt_sha256(),
            "prompt_cache_key": registry_evaluation.prompt_cache_key(entity.entity_id),
            "response_id": f"response-{entity.entity_id}",
            "response_model": model,
            "input_tokens": 1000,
            "cached_tokens": 768,
            "cache_write_tokens": 0,
            "output_tokens": 100,
            "reported_cost_usd": 0.001,
            "web_actions": [],
            "consulted_sources": [],
            "request_tags": [],
        }

    first = registry_evaluation_runs.evaluate_pending(
        run,
        model="gpt-5.4-mini",
        effort="high",
        run_id="test-run",
        workers=64,
        client_factory=lambda: object(),
        evaluator=evaluator,
    )
    second = registry_evaluation_runs.evaluate_pending(
        run,
        model="gpt-5.4-mini",
        effort="high",
        run_id="test-run",
        workers=64,
        client_factory=lambda: object(),
        evaluator=evaluator,
    )

    assert first == {"pending_at_start": 2, "complete": 2, "failed": 0}
    assert second == {"pending_at_start": 0, "complete": 0, "failed": 0}
    assert sorted(calls) == ["acme", "alice"]
    summary = registry_evaluation_runs.status(run)
    assert summary["evaluation_complete"] == 2
    assert summary["reported_cost_usd"] == pytest.approx(0.002)
    assert summary["cached_tokens"] == 1536
    assert summary["decisions"] == {"keep": 1, "remove": 1}


def test_cli_requires_explicit_all(tmp_path):
    with pytest.raises(SystemExit):
        registry_evaluation_runs.main(
            [
                "run",
                "--run-db",
                str(tmp_path / "run.db"),
                "--run-id",
                "test-run",
            ]
        )
