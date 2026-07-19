"""Production PDF rendering for one canonical daily editorial brief."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as calendar_date
import hashlib
import html
from itertools import zip_longest
import json
import os
from pathlib import Path
import re
import tempfile
from threading import Lock, get_ident
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from fli.insights import editorial_runs


REPORT_SCHEMA_VERSION = "daily-intelligence-pdf-v3"
DEFAULT_CACHE_ROOT = editorial_runs.DEFAULT_ROOT / "pdf-cache"

PAPER = HexColor("#FFFFFF")
SURFACE = HexColor("#F7F7F6")
BORDER = HexColor("#E4E4E2")
INK = HexColor("#151515")
INK_SOFT = HexColor("#434343")
MUTED = HexColor("#6B6B68")
BLUE = HexColor("#5BC5F2")
BLUE_INK = HexColor("#235165")
POSITIVE = HexColor("#2E7D4F")
NEGATIVE = HexColor("#A13333")

PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN = 17 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * PAGE_MARGIN

_cache_locks_guard = Lock()
_cache_locks: dict[str, Lock] = {}


class ReportUnavailable(ValueError):
    """The requested canonical daily report does not exist."""


@dataclass(frozen=True)
class ReportArtifact:
    path: Path
    filename: str
    etag: str
    cache_hit: bool
    report_version: str = REPORT_SCHEMA_VERSION


def _register_unicode_fallback() -> str:
    """Register a deterministic mixed-script fallback when the host provides one."""
    font_name = "FLIUnicode"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    candidates = (
        Path(__file__).parent / "assets" / "Arial-Unicode.ttf",
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(candidate)))
            return font_name
        except Exception:
            continue
    cid_name = "STSong-Light"
    if cid_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(cid_name))
    return cid_name


UNICODE_FONT = _register_unicode_fallback()


_TEXT_REPLACEMENTS = str.maketrans(
    {
        "\u00a0": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2190": "<-",
        "\u2192": "->",
        "\u2194": "<->",
        "\u2197": "up-right",
        "\u2198": "down-right",
        "\u2212": "-",
        "\u00d7": "x",
    }
)


def _plain(value: Any) -> str:
    text = html.unescape(str(value or "")).translate(_TEXT_REPLACEMENTS)
    return "".join(char for char in text if char in "\n\t" or ord(char) >= 32).strip()


def _needs_unicode_font(char: str) -> bool:
    value = ord(char)
    return value > 255 and char not in "\n\t"


def _markup(value: Any) -> str:
    """Escape model text and wrap non-WinAnsi runs in the Unicode font."""
    text = _plain(value)
    if not text:
        return ""
    parts: list[str] = []
    current: list[str] = []
    current_unicode = _needs_unicode_font(text[0])
    for char in text:
        is_unicode = _needs_unicode_font(char)
        if is_unicode != current_unicode and current:
            rendered = escape("".join(current)).replace("\n", "<br/>")
            parts.append(
                f'<font name="{UNICODE_FONT}">{rendered}</font>'
                if current_unicode
                else rendered
            )
            current = []
        current.append(char)
        current_unicode = is_unicode
    if current:
        rendered = escape("".join(current)).replace("\n", "<br/>")
        parts.append(
            f'<font name="{UNICODE_FONT}">{rendered}</font>'
            if current_unicode
            else rendered
        )
    return "".join(parts)


def _link(url: Any, label: Any) -> str:
    href = html.escape(str(url or ""), quote=True)
    if not href:
        return _markup(label)
    return f'<link href="{href}" color="#235165">{_markup(label)}</link>'


def _display_day(day: str) -> str:
    try:
        parsed = calendar_date.fromisoformat(day)
    except ValueError:
        return day
    return parsed.strftime("%d %B %Y").upper()


def _audience_label(audience: str) -> str:
    return "INVESTMENT" if audience == "investment" else "AI ENGINEERING"


def report_filename(payload: dict[str, Any]) -> str:
    day = re.sub(r"[^0-9-]", "", str(payload.get("date") or "undated")) or "undated"
    audience = "investment" if payload.get("audience") == "investment" else "ai-engineering"
    return f"fli-daily-brief-{day}-{audience}.pdf"


def _report_cache_key(payload: dict[str, Any]) -> str:
    run = payload.get("run") or {}
    identity = {
        "report_schema": REPORT_SCHEMA_VERSION,
        "read_schema": payload.get("schema_version"),
        "date": payload.get("date"),
        "audience": payload.get("audience"),
        "result_sha256": run.get("result_sha256"),
    }
    if not identity["result_sha256"]:
        identity["payload_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _cache_lock(key: str) -> Lock:
    with _cache_locks_guard:
        return _cache_locks.setdefault(key, Lock())


def _valid_cached_pdf(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 512:
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def get_or_create_report(
    payload: dict[str, Any],
    *,
    cache_root: Path = DEFAULT_CACHE_ROOT,
) -> ReportArtifact:
    """Return one immutable cached report, generating it atomically on first read."""
    if payload.get("content_kind") != "daily_editorial" or not payload.get("available"):
        raise ReportUnavailable(str(payload.get("reason") or "Daily editorial report unavailable."))
    key = _report_cache_key(payload)
    path = cache_root / f"{key}.pdf"
    filename = report_filename(payload)
    if _valid_cached_pdf(path):
        return ReportArtifact(path=path, filename=filename, etag=key, cache_hit=True)

    lock = _cache_lock(key)
    with lock:
        if _valid_cached_pdf(path):
            return ReportArtifact(path=path, filename=filename, etag=key, cache_hit=True)
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
        return ReportArtifact(path=path, filename=filename, etag=key, cache_hit=False)


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=INK,
            spaceAfter=0,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=31,
            leading=33,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=sample["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=12,
            textColor=INK_SOFT,
        ),
        "cover_lede": ParagraphStyle(
            "CoverLede",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=INK_SOFT,
        ),
        "title": ParagraphStyle(
            "InsightTitle",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=24,
            textColor=INK,
            spaceAfter=0,
        ),
        "rank": ParagraphStyle(
            "Rank",
            parent=sample["Normal"],
            fontName="Courier-Bold",
            fontSize=23,
            leading=25,
            textColor=INK,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=INK,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=sample["Normal"],
            fontName="Courier",
            fontSize=7.5,
            leading=9.5,
            textColor=MUTED,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.25,
            leading=13.5,
            textColor=INK_SOFT,
            spaceAfter=0,
        ),
        "body_strong": ParagraphStyle(
            "BodyStrong",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.25,
            leading=13.5,
            textColor=INK,
            spaceAfter=0,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=INK_SOFT,
            spaceAfter=0,
        ),
        "small_link": ParagraphStyle(
            "SmallLink",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11.5,
            textColor=BLUE_INK,
            spaceAfter=0,
        ),
        "impact": ParagraphStyle(
            "Impact",
            parent=sample["Normal"],
            fontName="Courier-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=MUTED,
        ),
        "toc_rank": ParagraphStyle(
            "TocRank",
            parent=sample["Normal"],
            fontName="Courier-Bold",
            fontSize=9,
            leading=12,
            textColor=INK,
        ),
        "toc_title": ParagraphStyle(
            "TocTitle",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=INK,
        ),
        "toc_note": ParagraphStyle(
            "TocNote",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=MUTED,
        ),
    }


def _later_page_chrome(pdf: canvas.Canvas, _: SimpleDocTemplate, *, audience: str, day: str) -> None:
    pdf.saveState()
    pdf.resetTransforms()
    pdf.setFillColor(BLUE)
    pdf.rect(PAGE_MARGIN, PAGE_HEIGHT - 15.2 * mm, 3.2 * mm, 3.2 * mm, stroke=0, fill=1)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 7.2)
    pdf.drawString(PAGE_MARGIN + 5.3 * mm, PAGE_HEIGHT - 13.3 * mm, "FRONTIER LAB INTELLIGENCE")
    pdf.setFillColor(MUTED)
    pdf.setFont("Courier", 6.8)
    pdf.drawRightString(
        PAGE_WIDTH - PAGE_MARGIN,
        PAGE_HEIGHT - 13.3 * mm,
        f"{_audience_label(audience)}  /  {_display_day(day)}",
    )
    pdf.setStrokeColor(INK)
    pdf.setLineWidth(0.55)
    pdf.line(PAGE_MARGIN, PAGE_HEIGHT - 18 * mm, PAGE_WIDTH - PAGE_MARGIN, PAGE_HEIGHT - 18 * mm)
    pdf.restoreState()
    _footer_chrome(pdf, audience=audience, day=day)


def _footer_chrome(pdf: canvas.Canvas, *, audience: str, day: str) -> None:
    pdf.saveState()
    pdf.resetTransforms()
    pdf.setStrokeColor(BORDER)
    pdf.setLineWidth(0.45)
    pdf.line(PAGE_MARGIN, 12.5 * mm, PAGE_WIDTH - PAGE_MARGIN, 12.5 * mm)
    pdf.setFillColor(MUTED)
    pdf.setFont("Courier", 6.6)
    pdf.drawString(
        PAGE_MARGIN,
        8.4 * mm,
        f"FRONTIER LAB INTELLIGENCE  /  {_audience_label(audience)}  /  {_display_day(day)}",
    )
    pdf.drawRightString(
        PAGE_WIDTH - PAGE_MARGIN,
        8.4 * mm,
        f"PAGE {pdf.getPageNumber()}",
    )
    pdf.restoreState()


def _first_page_chrome(
    pdf: canvas.Canvas,
    _: SimpleDocTemplate,
    *,
    audience: str,
    day: str,
) -> None:
    pdf.setTitle("Frontier Lab Intelligence - Daily Intelligence Brief")
    pdf.setAuthor("Frontier Lab Intelligence")
    pdf.setCreator(f"Frontier Lab Intelligence / {REPORT_SCHEMA_VERSION}")
    pdf.setSubject("Audience-specific, cited frontier AI daily intelligence")
    pdf.setKeywords("frontier AI, investment intelligence, engineering intelligence, cited report")
    _footer_chrome(pdf, audience=audience, day=day)


def _cover(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    audience = str(payload["audience"])
    day = str(payload["date"])
    run = payload.get("run") or {}
    counts = run.get("counts") or {}
    items = list(payload.get("items") or [])
    event_ids = {
        str(event.get("event_id"))
        for item in items
        for event in item.get("events", [])
        if event.get("event_id")
    }
    research_sources = [
        citation
        for item in items
        for citation in item.get("citations", [])
        if citation.get("kind") != "event"
    ]
    left = [
        Paragraph("FRONTIER LAB INTELLIGENCE", styles["brand"]),
        Spacer(1, 10 * mm),
        Paragraph("DAILY<br/>INTELLIGENCE<br/>BRIEF", styles["cover_title"]),
        Spacer(1, 7 * mm),
        HRFlowable(width="100%", thickness=0.65, color=INK, spaceBefore=0, spaceAfter=5 * mm),
        Paragraph(
            f'{_markup(_audience_label(audience))}  <font color="#5BC5F2">/</font>  {_markup(_display_day(day))}',
            styles["cover_meta"],
        ),
    ]
    meta_rows = [
        ("REPORT", "DAILY BRIEF"),
        ("AUDIENCE", _audience_label(audience)),
        ("INSIGHTS", str(len(items))),
        ("SOURCE EVENTS", str(len(event_ids))),
        ("RESEARCH SOURCES", str(len(research_sources))),
        ("RESULT", str(run.get("result_sha256") or "-")[:12].upper()),
    ]
    right = [
        Table(
            [
                [Paragraph(_markup(label), styles["label"]), Paragraph(_markup(value), styles["cover_meta"])]
                for label, value in meta_rows
            ],
            colWidths=[34 * mm, 42 * mm],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.35, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            ),
        )
    ]
    story: list[Any] = [
        Spacer(1, 9 * mm),
        Table(
            [[left, right]],
            colWidths=[CONTENT_WIDTH * 0.56, CONTENT_WIDTH * 0.44],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 8 * mm),
                    ("LEFTPADDING", (1, 0), (1, 0), 8 * mm),
                    ("RIGHTPADDING", (1, 0), (1, 0), 0),
                    ("LINEBEFORE", (1, 0), (1, 0), 0.45, BORDER),
                ]
            ),
        ),
        Spacer(1, 11 * mm),
        Paragraph(
            _markup(
                "A ranked, cited daily workbook for investment decisions."
                if audience == "investment"
                else "A ranked, cited daily workbook for engineering experiments and implementation decisions."
            ),
            styles["cover_lede"],
        ),
        Spacer(1, 9 * mm),
        Table(
            [
                [
                    Paragraph("READING NOTE", styles["label"]),
                    Paragraph(
                        _markup(
                            "Each Insight opens with the decision-useful analysis, then carries its "
                            "complete linked source ledger on the following page."
                        ),
                        styles["body"],
                    ),
                ]
            ],
            colWidths=[32 * mm, CONTENT_WIDTH - 32 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                    ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (0, 0), 10),
                    ("RIGHTPADDING", (0, 0), (0, 0), 8),
                    ("LEFTPADDING", (1, 0), (1, 0), 0),
                    ("RIGHTPADDING", (1, 0), (1, 0), 10),
                ]
            ),
        ),
    ]
    portfolio = payload.get("portfolio_reference")
    if portfolio:
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph(
                    _markup(portfolio.get("reader_note"))
                    + " "
                    + _link(portfolio.get("source_url"), "Portfolio source"),
                    styles["small"],
                ),
            ]
        )
    if counts:
        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph(
                    _markup(
                        f"Complete run: {counts.get('candidate_events', 0)} candidate Events, "
                        f"{counts.get('candidate_pairs', 0)} audience pairs, "
                        f"{counts.get('included_candidates', 0)} included candidates."
                    ),
                    styles["label"],
                ),
            ]
        )
    story.extend([PageBreak(), *_contents(items, styles)])
    return story


def _contents(items: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = [
        Spacer(1, 7 * mm),
        Paragraph("WORKBOOK INDEX", styles["label"]),
        Spacer(1, 3 * mm),
        Paragraph("Today's brief", styles["title"]),
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=0.8, color=BLUE, spaceBefore=0, spaceAfter=3 * mm),
    ]
    if not items:
        story.append(
            Table(
                [[Paragraph("No Insight cleared the audience bar for this complete run.", styles["body"]) ]],
                colWidths=[CONTENT_WIDTH],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                        ("PADDING", (0, 0), (-1, -1), 12),
                    ]
                ),
            )
        )
        return story
    toc_rows = [
        [
            Paragraph(f'#{int(item["rank"])}', styles["toc_rank"]),
            [
                Paragraph(_markup(item["title"]), styles["toc_title"]),
                Spacer(1, 1.2 * mm),
                Paragraph(_markup(item["rank_rationale"]), styles["toc_note"]),
            ],
        ]
        for item in items
    ]
    story.append(
        Table(
            toc_rows,
            colWidths=[15 * mm, CONTENT_WIDTH - 15 * mm],
            splitByRow=1,
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (0, 0), (-1, 0), 0.5, INK),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (0, -1), 8),
                    ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ]
            ),
        )
    )
    return story


def _section_title(title: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Spacer(1, 6 * mm),
        Paragraph(_markup(title), styles["section"]),
        Spacer(1, 2.8 * mm),
    ]


def _opening_table(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    analysis = item.get("analysis") or {}
    interpretation_label = (
        "INVESTMENT INTERPRETATION"
        if "key_uncertainty" in analysis
        else "ENGINEERING INTERPRETATION"
    )
    cells = [
        [
            [
                Paragraph("WHAT CHANGED", styles["label"]),
                Spacer(1, 2 * mm),
                Paragraph(_markup(item.get("what_changed")), styles["body"]),
            ],
            [
                Paragraph(interpretation_label, styles["label"]),
                Spacer(1, 2 * mm),
                Paragraph(_markup(item.get("interpretation")), styles["body_strong"]),
            ],
        ]
    ]
    return Table(
        cells,
        colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEABOVE", (0, 0), (-1, -1), 0.55, INK),
                ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                ("LINEBEFORE", (1, 0), (1, 0), 0.35, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 9),
                ("LEFTPADDING", (1, 0), (1, 0), 9),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        ),
    )


def _investment_sections(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    analysis = item.get("analysis") or {}
    entities = list(analysis.get("affected_entities") or [])
    story: list[Any] = []
    if entities:
        rows = []
        for entity in entities:
            impact = str(entity.get("impact") or "uncertain")
            impact_color = {
                "positive": POSITIVE,
                "negative": NEGATIVE,
                "mixed": MUTED,
                "uncertain": MUTED,
            }.get(impact, MUTED)
            impact_style = ParagraphStyle(
                f"Impact-{impact}",
                parent=styles["impact"],
                textColor=impact_color,
            )
            scope = (
                "PORTFOLIO"
                if entity.get("scope") == "portfolio"
                else "OUTSIDE PORTFOLIO"
            )
            rows.append(
                [
                    [
                        Paragraph(_markup(entity.get("name")), styles["body_strong"]),
                        Spacer(1, 1 * mm),
                        Paragraph(scope, styles["label"]),
                    ],
                    Paragraph(_markup(impact.upper()), impact_style),
                    Paragraph(_markup(entity.get("mechanism")), styles["small"]),
                ]
            )
        story.extend(_section_title("Company read-through", styles))
        story.append(
            Table(
                rows,
                colWidths=[35 * mm, 25 * mm, CONTENT_WIDTH - 60 * mm],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEABOVE", (0, 0), (-1, 0), 0.35, BORDER),
                        ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            )
        )
    watchpoints = list(analysis.get("watchpoints") or [])
    signals = [
        Paragraph(f'<font color="#4391B4">/</font> {_markup(value)}', styles["small"])
        for value in watchpoints
    ]
    story.extend(_section_title("What would confirm or challenge this", styles))
    story.append(
        Table(
            [
                [
                    [
                        Paragraph("KEY UNCERTAINTY", styles["label"]),
                        Spacer(1, 1.5 * mm),
                        Paragraph(_markup(analysis.get("key_uncertainty")), styles["small"]),
                    ],
                    [Paragraph("SIGNALS", styles["label"]), Spacer(1, 1.5 * mm), *signals],
                    [
                        Paragraph("NEXT DILIGENCE STEP", styles["label"]),
                        Spacer(1, 1.5 * mm),
                        Paragraph(_markup(item.get("next_step")), styles["small"]),
                    ],
                ]
            ],
            colWidths=[CONTENT_WIDTH * 0.31, CONTENT_WIDTH * 0.34, CONTENT_WIDTH * 0.35],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEBEFORE", (1, 0), (-1, 0), 0.35, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 7),
                    ("LEFTPADDING", (1, 0), (-1, 0), 7),
                    ("RIGHTPADDING", (1, 0), (-1, 0), 7),
                ]
            ),
        )
    )
    return story


def _engineering_sections(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    analysis = item.get("analysis") or {}
    story = _section_title("What to do next", styles)
    story.append(
        Table(
            [
                [
                    [
                        Paragraph("NEXT STEP", styles["label"]),
                        Spacer(1, 1.5 * mm),
                        Paragraph(_markup(item.get("next_step")), styles["body"]),
                    ],
                    [
                        Paragraph("DECISION RULE", styles["label"]),
                        Spacer(1, 1.5 * mm),
                        Paragraph(_markup(analysis.get("decision_rule")), styles["body_strong"]),
                    ],
                ]
            ],
            colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEBEFORE", (1, 0), (1, 0), 0.35, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 8),
                    ("LEFTPADDING", (1, 0), (1, 0), 8),
                    ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ]
            ),
        )
    )
    return story


def _source_block(
    value: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    *,
    events: bool,
) -> list[Any]:
    if events:
        feed_rank = int(value.get("feed_rank") or 0)
        role = str(value.get("role") or "source").upper()
        title = str(value.get("title") or f"Feed #{feed_rank}")
        url = value.get("url") or value.get("source_url")
        support = value.get("supports") or value.get("reason")
    else:
        title = str(value.get("title") or "Untitled source")
        url = value.get("url")
        support = value.get("supports")
    flowables: list[Any] = [
        Paragraph(_link(url, title), styles["small_link"]),
        Spacer(1, 1.2 * mm),
    ]
    if events:
        flowables.extend(
            [
                Paragraph(f"FEED #{feed_rank}  /  {_markup(role)}", styles["label"]),
                Spacer(1, 1.2 * mm),
            ]
        )
    flowables.append(Paragraph(_markup(support), styles["small"]))
    event_reason = value.get("event_reason") if events else None
    if event_reason and _plain(event_reason) != _plain(support):
        flowables.extend(
            [
                Spacer(1, 1.2 * mm),
                Paragraph(f"Insight role: {_markup(event_reason)}", styles["small"]),
            ]
        )
    return flowables


def _sources_section(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    citations = list(item.get("citations") or [])
    event_by_id = {
        str(event.get("event_id")): event
        for event in item.get("events", [])
        if event.get("event_id")
    }
    events: list[dict[str, Any]] = []
    cited_event_ids: set[str] = set()
    for citation in citations:
        if citation.get("kind") != "event":
            continue
        event_id = str(citation.get("event_id") or "")
        event = event_by_id.get(event_id, {})
        events.append(
            {
                **citation,
                "feed_rank": event.get("feed_rank"),
                "role": event.get("role"),
                "event_reason": event.get("reason") if event_id not in cited_event_ids else None,
            }
        )
        cited_event_ids.add(event_id)
    for event_id, event in event_by_id.items():
        if event_id not in cited_event_ids:
            events.append(event)
    research = [citation for citation in citations if citation.get("kind") != "event"]
    story: list[Any] = [
        Spacer(1, 7 * mm),
        Paragraph(
            f'SOURCE LEDGER  <font color="#5BC5F2">/</font>  INSIGHT #{int(item["rank"])}',
            styles["label"],
        ),
        Spacer(1, 3 * mm),
        Paragraph("Evidence and sources", styles["title"]),
        Spacer(1, 3 * mm),
        Paragraph(
            _markup(item.get("title")),
            styles["cover_lede"],
        ),
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=0.8, color=BLUE, spaceBefore=0, spaceAfter=5 * mm),
    ]
    source_rows: list[list[Any]] = [
        [
            Paragraph("ORIGINAL FEED", styles["label"]),
            Paragraph("ARTIFACTS &amp; CONTEXT", styles["label"]),
        ]
    ]
    event_values: list[dict[str, Any] | None] = events or [None]
    research_values: list[dict[str, Any] | None] = research or [None]
    for row_index, (event, source) in enumerate(zip_longest(event_values, research_values)):
        source_rows.append(
            [
                _source_block(event, styles, events=True)
                if event
                else (
                    [Paragraph("No sources in this group.", styles["small"])]
                    if not events and row_index == 0
                    else []
                ),
                _source_block(source, styles, events=False)
                if source
                else (
                    [Paragraph("No sources in this group.", styles["small"])]
                    if not research and row_index == 0
                    else []
                ),
            ]
        )
    story.append(
        Table(
            source_rows,
            colWidths=[CONTENT_WIDTH * 0.43, CONTENT_WIDTH * 0.57],
            repeatRows=1,
            splitByRow=1,
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEBEFORE", (1, 0), (1, -1), 0.35, BORDER),
                    ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (0, -1), 8),
                    ("RIGHTPADDING", (0, 0), (0, -1), 8),
                    ("LEFTPADDING", (1, 0), (1, -1), 8),
                    ("RIGHTPADDING", (1, 0), (1, -1), 8),
                ]
            ),
        )
    )
    return story


def _insight(item: dict[str, Any], payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    day = str(payload["date"])
    audience = str(payload["audience"])
    header = Table(
        [
            [
                Paragraph(f'#{int(item["rank"])}', styles["rank"]),
                [
                    Paragraph(_markup(item.get("title")), styles["title"]),
                    Spacer(1, 2.3 * mm),
                    Paragraph(
                        f'{_markup(_audience_label(audience))}  <font color="#5BC5F2">/</font>  {_markup(_display_day(day))}',
                        styles["label"],
                    ),
                ],
            ]
        ],
        colWidths=[18 * mm, CONTENT_WIDTH - 18 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 7),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        ),
    )
    rationale = Table(
        [
            [
                Paragraph("WHY THIS RANK", styles["label"]),
                Paragraph(_markup(item.get("rank_rationale")), styles["small"]),
            ]
        ],
        colWidths=[31 * mm, CONTENT_WIDTH - 31 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.35, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (0, 0), 7),
                ("RIGHTPADDING", (0, 0), (0, 0), 7),
                ("LEFTPADDING", (1, 0), (1, 0), 0),
                ("RIGHTPADDING", (1, 0), (1, 0), 7),
            ]
        ),
    )
    story: list[Any] = [
        Spacer(1, 7 * mm),
        header,
        Spacer(1, 4.5 * mm),
        HRFlowable(width="100%", thickness=0.8, color=BLUE, spaceBefore=0, spaceAfter=4 * mm),
        rationale,
        Spacer(1, 5 * mm),
        _opening_table(item, styles),
    ]
    analysis = item.get("analysis") or {}
    if "key_uncertainty" in analysis:
        story.extend(_investment_sections(item, styles))
    else:
        story.extend(_engineering_sections(item, styles))
    story.append(PageBreak())
    story.extend(_sources_section(item, styles))
    return story


def build_report_pdf(payload: dict[str, Any]) -> bytes:
    """Render a complete audience-specific workbook as vector PDF bytes."""
    if payload.get("content_kind") != "daily_editorial" or not payload.get("available"):
        raise ReportUnavailable(str(payload.get("reason") or "Daily editorial report unavailable."))
    audience = str(payload.get("audience") or "investment")
    day = str(payload.get("date") or payload.get("requested_date") or "")
    if audience not in {"investment", "ai_engineering"} or not day:
        raise ReportUnavailable("Daily editorial report is missing its audience or date.")

    from io import BytesIO

    output = BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=24 * mm,
        bottomMargin=19 * mm,
        title=f"Frontier Lab Intelligence - {_audience_label(audience).title()} - {day}",
        author="Frontier Lab Intelligence",
        subject="Audience-specific, cited frontier AI daily intelligence",
        pageCompression=1,
    )
    story = _cover(payload, styles)
    items = list(payload.get("items") or [])
    for item in items:
        story.append(PageBreak())
        story.extend(_insight(item, payload, styles))

    doc.build(
        story,
        onFirstPage=lambda pdf, document: _first_page_chrome(
            pdf, document, audience=audience, day=day
        ),
        onLaterPages=lambda pdf, document: _later_page_chrome(
            pdf, document, audience=audience, day=day
        ),
    )
    pdf_bytes = output.getvalue()
    if not pdf_bytes.startswith(b"%PDF-"):
        raise RuntimeError("Report renderer did not produce a PDF document.")
    return pdf_bytes
