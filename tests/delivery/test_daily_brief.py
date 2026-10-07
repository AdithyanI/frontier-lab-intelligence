from __future__ import annotations

import json

from fastapi.testclient import TestClient
import httpx

from fli.delivery import daily_brief
from fli.web.app import app


DAY = "2026-07-17"
CLIENT = TestClient(app)


def _payload() -> dict:
    payload = {
        "content_kind": "investment_agent",
        "available": True,
        "reason": None,
        "date": DAY,
        "requested_date": DAY,
        "audience": "investment",
        "run": {"result_sha256": "a" * 64},
        "items": [
            {
                "daily_rank": rank,
                "headline": f"Insight {rank}",
                "what_changed": f"Decision-useful interpretation {rank}.",
                "connections": [
                    {
                        "mechanism": f"Causal path {rank}",
                        "companies": [
                            {
                                "ticker": "NTSK",
                                "bet_id": "NTSK-B1",
                                "threshold_met": False,
                                "impact": f"Take next step {rank}.",
                            }
                        ],
                    }
                ],
                "company_names": {"NTSK": "Netskope"},
                "provenance": {"primary_event_id": f"event-{rank}"},
            }
            for rank in range(1, 7)
        ],
    }
    payload["items"][0]["what_changed"] = (
        "This complete interpretation must remain visible in Slack. " * 60
        + "FULL_INTERPRETATION_END"
    )
    return payload


def _engineering_payload() -> dict:
    return {
        "content_kind": "engineering_agent",
        "available": True,
        "reason": None,
        "date": DAY,
        "requested_date": DAY,
        "audience": "ai_engineering",
        "run": {"result_sha256": "b" * 64},
        "items": [
            {
                "daily_rank": 4,
                "headline": "Layered checks make costly research claims auditable",
                "what_changed": "A research agent combined formal proof and reduced-system tests.",
                "lands": [
                    {
                        "surface_id": "EVAL",
                        "surface_name": "Evaluation",
                        "why": "Use layered checks when an end-to-end experiment is too expensive.",
                    }
                ],
                "provenance": {"primary_event_id": "engineering-event"},
            }
        ],
    }


def _settings() -> daily_brief.DeliverySettings:
    return daily_brief.DeliverySettings(
        slack_webhook_url="https://hooks.slack.test/services/redacted",
        slack_destination_label="#frontier-lab-intelligence",
    )


def test_slack_delivery_shows_every_insight_with_company_directions(
    monkeypatch,
):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, text="ok")

    def unexpected_pdf(*_args, **_kwargs):
        raise AssertionError("Slack delivery must not generate a PDF")

    monkeypatch.setattr(
        daily_brief.pdf_report,
        "get_or_create_report",
        unexpected_pdf,
    )
    result = daily_brief.deliver_daily_brief(
        _payload(),
        channel="slack",
        settings=_settings(),
        slack_transport=httpx.MockTransport(handler),
    )

    rendered = json.dumps(captured, ensure_ascii=False)
    assert result["status"] == "sent"
    assert result["insight_count"] == 6
    assert "Insight 1" in rendered
    assert "FULL_INTERPRETATION_END" in rendered
    assert "Read full brief" in rendered
    assert "What changed" in rendered
    assert "How this reaches companies" in rendered
    assert "Netskope (NTSK)" in rendered
    assert "↑ Upside" in rendered
    assert "Insight 2" in rendered
    assert "Decision-useful interpretation 2." in rendered
    assert "Insight 5" in rendered
    assert "Insight 6" in rendered
    assert "Decision-useful interpretation 6." in rendered
    assert "more cited Insights" not in rendered
    assert "/api/insights/report.pdf" not in rendered
    assert "Download PDF" not in rendered
    assert "hooks.slack" not in rendered
    section_text = [
        block["text"]["text"]
        for block in captured["blocks"]
        if block["type"] == "section"
    ]
    assert all(len(text) <= 3000 for text in section_text)


def test_slack_uses_brief_positions_instead_of_feed_ranks():
    payload = _payload()
    for item, feed_rank in zip(payload["items"], (4, 12, 24, 25, 30, 31), strict=True):
        item["daily_rank"] = feed_rank

    rendered = json.dumps(daily_brief._slack_payload(payload), ensure_ascii=False)

    assert "*1. Insight 1*" in rendered
    assert "*2. Insight 2*" in rendered
    assert "*4. Insight 4*" in rendered
    assert "*12. Insight 2*" not in rendered
    assert "*25. Insight 4*" not in rendered


def test_engineering_slack_is_simple_and_lists_surfaces():
    rendered = json.dumps(
        daily_brief._slack_payload(_engineering_payload()),
        ensure_ascii=False,
    )

    assert "AI Engineering brief" in rendered
    assert "*1. Layered checks make costly research claims auditable*" in rendered
    assert "What changed" in rendered
    assert "Engineering surfaces" in rendered
    assert "Evaluation (EVAL)" in rendered
    assert "How this reaches companies" not in rendered
    assert "Download PDF" not in rendered


def test_status_discloses_labels_but_not_delivery_secrets():
    status = daily_brief.delivery_status_payload(
        _payload(),
        settings=_settings(),
    )
    rendered = json.dumps(status)

    assert status["total_insight_count"] == 6
    assert status["channels"] == [
        {
            "channel": "slack",
            "label": "Slack",
            "configured": True,
            "available": True,
            "destination": "#frontier-lab-intelligence",
        }
    ]
    assert all(channel["available"] for channel in status["channels"])
    assert "hooks.slack" not in rendered


def test_delivery_api_exposes_status_and_forwards_explicit_confirmation(monkeypatch):
    payload = _payload()
    monkeypatch.setattr(
        "fli.web.app._investment_insights",
        lambda **_kwargs: payload,
    )
    monkeypatch.setattr(
        "fli.web.app.brief_delivery.DeliverySettings.from_environment",
        lambda: _settings(),
    )
    calls: list[dict] = []

    def deliver(_payload, **kwargs):
        calls.append(kwargs)
        return {
            "schema_version": daily_brief.SCHEMA_VERSION,
            "status": "sent",
            "channel": kwargs["channel"],
            "destination": "#frontier-lab-intelligence",
            "audience": "investment",
            "date": DAY,
            "insight_count": 5,
            "delivery_id": "delivery-id",
            "provider_id": "provider-id",
            "sent_at": "2026-07-19T12:00:00+00:00",
        }

    monkeypatch.setattr("fli.web.app.brief_delivery.deliver_daily_brief", deliver)

    status = CLIENT.get(f"/api/insights/delivery?audience=investment&date={DAY}")
    response = CLIENT.post(
        "/api/insights/delivery",
        headers={"Origin": "http://testserver"},
        json={"audience": "investment", "date": DAY, "channel": "slack"},
    )
    cross_site = CLIENT.post(
        "/api/insights/delivery",
        headers={"Origin": "https://unrelated.example"},
        json={"audience": "investment", "date": DAY, "channel": "slack"},
    )
    retired_email = CLIENT.post(
        "/api/insights/delivery",
        headers={"Origin": "http://testserver"},
        json={"audience": "investment", "date": DAY, "channel": "email"},
    )

    assert status.status_code == 200
    assert status.json()["total_insight_count"] == 6
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert cross_site.status_code == 403
    assert retired_email.status_code == 422
    assert calls == [{"channel": "slack"}]


def test_delivery_api_supports_engineering_status_and_send(monkeypatch):
    payload = _engineering_payload()
    monkeypatch.setattr(
        "fli.web.app._engineering_insights",
        lambda **_kwargs: payload,
    )
    monkeypatch.setattr(
        "fli.web.app.brief_delivery.DeliverySettings.from_environment",
        lambda: _settings(),
    )
    calls: list[dict] = []

    def deliver(_payload, **kwargs):
        calls.append({"payload": _payload, **kwargs})
        return {
            "schema_version": daily_brief.SCHEMA_VERSION,
            "status": "sent",
            "channel": kwargs["channel"],
            "destination": "#frontier-lab-intelligence",
            "audience": "ai_engineering",
            "date": DAY,
            "insight_count": 1,
            "delivery_id": "delivery-id",
            "provider_id": "provider-id",
            "sent_at": "2026-07-19T12:00:00+00:00",
        }

    monkeypatch.setattr("fli.web.app.brief_delivery.deliver_daily_brief", deliver)

    status = CLIENT.get(
        f"/api/insights/delivery?audience=ai_engineering&date={DAY}"
    )
    response = CLIENT.post(
        "/api/insights/delivery",
        headers={"Origin": "http://testserver"},
        json={"audience": "ai_engineering", "date": DAY, "channel": "slack"},
    )

    assert status.status_code == 200
    assert status.json()["available"] is True
    assert status.json()["total_insight_count"] == 1
    assert response.status_code == 200
    assert calls == [{"payload": payload, "channel": "slack"}]


def test_delivery_is_unconfigured_and_blocked_in_read_only_mode(monkeypatch):
    monkeypatch.setenv("FLI_READ_ONLY", "true")
    monkeypatch.setattr(
        "fli.web.app._investment_insights",
        lambda **_kwargs: _payload(),
    )

    status = CLIENT.get(f"/api/insights/delivery?audience=investment&date={DAY}")
    response = CLIENT.post(
        "/api/insights/delivery",
        headers={"Origin": "http://testserver"},
        json={"audience": "investment", "date": DAY, "channel": "slack"},
    )

    assert status.status_code == 200
    assert not any(channel["configured"] for channel in status.json()["channels"])
    assert response.status_code == 403
    assert response.json()["detail"] == "This reviewer demo is read-only."
