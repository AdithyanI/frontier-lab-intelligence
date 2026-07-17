import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from fli.insights import editorial
from fli.insights import editorial_cli
from fli.insights import editorial_runs
from fli.routing import model as routing_model
from fli.routing import runs as routing_runs


DAY = "2026-07-15"


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
            "skill_version": "fli-daily-intelligence-v1",
            "model": "codex-test",
            "notes": None,
        },
        "insights": [
            {
                "local_id": "investment-inkling",
                "audience": "investment",
                "rank": 1,
                "title": "Open models shorten the enterprise distribution path",
                "what_changed": "Inkling launched with weights and enterprise distribution support.",
                "interpretation": "Distribution evidence matters more than launch attention alone.",
                "impact_chain": [
                    "Open weights become available",
                    "Enterprise gateways reduce adoption friction",
                    "Closed API differentiation faces a new test",
                ],
                "evidence_limitations": ["No customer adoption or unit economics are disclosed."],
                "next_step": "Measure adoption and serving economics across one enterprise workload.",
                "analysis": {
                    **editorial.investment_analysis_template(),
                    "financial_driver": "Inference cost and platform gross margin remain unknown.",
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
                "title": "Test open-model serving before adopting the launch claim",
                "what_changed": "Inkling shipped downloadable weights and implementation artifacts.",
                "interpretation": "A bounded serving test can establish whether it transfers locally.",
                "impact_chain": ["Weights become available", "Local serving becomes testable"],
                "evidence_limitations": ["The packet does not establish local latency or quality."],
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
    assert editorial_runs.search_workspace(workspace, query="Inkling")["match_count"] == 2

    reused = editorial_runs.prepare_workspace(
        day=DAY,
        routing_root=tmp_path / "routing",
        insights_db=tmp_path / "missing-insights.db",
        workspace_root=tmp_path / "workspaces",
    )
    assert reused["reused"] is True


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
    assert conn.execute("SELECT COUNT(*) FROM editorial_candidate").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM editorial_event_disposition").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM editorial_run").fetchone()[0] == 1
    conn.close()


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


def test_cli_default_json_and_stable_validation_error(tmp_path, monkeypatch, capsys):
    workspace = _workspace(tmp_path, monkeypatch)
    draft_path = workspace / "invalid.json"
    draft_path.write_text(json.dumps(editorial.draft_template(editorial_runs.load_manifest(workspace))), encoding="utf-8")

    assert editorial_cli.main(["contract", "--no-input"]) == 0
    success = json.loads(capsys.readouterr().out)
    assert success["schema_version"] == "1.0"
    assert success["status"] == "ok"
    assert success["error"] is None

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
