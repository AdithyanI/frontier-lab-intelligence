import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient

from fli.insights import editorial
from fli.insights import editorial_cli
from fli.insights import editorial_runs
from fli.insights import runs as insight_runs
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs
from fli.web.app import app


DAY = "2026-07-15"
CLIENT = TestClient(app)


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


def _routing_fixture(root: Path) -> Path:
    path = root / "current" / "routing.db"
    conn = routing_runs.connect_run(path)
    now = "2026-07-17T12:00:00+00:00"
    conn.execute(
        """INSERT INTO run_meta (
               singleton, run_id, day, model, reasoning_effort,
               prompt_version, prompt_sha256, schema_version,
               source_event_run_id, source_feed_run_id, source_artifact_db,
               selection_kind, selection_limit, requested_event_id,
               cohort_sha256, expected_count, created_at, updated_at)
           VALUES (1, 'routing-current', ?, 'gpt-5.4-mini', 'high', ?, ?, ?,
                   'event-run', 'feed-run', 'artifacts.db', 'top_ranked', 3,
                   NULL, 'cohort-sha', 3, ?, ?)""",
        (
            DAY,
            routing_model.PROMPT_VERSION,
            routing_model.prompt_sha256(),
            routing_model.SCHEMA_VERSION,
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
                   event_id, feed_rank, root_url, snapshot_content_sha256,
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
            "skill_version": "fli-daily-intelligence-v3",
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
                "excerpt": None,
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
                "excerpt": None,
            },
        ],
    }


def test_prepare_freezes_union_positive_workspace_and_reuses_it(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path, monkeypatch)
    manifest = editorial_runs.load_manifest(workspace)

    assert manifest["counts"] == {
        "events": 3,
        "candidate_pairs": 4,
        "investment": 2,
        "ai_engineering": 2,
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
        "skill_version": "fli-daily-intelligence-v3",
        "model": "codex-test",
        "notes": "Second editorial pass.",
    }
    assert payload["run"]["counts"]["insights"] == 1
    assert [item["audience"] for item in payload["items"]] == ["investment"]
    assert payload["items"][0]["rank"] == 1
    assert payload["items"][0]["rank_rationale"].startswith("Ranked first")
    assert payload["items"][0]["day"] == DAY
    assert payload["items"][0]["title"] == "Revised distribution judgment"
    assert payload["items"][0]["events"][0]["event_id"] == "event-a"
    assert "root_url" not in payload["items"][0]["events"][0]
    assert payload["items"][0]["citations"][0]["local_id"] == "source-a"
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
            "suppressed_count": 0,
            "evaluated_count": 2,
            "item_count": 1,
        }
    ]


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

    assert context["schema_version"] == "bit-investment-context-v1"
    assert len(portfolio["holdings"]) == 34
    assert round(sum(item["weight_pct"] for item in portfolio["holdings"]), 2) == 97.43
    assert {item["name"] for item in portfolio["holdings"]} >= {
        "Alphabet",
        "Microsoft",
        "NVIDIA",
    }
    assert context["research_process"]["challenge_process"]["principle"]
    assert context["outside_portfolio_policy"]["label"] == "Outside the disclosed portfolio"

    assert editorial_cli.main(
        ["context", "--audience", "investment", "--json", "--no-input"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["format"] == "json"
    assert payload["data"]["context"]["schema_version"] == "bit-investment-context-v1"
    assert payload["data"]["path"].endswith("references/bit-investment-context.json")


def test_cli_default_json_and_stable_validation_error(tmp_path, monkeypatch, capsys):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "invalid.json"
    draft_path.write_text(json.dumps(editorial.draft_template(editorial_runs.load_manifest(workspace))), encoding="utf-8")

    assert editorial_cli.main(["contract", "--no-input"]) == 0
    success = json.loads(capsys.readouterr().out)
    assert success["schema_version"] == "1.0"
    assert success["status"] == "ok"
    assert success["error"] is None
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
