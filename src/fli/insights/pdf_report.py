"""Production PDF rendering for one company-aware Investment daily brief."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as calendar_date
from functools import lru_cache
import hashlib
import html
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
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


REPORT_SCHEMA_VERSION = "investment-agent-pdf-v14"
REPO_ROOT = Path(__file__).resolve().parents[3]
COMPANY_MEMO_PATH = REPO_ROOT / "docs" / "references" / "company-memos.json"
DEFAULT_CACHE_ROOT = REPO_ROOT / "data" / "derived" / "insights" / "pdf-cache"
PUBLIC_APP_URL = "https://frontier-lab-intelligence.adithyan.io"

PAPER = HexColor("#FFFFFF")
SURFACE = HexColor("#F7F7F6")
BORDER = HexColor("#E4E4E2")
INK = HexColor("#151515")
INK_SOFT = HexColor("#434343")
MUTED = HexColor("#6B6B68")
BLUE = HexColor("#5BC5F2")
BLUE_MID = HexColor("#4391B4")
BLUE_INK = HexColor("#235165")
POSITIVE = HexColor("#2E7D4F")
NEGATIVE = HexColor("#A13333")

PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN = 20 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * PAGE_MARGIN
RAIL_WIDTH = 25 * mm
RAIL_GUTTER = 7 * mm
BODY_WIDTH = CONTENT_WIDTH - RAIL_WIDTH - RAIL_GUTTER
CARD_INNER_WIDTH = BODY_WIDTH - 1.8 * mm - 10 * mm

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


def _insight_app_url(audience: str, day: str, development_id: str) -> str:
    """Deep link back into the live app, scrolled and focused to this exact Insight."""
    query = {"audience": audience, "date": day, "insight": development_id}
    return f"{PUBLIC_APP_URL}/insights?{urlencode(query)}"


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
    normal = sample["Normal"]
    return {
        "brand": ParagraphStyle(
            "Brand",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=7.6,
            leading=10,
            textColor=INK,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="Times-Bold",
            fontSize=33,
            leading=34,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=normal,
            fontName="Courier",
            fontSize=8.2,
            leading=12,
            textColor=INK_SOFT,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=sample["Heading2"],
            fontName="Times-Bold",
            fontSize=15,
            leading=17,
            textColor=INK,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "insight_title": ParagraphStyle(
            "InsightTitle",
            parent=sample["Heading1"],
            fontName="Times-Bold",
            fontSize=20,
            leading=23,
            textColor=INK,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "rail": ParagraphStyle(
            "Rail",
            parent=normal,
            fontName="Courier-Bold",
            fontSize=6.6,
            leading=9.6,
            textColor=MUTED,
        ),
        "rail_rank": ParagraphStyle(
            "RailRank",
            parent=normal,
            fontName="Courier-Bold",
            fontSize=17,
            leading=18,
            textColor=BLUE_MID,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=15,
            textColor=INK_SOFT,
            spaceAfter=0,
        ),
        "body_ink": ParagraphStyle(
            "BodyInk",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=15,
            textColor=INK,
            spaceAfter=0,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.6,
            leading=13,
            textColor=INK_SOFT,
            spaceAfter=0,
        ),
        "quiet": ParagraphStyle(
            "Quiet",
            parent=sample["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.9,
            leading=13.4,
            textColor=MUTED,
            spaceAfter=0,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=normal,
            fontName="Courier",
            fontSize=7,
            leading=11,
            textColor=MUTED,
        ),
        "meta_right": ParagraphStyle(
            "MetaRight",
            parent=normal,
            fontName="Courier",
            fontSize=7,
            leading=11,
            textColor=MUTED,
            alignment=TA_RIGHT,
        ),
        "link": ParagraphStyle(
            "Link",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=13,
            textColor=BLUE_INK,
            spaceAfter=0,
        ),
        "company": ParagraphStyle(
            "Company",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=INK,
        ),
        "badge": ParagraphStyle(
            "Badge",
            parent=normal,
            fontName="Courier-Bold",
            fontSize=6.4,
            leading=8,
            textColor=PAPER,
            alignment=TA_CENTER,
        ),
        "toc_rank": ParagraphStyle(
            "TocRank",
            parent=normal,
            fontName="Courier-Bold",
            fontSize=9,
            leading=14,
            textColor=MUTED,
        ),
        "toc_title": ParagraphStyle(
            "TocTitle",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=BLUE_INK,
        ),
        "toc_tickers": ParagraphStyle(
            "TocTickers",
            parent=normal,
            fontName="Courier",
            fontSize=7,
            leading=14,
            textColor=MUTED,
            alignment=TA_RIGHT,
        ),
    }


def _rail(
    label: str,
    content: Any,
    styles: dict[str, ParagraphStyle],
    *,
    label_style: str = "rail",
    label_offset: float = 2.4,
) -> Table:
    """Place a mono label in the left rail beside a measured body column."""
    body = content if isinstance(content, list) else [content]
    cells: list[Any] = [
        Paragraph(label, styles[label_style]) if label else "",
        body,
    ]
    return Table(
        [cells],
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
                ("TOPPADDING", (0, 0), (0, 0), label_offset),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def _section_heading(
    title: str,
    note: str,
    styles: dict[str, ParagraphStyle],
    *,
    space_before: float = 7 * mm,
) -> list[Any]:
    heading = Table(
        [
            [
                Paragraph(
                    f'<font name="Helvetica-Bold" color="#5BC5F2">/</font> {_markup(title)}',
                    styles["section"],
                ),
                Paragraph(_markup(note), styles["meta_right"]),
            ]
        ],
        colWidths=[CONTENT_WIDTH * 0.45, CONTENT_WIDTH * 0.55],
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
    # spaceBefore collapses at the top of a frame; a leading Spacer would not.
    heading.spaceBefore = space_before
    return [heading, Spacer(1, 4.2 * mm)]


def _page_chrome(pdf: canvas.Canvas, *, audience: str, day: str) -> None:
    pdf.saveState()
    pdf.resetTransforms()
    pdf.setStrokeColor(BORDER)
    pdf.setLineWidth(0.45)
    pdf.line(PAGE_MARGIN, 13 * mm, PAGE_WIDTH - PAGE_MARGIN, 13 * mm)
    pdf.setFillColor(MUTED)
    pdf.setFont("Courier", 6.6)
    pdf.drawString(
        PAGE_MARGIN,
        8.9 * mm,
        f"FRONTIER LAB INTELLIGENCE  /  {_audience_label(audience)}  /  {_display_day(day)}",
    )
    pdf.drawRightString(PAGE_WIDTH - PAGE_MARGIN, 8.9 * mm, f"PAGE {pdf.getPageNumber()}")
    pdf.restoreState()


def _later_page_chrome(
    pdf: canvas.Canvas, _: SimpleDocTemplate, *, audience: str, day: str
) -> None:
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
    _page_chrome(pdf, audience=audience, day=day)


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
    _page_chrome(pdf, audience=audience, day=day)


def _item_tickers(item: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for connection in item.get("connections") or []:
        for company in connection.get("companies") or []:
            ticker = str(company.get("ticker") or "")
            if ticker and ticker not in seen:
                seen.append(ticker)
    return seen


def _cover(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    audience = str(payload["audience"])
    day = str(payload["date"])
    items = list(payload.get("items") or [])
    story: list[Any] = [
        HRFlowable(width=14 * mm, thickness=2.6, color=BLUE, hAlign="LEFT", spaceAfter=3.4 * mm),
        Paragraph('<a name="brief-index"/>FRONTIER LAB INTELLIGENCE', styles["brand"]),
        Spacer(1, 11 * mm),
        Paragraph("DAILY<br/>INTELLIGENCE BRIEF", styles["cover_title"]),
        Spacer(1, 5 * mm),
        Paragraph(
            f'{_markup(_audience_label(audience))}'
            f'  <font color="#5BC5F2">/</font>  {_markup(_display_day(day))}',
            styles["cover_meta"],
        ),
        Spacer(1, 7 * mm),
        HRFlowable(width="100%", thickness=0.9, color=INK, spaceAfter=0),
        Spacer(1, 6 * mm),
    ]
    story.extend(
        _section_heading(
            "Today's brief",
            "CLICK A TITLE TO OPEN ITS ANALYSIS",
            styles,
        )
    )
    if not items:
        story.append(
            Table(
                [
                    [
                        Paragraph(
                            "No Insight cleared the audience bar for this complete run.",
                            styles["body"],
                        )
                    ]
                ],
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
            Paragraph(f"#{position}", styles["toc_rank"]),
            Paragraph(
                f'<link href="#insight-{position}" color="#235165">'
                f'{_markup(item["headline"])}</link>',
                styles["toc_title"],
            ),
            Paragraph(_markup(" ".join(_item_tickers(item))), styles["toc_tickers"]),
        ]
        for position, item in enumerate(items, start=1)
    ]
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


@lru_cache(maxsize=1)
def _bet_index() -> dict[str, dict[str, Any]]:
    payload = json.loads(COMPANY_MEMO_PATH.read_text(encoding="utf-8"))
    return {
        str(bet["id"]): bet
        for memo in (payload.get("companies") or {}).values()
        for bet in memo.get("bets") or []
    }


def _bet_url(ticker: str, bet_id: str) -> str:
    if not ticker:
        return ""
    query = {"company": ticker}
    if bet_id:
        query["bet"] = bet_id
    return f"{PUBLIC_APP_URL}/bit-lens/companies?{urlencode(query)}"


def _company_card(
    company: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    company_names: dict[str, Any],
    bets: dict[str, dict[str, Any]],
) -> Table:
    """One company read-through: direction rule, standing bet, model impact."""
    ticker = str(company.get("ticker") or "")
    name = str(company_names.get(ticker) or ticker)
    bet_id = str(company.get("bet_id") or "")
    bet = bets.get(bet_id, {})
    direction = str(bet.get("direction") or "")
    label, accent = {
        "upside": ("UPSIDE", POSITIVE),
        "downside": ("DOWNSIDE", NEGATIVE),
    }.get(direction, ("DIRECTION UNAVAILABLE", MUTED))
    threshold_met = bool(company.get("threshold_met"))

    badge_width = pdfmetrics.stringWidth(label, "Courier-Bold", 6.4) + 7 * mm
    header = Table(
        [
            [
                Paragraph(
                    f'{_markup(name)}'
                    f'  <font name="Courier" size="8" color="#6B6B68">{_markup(ticker)}</font>',
                    styles["company"],
                ),
                Paragraph(label, styles["badge"]),
            ]
        ],
        colWidths=[CARD_INNER_WIDTH - badge_width, badge_width],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (1, 0), (1, 0), accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 6),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (1, 0), (1, 0), 2.8),
                ("BOTTOMPADDING", (1, 0), (1, 0), 3.2),
            ]
        ),
    )

    status = (
        '<font name="Courier-Bold" color="#151515">REVIEW THESIS</font>'
        if threshold_met
        else "EARLY SIGNAL"
    )
    bet_link = _bet_url(ticker, bet_id)
    bet_reference = (
        f'<link href="{html.escape(bet_link, quote=True)}" color="#235165">{_markup(bet_id)}</link>'
        if bet_link and bet_id
        else _markup(bet_id)
    )
    meta_row = Table(
        [
            [
                Paragraph(f"STANDING BET  {bet_reference}", styles["meta"]),
                Paragraph(status, styles["meta_right"]),
            ]
        ],
        colWidths=[CARD_INNER_WIDTH * 0.55, CARD_INNER_WIDTH * 0.45],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    inner: list[Any] = [
        header,
        Spacer(1, 2.4 * mm),
        HRFlowable(width="100%", thickness=0.4, color=BORDER, spaceAfter=2.4 * mm),
        meta_row,
        Spacer(1, 2.2 * mm),
        Paragraph(_markup(bet.get("if")), styles["quiet"]),
    ]
    impact = company.get("impact")
    if impact:
        inner.extend([Spacer(1, 2.6 * mm), Paragraph(_markup(impact), styles["small"])])

    return Table(
        [[" ", inner]],
        colWidths=[1.8 * mm, BODY_WIDTH - 1.8 * mm],
        hAlign="RIGHT",
        splitByRow=1,
        splitInRow=1,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), accent),
                ("BACKGROUND", (1, 0), (1, -1), SURFACE),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("TOPPADDING", (0, 0), (0, -1), 0),
                ("BOTTOMPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 5 * mm),
                ("RIGHTPADDING", (1, 0), (1, -1), 5 * mm),
                ("TOPPADDING", (1, 0), (1, -1), 4 * mm),
                ("BOTTOMPADDING", (1, 0), (1, -1), 4.4 * mm),
            ]
        ),
    )


def _mechanism_block(
    connection: dict[str, Any],
    position: int,
    total: int,
    styles: dict[str, ParagraphStyle],
    company_names: dict[str, Any],
    bets: dict[str, dict[str, Any]],
) -> list[Any]:
    """Render one causal path and every company hanging off it."""
    label = "MECHANISM" if total == 1 else f"MECHANISM<br/>{position} OF {total}"
    companies = sorted(
        connection.get("companies") or [],
        key=lambda item: not bool(item.get("threshold_met")),
    )
    cards = [_company_card(company, styles, company_names, bets) for company in companies]
    opening: list[Any] = [
        _rail(label, Paragraph(_markup(connection.get("mechanism")), styles["body_ink"]), styles)
    ]
    if cards:
        opening.extend([Spacer(1, 4 * mm), cards[0]])
    story: list[Any] = [KeepTogether(opening)]
    for card in cards[1:]:
        story.extend([Spacer(1, 3 * mm), KeepTogether([card])])
    return story


def _sources_block(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    app_url = _insight_app_url(
        "investment", str(item.get("day") or ""), str(item.get("development_id") or "")
    )
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
    company_names = item.get("company_names") or {}
    provenance = item.get("provenance") or {}
    original = provenance.get("original_post") or {}
    trail = [
        str(original.get("author") or "").upper(),
        f'{provenance.get("source_event_count")} SOURCE EVENTS'
        if provenance.get("source_event_count")
        else "",
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
            label_offset=3.4,
        ),
        Spacer(1, 4.5 * mm),
        HRFlowable(width="100%", thickness=0.9, color=BLUE, spaceAfter=5.5 * mm),
        _rail("WHAT<br/>HAPPENED", Paragraph(_markup(item.get("what_changed")), styles["body"]), styles),
    ]
    connections = list(item.get("connections") or [])
    bets = _bet_index()
    if connections:
        tickers = len(_item_tickers(item))
        note = (
            f'{tickers} {"COMPANY" if tickers == 1 else "COMPANIES"}'
            f' / {len(connections)} {"MECHANISM" if len(connections) == 1 else "MECHANISMS"}'
        )
        story.extend(_section_heading("Company read-through", note, styles))
        for index, connection in enumerate(connections, start=1):
            if index > 1:
                story.append(Spacer(1, 6 * mm))
            story.extend(
                _mechanism_block(
                    connection, index, len(connections), styles, company_names, bets
                )
            )
    elif item.get("no_match_reason"):
        story.extend(_section_heading("No company read-through", "NO STANDING BET MATCHED", styles))
        story.append(_rail("REASON", Paragraph(_markup(item["no_match_reason"]), styles["body"]), styles))
    story.extend(_sources_block(item, styles))
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
        topMargin=27 * mm,
        bottomMargin=20 * mm,
        title=f"Frontier Lab Intelligence - {_audience_label(audience).title()} - {day}",
        author="Frontier Lab Intelligence",
        subject="Audience-specific, cited frontier AI daily intelligence",
        pageCompression=1,
    )
    story = _cover(payload, styles)
    for position, item in enumerate(payload.get("items") or [], start=1):
        story.append(PageBreak())
        story.extend(_insight(item, styles, position))

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
