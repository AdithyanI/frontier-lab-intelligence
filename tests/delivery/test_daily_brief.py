from __future__ import annotations

from email.message import EmailMessage
import json
from pathlib import Path

from fastapi.testclient import TestClient
import httpx

from fli.delivery import daily_brief
from fli.insights import pdf_report
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
        email_recipients=("reader@example.com",),
        email_destination_label="re****@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="smtp-user",
        smtp_password="smtp-secret",
        smtp_from_email="briefs@example.com",
        smtp_from_name="Frontier Lab Intelligence",
        smtp_reply_to="reply@example.com",
    )


def _artifact(tmp_path: Path) -> pdf_report.ReportArtifact:
    path = tmp_path / "daily-brief.pdf"
    path.write_bytes(b"%PDF-1.7\nmock")
    return pdf_report.ReportArtifact(
        path=path,
        filename="fli-daily-brief-2026-07-17-investment.pdf",
        etag="report-etag",
        cache_hit=True,
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
    assert result["pdf_delivery"] == "none"
    assert result["pdf_filename"] is None
    assert result["report_version"] is None
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


def test_email_delivery_attaches_pdf_and_contains_only_top_five(tmp_path):
    sent: list[EmailMessage] = []

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs):
            self.logged_in = False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def ehlo(self):
            return None

        def starttls(self, **_kwargs):
            return None

        def login(self, username, password):
            self.logged_in = username == "smtp-user" and password == "smtp-secret"

        def send_message(self, message, **_kwargs):
            assert self.logged_in
            sent.append(message)

    result = daily_brief._send_email(
        _settings(),
        _payload(),
        _artifact(tmp_path),
        smtp_factory=FakeSMTP,
    )

    assert result
    assert len(sent) == 1
    message = sent[0]
    rendered = message.as_string()
    attachments = list(message.iter_attachments())
    assert "Insight 1" in rendered
    assert "Insight 5" in rendered
    assert "Insight 6" not in rendered
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_filename() == "fli-daily-brief-2026-07-17-investment.pdf"


def test_email_uses_brief_positions_for_both_audiences():
    investment = _payload()
    for item, feed_rank in zip(
        investment["items"],
        (4, 12, 24, 25, 30, 31),
        strict=True,
    ):
        item["daily_rank"] = feed_rank

    _, investment_plain, investment_html = daily_brief._email_content(investment)
    _, engineering_plain, engineering_html = daily_brief._email_content(
        _engineering_payload()
    )

    assert "1. Insight 1" in investment_plain
    assert "2. Insight 2" in investment_plain
    assert "12. Insight 2" not in investment_plain
    assert ">1. Insight 1</a>" in investment_html
    assert "1. Layered checks make costly research claims auditable" in engineering_plain
    assert ">1. Layered checks make costly research claims auditable</a>" in engineering_html
    assert "Engineering relevance" not in engineering_plain
    assert "Engineering relevance" not in engineering_html


def test_engineering_email_uses_the_engineering_pdf_renderer(tmp_path, monkeypatch):
    artifact = _artifact(tmp_path)
    captured: list[tuple[dict, Path]] = []

    def engineering_report(payload, *, cache_root):
        captured.append((payload, cache_root))
        return artifact

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def ehlo(self):
            return None

        def starttls(self, **_kwargs):
            return None

        def login(self, *_args):
            return None

        def send_message(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(
        daily_brief.pdf_report_engineering,
        "get_or_create_report",
        engineering_report,
    )
    monkeypatch.setattr(
        daily_brief.pdf_report_engineering,
        "DEFAULT_CACHE_ROOT",
        tmp_path / "engineering-cache",
    )

    result = daily_brief.deliver_daily_brief(
        _engineering_payload(),
        channel="email",
        settings=_settings(),
        smtp_factory=FakeSMTP,
    )

    assert result["status"] == "sent"
    assert result["audience"] == "ai_engineering"
    assert result["pdf_delivery"] == "attachment"
    assert captured == [
        (_engineering_payload(), tmp_path / "engineering-cache")
    ]


def test_status_discloses_labels_but_not_delivery_secrets():
    status = daily_brief.delivery_status_payload(
        _payload(),
        settings=_settings(),
    )
    rendered = json.dumps(status)

    assert status["top_insight_count"] == 5
    assert status["total_insight_count"] == 6
    assert all(channel["available"] for channel in status["channels"])
    assert "smtp-secret" not in rendered
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
            "pdf_delivery": "none",
            "pdf_filename": None,
            "report_version": None,
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

    assert status.status_code == 200
    assert status.json()["top_insight_count"] == 5
    assert status.json()["total_insight_count"] == 6
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert cross_site.status_code == 403
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
            "pdf_delivery": "none",
            "pdf_filename": None,
            "report_version": None,
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
