"""Production PDF rendering for one AI Engineering daily brief.

This is a deliberately separate, simpler renderer from `pdf_report` (the
Investment workbook): the Engineering lane has no company memo loop, bet
directions, or materiality gate, so its report has no company cards or
screening funnel to render. It shares only brand-level primitives (colors,
page geometry, text sanitization, the cache dataclasses) with the Investment
renderer; its cover, page chrome, and per-item layout are its own.
"""

from __future__ import annotations

from datetime import date as calendar_date
import hashlib
import json
import os
from pathlib import Path
import tempfile
from threading import get_ident
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .pdf_report import (
    BLUE,
    BODY_WIDTH,
    BORDER,
    CONTENT_WIDTH,
    INK,
    INK_SOFT,
    MUTED,
    PAGE_HEIGHT,
    PAGE_MARGIN,
    PAGE_WIDTH,
    PUBLIC_APP_URL,
    RAIL_GUTTER,
    RAIL_WIDTH,
    REPO_ROOT,
    ReportArtifact,
    ReportUnavailable,
    _cache_lock,
    _insight_app_url,
    _link,
    _markup,
    _valid_cached_pdf,
)

REPORT_SCHEMA_VERSION = "engineering-agent-pdf-v3"
DEFAULT_CACHE_ROOT = REPO_ROOT / "data" / "derived" / "insights" / "pdf-cache-engineering"


def _display_day(day: str) -> str:
    try:
        parsed = calendar_date.fromisoformat(day)
    except ValueError:
        return day
    return parsed.strftime("%d %B %Y").upper()


def report_filename(payload: dict[str, Any]) -> str:
    import re

    day = re.sub(r"[^0-9-]", "", str(payload.get("date") or "undated")) or "undated"
    return f"fli-daily-brief-{day}-ai-engineering.pdf"


def _report_cache_key(payload: dict[str, Any]) -> str:
    run = payload.get("run") or {}
    identity = {
        "report_schema": REPORT_SCHEMA_VERSION,
        "read_schema": payload.get("schema_version"),
        "date": payload.get("date"),
        "audience": payload.get("audience"),
        "selection_sha256": run.get("selection_sha256"),
    }
    if not identity["selection_sha256"]:
        identity["payload_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def get_or_create_report(
    payload: dict[str, Any],
    *,
    cache_root: Path = DEFAULT_CACHE_ROOT,
) -> ReportArtifact:
    """Return one immutable cached report, generating it atomically on first read."""
    if payload.get("content_kind") != "engineering_agent" or not payload.get("available"):
        raise ReportUnavailable(
            str(payload.get("reason") or "Surface-linked Engineering report unavailable.")
        )
    key = _report_cache_key(payload)
    path = cache_root / f"{key}.pdf"
    filename = report_filename(payload)
    if _valid_cached_pdf(path):
        return ReportArtifact(
            path=path, filename=filename, etag=key, cache_hit=True, report_version=REPORT_SCHEMA_VERSION
        )

    lock = _cache_lock(key)
    with lock:
        if _valid_cached_pdf(path):
            return ReportArtifact(
                path=path,
                filename=filename,
                etag=key,
                cache_hit=True,
                report_version=REPORT_SCHEMA_VERSION,
            )
        cache_root.mkdir(parents=True, exist_ok=True)
        pdf_bytes = build_report_pdf(payload)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{key[:12]}-{os.getpid()}-{get_ident()}-",
                suffix=".tmp",
                dir=cache_root,
                delete=False,
            ) as temporary:
                temporary.write(pdf_bytes)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        return ReportArtifact(
            path=path,
            filename=filename,
            etag=key,
            cache_hit=False,
            report_version=REPORT_SCHEMA_VERSION,
        )


def _styles() -> dict[str, ParagraphStyle]:
    """A sans-serif, technical type ramp — distinct from the Investment workbook's
    editorial serif so the two reports read as clearly separate artifacts."""
    sample = getSampleStyleSheet()
    normal = sample["Normal"]
    return {
        "brand": ParagraphStyle(
            "Brand", parent=normal, fontName="Helvetica-Bold", fontSize=7.6, leading=10, textColor=INK
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=29,
            leading=32,
            textColor=INK,
            alignment=0,
            spaceAfter=0,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta", parent=normal, fontName="Courier", fontSize=8.2, leading=12, textColor=INK_SOFT
        ),
        "section": ParagraphStyle(
            "Section",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=INK,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "insight_title": ParagraphStyle(
            "InsightTitle",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=INK,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "rail": ParagraphStyle(
            "Rail", parent=normal, fontName="Courier-Bold", fontSize=6.6, leading=9.6, textColor=MUTED
        ),
        "rail_rank": ParagraphStyle(
            "RailRank", parent=normal, fontName="Courier-Bold", fontSize=16, leading=18, textColor=BLUE
        ),
        "body": ParagraphStyle(
            "Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.6, leading=15,
            textColor=INK_SOFT, spaceAfter=0,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=normal, fontName="Courier", fontSize=7, leading=11, textColor=MUTED
        ),
        "meta_right": ParagraphStyle(
            "MetaRight", parent=normal, fontName="Courier", fontSize=7, leading=11, textColor=MUTED,
            alignment=2,
        ),
        "link": ParagraphStyle(
            "Link", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8.8, leading=13,
            textColor=INK, spaceAfter=0,
        ),
        "surface_id": ParagraphStyle(
            "SurfaceId", parent=normal, fontName="Courier-Bold", fontSize=8, leading=13, textColor=BLUE
        ),
        "surface_name": ParagraphStyle(
            "SurfaceName", parent=normal, fontName="Helvetica-Bold", fontSize=9.6, leading=13,
            textColor=INK,
        ),
        "toc_rank": ParagraphStyle(
            "TocRank", parent=normal, fontName="Courier-Bold", fontSize=9, leading=14, textColor=MUTED
        ),
        "toc_title": ParagraphStyle(
            "TocTitle", parent=normal, fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=INK
        ),
        "toc_surfaces": ParagraphStyle(
            "TocSurfaces", parent=normal, fontName="Courier", fontSize=7, leading=14, textColor=MUTED,
            alignment=2,
        ),
    }


def _rail(label: str, content: Any, styles: dict[str, ParagraphStyle], *, label_style: str = "rail") -> Table:
    body = content if isinstance(content, list) else [content]
    return Table(
        [[Paragraph(label, styles[label_style]) if label else "", body]],
        colWidths=[RAIL_WIDTH + RAIL_GUTTER, BODY_WIDTH],
        splitByRow=1,
        splitInRow=1,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), RAIL_GUTTER),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def _section_heading(title: str, note: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    heading = Table(
        [
            [
                Paragraph(f'<font color="#5BC5F2">/</font> {_markup(title)}', styles["section"]),
                Paragraph(_markup(note), styles["meta_right"]),
            ]
        ],
        colWidths=[CONTENT_WIDTH * 0.55, CONTENT_WIDTH * 0.45],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LINEABOVE", (0, 0), (-1, 0), 0.7, INK),
                ("TOPPADDING", (0, 0), (-1, -1), 3.4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    heading.spaceBefore = 7 * mm
    return [heading, Spacer(1, 4.2 * mm)]


def _page_chrome(pdf: canvas.Canvas, *, day: str) -> None:
    pdf.saveState()
    pdf.resetTransforms()
    pdf.setStrokeColor(BORDER)
    pdf.setLineWidth(0.45)
    pdf.line(PAGE_MARGIN, 13 * mm, PAGE_WIDTH - PAGE_MARGIN, 13 * mm)
    pdf.setFillColor(MUTED)
    pdf.setFont("Courier", 6.6)
    pdf.drawString(
        PAGE_MARGIN, 8.9 * mm, f"FRONTIER LAB INTELLIGENCE  /  AI ENGINEERING  /  {_display_day(day)}"
    )
    pdf.drawRightString(PAGE_WIDTH - PAGE_MARGIN, 8.9 * mm, f"PAGE {pdf.getPageNumber()}")
    pdf.restoreState()


def _later_page_chrome(pdf: canvas.Canvas, _: SimpleDocTemplate, *, day: str) -> None:
    pdf.saveState()
    pdf.resetTransforms()
    pdf.setFillColor(BLUE)
    pdf.rect(PAGE_MARGIN, PAGE_HEIGHT - 15.4 * mm, 3 * mm, 3 * mm, stroke=0, fill=1)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(PAGE_MARGIN + 5 * mm, PAGE_HEIGHT - 13.6 * mm, "FRONTIER LAB INTELLIGENCE")
    navigation = "BRIEF INDEX"
    pdf.setFillColor(MUTED)
    pdf.setFont("Courier", 6.6)
    navigation_x = PAGE_WIDTH - PAGE_MARGIN
    navigation_y = PAGE_HEIGHT - 13.6 * mm
    pdf.drawRightString(navigation_x, navigation_y, navigation)
    navigation_width = pdf.stringWidth(navigation, "Courier", 6.6)
    pdf.linkRect(
        "Back to the brief index",
        "brief-index",
        (
            navigation_x - navigation_width - 1.2 * mm,
            navigation_y - 1.4 * mm,
            navigation_x + 1.2 * mm,
            navigation_y + 3 * mm,
        ),
        relative=0,
        thickness=0,
    )
    pdf.setStrokeColor(BORDER)
    pdf.setLineWidth(0.5)
    pdf.line(PAGE_MARGIN, PAGE_HEIGHT - 18.4 * mm, PAGE_WIDTH - PAGE_MARGIN, PAGE_HEIGHT - 18.4 * mm)
    pdf.restoreState()
    _page_chrome(pdf, day=day)


def _first_page_chrome(pdf: canvas.Canvas, _: SimpleDocTemplate, *, day: str) -> None:
    pdf.setTitle("Frontier Lab Intelligence - AI Engineering Brief")
    pdf.setAuthor("Frontier Lab Intelligence")
    pdf.setCreator(f"Frontier Lab Intelligence / {REPORT_SCHEMA_VERSION}")
    pdf.setSubject("Cited frontier AI engineering intelligence")
    pdf.setKeywords("frontier AI, engineering intelligence, cited report")
    _page_chrome(pdf, day=day)


def _cover(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    day = str(payload["date"])
    items = list(payload.get("items") or [])

    story: list[Any] = [
        HRFlowable(width=14 * mm, thickness=2.6, color=BLUE, hAlign="LEFT", spaceAfter=3.4 * mm),
        Paragraph('<a name="brief-index"/>FRONTIER LAB INTELLIGENCE', styles["brand"]),
        Spacer(1, 11 * mm),
        Paragraph("AI ENGINEERING BRIEF", styles["cover_title"]),
        Spacer(1, 5 * mm),
        Paragraph(f'AI ENGINEERING  <font color="#5BC5F2">/</font>  {_markup(_display_day(day))}', styles["cover_meta"]),
        Spacer(1, 7 * mm),
    ]

    story.extend(_section_heading("Today's brief", "CLICK A TITLE TO OPEN ITS ANALYSIS", styles))

    if not items:
        story.append(
            Table(
                [[Paragraph("No Insight cleared the audience bar for this complete run.", styles["body"])]],
                colWidths=[CONTENT_WIDTH],
                style=TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                        ("PADDING", (0, 0), (-1, -1), 12),
                    ]
                ),
            )
        )
        return story

    toc_rows = []
    for position, item in enumerate(items, start=1):
        surface_ids = " ".join(landing["surface_id"] for landing in item.get("lands") or [])
        toc_rows.append(
            [
                Paragraph(f"#{position}", styles["toc_rank"]),
                Paragraph(
                    f'<link href="#insight-{position}" color="#151515">'
                    f'{_markup(item["headline"])}</link>',
                    styles["toc_title"],
                ),
                Paragraph(_markup(surface_ids), styles["toc_surfaces"]),
            ]
        )
    story.append(
        Table(
            toc_rows,
            colWidths=[12 * mm, CONTENT_WIDTH - 52 * mm, 40 * mm],
            splitByRow=1,
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (0, -1), 6),
                    ("RIGHTPADDING", (1, 0), (1, -1), 6),
                    ("RIGHTPADDING", (2, 0), (2, -1), 0),
                ]
            ),
        )
    )
    return story


def _sources_block(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    app_url = _insight_app_url("ai_engineering", str(item.get("day") or ""), str(item.get("development_id") or ""))
    return [
        KeepTogether(
            [
                Spacer(1, 7 * mm),
                HRFlowable(width="100%", thickness=0.4, color=BORDER, spaceAfter=2.8 * mm),
                Paragraph(
                    _link(
                        app_url,
                        "For references and sources, open this Insight in the app \u2192",
                    ),
                    styles["link"],
                ),
            ]
        )
    ]


def _insight(
    item: dict[str, Any], styles: dict[str, ParagraphStyle], position: int
) -> list[Any]:
    provenance = item.get("provenance") or {}
    original = provenance.get("original_post") or {}
    trail = [
        str(original.get("author") or "").upper(),
        f'{provenance.get("source_event_count")} SOURCE EVENTS' if provenance.get("source_event_count") else "",
        _display_day(str(item.get("day") or "")),
    ]
    story: list[Any] = [
        _rail(
            f"#{position}",
            [
                Paragraph(
                    f'<a name="insight-{position}"/>{_markup(item.get("headline"))}',
                    styles["insight_title"],
                ),
                Spacer(1, 2.8 * mm),
                Paragraph(_markup("  ·  ".join(part for part in trail if part)), styles["meta"]),
            ],
            styles,
            label_style="rail_rank",
        ),
        Spacer(1, 4.5 * mm),
        HRFlowable(width="100%", thickness=0.9, color=BLUE, spaceAfter=5.5 * mm),
        _rail("WHAT<br/>CHANGED", Paragraph(_markup(item.get("what_changed")), styles["body"]), styles),
    ]

    lands = list(item.get("lands") or [])
    if lands:
        note = f'{len(lands)} {"SURFACE" if len(lands) == 1 else "SURFACES"}'
        story.extend(_section_heading("Where this lands", note, styles))
        for index, landing in enumerate(lands):
            if index:
                story.append(Spacer(1, 4 * mm))
            story.append(
                KeepTogether(
                    [
                        _rail(
                            "",
                            [
                                Paragraph(
                                    _markup(landing["surface_name"]),
                                    styles["surface_name"],
                                ),
                                Spacer(1, 1.4 * mm),
                                Paragraph(_markup(landing["why"]), styles["body"]),
                            ],
                            styles,
                        )
                    ]
                )
            )
    elif item.get("no_match_reason"):
        story.extend(_section_heading("No surface cleared the bar", "", styles))
        story.append(_rail("REASON", Paragraph(_markup(item["no_match_reason"]), styles["body"]), styles))

    story.extend(_sources_block(item, styles))
    return story


def build_report_pdf(payload: dict[str, Any]) -> bytes:
    """Render a complete AI Engineering workbook as vector PDF bytes."""
    if payload.get("content_kind") != "engineering_agent" or not payload.get("available"):
        raise ReportUnavailable(
            str(payload.get("reason") or "Surface-linked Engineering report unavailable.")
        )
    day = str(payload.get("date") or payload.get("requested_date") or "")
    if not day:
        raise ReportUnavailable("Engineering report is missing its date.")

    from io import BytesIO

    output = BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=27 * mm,
        bottomMargin=20 * mm,
        title=f"Frontier Lab Intelligence - AI Engineering - {day}",
        author="Frontier Lab Intelligence",
        subject="Cited frontier AI engineering intelligence",
        pageCompression=1,
    )
    story = _cover(payload, styles)
    for position, item in enumerate(payload.get("items") or [], start=1):
        story.append(PageBreak())
        story.extend(_insight(item, styles, position))

    doc.build(
        story,
        onFirstPage=lambda pdf, document: _first_page_chrome(pdf, document, day=day),
        onLaterPages=lambda pdf, document: _later_page_chrome(pdf, document, day=day),
    )
    pdf_bytes = output.getvalue()
    if not pdf_bytes.startswith(b"%PDF-"):
        raise RuntimeError("Report renderer did not produce a PDF document.")
    return pdf_bytes
