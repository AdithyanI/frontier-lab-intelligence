"""Production PDF rendering for one company-aware Investment daily brief."""

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
from urllib.parse import urlencode
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



REPORT_SCHEMA_VERSION = "investment-agent-pdf-v10"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_ROOT = REPO_ROOT / "data" / "derived" / "insights" / "pdf-cache"
PUBLIC_APP_URL = "https://frontier-lab-intelligence.adithyan.io"

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
    if payload.get("content_kind") != "investment_agent" or not payload.get("available"):
        raise ReportUnavailable(
            str(payload.get("reason") or "Company-aware Investment report unavailable.")
        )
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
            fontName="Times-Bold",
            fontSize=31,
            leading=31.5,
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
        "cover_section": ParagraphStyle(
            "CoverSection",
            parent=sample["Heading2"],
            fontName="Times-Bold",
            fontSize=17,
            leading=19,
            textColor=INK,
            spaceAfter=0,
        ),
        "title": ParagraphStyle(
            "InsightTitle",
            parent=sample["Heading1"],
            fontName="Times-Bold",
            fontSize=22,
            leading=23.5,
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
            fontName="Times-Bold",
            fontSize=13.5,
            leading=16,
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
            fontName="Helvetica-Bold",
            fontSize=8.25,
            leading=11,
            textColor=MUTED,
        ),
        "toc_rank": ParagraphStyle(
            "TocRank",
            parent=sample["Normal"],
            fontName="Courier-Bold",
            fontSize=10,
            leading=14,
            textColor=INK,
        ),
        "toc_title": ParagraphStyle(
            "TocTitle",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=BLUE_INK,
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
    navigation = "BRIEF INDEX"
    pdf.setFillColor(BLUE_INK)
    pdf.setFont("Courier-Bold", 6.8)
    navigation_x = PAGE_WIDTH - PAGE_MARGIN
    navigation_y = PAGE_HEIGHT - 13.3 * mm
    pdf.drawRightString(navigation_x, navigation_y, navigation)
    navigation_width = pdf.stringWidth(navigation, "Courier-Bold", 6.8)
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
    items = list(payload.get("items") or [])
    story: list[Any] = [
        Spacer(1, 9 * mm),
        Paragraph('<a name="brief-index"/>FRONTIER LAB INTELLIGENCE', styles["brand"]),
        Spacer(1, 10 * mm),
        Paragraph("DAILY<br/>INTELLIGENCE BRIEF", styles["cover_title"]),
        Spacer(1, 6 * mm),
        Paragraph(
            f'{_markup(_audience_label(audience))}  <font color="#5BC5F2">/</font>  {_markup(_display_day(day))}',
            styles["cover_meta"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            _markup(
                "The ranked developments most likely to change today's investment work."
                if audience == "investment"
                else "The ranked developments most likely to change today's engineering work."
            ),
            styles["cover_lede"],
        ),
        Spacer(1, 8 * mm),
        HRFlowable(width="100%", thickness=0.8, color=BLUE, spaceBefore=0, spaceAfter=5 * mm),
        Paragraph(
            '<font name="Helvetica-Bold" color="#5BC5F2">/</font> Today\'s brief',
            styles["cover_section"],
        ),
        Spacer(1, 2.5 * mm),
        Paragraph(
            "Click any title to jump to its analysis. Each brief is followed by its linked sources.",
            styles["body"],
        ),
        Spacer(1, 4 * mm),
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
            Paragraph(f'#{int(item["daily_rank"])}', styles["toc_rank"]),
            Paragraph(
                f'<link href="#insight-{int(item["daily_rank"])}" color="#235165">'
                f'{_markup(item["investment_headline"])}</link>',
                styles["toc_title"],
            ),
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
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
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
        Paragraph(
            f'<font name="Helvetica-Bold" color="#5BC5F2">/</font> {_markup(title)}',
            styles["section"],
        ),
        Spacer(1, 2.8 * mm),
    ]


def _mechanism_block(
    assessment: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    company_names: dict[str, Any],
) -> list[Any]:
    """Render one causal path and every company hanging off it."""
    direction_copy = {
        "positive": ("Potential positive", POSITIVE),
        "negative": ("Potential negative", NEGATIVE),
        "mixed": ("Mixed", MUTED),
        "unclear": ("Direction unclear", MUTED),
    }
    story: list[Any] = [
        Paragraph(_markup(assessment.get("mechanism_title")), styles["body_strong"]),
        Spacer(1, 1.6 * mm),
        Paragraph(_markup(assessment.get("mechanism")), styles["body"]),
        Spacer(1, 3.2 * mm),
    ]
    rows: list[list[Any]] = []
    for index, exposure in enumerate(assessment.get("exposures") or [], start=1):
        ticker = str(exposure.get("ticker") or "")
        name = str(company_names.get(ticker) or ticker)
        label, color = direction_copy.get(
            str(exposure.get("direction") or "unclear"), direction_copy["unclear"]
        )
        direction_style = ParagraphStyle(
            f"Direction-{ticker}-{index}",
            parent=styles["impact"],
            textColor=color,
        )
        body: list[Any] = [
            Paragraph(f"{_markup(name)}  <font color='#6B6B68'>{_markup(ticker)}</font>", styles["body_strong"]),
            Spacer(1, 1.2 * mm),
            Paragraph(_markup(label), direction_style),
            Spacer(1, 0.8 * mm),
            Paragraph(_markup(exposure.get("affected_driver")), styles["body"]),
        ]
        impact = exposure.get("impact") or exposure.get("note")
        if impact:
            body.extend([Spacer(1, 1.4 * mm), Paragraph(_markup(impact), styles["small"])])
        size_basis = exposure.get("size_basis")
        if size_basis:
            body.extend([Spacer(1, 1.2 * mm), Paragraph(_markup(size_basis), styles["small"])])
        rows.append([Paragraph(str(index), styles["toc_rank"]), body])
    if rows:
        story.append(
            Table(
                rows,
                colWidths=[10 * mm, CONTENT_WIDTH - 10 * mm],
                splitByRow=1,
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, -2), 0.35, BORDER),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (0, -1), 6),
                        ("RIGHTPADDING", (1, 0), (1, -1), 0),
                    ]
                ),
            )
        )
    footer_rows = [
        (label, assessment.get(key))
        for label, key in (("UNPROVEN", "main_uncertainty"), ("WATCH", "next_check"))
        if assessment.get(key)
    ]
    if footer_rows:
        story.extend([Spacer(1, 2.5 * mm)])
        story.append(
            Table(
                [
                    [
                        Paragraph(label, styles["label"]),
                        Paragraph(_markup(value), styles["small"]),
                    ]
                    for label, value in footer_rows
                ],
                colWidths=[22 * mm, CONTENT_WIDTH - 22 * mm],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEABOVE", (0, 0), (-1, 0), 0.35, BORDER),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (0, -1), 6),
                    ]
                ),
            )
        )
    return story


def _agent_sources_section(
    item: dict[str, Any], styles: dict[str, ParagraphStyle]
) -> list[Any]:
    """Application-owned provenance: the Feed post, artifacts, and the memo funnel."""
    provenance = item.get("provenance") or {}
    telemetry = item.get("telemetry") or {}
    company_names = item.get("company_names") or {}
    story: list[Any] = [
        Spacer(1, 9 * mm),
        Paragraph(
            '<font name="Helvetica-Bold" color="#5BC5F2">/</font> Sources and audit trail',
            styles["section"],
        ),
        Spacer(1, 3 * mm),
    ]
    original = provenance.get("original_post") or {}
    if original.get("url"):
        story.extend(
            [
                Paragraph("ORIGINAL POST", styles["label"]),
                Spacer(1, 1.4 * mm),
                Paragraph(
                    _link(original.get("url"), original.get("author") or original.get("url")),
                    styles["small_link"],
                ),
                Spacer(1, 4 * mm),
            ]
        )
    artifacts = list(provenance.get("artifacts") or [])
    if artifacts:
        story.extend([Paragraph("LINKED ARTIFACTS", styles["label"]), Spacer(1, 1.4 * mm)])
        for artifact in artifacts:
            story.extend(
                [
                    Paragraph(
                        _link(artifact.get("url"), artifact.get("title")), styles["small_link"]
                    ),
                    Spacer(1, 2 * mm),
                ]
            )
        story.append(Spacer(1, 2 * mm))

    memo_calls = list(item.get("memo_calls") or [])
    if memo_calls:
        retained = len(
            {
                str(exposure.get("ticker"))
                for assessment in item.get("company_assessments") or []
                for exposure in assessment.get("exposures") or []
            }
        )
        rejected = len(item.get("rejected_after_memo") or [])
        funnel = (
            f'{telemetry.get("company_universe_count", 0)} screened'
            f' / {telemetry.get("memo_count", 0)} memos opened'
            f' / {retained} retained'
        )
        if rejected:
            funnel = f"{funnel} / {rejected} rejected"
        story.extend(
            [
                Paragraph("HOW THE AGENT GOT HERE", styles["label"]),
                Spacer(1, 1.4 * mm),
                Paragraph(_markup(funnel), styles["small"]),
                Spacer(1, 3 * mm),
            ]
        )
        rows = []
        for call in memo_calls:
            arguments = call.get("arguments") or {}
            ticker = str(arguments.get("ticker") or "")
            name = str(company_names.get(ticker) or ticker)
            rows.append(
                [
                    Paragraph(
                        f'{_markup(name)}<br/><font color="#6B6B68">{_markup(ticker)}</font>',
                        styles["small"],
                    ),
                    Paragraph(_markup(arguments.get("why_memo_is_needed")), styles["small"]),
                ]
            )
        story.append(
            Table(
                rows,
                colWidths=[30 * mm, CONTENT_WIDTH - 30 * mm],
                splitByRow=1,
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEABOVE", (0, 0), (-1, 0), 0.5, INK),
                        ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (0, -1), 8),
                    ]
                ),
            )
        )

    rejected_rows = [
        [
            Paragraph(
                _markup(company_names.get(str(entry.get("ticker"))) or entry.get("ticker")),
                styles["small"],
            ),
            Paragraph(_markup(entry.get("reason")), styles["small"]),
        ]
        for entry in item.get("rejected_after_memo") or []
    ]
    if rejected_rows:
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph("OPENED AND REJECTED", styles["label"]),
                Spacer(1, 1.4 * mm),
                Table(
                    rejected_rows,
                    colWidths=[30 * mm, CONTENT_WIDTH - 30 * mm],
                    splitByRow=1,
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (0, -1), 8),
                        ]
                    ),
                ),
            ]
        )

    if telemetry:
        story.extend(
            [
                Spacer(1, 6 * mm),
                Paragraph(
                    _markup(
                        f'{telemetry.get("model", "")} / {telemetry.get("reasoning_effort", "")}'
                        f' / {telemetry.get("prompt_version", "")}'
                        f' / {telemetry.get("turn_count", 0)} turns'
                    ),
                    styles["small"],
                ),
            ]
        )
    return story


def _insight(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    rank = int(item["daily_rank"])
    company_names = item.get("company_names") or {}
    header = Table(
        [
            [
                Paragraph(f"#{rank}", styles["rank"]),
                [
                    Paragraph(
                        f'<a name="insight-{rank}"/>{_markup(item.get("investment_headline"))}',
                        styles["title"],
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
    story: list[Any] = [
        Spacer(1, 7 * mm),
        header,
        Spacer(1, 4.5 * mm),
        HRFlowable(
            width="100%",
            thickness=0.8,
            color=BLUE,
            spaceBefore=0,
            spaceAfter=5 * mm,
        ),
        Paragraph("WHAT HAPPENED", styles["label"]),
        Spacer(1, 2 * mm),
        Paragraph(_markup(item.get("development_summary")), styles["body"]),
    ]
    assessments = list(item.get("company_assessments") or [])
    if assessments:
        story.extend(_section_title("Company read-through", styles))
        for index, assessment in enumerate(assessments):
            if index:
                story.extend(
                    [
                        Spacer(1, 5 * mm),
                        HRFlowable(
                            width="100%",
                            thickness=0.35,
                            color=BORDER,
                            spaceBefore=0,
                            spaceAfter=4 * mm,
                        ),
                    ]
                )
            story.extend(_mechanism_block(assessment, styles, company_names))
    elif item.get("no_match_reason"):
        story.extend(_section_title("No company read-through", styles))
        story.append(Paragraph(_markup(item["no_match_reason"]), styles["body"]))
    if item.get("prior_assumption"):
        story.extend(_section_title("The belief this moves", styles))
        story.append(Paragraph(_markup(item["prior_assumption"]), styles["body"]))
    story.append(PageBreak())
    story.extend(_agent_sources_section(item, styles))
    return story


def build_report_pdf(payload: dict[str, Any]) -> bytes:
    """Render a complete audience-specific workbook as vector PDF bytes."""
    if payload.get("content_kind") != "investment_agent" or not payload.get("available"):
        raise ReportUnavailable(
            str(payload.get("reason") or "Company-aware Investment report unavailable.")
        )
    audience = str(payload.get("audience") or "investment")
    day = str(payload.get("date") or payload.get("requested_date") or "")
    if audience != "investment" or not day:
        raise ReportUnavailable("Investment report is missing its audience or date.")

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
        story.extend(_insight(item, styles))

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
