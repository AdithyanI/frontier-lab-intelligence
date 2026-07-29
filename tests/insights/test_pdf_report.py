from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from fli.insights import pdf_report
from fli.web.app import app


CLIENT = TestClient(app)
DAY = "2026-07-17"


def _item(rank: int) -> dict:
    return {
        "daily_rank": rank,
        "day": DAY,
        "development_id": f"development-{rank}",
        "investment_headline": f"Model escape strengthens independent controls {rank}",
        "development_summary": (
            "OpenAI reported that cyber-capable models escaped a constrained "
            "evaluation environment and 昇腾950发布说明 remained unresolved."
        ),
        "prior_assumption": (
            "A reasonable prior is that agent escapes remain confined to test systems."
        ),
        "no_match_reason": None,
        "company_names": {"NTSK": "Netskope", "PANW": "Palo Alto Networks"},
        "company_assessments": [
            {
                "mechanism_title": "Independent runtime containment and egress control",
                "mechanism": "The escape turns unauthorized egress into a demonstrated risk.",
                "main_uncertainty": "We do not know whether enterprises buy new controls.",
                "next_check": "Netskope's disclosed count of paid AI-security customers.",
                "splits": False,
                "exposures": [
                    {
                        "ticker": "NTSK",
                        "affected_driver": "Paid AI-security module adoption",
                        "direction": "positive",
                        "materiality": "material",
                        "size_basis": "ARR was $845 million",
                        "impact": "Netskope sells inline enforcement for agent traffic.",
                    },
                    {
                        "ticker": "PANW",
                        "affected_driver": "AI-security product attachment",
                        "direction": "negative",
                        "materiality": "unknown",
                        "size_basis": None,
                        "impact": "Palo Alto's coverage is broader but undisclosed.",
                    },
                ],
            }
        ],
        "rejected_after_memo": [
            {"ticker": "RBRK", "reason": "Rubrik needs agent telemetry this lacks."}
        ],
        "memo_calls": [
            {
                "turn": 1,
                "call_id": f"call-{rank}",
                "arguments": {
                    "ticker": "NTSK",
                    "connection_type": "direct",
                    "mechanism": "Inline controls cover unauthorized egress.",
                    "affected_operating_driver": "Paid module adoption",
                    "why_memo_is_needed": "Confirm Netskope's agent traffic controls map here.",
                },
            }
        ],
        "telemetry": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "prompt_version": "investment-agent-v11",
            "company_universe_count": 37,
            "memo_count": 3,
            "turn_count": 2,
        },
        "provenance": {
            "primary_event_id": "event-one",
            "original_post": {
                "url": "https://x.com/example/status/1",
                "author": "OpenAI",
            },
            "artifacts": [
                {
                    "artifact_id": "artifact-one",
                    "title": "Primary research artifact",
                    "url": "https://example.com/research",
                }
            ],
        },
    }


def _payload() -> dict:
    return {
        "schema_version": "investment-agent-read-v6",
        "content_kind": "investment_agent",
        "available": True,
        "reason": None,
        "audience": "investment",
        "status": "kept",
        "date": DAY,
        "requested_date": DAY,
        "run": {"result_sha256": "a" * 64},
        "items": [_item(rank) for rank in (1, 2)],
    }


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _pdf_links(pdf_bytes: bytes) -> set[str]:
    reader = PdfReader(BytesIO(pdf_bytes))
    links: set[str] = set()
    for page in reader.pages:
        for annotation in page.get("/Annots") or []:
            action = annotation.get_object().get("/A") or {}
            uri = action.get("/URI")
            if uri:
                links.add(str(uri))
    return links


def test_report_renders_the_complete_investment_workbook():
    pdf_bytes = pdf_report.build_report_pdf(_payload())
    text = _pdf_text(pdf_bytes)

    assert pdf_bytes.startswith(b"%PDF-")
    assert "DAILY" in text
    assert "INTELLIGENCE" in text
    assert "Today's brief" in text
    assert "WHAT HAPPENED" in text
    assert "Company read-through" in text
    assert "The belief this moves" in text
    assert "Sources and audit trail" in text
    assert "昇腾950发布说明" in text
    # Superseded editorial sections must not reappear.
    assert "WHAT CHANGED" not in text
    assert "DECISION RULE" not in text
    assert "SOURCE LEDGER" not in text


def test_report_shows_every_company_with_its_direction_and_evidence():
    text = _pdf_text(pdf_report.build_report_pdf(_payload()))

    assert "Netskope" in text
    assert "NTSK" in text
    assert "Palo Alto Networks" in text
    assert "Potential positive" in text
    assert "Potential negative" in text
    assert "ARR was $845 million" in text
    assert "UNPROVEN" in text
    assert "WATCH" in text


def test_report_shows_the_screening_funnel_and_rejections():
    text = _pdf_text(pdf_report.build_report_pdf(_payload()))

    assert "HOW THE AGENT GOT HERE" in text
    assert "37 screened" in text
    assert "3 memos opened" in text
    assert "2 retained" in text
    assert "1 rejected" in text
    assert "OPENED AND REJECTED" in text
    assert "Rubrik needs agent telemetry this lacks." in text


def test_report_links_only_application_owned_sources():
    links = _pdf_links(pdf_report.build_report_pdf(_payload()))

    assert "https://example.com/research" in links
    assert "https://x.com/example/status/1" in links


def test_report_cache_is_content_addressed_and_atomic(tmp_path):
    first = pdf_report.get_or_create_report(_payload(), cache_root=tmp_path)
    second = pdf_report.get_or_create_report(_payload(), cache_root=tmp_path)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert first.path == second.path
    assert first.etag == second.etag
    assert first.filename == "fli-daily-brief-2026-07-17-investment.pdf"
    assert first.path.read_bytes().startswith(b"%PDF-")
    assert list(tmp_path.glob("*.tmp")) == []


def test_report_rejects_a_payload_from_outside_the_current_path(tmp_path):
    with pytest.raises(pdf_report.ReportUnavailable, match="unavailable"):
        pdf_report.get_or_create_report(
            {
                "content_kind": "candidate_decisions",
                "available": False,
                "reason": "Company-aware Investment report unavailable.",
            },
            cache_root=tmp_path,
        )


def test_report_api_downloads_and_revalidates_cached_pdf(tmp_path, monkeypatch):
    payload = _payload()
    monkeypatch.setattr("fli.web.app._investment_insights", lambda **_: payload)
    monkeypatch.setattr("fli.web.app.pdf_report.DEFAULT_CACHE_ROOT", tmp_path)

    first = CLIENT.get(f"/api/insights/report.pdf?audience=investment&date={DAY}")
    second = CLIENT.get(f"/api/insights/report.pdf?audience=investment&date={DAY}")
    conditional = CLIENT.get(
        f"/api/insights/report.pdf?audience=investment&date={DAY}",
        headers={"If-None-Match": second.headers["etag"]},
    )

    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert (
        'filename="fli-daily-brief-2026-07-17-investment.pdf"'
        in first.headers["content-disposition"]
    )
    assert first.headers["x-fli-pdf-cache"] == "miss"
    assert second.headers["x-fli-pdf-cache"] == "hit"
    assert second.headers["etag"] == first.headers["etag"]
    assert conditional.status_code == 304
    assert conditional.content == b""


def test_report_api_refuses_an_audience_without_a_current_run():
    response = CLIENT.get(f"/api/insights/report.pdf?audience=ai_engineering&date={DAY}")

    assert response.status_code == 404
