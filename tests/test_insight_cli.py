import json
from pathlib import Path
from types import SimpleNamespace

from fli import audience_routing, audience_routing_runs, insight_cli


EVENT_ID = "event-spike-1"


def _packet(*, event_id: str = EVENT_ID, day: str = "2026-07-13"):
    return audience_routing.RoutingPacket(
        event_id=event_id,
        day=day,
        sources=(
            audience_routing.EvidenceSource(
                source_type="x_post",
                source_id="root-1",
                url="https://x.com/alice/status/root-1",
                text="We published a measured harness evaluation.",
                author="@alice",
                relation="root",
            ),
            audience_routing.EvidenceSource(
                source_type="artifact",
                source_id="artifact-1",
                url="https://example.com/harness-eval",
                text="The harness reduced recovery failures from 20% to 8%.",
                title="Harness evaluation",
                relation="linked_artifact",
            ),
            audience_routing.EvidenceSource(
                source_type="x_post",
                source_id="reaction-1",
                url="https://x.com/bob/status/reaction-1",
                text="Huge if true.",
                author="@bob",
                relation="quote",
            ),
        ),
    )


def _routing_fixture(
    root: Path,
    *,
    run_id: str = "current-run",
    day: str = "2026-07-13",
    event_id: str = EVENT_ID,
) -> Path:
    path = root / run_id / "routing.db"
    conn = audience_routing_runs.connect_run(path)
    packet = _packet(event_id=event_id, day=day)
    now = "2026-07-15T20:00:00+00:00"
    with conn:
        conn.execute(
            """INSERT INTO run_meta
               (singleton, run_id, day, model, reasoning_effort,
                prompt_version, prompt_sha256, schema_version,
                source_event_run_id, source_feed_run_id, source_artifact_db,
                selection_kind, selection_limit, requested_event_id,
                cohort_sha256, expected_count, created_at, updated_at)
               VALUES (1, ?, ?, 'gpt-5.4-mini', 'high',
                       ?, 'prompt-sha', ?, 'event-run', 'feed-run',
                       'artifacts.db', 'top_ranked', 100, NULL,
                       'cohort-sha', 1, ?, ?)""",
            (
                run_id,
                day,
                audience_routing.PROMPT_VERSION,
                audience_routing.SCHEMA_VERSION,
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, snapshot_content_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                status, attempts, ai_engineering_relevant,
                ai_engineering_reason, investment_relevant,
                investment_reason, updated_at)
               VALUES (?, 4, 'https://x.com/alice/status/root-1', 'snapshot',
                       ?, ?, ?, ?, 'complete', 1, 1, 'Useful to engineers.',
                       1, 'Useful to investors.', ?)""",
            (
                event_id,
                audience_routing_runs._canonical_json(
                    audience_routing_runs._packet_payload(packet)
                ),
                packet.evidence_sha256,
                audience_routing.render_input(packet),
                packet.input_sha256,
                now,
            ),
        )
    conn.close()
    return path


def _add_routed_event(
    path: Path,
    *,
    event_id: str,
    feed_rank: int,
    ai_engineering_relevant: bool,
    investment_relevant: bool,
) -> None:
    packet = audience_routing.RoutingPacket(
        event_id=event_id,
        day="2026-07-13",
        sources=(
            audience_routing.EvidenceSource(
                source_type="x_post",
                source_id=f"root-{event_id}",
                url=f"https://x.com/alice/status/root-{event_id}",
                text=f"Measured evidence for {event_id}.",
                author="@alice",
                relation="root",
            ),
        ),
    )
    conn = audience_routing_runs.connect_run(path)
    now = "2026-07-15T20:00:00+00:00"
    with conn:
        conn.execute(
            """UPDATE run_meta
               SET expected_count = expected_count + 1
               WHERE singleton = 1"""
        )
        conn.execute(
            """INSERT INTO routing_item
               (event_id, feed_rank, root_url, snapshot_content_sha256,
                packet_json, evidence_sha256, input_text, input_sha256,
                status, attempts, ai_engineering_relevant,
                ai_engineering_reason, investment_relevant,
                investment_reason, updated_at)
               VALUES (?, ?, ?, 'snapshot', ?, ?, ?, ?, 'complete', 1, ?,
                       'Engineering reason.', ?, 'Investment reason.', ?)""",
            (
                event_id,
                feed_rank,
                f"https://x.com/alice/status/root-{event_id}",
                audience_routing_runs._canonical_json(
                    audience_routing_runs._packet_payload(packet)
                ),
                packet.evidence_sha256,
                audience_routing.render_input(packet),
                packet.input_sha256,
                int(ai_engineering_relevant),
                int(investment_relevant),
                now,
            ),
        )
    conn.close()


class _RawResponse:
    def __init__(self, response):
        self.response = response
        self.headers = {"x-litellm-response-cost": "0.0125"}

    def parse(self):
        return self.response


class _RawAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = {
            "decision": "surface",
            "suppression_reason": None,
            "title": "Make agent recovery measurable",
            "summary": "Alice reports a measured harness-recovery improvement.",
            "implication": "The harness design may improve agent reliability.",
            "next_step": "Reproduce the evaluation on one internal workflow.",
        }
        response = SimpleNamespace(
            id=f"response-{len(self.calls)}",
            model=kwargs["model"],
            status="completed",
            output_text=json.dumps(output),
            usage=SimpleNamespace(
                input_tokens=2_400,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_280,
                    cache_write_tokens=0,
                ),
                output_tokens=120,
            ),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
            "output_text": response.output_text,
        }
        return _RawResponse(response)


class _Client:
    def __init__(self):
        self.raw_api = _RawAPI()
        self.responses = SimpleNamespace(with_raw_response=self.raw_api)

    def with_options(self, **_):
        return self


def test_contract_command_exposes_exact_schema(capsys):
    assert insight_cli.main(["contract", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "ok"
    assert payload["schema_version"] == "1.0"
    assert payload["data"]["output_format"] == insight_cli.insight_generation.OUTPUT_FORMAT
    assert payload["data"]["model_view"].endswith("artifacts_only")


def test_dry_run_resolves_latest_route_and_dumps_first_party_requests(
    tmp_path, capsys
):
    routing_root = tmp_path / "routing"
    _routing_fixture(routing_root)
    dump = tmp_path / "dump"

    exit_code = insight_cli.main(
        [
            "run",
            "--event-id",
            EVENT_ID,
            "--routing-root",
            str(routing_root),
            "--dump-dir",
            str(dump),
            "--dry-run",
            "--no-input",
            "--progress",
            "off",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    request = json.loads((dump / "investment-request.json").read_text())

    assert exit_code == 0
    assert payload["data"]["day"] == "2026-07-13"
    assert payload["data"]["will_call_model"] is False
    assert "Harness evaluation" in request["input"]
    assert "Huge if true" not in request["input"]
    assert request["text"]["format"] == insight_cli.insight_generation.OUTPUT_FORMAT
    assert request["prompt_cache_retention"] == "24h"


def test_run_records_results_cache_and_cost(tmp_path, capsys):
    routing_root = tmp_path / "routing"
    _routing_fixture(routing_root)
    dump = tmp_path / "dump"
    client = _Client()
    db = tmp_path / "insights.db"

    exit_code = insight_cli.main(
        [
            "run",
            "--event-id",
            EVENT_ID,
            "--routing-root",
            str(routing_root),
            "--dump-dir",
            str(dump),
            "--db",
            str(db),
            "--run-id",
            "test-insight-run",
            "--progress",
            "off",
            "--json",
        ],
        client_factory=lambda: client,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert {
        key: payload["data"]["telemetry"][key]
        for key in (
            "input_tokens",
            "cached_tokens",
            "cache_write_tokens",
            "output_tokens",
            "reported_cost_usd",
            "cache_hit_requests",
            "request_count",
        )
    } == {
        "input_tokens": 4_800,
        "cached_tokens": 2_560,
        "cache_write_tokens": 0,
        "output_tokens": 240,
        "reported_cost_usd": 0.025,
        "cache_hit_requests": 2,
        "request_count": 2,
    }
    assert len(payload["data"]["evaluations"]) == 2
    assert (dump / "result.json").is_file()
    assert len(client.raw_api.calls) == 2

    second_exit = insight_cli.main(
        [
            "run",
            "--event-id",
            EVENT_ID,
            "--routing-root",
            str(routing_root),
            "--dump-dir",
            str(tmp_path / "resumed-dump"),
            "--db",
            str(db),
            "--run-id",
            "test-insight-run",
            "--progress",
            "off",
            "--json",
        ],
        client_factory=lambda: (_ for _ in ()).throw(
            AssertionError("resume must not create a model client")
        ),
    )
    capsys.readouterr()

    assert second_exit == 0
    assert len(client.raw_api.calls) == 2


def test_missing_envelope_uses_stable_validation_error(tmp_path, capsys):
    exit_code = insight_cli.main(
        [
            "run",
            "--event-id",
            "missing",
            "--routing-root",
            str(tmp_path),
            "--dry-run",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "E_INVALID_INPUT"
    assert payload["error"]["retryable"] is False


def test_refresh_dry_run_plans_current_routes_without_writes(
    tmp_path, capsys, monkeypatch
):
    routing_root = tmp_path / "routing"
    _routing_fixture(routing_root)
    db = tmp_path / "insights.db"
    dump = tmp_path / "dump"
    monkeypatch.setattr(
        audience_routing_runs,
        "_published_event_source",
        lambda: {"event_run_id": "event-run", "feed_run_id": "feed-run"},
    )

    exit_code = insight_cli.main(
        [
            "refresh",
            "--through",
            "2026-07-13",
            "--limit-per-day",
            "10",
            "--routing-root",
            str(routing_root),
            "--db",
            str(db),
            "--dump-dir",
            str(dump),
            "--dry-run",
            "--progress",
            "off",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["data"]["event_count"] == 1
    assert payload["data"]["request_count"] == 2
    assert payload["data"]["will_call_model"] is False
    assert payload["data"]["workers"] == 2
    assert not db.exists()
    assert not dump.exists()


def test_refresh_scales_from_ten_to_all_and_reuses_completed_requests(
    tmp_path, capsys, monkeypatch
):
    routing_root = tmp_path / "routing"
    run_db = _routing_fixture(routing_root)
    _add_routed_event(
        run_db,
        event_id="event-spike-2",
        feed_rank=7,
        ai_engineering_relevant=True,
        investment_relevant=False,
    )
    monkeypatch.setattr(
        audience_routing_runs,
        "_published_event_source",
        lambda: {"event_run_id": "event-run", "feed_run_id": "feed-run"},
    )
    client = _Client()
    db = tmp_path / "insights.db"
    common = [
        "refresh",
        "--through",
        "2026-07-13",
        "--routing-root",
        str(routing_root),
        "--db",
        str(db),
        "--dump-dir",
        str(tmp_path / "dump"),
        "--workers",
        "3",
        "--progress",
        "off",
        "--json",
    ]

    assert insight_cli.main(
        [*common, "--limit-per-day", "1"], client_factory=lambda: client
    ) == 0
    first = json.loads(capsys.readouterr().out)["data"]
    assert first["request_count"] == 2
    assert first["telemetry"]["model_requests"] == 2
    assert len(client.raw_api.calls) == 2

    assert insight_cli.main(
        [*common, "--limit-per-day", "1"], client_factory=lambda: client
    ) == 0
    resumed = json.loads(capsys.readouterr().out)["data"]
    assert resumed["telemetry"]["model_requests"] == 0
    assert resumed["telemetry"]["reused_results"] == 2
    assert resumed["telemetry"]["reported_cost_usd"] == 0
    assert len(client.raw_api.calls) == 2

    assert insight_cli.main(
        [*common, "--all-routed"], client_factory=lambda: client
    ) == 0
    expanded = json.loads(capsys.readouterr().out)["data"]
    assert expanded["event_count"] == 2
    assert expanded["request_count"] == 3
    assert expanded["telemetry"]["model_requests"] == 1
    assert expanded["telemetry"]["reused_results"] == 2
    assert len(client.raw_api.calls) == 3


def test_refresh_rejects_same_event_on_multiple_days(tmp_path, capsys, monkeypatch):
    routing_root = tmp_path / "routing"
    _routing_fixture(
        routing_root,
        run_id="route-day-one",
        day="2026-07-12",
    )
    _routing_fixture(
        routing_root,
        run_id="route-day-two",
        day="2026-07-13",
    )
    monkeypatch.setattr(
        audience_routing_runs,
        "_published_event_source",
        lambda: {"event_run_id": "event-run", "feed_run_id": "feed-run"},
    )

    exit_code = insight_cli.main(
        [
            "refresh",
            "--through",
            "2026-07-13",
            "--days",
            "2",
            "--routing-root",
            str(routing_root),
            "--dry-run",
            "--progress",
            "off",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "E_INVALID_INPUT"
    assert "appears on both" in payload["error"]["message"]
