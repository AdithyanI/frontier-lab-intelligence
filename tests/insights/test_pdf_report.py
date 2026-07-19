from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from fli.insights import pdf_report
from fli.web.app import app


CLIENT = TestClient(app)
DAY = "2026-07-17"


def _payload(audience: str = "investment") -> dict:
    analysis = (
        {
            "affected_entities": [
                {
                    "name": "NVIDIA",
                    "scope": "portfolio",
                    "impact": "uncertain",
                    "mechanism": "Demand may rise, but deployment evidence is missing.",
                }
            ],
            "key_uncertainty": "The release has no customer evidence.",
            "watchpoints": [
                "Named production deployments.",
                "Matched cost per successful task.",
            ],
        }
        if audience == "investment"
        else {"decision_rule": "Adopt only if the fixed eval improves reliability by 10%."}
    )
    return {
        "schema_version": "daily-intelligence-read-v4",
        "content_kind": "daily_editorial",
        "available": True,
        "reason": None,
        "status": "kept",
        "requested_date": DAY,
        "date": DAY,
        "audience": audience,
        "portfolio_reference": (
            {
                "basis": "complete audited year-end portfolio",
                "as_of": "2025-12-31",
                "source_label": "Audited annual report",
                "source_url": "https://example.com/portfolio.pdf",
                "reader_note": "Portfolio mappings use the audited public portfolio.",
            }
            if audience == "investment"
            else None
        ),
        "run": {
            "run_id": "daily-brief-test",
            "date": DAY,
            "status": "complete",
            "created_at": "2026-07-18T19:47:28+00:00",
            "schema_version": "daily-intelligence-store-v4",
            "draft_schema_version": "daily-intelligence-draft-v4",
            "workspace": {"run_id": "workspace-test", "manifest_sha256": "a" * 64},
            "source": {
                "routing_run_id": "routing-test",
                "cohort_sha256": "b" * 64,
                "event_run_id": "event-test",
                "feed_run_id": "feed-test",
            },
            "agent": {"skill_version": "fli-daily-intelligence-v4", "model": "codex", "notes": None},
            "result_sha256": ("c" if audience == "investment" else "d") * 64,
            "counts": {
                "candidate_events": 8,
                "candidate_pairs": 10,
                "insights_all_audiences": 2,
                "citations_all_audiences": 4,
                "insights": 1,
                "included_candidates": 1,
                "not_selected_candidates": 4,
            },
        },
        "items": [
            {
                "insight_id": "insight-test",
                "local_id": "local-test",
                "audience": audience,
                "rank": 1,
                "rank_rationale": "Highest decision consequence with primary-source evidence.",
                "day": DAY,
                "title": "A cited result becomes a decision - not a dashboard",
                "what_changed": "A first-party release reported a new result -> one week earlier than expected.",
                "interpretation": "The result changes the next diligence or implementation decision.",
                "next_step": "Run one fixed comparison and record the decision.",
                "analysis": analysis,
                "events": [
                    {
                        "event_id": "event-one",
                        "feed_rank": 7,
                        "role": "primary",
                        "reason": "Provides the exact first-party claim.",
                    }
                ],
                "citations": [
                    {
                        "citation_id": "citation-event",
                        "local_id": "event-source",
                        "kind": "event",
                        "url": "https://x.com/example/status/1",
                        "title": "Original X post",
                        "event_id": "event-one",
                        "artifact_id": None,
                        "published_at": DAY,
                        "retrieved_at": None,
                        "supports": "Provides the exact first-party claim.",
                        "excerpt": None,
                    },
                    {
                        "citation_id": "citation-one",
                        "local_id": "artifact-one",
                        "kind": "artifact",
                        "url": "https://example.com/research",
                        "title": "Primary research artifact",
                        "event_id": "event-one",
                        "artifact_id": "artifact-one",
                        "published_at": DAY,
                        "retrieved_at": None,
                        "supports": "Defines the measurement and result.",
                        "excerpt": "The result improved by ten percent.",
                    },
                    {
                        "citation_id": "citation-event-two",
                        "local_id": "event-source-two",
                        "kind": "event",
                        "url": "https://x.com/example/status/2",
                        "title": "Original X continuation",
                        "event_id": "event-one",
                        "artifact_id": None,
                        "published_at": DAY,
                        "retrieved_at": None,
                        "supports": "Qualifies the first-party claim.",
                        "excerpt": None,
                    },
                    {
                        "citation_id": "citation-two",
                        "local_id": "context-two",
                        "kind": "context",
                        "url": "https://example.com/context",
                        "title": "Portfolio context",
                        "event_id": None,
                        "artifact_id": None,
                        "published_at": None,
                        "retrieved_at": None,
                        "supports": "Establishes the comparison baseline.",
                        "excerpt": None,
                    },
                    {
                        "citation_id": "citation-three",
                        "local_id": "web-three",
                        "kind": "web",
                        "url": "https://example.com/launch",
                        "title": "昇腾950发布说明",
                        "event_id": None,
                        "artifact_id": None,
                        "published_at": None,
                        "retrieved_at": "2026-07-18T19:35:21Z",
                        "supports": "Confirms the release timing.",
                        "excerpt": None,
                    },
                ],
            }
        ],
    }


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _pdf_links(pdf_bytes: bytes) -> set[str]:
    reader = PdfReader(BytesIO(pdf_bytes))
    links: set[str] = set()
    for page in reader.pages:
        for annotation_ref in page.get("/Annots", []):
            annotation = annotation_ref.get_object()
            action = annotation.get("/A")
            if action and action.get("/URI"):
                links.add(str(action["/URI"]))
    return links


def _pdf_internal_destinations(pdf_bytes: bytes) -> list[object]:
    reader = PdfReader(BytesIO(pdf_bytes))
    return [
        annotation_ref.get_object()["/Dest"]
        for annotation_ref in reader.pages[0].get("/Annots", [])
        if annotation_ref.get_object().get("/Dest")
    ]


@pytest.mark.parametrize(
    ("audience", "expected", "unexpected"),
    [
        ("investment", "Company read-through", "Decision rule"),
        ("ai_engineering", "DECISION RULE", "Company read-through"),
    ],
)
def test_report_renders_complete_audience_workbook(audience, expected, unexpected):
    pdf_bytes = pdf_report.build_report_pdf(_payload(audience))
    reader = PdfReader(BytesIO(pdf_bytes))
    text = _pdf_text(pdf_bytes)

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(reader.pages) == 3
    assert "DAILY" in text
    assert "INTELLIGENCE" in text
    assert "Evidence and sources" in text
    assert "Today's brief" in text
    assert "Click any title to jump to its analysis." in text
    assert "SOURCE EVENTS" not in text
    assert "RESEARCH SOURCES" not in text
    assert "Complete run:" not in text
    assert "READING NOTE" not in text
    assert len(_pdf_internal_destinations(pdf_bytes)) == 1
    assert expected in text
    assert unexpected not in text
    assert "Primary research artifact" in text
    assert "Original X continuation" in text
    assert "Portfolio context" in text
    assert "昇腾950发布说明" in text
    assert {
        "https://x.com/example/status/1",
        "https://x.com/example/status/2",
        "https://example.com/research",
        "https://example.com/context",
        "https://example.com/launch",
    }.issubset(_pdf_links(pdf_bytes))


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


def test_report_rejects_non_editorial_payload(tmp_path):
    with pytest.raises(pdf_report.ReportUnavailable, match="unavailable"):
        pdf_report.get_or_create_report(
            {
                "content_kind": "candidate_decisions",
                "available": False,
                "reason": "Daily editorial report unavailable.",
            },
            cache_root=tmp_path,
        )


def test_report_api_downloads_and_revalidates_cached_pdf(tmp_path, monkeypatch):
    payload = _payload()
    monkeypatch.setattr(
        "fli.web.app.editorial_store.editorial_insights_payload",
        lambda **_: payload,
    )
    monkeypatch.setattr("fli.web.app.pdf_report.DEFAULT_CACHE_ROOT", tmp_path)

    first = CLIENT.get(f"/api/insights/report.pdf?audience=investment&date={DAY}")
    second = CLIENT.get(f"/api/insights/report.pdf?audience=investment&date={DAY}")
    conditional = CLIENT.get(
        f"/api/insights/report.pdf?audience=investment&date={DAY}",
        headers={"If-None-Match": second.headers["etag"]},
    )

    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert 'filename="fli-daily-brief-2026-07-17-investment.pdf"' in first.headers["content-disposition"]
    assert first.headers["x-fli-pdf-cache"] == "miss"
    assert second.headers["x-fli-pdf-cache"] == "hit"
    assert second.headers["etag"] == first.headers["etag"]
    assert conditional.status_code == 304
    assert conditional.content == b""
