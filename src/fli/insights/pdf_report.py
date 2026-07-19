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

from fli.insights import editorial_runs


REPORT_SCHEMA_VERSION = "daily-intelligence-pdf-v9"
DEFAULT_CACHE_ROOT = editorial_runs.DEFAULT_ROOT / "pdf-cache"
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
            Paragraph(f'#{int(item["rank"])}', styles["toc_rank"]),
            Paragraph(
                f'<link href="#insight-{int(item["rank"])}" color="#235165">'
                f'{_markup(item["title"])}</link>',
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
        story.extend(_section_title("Company read-through", styles))
        impact_copy = {
            "positive": ("↗", "Potential positive", POSITIVE),
            "negative": ("↘", "Potential negative", NEGATIVE),
            "mixed": ("↔", "Mixed", MUTED),
            "uncertain": ("?", "Direction unclear", MUTED),
        }
        rendered_group_count = 0
        for scope, scope_label in (
            ("portfolio", "PORTFOLIO COMPANIES"),
            ("outside_portfolio", "OUTSIDE THE DISCLOSED PORTFOLIO"),
        ):
            group = [
                entity
                for entity in entities
                if str(entity.get("scope") or "outside_portfolio") == scope
            ]
            if not group:
                continue
            if rendered_group_count:
                story.append(Spacer(1, 3.5 * mm))
            story.extend(
                [
                    Paragraph(scope_label, styles["label"]),
                    Spacer(1, 1.8 * mm),
                ]
            )
            rows: list[list[Any]] = []
            for entity in group:
                impact = str(entity.get("impact") or "uncertain")
                symbol, label, impact_color = impact_copy.get(
                    impact, impact_copy["uncertain"]
                )
                impact_style = ParagraphStyle(
                    f"Impact-{impact}",
                    parent=styles["impact"],
                    textColor=impact_color,
                )
                symbol_markup = (
                    f'<font name="{UNICODE_FONT}" size="9">{escape(symbol)}</font>'
                    if symbol != "?"
                    else "?"
                )
                rows.append(
                    [
                        Paragraph(_markup(entity.get("name")), styles["body_strong"]),
                        Paragraph(f"{symbol_markup}  {_markup(label)}", impact_style),
                        Paragraph(_markup(entity.get("mechanism")), styles["small"]),
                    ]
                )
            story.append(
                Table(
                    rows,
                    colWidths=[32 * mm, 37 * mm, CONTENT_WIDTH - 69 * mm],
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LINEABOVE", (0, 0), (-1, 0), 0.35, BORDER),
                            ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                            ("LINEBEFORE", (1, 0), (-1, -1), 0.35, BORDER),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                            ("LEFTPADDING", (0, 0), (0, -1), 0),
                            ("RIGHTPADDING", (0, 0), (0, -1), 7),
                            ("LEFTPADDING", (1, 0), (-1, -1), 7),
                            ("RIGHTPADDING", (1, 0), (-1, -1), 7),
                            ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
                        ]
                    ),
                )
            )
            rendered_group_count += 1
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
    day: str,
) -> list[Any]:
    if events:
        support = value.get("supports") or value.get("reason")
        title = str(value.get("title") or support or "Feed evidence")
        event_id = str(value.get("event_id") or "")
        url = (
            f"{PUBLIC_APP_URL}/evidence/feed?"
            f"{urlencode({'date': day, 'event_id': event_id})}"
            if event_id
            else value.get("url") or value.get("source_url")
        )
    else:
        title = str(value.get("title") or "Untitled source")
        url = value.get("url")
        support = value.get("supports")
    flowables: list[Any] = [
        Paragraph(_link(url, title), styles["small_link"]),
        Spacer(1, 1.2 * mm),
    ]
    if support and _plain(support) != _plain(title):
        flowables.append(Paragraph(_markup(support), styles["small"]))
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
        Spacer(1, 9 * mm),
        Paragraph("Evidence and sources", styles["title"]),
        Spacer(1, 3 * mm),
        Paragraph(
            _markup(item.get("title")),
            styles["cover_lede"],
        ),
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=0.8, color=BLUE, spaceBefore=0, spaceAfter=5 * mm),
    ]
    day = str(item.get("day") or "")
    line_before: list[tuple[Any, ...]] = []
    if events and research:
        source_rows: list[list[Any]] = [
            [
                Paragraph("FEED EVIDENCE", styles["label"]),
                Paragraph("DOCUMENTS &amp; CONTEXT", styles["label"]),
            ]
        ]
        for event, source in zip_longest(events, research):
            source_rows.append(
                [
                    _source_block(event, styles, events=True, day=day) if event else [],
                    _source_block(source, styles, events=False, day=day) if source else [],
                ]
            )
        col_widths = [CONTENT_WIDTH * 0.43, CONTENT_WIDTH * 0.57]
        line_before = [("LINEBEFORE", (1, 0), (1, -1), 0.35, BORDER)]
    else:
        values = events or research
        source_rows = [
            [
                Paragraph(
                    "FEED EVIDENCE" if events else "DOCUMENTS &amp; CONTEXT",
                    styles["label"],
                )
            ]
        ]
        for value in values:
            source_rows.append(
                [
                    _source_block(
                        value,
                        styles,
                        events=bool(events),
                        day=day,
                    )
                ]
            )
        col_widths = [CONTENT_WIDTH]
    story.append(
        Table(
            source_rows,
            colWidths=col_widths,
            repeatRows=1,
            splitByRow=1,
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                    *line_before,
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


def _insight(item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    header = Table(
        [
            [
                Paragraph(f'#{int(item["rank"])}', styles["rank"]),
                [
                    Paragraph(
                        f'<a name="insight-{int(item["rank"])}"/>{_markup(item.get("title"))}',
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
