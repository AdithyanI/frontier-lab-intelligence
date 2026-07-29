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
        "headline": f"Model escape strengthens independent controls {rank}",
        "what_changed": (
            "OpenAI reported that cyber-capable models escaped a constrained "
            "evaluation environment and 昇腾950发布说明 remained unresolved."
        ),
        "no_match_reason": None,
        "company_names": {"NTSK": "Netskope", "PANW": "Palo Alto Networks"},
        "connections": [
            {
                "mechanism": "The escape turns unauthorized egress into a demonstrated risk.",
                "companies": [
                    {
                        "ticker": "NTSK",
                        "bet_id": "NTSK-B1",
                        "threshold_met": True,
                        "impact": "Netskope sells inline enforcement for agent traffic.",
                    },
                    {
                        "ticker": "PANW",
                        "bet_id": "PANW-B5",
                        "threshold_met": False,
                        "impact": "Palo Alto's coverage is broader but undisclosed.",
                    },
                ],
            }
        ],
        "memo_calls": [
            {
                "turn": 1,
                "call_id": f"call-{rank}",
                "arguments": {
                    "ticker": "NTSK",
                    "connection_type": "direct",
                    "mechanism": "Inline controls cover unauthorized egress.",
                    "candidate_bet_id": "NTSK-B1",
                    "why_memo_is_needed": "Confirm Netskope's agent traffic controls map here.",
                },
            },
            {
                "turn": 1,
                "call_id": f"call-panw-{rank}",
                "arguments": {
                    "ticker": "PANW",
                    "connection_type": "direct",
                    "mechanism": "Native controls may constrain independent security demand.",
                    "candidate_bet_id": "PANW-B5",
                    "why_memo_is_needed": "Test whether native controls threaten the product category.",
                },
            },
            {
                "turn": 1,
                "call_id": f"call-rbrk-{rank}",
                "arguments": {
                    "ticker": "RBRK",
                    "connection_type": "indirect",
                    "mechanism": "Recovery demand may rise after agent incidents.",
                    "candidate_bet_id": "RBRK-B2",
                    "why_memo_is_needed": "Test whether this incident reaches recovery demand.",
                },
            },
        ],
        "telemetry": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "prompt_version": "investment-agent-v14",
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
        "schema_version": "investment-agent-read-v8",
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
    assert "HAPPENED" in text
    assert "Company read-through" in text
    assert "SOURCES" in text
    assert "昇腾950发布说明" in text
    # Superseded editorial sections must not reappear.
    assert "WHAT CHANGED" not in text
    assert "DECISION RULE" not in text
    assert "SOURCE LEDGER" not in text


def test_cover_omits_pipeline_plumbing_analysts_do_not_need():
    text = _pdf_text(pdf_report.build_report_pdf(_payload()))

    # The screening stat band and METHOD blurb were pipeline internals, not
    # reading material for an analyst opening the brief.
    assert "READ-THROUGHS" not in text
    assert "COMPANIES\nSCREENED" not in text
    assert "METHOD" not in text
    # Model, effort, prompt version, and turn counts are run plumbing, not reading.
    assert "GPT-5.6-SOL" not in text
    assert "XHIGH" not in text
    assert "INVESTMENT-AGENT-V14" not in text
    assert "investment-agent-v14" not in text
    assert "2 turns" not in text


def test_report_wastes_no_page_on_chrome_alone():
    reader = PdfReader(BytesIO(pdf_report.build_report_pdf(_payload())))
    chrome = ("FRONTIER LAB INTELLIGENCE", "BRIEF INDEX", "PAGE", "/", "INVESTMENT", "2026")

    for number, page in enumerate(reader.pages, start=1):
        body = (page.extract_text() or "").splitlines()
        substantive = [
            line
            for line in body
            if line.strip() and not any(line.strip().startswith(mark) for mark in chrome)
        ]
        assert len(substantive) > 3, f"page {number} carries chrome only"


def test_report_shows_every_company_with_its_direction_and_evidence():
    text = _pdf_text(pdf_report.build_report_pdf(_payload()))

    assert "Netskope" in text
    assert "NTSK" in text
    assert "Palo Alto Networks" in text
    assert "UPSIDE" in text
    assert "DOWNSIDE" in text
    assert "REVIEW THESIS" in text
    assert "EARLY SIGNAL" in text
    assert "STANDING BET" in text
    assert "NTSK-B1" in text
    assert "PANW-B5" in text


def test_report_keeps_sources_clean_and_points_to_the_live_audit_trail():
    text = _pdf_text(pdf_report.build_report_pdf(_payload()))

    assert "Sources and audit trail" in text
    assert "PRIMARY" in text
    assert "SOURCES" in text
    assert "Open the full company read-through and audit trail" in text
    # The memo screening funnel and per-memo rationale are pipeline noise;
    # analysts get the same detail interactively in the app link above.
    assert "SCREENED" not in text
    assert "MEMOS OPENED" not in text
    assert "RETAINED" not in text
    assert "REJECTED" not in text
    assert "WHY THESE" not in text
    assert "Confirm Netskope's agent traffic controls map here." not in text


def test_report_links_only_application_owned_sources():
    links = _pdf_links(pdf_report.build_report_pdf(_payload()))

    assert "https://example.com/research" in links
    assert "https://x.com/example/status/1" in links
    assert (
        "https://frontier-lab-intelligence.adithyan.io/bit-lens/companies"
        "?company=NTSK&bet=NTSK-B1" in links
    )
    assert (
        "https://frontier-lab-intelligence.adithyan.io/insights"
        "?audience=investment&date=2026-07-17&insight=development-1" in links
    )


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
