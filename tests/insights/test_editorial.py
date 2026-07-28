import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient
import pytest

from fli.insights import editorial
from fli.insights import editorial_cli
from fli.insights import editorial_runs
from fli.insights import runs as insight_runs
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs
from fli.scoring import development_attention
from fli.web.app import app
from fli.web import developments as development_store


DAY = "2026-07-15"
SOURCE_RANK_INPUT_SHA256 = "a" * 64
CLIENT = TestClient(app)


def test_connect_migrates_editorial_candidate_snapshot_column(tmp_path):
    db = tmp_path / "editorial-v3.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        editorial_runs.SCHEMA.replace(
            "semantic_snapshot_sha256", "snapshot_content_sha256"
        )
    )
    conn.close()

    assert editorial_runs.migrate_editorial_store(db) is True
    migrated = editorial_runs.connect(db)
    columns = {
        str(row["name"])
        for row in migrated.execute(
            "PRAGMA table_info(editorial_candidate)"
        ).fetchall()
    }
    user_version = int(migrated.execute("PRAGMA user_version").fetchone()[0])
    migrated.close()

    assert "semantic_snapshot_sha256" in columns
    assert "snapshot_content_sha256" not in columns
    assert user_version == 4
    assert editorial_runs.migrate_editorial_store(db) is False


def _packet(event_id: str, text: str, *, artifact: bool = False):
    sources = [
        routing_model.EvidenceSource(
            source_type="x_post",
            source_id=f"post-{event_id}",
            url=f"https://x.com/example/status/{event_id}",
            text=text,
            author="@example",
            relation="root",
        )
    ]
    if artifact:
        sources.append(
            routing_model.EvidenceSource(
                source_type="artifact",
                source_id=f"artifact-{event_id}",
                url=f"https://example.com/{event_id}",
                text=f"Primary research for {text}",
                title=f"Research for {event_id}",
                relation="linked_artifact",
            )
        )
    return routing_model.RoutingPacket(
        event_id=event_id,
        day=DAY,
        sources=tuple(sources),
    )


def _routing_fixture(
    root: Path,
    *,
    directory: str = "current",
    run_id: str = "routing-current",
    source_rank_input_sha256: str = SOURCE_RANK_INPUT_SHA256,
    source_event_run_id: str = "event-run",
    source_feed_run_id: str = "feed-run",
    cohort_sha256: str = "cohort-sha",
) -> Path:
    path = root / directory / "routing.db"
    conn = routing_runs.connect_run(path)
    now = "2026-07-17T12:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta (
               singleton, run_id, day, model, reasoning_effort,
               prompt_version, prompt_sha256, schema_version, rank_version,
               source_rank_input_sha256, source_event_run_id,
               source_feed_run_id, source_artifact_db,
               selection_kind, selection_limit, requested_event_id,
               cohort_sha256, expected_count, created_at, updated_at)
           VALUES (1, ?, ?, 'gpt-5.4-mini', 'high', ?, ?, ?, ?, ?,
                   ?, ?, 'artifacts.db', 'top_ranked', 3,
                   NULL, ?, 3, ?, ?)""",
        (
            run_id,
            DAY,
            routing_model.PROMPT_VERSION,
            routing_model.prompt_sha256(),
            routing_model.SCHEMA_VERSION,
            development_attention.DAILY_RANK_VERSION,
            source_rank_input_sha256,
            source_event_run_id,
            source_feed_run_id,
            cohort_sha256,
            now,
            now,
        ),
    )
    fixtures = (
        ("event-a", 1, "Inkling open model release and weights", True, True, True),
        ("event-b", 4, "Inkling enterprise distribution and serving", True, False, True),
        ("event-c", 9, "A bounded agent recovery evaluation", False, True, False),
    )
    for event_id, rank, text, artifact, engineering, investment in fixtures:
        packet = _packet(event_id, text, artifact=artifact)
        conn.execute(
            """INSERT INTO routing_item (
                   event_id, feed_rank, root_url, semantic_snapshot_sha256,
                   packet_json, evidence_sha256, input_text, input_sha256,
                   status, attempts, ai_engineering_relevant,
                   ai_engineering_reason, investment_relevant,
                   investment_reason, completed_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete', 1, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                rank,
                f"https://x.com/example/status/{event_id}",
                f"snapshot-{event_id}",
                routing_runs._canonical_json(routing_runs._packet_payload(packet)),
                packet.evidence_sha256,
                routing_model.render_input(packet),
                packet.input_sha256,
                int(engineering),
                "Useful engineering evidence." if engineering else "Not engineering relevant.",
                int(investment),
                "Useful investment evidence." if investment else "Not investment relevant.",
                now,
                now,
            ),
        )
    conn.commit()
    conn.close()
    return path


def _workspace(tmp_path, monkeypatch):
    routing_root = tmp_path / "routing"
    _routing_fixture(routing_root)
    monkeypatch.setattr(
        routing_runs,
        "_published_event_source",
        lambda: {"event_run_id": "event-run", "feed_run_id": "feed-run"},
    )
    monkeypatch.setattr(
        development_store,
        "current_rank_identity",
        lambda *, day: {
            "day": day,
            "rank_version": development_attention.DAILY_RANK_VERSION,
            "rank_input_sha256": SOURCE_RANK_INPUT_SHA256,
            "event_run_id": "event-run",
            "feed_run_id": "feed-run",
        },
    )
    monkeypatch.setattr(
        editorial_runs,
        "_event_x_publication_times",
        lambda **_kwargs: {
            event_id: {f"post-{event_id}": f"{DAY}T12:00:00+00:00"}
            for event_id in ("event-a", "event-b", "event-c")
        },
    )
    monkeypatch.setattr(
        editorial_runs,
        "_event_artifact_disclosures",
        lambda **_kwargs: {
            event_id: {
                f"artifact-{event_id}": [
                    {
                        "source_id": f"post-{event_id}",
                        "source_url": f"https://x.com/example/status/{event_id}",
                        "published_at": f"{DAY}T12:00:00+00:00",
                        "relation": "links_to",
                    }
                ]
            }
            for event_id in ("event-a", "event-b")
        },
    )
    result = editorial_runs.prepare_workspace(
        day=DAY,
        routing_root=routing_root,
        insights_db=tmp_path / "missing-insights.db",
        workspace_root=tmp_path / "workspaces",
    )
    return editorial_runs.REPO_ROOT / result["workspace"] if not Path(result["workspace"]).is_absolute() else Path(result["workspace"])


def _draft(workspace: Path):
    manifest = editorial_runs.load_manifest(workspace)
    return {
        "schema_version": editorial.DRAFT_SCHEMA_VERSION,
        "workspace_run_id": manifest["run_id"],
        "workspace_manifest_sha256": manifest["manifest_sha256"],
        "agent": {
            "skill_version": editorial.SKILL_VERSION,
            "model": "codex-test",
            "notes": None,
        },
        "insights": [
            {
                "local_id": "investment-inkling",
                "audience": "investment",
                "rank": 1,
                "rank_rationale": (
                    "Ranked first because it affects two named companies and has "
                    "a concrete enterprise-economics diligence path."
                ),
                "title": "Open models shorten the enterprise distribution path",
                "what_changed": "Inkling launched with weights and enterprise distribution support.",
                "interpretation": (
                    "Distribution evidence matters more than launch attention alone because "
                    "enterprise gateways can reduce adoption friction before model economics are proven."
                ),
                "next_step": "Measure adoption and serving economics across one enterprise workload.",
                "analysis": {
                    **editorial.investment_analysis_template(),
                    "affected_entities": [
                        {
                            "name": "Microsoft",
                            "scope": "portfolio",
                            "impact": "mixed",
                            "mechanism": "Open models can pressure model economics while increasing cloud demand.",
                        },
                        {
                            "name": "Toyota",
                            "scope": "outside_portfolio",
                            "impact": "uncertain",
                            "mechanism": "A named deployment provides a specific diligence target outside the book.",
                        },
                    ],
                    "key_uncertainty": "No customer adoption or unit economics are disclosed.",
                },
                "event_links": [
                    {
                        "event_id": "event-a",
                        "role": "primary",
                        "reason": "Establishes the release and open weights.",
                    },
                    {
                        "event_id": "event-b",
                        "role": "supporting",
                        "reason": "Establishes an enterprise distribution path.",
                    },
                ],
                "citation_ids": ["source-a", "source-b"],
            },
            {
                "local_id": "engineering-inkling",
                "audience": "ai_engineering",
                "rank": 1,
                "rank_rationale": (
                    "Ranked first because it creates a bounded, immediately runnable "
                    "engineering test."
                ),
                "title": "Test open-model serving before adopting the launch claim",
                "what_changed": "Inkling shipped downloadable weights and implementation artifacts.",
                "interpretation": "A bounded serving test can establish whether it transfers locally.",
                "next_step": "Run one frozen multimodal workload on the supported stack.",
                "analysis": editorial.engineering_analysis_template(),
                "event_links": [
                    {
                        "event_id": "event-a",
                        "role": "primary",
                        "reason": "Provides the model and technical artifact.",
                    }
                ],
                "citation_ids": ["source-a"],
            },
        ],
        "not_selected": [
            {
                "event_id": "event-c",
                "audience": "ai_engineering",
                "reason": "Useful but lower priority than the selected bounded experiment.",
            }
        ],
        "citations": [
            {
                "local_id": "source-a",
                "kind": "artifact",
                "url": "https://example.com/event-a",
                "title": "Research for event-a",
                "event_id": "event-a",
                "artifact_id": "artifact-event-a",
                "published_at": DAY,
                "retrieved_at": None,
                "supports": "The release and its model artifact.",
                "excerpt": "Primary research for Inkling open model release and weights",
            },
            {
                "local_id": "source-b",
                "kind": "artifact",
                "url": "https://example.com/event-b",
                "title": "Research for event-b",
                "event_id": "event-b",
                "artifact_id": "artifact-event-b",
                "published_at": DAY,
                "retrieved_at": None,
                "supports": "The enterprise distribution evidence.",
                "excerpt": "Primary research for Inkling enterprise distribution and serving",
            },
        ],
    }


def test_prepare_freezes_union_positive_workspace_and_reuses_it(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path, monkeypatch)
    manifest = editorial_runs.load_manifest(workspace)

    assert manifest["counts"] == {
        "events": 3,
        "candidate_pairs": 4,
        "stale_events_excluded": 0,
        "stale_x_sources_excluded": 0,
        "investment": 2,
        "ai_engineering": 2,
    }
    assert manifest["source_window"]["max_source_age_days"] == 7
    assert manifest["events"][0]["source_dates"] == {
        "https://x.com/example/status/event-a": DAY
    }
    assert [item["feed_rank"] for item in manifest["events"]] == [1, 4, 9]
    assert (workspace / "draft.template.json").is_file()
    assert json.loads((workspace / "draft.template.json").read_text())["schema_version"] == (
        editorial.DRAFT_SCHEMA_VERSION
    )
    assert editorial_runs.search_workspace(workspace, query="Inkling")["match_count"] == 2

    reused = editorial_runs.prepare_workspace(
        day=DAY,
        routing_root=tmp_path / "routing",
        insights_db=tmp_path / "missing-insights.db",
        workspace_root=tmp_path / "workspaces",
    )
    assert reused["reused"] is True
    assert json.loads((workspace / "draft.template.json").read_text())["schema_version"] == (
        editorial.DRAFT_SCHEMA_VERSION
    )


def test_prepare_omits_prior_insight_when_routing_input_hash_changed(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        editorial_runs,
        "_prior_insights",
        lambda *_args, **_kwargs: {
            ("event-a", "ai_engineering"): {
                "summary": "An annotation from an older routing input.",
                "input_sha256": "different-input",
            }
        },
    )

    workspace = _workspace(tmp_path, monkeypatch)
    manifest = editorial_runs.load_manifest(workspace)
    event = next(item for item in manifest["events"] if item["event_id"] == "event-a")
    payload = json.loads((workspace / event["file"]).read_text())

    assert payload["input_sha256"] != "different-input"
    assert payload["prior_per_event_insights"] == {}


def test_artifact_disclosures_are_loaded_from_the_bound_catalog(
    tmp_path, monkeypatch
):
    db = tmp_path / "artifacts.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """CREATE TABLE artifact_import_run (
               import_run_id TEXT PRIMARY KEY,
               selection_policy TEXT NOT NULL
           );
           CREATE TABLE artifact_import_candidate (
               event_id TEXT NOT NULL,
               artifact_id TEXT,
               import_run_id TEXT NOT NULL,
               disclosure_external_id TEXT NOT NULL,
               disclosure_url TEXT NOT NULL,
               disclosure_published_at TEXT NOT NULL,
               relation TEXT NOT NULL,
               decision TEXT NOT NULL
           );"""
    )
    conn.execute(
        "INSERT INTO artifact_import_run VALUES ('run', ?)",
        (editorial_runs.artifact_store.PRIMARY_AUTHOR_SELECTION_POLICY,),
    )
    conn.execute(
        """INSERT INTO artifact_import_candidate VALUES
           ('event-a', 'artifact-a', 'run', 'post-a',
            'https://x.com/example/status/post-a',
            '2026-07-15T12:00:00+00:00', 'links_to', 'accepted')"""
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        development_store,
        "developments_payload",
        lambda **_kwargs: {
            "available": True,
            "items": [
                {
                    "development_id": "development-a",
                    "source_event_ids": ["event-a"],
                },
                {
                    "development_id": "development-b",
                    "source_event_ids": ["event-b"],
                },
            ],
        },
    )

    assert editorial_runs._event_artifact_disclosures(
        day=DAY,
        artifact_db=db,
        event_ids={"development-a", "development-b"},
    ) == {
        "development-a": {
            "artifact-a": [
                {
                    "source_id": "post-a",
                    "source_url": "https://x.com/example/status/post-a",
                    "published_at": "2026-07-15T12:00:00+00:00",
                    "relation": "links_to",
                }
            ]
        }
    }
def test_prepare_prunes_stale_prose_and_promotes_current_source(tmp_path, monkeypatch):
    routing_root = tmp_path / "routing"
    path = routing_root / "current" / "routing.db"
    conn = routing_runs.connect_run(path)
    now = "2026-07-17T12:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta (
               singleton, run_id, day, model, reasoning_effort,
               prompt_version, prompt_sha256, schema_version, rank_version,
               source_rank_input_sha256, source_event_run_id,
               source_feed_run_id, source_artifact_db,
               selection_kind, selection_limit, requested_event_id,
               cohort_sha256, expected_count, created_at, updated_at)
           VALUES (1, 'routing-current', ?, 'gpt-5.4-mini', 'high', ?, ?, ?, ?, ?,
                   'event-run', 'feed-run', 'artifacts.db', 'top_ranked', 1,
                   NULL, 'cohort-sha', 1, ?, ?)""",
        (
            DAY,
            routing_model.PROMPT_VERSION,
            routing_model.prompt_sha256(),
            routing_model.SCHEMA_VERSION,
            development_attention.DAILY_RANK_VERSION,
            SOURCE_RANK_INPUT_SHA256,
            now,
            now,
        ),
    )
    packet = routing_model.RoutingPacket(
        event_id="event-pruned",
        day=DAY,
        sources=(
            routing_model.EvidenceSource(
                source_type="x_post",
                source_id="old-root",
                url="https://x.com/example/status/old-root",
                text="Old financing claim.",
                author="@example",
                relation="root",
            ),
            routing_model.EvidenceSource(
                source_type="x_post",
                source_id="current-update",
                url="https://x.com/example/status/current-update",
                text="Current first-party update.",
                author="@example",
                relation="same_author_continuation",
            ),
        ),
    )
    conn.execute(
        """INSERT INTO routing_item (
               event_id, feed_rank, root_url, semantic_snapshot_sha256,
               packet_json, evidence_sha256, input_text, input_sha256,
               status, attempts, ai_engineering_relevant,
               ai_engineering_reason, investment_relevant,
               investment_reason, completed_at, updated_at)
           VALUES ('event-pruned', 1, 'https://x.com/example/status/old-root',
                   'snapshot', ?, ?, ?, ?, 'complete', 1, 0, 'Not relevant.',
                   1, 'Old financing claim drives relevance.', ?, ?)""",
        (
            routing_runs._canonical_json(routing_runs._packet_payload(packet)),
            packet.evidence_sha256,
            routing_model.render_input(packet),
            packet.input_sha256,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(
        routing_runs,
        "_published_event_source",
        lambda: {"event_run_id": "event-run", "feed_run_id": "feed-run"},
    )
    monkeypatch.setattr(
        development_store,
        "current_rank_identity",
        lambda *, day: {
            "day": day,
            "rank_version": development_attention.DAILY_RANK_VERSION,
            "rank_input_sha256": SOURCE_RANK_INPUT_SHA256,
            "event_run_id": "event-run",
            "feed_run_id": "feed-run",
        },
    )
    monkeypatch.setattr(
        editorial_runs,
        "_event_x_publication_times",
        lambda **_kwargs: {
            "event-pruned": {
                "old-root": "2025-07-15T12:00:00+00:00",
                "current-update": f"{DAY}T12:00:00+00:00",
            }
        },
    )
    monkeypatch.setattr(
        editorial_runs,
        "_prior_insights",
        lambda *_args, **_kwargs: {
            ("event-pruned", "investment"): {"summary": "Old financing claim."}
        },
    )
    monkeypatch.setattr(
        editorial_runs,
        "_event_artifact_disclosures",
        lambda **_kwargs: {},
    )

    result = editorial_runs.prepare_workspace(
        day=DAY,
        routing_root=routing_root,
        insights_db=tmp_path / "missing.db",
        workspace_root=tmp_path / "workspaces",
    )
    workspace = Path(result["workspace"])
    if not workspace.is_absolute():
        workspace = editorial_runs.REPO_ROOT / workspace
    manifest = editorial_runs.load_manifest(workspace)
    payload = json.loads((workspace / manifest["events"][0]["file"]).read_text())

    assert payload["root_url"].endswith("/current-update")
    assert [source["source_id"] for source in payload["packet"]["sources"]] == [
        "current-update"
    ]
    assert payload["routing"]["investment"]["reason"].startswith(
        "Positive route inherited"
    )
    assert payload["prior_per_event_insights"] == {}


def test_validate_requires_exact_candidate_coverage(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path, monkeypatch)
    draft = _draft(workspace)
    normalized, report = editorial.validate_draft(
        draft, editorial_runs.load_manifest(workspace)
    )

    assert report["candidate_pair_count"] == 4
    assert report["included_candidate_pairs"] == 3
    assert report["not_selected_candidate_pairs"] == 1
    assert normalized["insights"][0]["local_id"] == "investment-inkling"
    assert normalized["insights"][0]["analysis"]["affected_entities"] == [
        {
            "name": "Microsoft",
            "scope": "portfolio",
            "impact": "mixed",
            "mechanism": "Open models can pressure model economics while increasing cloud demand.",
        },
        {
            "name": "Toyota",
            "scope": "outside_portfolio",
            "impact": "uncertain",
            "mechanism": "A named deployment provides a specific diligence target outside the book.",
        },
    ]

    draft["not_selected"] = []
    try:
        editorial.validate_draft(draft, editorial_runs.load_manifest(workspace))
    except ValueError as error:
        assert "does not dispose every routed candidate" in str(error)
    else:
        raise AssertionError("missing coverage must fail validation")


def test_preflight_ledger_exposes_pair_coverage_without_making_decisions(
    tmp_path, monkeypatch
):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "draft.json"
    draft_path.write_text(json.dumps(_draft(workspace)), encoding="utf-8")

    report = editorial_runs.preflight_workspace(workspace, draft_path=draft_path)

    assert report["workspace_run_id"] == editorial_runs.load_manifest(workspace)["run_id"]
    assert report["complete"] is True
    assert report["counts"] == {
        "events": 3,
        "candidate_pairs": 4,
        "included": 3,
        "not_selected": 1,
        "missing": 0,
        "duplicate": 0,
        "unexpected": 0,
    }
    by_pair = {
        (row["event_id"], row["audience"]): row for row in report["pairs"]
    }
    selected = by_pair[("event-a", "investment")]
    assert selected["status"] == "included"
    assert selected["insight"] == {
        "local_id": "investment-inkling",
        "rank": 1,
        "title": "Open models shorten the enterprise distribution path",
    }
    assert selected["event_role"] == "primary"
    assert selected["citation_ids"] == ["source-a", "source-b"]
    assert selected["affected_entities"] == ["Microsoft", "Toyota"]
    rejected = by_pair[("event-c", "ai_engineering")]
    assert rejected["status"] == "not_selected"
    assert rejected["reason"].startswith("Useful but lower priority")

    incomplete = _draft(workspace)
    incomplete["not_selected"] = []
    draft_path.write_text(json.dumps(incomplete), encoding="utf-8")
    missing = editorial_runs.preflight_workspace(workspace, draft_path=draft_path)
    assert missing["complete"] is False
    assert missing["counts"]["missing"] == 1
    assert {
        (row["event_id"], row["audience"])
        for row in missing["pairs"]
        if row["status"] == "missing"
    } == {("event-c", "ai_engineering")}


def test_event_citation_date_is_filled_from_source_truth_and_conflicts_fail(
    tmp_path, monkeypatch
):
    workspace = _workspace(tmp_path, monkeypatch)
    manifest = editorial_runs.load_manifest(workspace)
    draft = _draft(workspace)
    citation = draft["citations"][0]
    citation.update(
        {
            "kind": "event",
            "url": "https://x.com/example/status/event-a",
            "artifact_id": None,
            "published_at": None,
        }
    )

    normalized, _report = editorial.validate_draft(draft, manifest)
    assert normalized["citations"][0]["published_at"] == DAY

    citation["published_at"] = "2026-07-14"
    with pytest.raises(ValueError, match="must match frozen source date"):
        editorial.validate_draft(draft, manifest)


def test_artifact_citations_require_and_verify_a_frozen_excerpt(
    tmp_path, monkeypatch
):
    workspace = _workspace(tmp_path, monkeypatch)
    manifest = editorial_runs.load_manifest(workspace)
    draft = _draft(workspace)

    draft["citations"][0]["excerpt"] = None
    with pytest.raises(ValueError, match="artifact citations require a supporting excerpt"):
        editorial.validate_draft(draft, manifest)

    draft = _draft(workspace)
    draft["citations"][0]["excerpt"] = "A claim the frozen artifact never makes"
    draft_path = workspace / "bad-excerpt.json"
    draft_path.write_text(json.dumps(draft), encoding="utf-8")
    with pytest.raises(ValueError, match="does not occur in the frozen artifact text"):
        editorial_runs.validate_result(workspace, draft_path)


def test_import_is_atomic_normalized_and_idempotent(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "draft.json"
    draft_path.write_text(json.dumps(_draft(workspace)), encoding="utf-8")
    db = tmp_path / "editorial.db"

    first = editorial_runs.import_result(workspace, draft_path, db_path=db)
    second = editorial_runs.import_result(workspace, draft_path, db_path=db)

    assert first["reused"] is False
    assert second["reused"] is True
    assert first["run"]["insight_count"] == 2
    assert len(first["run"]["insights"]) == 2
    assert first["run"]["insights"][0]["events"][0]["feed_rank"] == 1
    conn = editorial_runs.connect(db)
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(editorial_insight)").fetchall()
    }
    assert "impact_chain_json" not in columns
    assert "evidence_limitations_json" not in columns
    assert "rank_rationale" in columns
    assert conn.execute("SELECT COUNT(*) FROM editorial_candidate").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM editorial_event_disposition").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM editorial_run").fetchone()[0] == 1
    conn.close()


def test_store_migration_collapses_legacy_investment_analysis(tmp_path):
    db = tmp_path / "legacy-editorial.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE editorial_insight (
               run_id TEXT NOT NULL,
               insight_id TEXT NOT NULL,
               local_id TEXT NOT NULL,
               audience TEXT NOT NULL,
               display_rank INTEGER NOT NULL,
               title TEXT NOT NULL,
               what_changed TEXT NOT NULL,
               interpretation TEXT NOT NULL,
               impact_chain_json TEXT NOT NULL,
               evidence_limitations_json TEXT NOT NULL,
               next_step TEXT NOT NULL,
               analysis_json TEXT NOT NULL
           )"""
    )
    conn.execute(
        """INSERT INTO editorial_insight VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "legacy-run",
            "legacy-insight",
            "legacy-local",
            "investment",
            1,
            "Legacy title",
            "Legacy facts",
            "Legacy interpretation",
            json.dumps(["Evidence", "Consequence"]),
            json.dumps(["Provider evidence is not independent."]),
            "Legacy next step",
            json.dumps(
                {
                    "affected_entities": [],
                    "thesis_effect": "mixed",
                    "operating_driver": "Legacy operating driver.",
                    "financial_driver": "Legacy financial driver.",
                    "edge": "Legacy edge.",
                    "counter_case": "Legacy counter-case.",
                    "watchpoints": ["One", "Two", "Three", "Four"],
                }
            ),
        ),
    )
    conn.execute(
        """INSERT INTO editorial_insight VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "legacy-run",
            "legacy-engineering-insight",
            "legacy-engineering-local",
            "ai_engineering",
            1,
            "Legacy engineering title",
            "Legacy engineering facts",
            "Legacy engineering interpretation",
            json.dumps(["Evidence", "Consequence"]),
            json.dumps(["Provider evidence is not independent."]),
            "Run one bounded test.",
            json.dumps(
                {
                    "system_surface": "Agent evaluation",
                    "technical_implication": "Add adaptive attacks.",
                    "recommended_action": "test",
                    "experiment": {
                        "hypothesis": "Adaptive attacks find more failures.",
                        "smallest_test": "Run one frozen suite.",
                        "success_metric": "Find three new failures",
                        "stop_condition": "Stop if no new failures are found",
                    },
                    "constraints": ["Use synthetic credentials."],
                }
            ),
        ),
    )
    conn.commit()
    conn.close()

    migrated = editorial_runs.connect(db)
    columns = {
        row["name"]
        for row in migrated.execute("PRAGMA table_info(editorial_insight)").fetchall()
    }
    row = migrated.execute(
        """SELECT analysis_json, rank_rationale FROM editorial_insight
           WHERE insight_id = 'legacy-insight'"""
    ).fetchone()
    engineering_row = migrated.execute(
        """SELECT analysis_json FROM editorial_insight
           WHERE insight_id = 'legacy-engineering-insight'"""
    ).fetchone()
    migrated.close()

    assert "impact_chain_json" not in columns
    assert "evidence_limitations_json" not in columns
    assert "rank_rationale" in columns
    assert row["rank_rationale"].startswith("This historical run predates")
    assert json.loads(row["analysis_json"]) == {
        "affected_entities": [],
        "key_uncertainty": (
            "Legacy counter-case. Provider evidence is not independent."
        ),
        "watchpoints": ["One", "Two", "Three"],
    }
    assert json.loads(engineering_row["analysis_json"]) == {
        "decision_rule": (
            "Proceed if the success criterion is met: Find three new failures. "
            "Stop or revise if: Stop if no new failures are found."
        )
    }


def test_editorial_read_selects_latest_complete_run_and_filters_audience(
    tmp_path, monkeypatch
):
    workspace = _workspace(tmp_path, monkeypatch)
    db = tmp_path / "editorial.db"

    first_draft = workspace / "first.json"
    first_draft.write_text(json.dumps(_draft(workspace)), encoding="utf-8")
    first = editorial_runs.import_result(workspace, first_draft, db_path=db)

    revised = _draft(workspace)
    revised["agent"]["notes"] = "Second editorial pass."
    revised["insights"][0]["title"] = "Revised distribution judgment"
    second_draft = workspace / "second.json"
    second_draft.write_text(json.dumps(revised), encoding="utf-8")
    second = editorial_runs.import_result(workspace, second_draft, db_path=db)

    assert (
        second["run"]["insights"][0]["insight_id"]
        == first["run"]["insights"][0]["insight_id"]
    )

    conn = editorial_runs.connect(db)
    with conn:
        conn.execute(
            "UPDATE editorial_run SET created_at = ? WHERE run_id = ?",
            ("2026-07-17T12:00:00+00:00", first["run_id"]),
        )
        conn.execute(
            "UPDATE editorial_run SET created_at = ? WHERE run_id = ?",
            ("2026-07-17T13:00:00+00:00", second["run_id"]),
        )
    conn.close()

    payload = editorial_runs.editorial_insights_payload(
        audience="investment", day=DAY, db_path=db
    )

    assert payload["schema_version"] == "daily-intelligence-read-v4"
    assert payload["content_kind"] == "daily_editorial"
    assert payload["available"] is True
    assert payload["reason"] is None
    assert payload["run"]["run_id"] == second["run_id"]
    assert payload["run"]["agent"] == {
        "skill_version": editorial.SKILL_VERSION,
        "model": "codex-test",
        "notes": "Second editorial pass.",
    }
    assert payload["run"]["counts"]["insights"] == 1
    assert (
        payload["run"]["source"]["rank_version"]
        == development_attention.DAILY_RANK_VERSION
    )
    assert (
        payload["run"]["source"]["rank_input_sha256"]
        == SOURCE_RANK_INPUT_SHA256
    )
    assert [item["audience"] for item in payload["items"]] == ["investment"]
    assert payload["items"][0]["rank"] == 1
    assert payload["items"][0]["rank_rationale"].startswith("Ranked first")
    assert payload["items"][0]["day"] == DAY
    assert payload["items"][0]["title"] == "Revised distribution judgment"
    assert payload["items"][0]["events"][0]["event_id"] == "event-a"
    assert "root_url" not in payload["items"][0]["events"][0]
    assert payload["items"][0]["citations"][0]["local_id"] == "source-a"
    assert payload["declined"] == []
    engineering = editorial_runs.editorial_insights_payload(
        audience="ai_engineering", day=DAY, db_path=db
    )
    assert engineering["declined"] == [
        {
            "event_id": "event-c",
            "feed_rank": 9,
            "author": "@example",
            "excerpt": "A bounded agent recovery evaluation",
            "reason": "Useful but lower priority than the selected bounded experiment.",
        }
    ]
    assert "analysis" in payload["items"][0]
    assert payload["items"][0]["analysis"]["key_uncertainty"].startswith("No customer")
    assert "impact_chain" not in payload["items"][0]
    assert "evidence_limitations" not in payload["items"][0]
    assert payload["portfolio_reference"] == {
        "basis": "complete audited year-end portfolio",
        "as_of": "2025-12-31",
        "source_label": "BIT Global Technology Leaders audited annual report",
        "source_url": "https://fondswelt.hansainvest.com/uploads/documents/jahresbericht/JB_1806_BIT_Global_Technology_Leaders_2025-12-31.pdf",
        "reader_note": (
            "Portfolio mappings use the complete audited public portfolio. "
            "They are research context, not a claim about a live portfolio or a trade recommendation."
        ),
    }

    missing = editorial_runs.editorial_insights_payload(
        audience="investment", day="2026-07-14", db_path=db
    )
    assert missing["available"] is False
    assert missing["run"] is None
    assert missing["items"] == []
    assert missing["declined"] == []


def test_web_prefers_editorial_for_kept_and_preserves_candidate_fallback(
    tmp_path, monkeypatch
):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "draft.json"
    draft_path.write_text(json.dumps(_draft(workspace)), encoding="utf-8")
    db = tmp_path / "editorial.db"
    editorial_runs.import_result(workspace, draft_path, db_path=db)
    monkeypatch.setattr(editorial_runs, "DEFAULT_DB", db)
    monkeypatch.setattr(insight_runs, "DEFAULT_DB", tmp_path / "missing-insights.db")

    kept = CLIENT.get(
        f"/api/insights?audience=investment&date={DAY}&status=kept"
    ).json()
    suppressed = CLIENT.get(
        f"/api/insights?audience=investment&date={DAY}&status=suppressed"
    ).json()
    dates = CLIENT.get("/api/insights/dates?audience=investment").json()
    assert kept["content_kind"] == "daily_editorial"
    assert kept["status"] == "kept"
    assert kept["items"][0]["title"].startswith("Open models")
    assert suppressed["content_kind"] == "candidate_decisions"
    assert suppressed["available"] is False
    assert dates["dates"] == [
        {
            "day": DAY,
            "content_kind": "daily_editorial",
            "item_count": 1,
            "candidate_count": 2,
            "included_candidate_count": 2,
            "not_selected_candidate_count": 0,
        }
    ]


def test_editorial_date_lineage_is_reused_until_a_source_changes(
    tmp_path, monkeypatch
):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "draft.json"
    draft_path.write_text(json.dumps(_draft(workspace)), encoding="utf-8")
    db = tmp_path / "editorial.db"
    editorial_runs.import_result(workspace, draft_path, db_path=db)

    current_rank_identity = development_store.current_rank_identity
    calls = 0

    def counted_rank_identity(*, day):
        nonlocal calls
        calls += 1
        return current_rank_identity(day=day)

    monkeypatch.setattr(
        development_store,
        "current_rank_identity",
        counted_rank_identity,
    )
    editorial_runs._current_editorial_lineage_cached.cache_clear()

    investment = editorial_runs.editorial_insight_dates_payload(
        audience="investment",
        db_path=db,
    )
    engineering = editorial_runs.editorial_insight_dates_payload(
        audience="ai_engineering",
        db_path=db,
    )

    assert investment["available"] is True
    assert engineering["available"] is True
    assert calls == 1
    editorial_runs._current_editorial_lineage_cached.cache_clear()


def test_reader_and_api_reject_editorial_from_superseded_rank_lineage(
    tmp_path, monkeypatch
):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "draft.json"
    draft_path.write_text(json.dumps(_draft(workspace)), encoding="utf-8")
    db = tmp_path / "editorial.db"
    editorial_runs.import_result(workspace, draft_path, db_path=db)

    replacement_rank_sha = "b" * 64
    _routing_fixture(
        tmp_path / "routing",
        directory="replacement",
        run_id="routing-v3",
        source_rank_input_sha256=replacement_rank_sha,
        source_event_run_id="event-run-v3",
        source_feed_run_id="feed-run-v3",
        cohort_sha256="cohort-sha-v3",
    )
    monkeypatch.setattr(
        development_store,
        "current_rank_identity",
        lambda *, day: {
            "day": day,
            "rank_version": development_attention.DAILY_RANK_VERSION,
            "rank_input_sha256": replacement_rank_sha,
            "event_run_id": "event-run-v3",
            "feed_run_id": "feed-run-v3",
        },
    )

    payload = editorial_runs.editorial_insights_payload(
        audience="investment", day=DAY, db_path=db
    )
    dates = editorial_runs.editorial_insight_dates_payload(
        audience="investment", db_path=db
    )

    assert payload["available"] is False
    assert payload["run"] is None
    assert "No current complete daily editorial run" in payload["reason"]
    assert dates["available"] is False
    assert dates["dates"] == []

    monkeypatch.setattr(editorial_runs, "DEFAULT_DB", db)
    monkeypatch.setattr(insight_runs, "DEFAULT_DB", tmp_path / "missing-insights.db")
    kept = CLIENT.get(
        f"/api/insights?audience=investment&date={DAY}&status=kept"
    ).json()
    api_dates = CLIENT.get("/api/insights/dates?audience=investment").json()

    assert kept["content_kind"] == "candidate_decisions"
    assert kept["available"] is False
    assert api_dates["dates"] == []


class _RawResponse:
    def __init__(self, response):
        self._response = response
        self.headers = {"x-litellm-response-cost": "0.001"}

    def parse(self):
        return self._response


class _EmbeddingAPI:
    def __init__(self):
        self.calls = []
        self.with_raw_response = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        data = []
        for index, _ in enumerate(kwargs["input"]):
            vector = [1.0, 0.0, 0.0] if index < 2 else [0.0, 1.0, 0.0]
            data.append(SimpleNamespace(index=index, embedding=vector))
        return _RawResponse(
            SimpleNamespace(
                data=data,
                usage=SimpleNamespace(total_tokens=123),
            )
        )


class _EmbeddingClient:
    def __init__(self):
        self.embeddings = _EmbeddingAPI()

    def with_options(self, **_kwargs):
        return self


def test_embedding_index_is_packet_keyed_reused_and_queryable(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path, monkeypatch)
    db = tmp_path / "editorial.db"
    client = _EmbeddingClient()

    first = editorial_runs.index_workspace(
        workspace,
        db_path=db,
        client_factory=lambda: client,
    )
    second = editorial_runs.index_workspace(
        workspace,
        db_path=db,
        client_factory=lambda: (_ for _ in ()).throw(AssertionError("must reuse index")),
    )
    similar = editorial_runs.similar_events(
        workspace,
        event_id="event-a",
        db_path=db,
        limit=2,
    )

    assert first["indexed_count"] == 3
    assert first["input_tokens"] == 123
    assert second["indexed_count"] == 0
    assert second["reused_count"] == 3
    assert len(client.embeddings.calls) == 1
    assert similar["items"][0]["event_id"] == "event-b"
    assert np.isclose(similar["items"][0]["cosine_similarity"], 1.0)


def test_investment_context_is_complete_structured_skill_packet(capsys):
    context = editorial_runs.investment_context()
    portfolio = context["portfolio"]

    assert context["schema_version"] == "bit-investment-context-v5"
    assert len(portfolio["holdings"]) == 34
    assert round(sum(item["weight_pct"] for item in portfolio["holdings"]), 2) == 97.43
    assert {item["name"] for item in portfolio["holdings"]} >= {
        "Alphabet",
        "Microsoft",
        "NVIDIA",
    }
    assert context["research_process"]["challenge_process"]["principle"]
    assert context["outside_portfolio_policy"]["label"] == "Outside the disclosed portfolio"
    profiles = context["company_profiles"]
    assert context["company_profiles_reviewed_at"] == "2026-07-28"
    assert len(profiles) == 37
    assert [profile["name"] for profile in profiles] == [
        holding["name"] for holding in editorial_runs._covered_holdings(context)
    ]
    assert len({profile["ticker"] for profile in profiles}) == 37
    assert context["event_company_mapping"] == {
        "candidate_universe": "all_profiles",
        "connection_types": ["direct", "indirect", "none"],
        "thesis_effects": [
            "supports",
            "challenges",
            "mixed",
            "unclear",
            "no_public_thesis",
        ],
        "shortlist_rule": (
            "Review the compact index for every Event, then retrieve complete "
            "profiles only for companies with a credible causal connection."
        ),
        "publication_rule": (
            "Publish direct connections and well-evidenced material indirect "
            "connections. Suppress none and weak indirect matches."
        ),
    }
    assert {profile["bit_public_view"]["grade"] for profile in profiles} <= {
        "explicit_thesis",
        "commentary",
        "none",
    }
    assert {profile["bit_public_view"]["source_scope"] for profile in profiles} <= {
        "firm",
        "flagship",
        "other_product",
        "mixed",
        "none",
    }
    assert all(profile["analyst_context"]["frontier_ai_channels"] for profile in profiles)
    by_name = {profile["name"]: profile for profile in profiles}
    assert all(
        "frontier_lab_relevance" not in profile
        and "frontier_lab_relevance_reason" not in profile
        for profile in profiles
    )
    assert by_name["IREN"]["bit_public_view"]["grade"] == "explicit_thesis"
    assert by_name["Amazon"]["bit_public_view"] == {
        "grade": "none",
        "source_scope": "none",
        "thesis": None,
        "edge": None,
        "signals": [],
        "countercase": None,
        "sources": [],
    }
    assert by_name["Kaspi"]["bit_public_view"]["source_scope"] == "other_product"
    assert by_name["Grindr"]["bit_public_view"]["source_scope"] == "flagship"
    assert "Finisar" not in by_name["Coherent"]["aliases"]

    current = context["portfolio_current_top_ten"]
    assert current["as_of"] == "2026-06-30"
    assert current["position_count"] == 28
    assert len(current["holdings"]) == 10
    assert current["source"]["isin"] == "DE000A2N8127"
    assert by_name["Marvell"]["bit_public_view"]["grade"] == "commentary"
    assert by_name["Marvell"]["bit_public_view"]["source_scope"] == "flagship"
    assert {holding["name"] for holding in current["holdings"]} - {
        holding["name"] for holding in portfolio["holdings"]
    } == {"SanDisk", "Marvell", "Infineon"}

    assert editorial_cli.main(
        ["context", "--audience", "investment", "--json", "--no-input"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["format"] == "json"
    assert payload["data"]["projection"] == "full"
    assert payload["data"]["context"]["schema_version"] == "bit-investment-context-v5"
    assert payload["data"]["path"].endswith("references/bit-investment-context.json")

    assert editorial_cli.main(
        [
            "context",
            "--audience",
            "investment",
            "--compact",
            "--json",
            "--no-input",
        ]
    ) == 0
    compact = json.loads(capsys.readouterr().out)
    assert compact["data"]["projection"] == "compact"
    assert "company_profiles" not in compact["data"]["context"]
    assert len(compact["data"]["context"]["company_profile_index"]) == 37
    compact_by_name = {
        item["name"]: item
        for item in compact["data"]["context"]["company_profile_index"]
    }
    assert set(compact_by_name["GCL-Poly"]) == {
        "name",
        "ticker",
        "aliases",
        "bit_public_view_grade",
        "bit_public_view_source_scope",
    }


def test_ai_engineering_context_encodes_bit_operating_and_relevance_boundary(capsys):
    assert editorial_cli.main(
        ["context", "--audience", "ai_engineering", "--json", "--no-input"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    context = payload["data"]["context"]

    assert payload["data"]["format"] == "markdown"
    assert "Aion as an agentic research platform" in context
    assert "scores, alerts, signals, and insights" in context
    assert "Current and high priority" in context
    assert "Do not confuse “an agent could use this”" in context
    assert "BIT's private architecture" in context
    assert "case-study\ntestbed" in context


def test_company_context_lookup_is_exact_and_machine_readable(capsys):
    assert editorial_cli.main(
        ["company-context", "--company", "MSFT", "--json", "--no-input"]
    ) == 0
    ticker_match = json.loads(capsys.readouterr().out)
    assert ticker_match["command"] == "daily-intelligence.company-context"
    assert ticker_match["data"]["matched_by"] == "ticker"
    assert ticker_match["data"]["profile"]["name"] == "Microsoft"
    assert ticker_match["data"]["portfolio_holding"]["name"] == "Microsoft"

    assert editorial_cli.main(
        ["company-context", "--company", "Google", "--json", "--no-input"]
    ) == 0
    alias_match = json.loads(capsys.readouterr().out)
    assert alias_match["data"]["matched_by"] == "alias"
    assert alias_match["data"]["profile"]["name"] == "Alphabet"

    assert editorial_cli.main(
        ["company-context", "--company", "not-a-company", "--json", "--no-input"]
    ) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "error"
    assert missing["error"]["code"] == "E_COMPANY_NOT_FOUND"
    assert missing["error"]["retryable"] is False
    assert "--compact" in missing["error"]["hint"]


def test_investment_company_universe_payload_is_complete_and_dated():
    payload = editorial_runs.investment_company_universe_payload()
    research_memos = sum(
        company["research_memo"] is not None for company in payload["companies"]
    )
    assert research_memos == 37

    assert payload["schema_version"] == "investment-company-universe-v5"
    assert payload["mapping_policy"]["candidate_universe"] == "all_profiles"
    assert payload["counts"] == {
        "companies": 37,
        "current_top_ten": 10,
        "audited_baseline": 34,
        "later_top_ten_additions": 3,
        "research_memos": research_memos,
        "frontier_ai_channels": 63,
        "bit_public_views": 14,
        "bit_public_view_grades": {
            "explicit_thesis": 4,
            "commentary": 10,
            "none": 23,
        },
    }
    companies = {company["name"]: company for company in payload["companies"]}
    assert companies["Amazon"]["portfolio_context"] == {
        "reference_holding": {
            "as_of": "2026-06-30",
            "weight_pct": 10.4,
            "basis": "current_top_ten",
            "currently_confirmed": True,
        },
        "current_top_ten": {
            "as_of": "2026-06-30",
            "rank": 1,
            "weight_pct": 10.4,
        },
        "audited_baseline": {
            "as_of": "2025-12-31",
            "weight_pct": 1.78,
        },
    }
    assert companies["SanDisk"]["portfolio_context"]["audited_baseline"] is None
    assert companies["SanDisk"]["portfolio_context"]["current_top_ten"]["rank"] == 4
    assert companies["Microsoft"]["portfolio_context"]["reference_holding"] == {
        "as_of": "2025-12-31",
        "weight_pct": 2.89,
        "basis": "audited_baseline",
        "currently_confirmed": False,
    }
    assert companies["Microsoft"]["bit_public_view"]["grade"] == "commentary"
    assert companies["Microsoft"]["research_memo"]["memo"][
        "business_and_economics"
    ]["summary"]
    assert companies["IREN"]["research_memo"]["provenance"]["model"] == "gpt-5.6-sol"
    assert companies["Amazon"]["research_memo"]["memo"][
        "business_and_economics"
    ]["summary"]
    assert companies["Microsoft"]["analyst_context"]["frontier_ai_channels"]
    assert companies["Microsoft"]["identity_sources"]
    assert "frontier_lab_relevance" not in companies["GCL-Poly"]


def test_cli_default_json_and_stable_validation_error(tmp_path, monkeypatch, capsys):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "invalid.json"
    draft_path.write_text(json.dumps(editorial.draft_template(editorial_runs.load_manifest(workspace))), encoding="utf-8")

    assert editorial_cli.main(["contract", "--no-input"]) == 0
    success = json.loads(capsys.readouterr().out)
    assert success["schema_version"] == "1.0"
    assert success["status"] == "ok"
    assert success["error"] is None
    assert (
        success["data"]["investment_context_schema_version"]
        == "bit-investment-context-v5"
    )
    contract = success["data"]["draft"]
    assert contract["max_insights_per_audience"] is None
    assert set(contract["analysis_shapes"]) == {"investment", "ai_engineering"}
    assert set(contract["analysis_shapes"]["ai_engineering"]) == {"decision_rule"}

    assert editorial_cli.main(
        [
            "validate",
            "--workspace",
            str(workspace),
            "--draft",
            str(draft_path),
            "--no-input",
        ]
    ) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure["status"] == "error"
    assert failure["error"]["code"] == "E_INVALID_INPUT"
    assert failure["error"]["retryable"] is False

    assert editorial_cli.main(["prepare", "--no-input"]) == 2
    missing_argument = json.loads(capsys.readouterr().out)
    assert missing_argument["command"] == "daily-intelligence"
    assert missing_argument["error"]["code"] == "E_INVALID_INPUT"


def test_cli_preflight_and_additive_run_projections(
    tmp_path, monkeypatch, capsys
):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "draft.json"
    draft_path.write_text(json.dumps(_draft(workspace)), encoding="utf-8")
    db = tmp_path / "editorial.db"

    assert editorial_cli.main(
        [
            "preflight",
            "--workspace",
            str(workspace),
            "--draft",
            str(draft_path),
            "--json",
            "--no-input",
        ]
    ) == 0
    preflight = json.loads(capsys.readouterr().out)
    assert preflight["command"] == "daily-intelligence.preflight"
    assert preflight["data"]["complete"] is True
    assert preflight["data"]["counts"]["candidate_pairs"] == 4

    assert editorial_cli.main(
        [
            "import-result",
            "--workspace",
            str(workspace),
            "--draft",
            str(draft_path),
            "--db",
            str(db),
            "--projection",
            "summary",
            "--json",
            "--no-input",
        ]
    ) == 0
    imported = json.loads(capsys.readouterr().out)["data"]
    run_id = imported["run_id"]
    assert imported["projection"] == "summary"
    assert imported["run"]["counts"] == {
        "candidate_events": 3,
        "candidate_pairs": 4,
        "insights": 2,
        "citations": 2,
        "included": 3,
        "not_selected": 1,
    }
    assert "insights" not in imported["run"]

    expected_keys = {
        "summary": "counts",
        "insights": "insights",
        "citations": "citations",
        "dispositions": "dispositions",
    }
    projections = {}
    for projection, expected_key in expected_keys.items():
        assert editorial_cli.main(
            [
                "inspect-run",
                "--run-id",
                run_id,
                "--db",
                str(db),
                "--projection",
                projection,
                "--json",
                "--no-input",
            ]
        ) == 0
        payload = json.loads(capsys.readouterr().out)["data"]
        assert payload["projection"] == projection
        assert expected_key in payload["run"]
        projections[projection] = payload["run"]

    assert projections["insights"]["insights"][0] == {
        "audience": "ai_engineering",
        "citation_ids": [projections["citations"]["citations"][0]["citation_id"]],
        "display_rank": 1,
        "event_ids": ["event-a"],
        "insight_id": projections["insights"]["insights"][0]["insight_id"],
        "local_id": "engineering-inkling",
        "title": "Test open-model serving before adopting the launch claim",
    }
    assert len(projections["citations"]["citations"]) == 2
    assert len(projections["dispositions"]["dispositions"]) == 4
