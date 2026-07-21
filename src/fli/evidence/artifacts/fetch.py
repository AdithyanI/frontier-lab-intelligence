"""Safe bounded retrieval and deterministic text extraction for artifacts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shlex
import socket
import sqlite3
import tempfile
import time
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura
from lxml import etree, html as lxml_html
from pypdf import PdfReader

from fli.evidence.artifacts import store as artifacts
from fli.evidence.artifacts import urls as artifact_urls


FETCH_POLICY = "bounded-public-v1"
EXPLICIT_SELECTION_POLICY = "explicit-artifact-ids-v1"
JINA_READER_POLICY = "jina-reader-v1"
JINA_READER_SELECTION = "native-public-failure-v1"
JINA_READER_URL = "https://r.jina.ai/"
JINA_READER_EXTRACTOR = "jina-reader-markdown-v1"
JINA_API_KEY_ENV = "JINA_API_KEY"
DEFAULT_REPO_ENV = artifacts.REPO_ROOT / ".env"
EXTRACTOR_CONTRACT = "artifact-text-v2"
CONTENT_VALIDATION_CONTRACT = "artifact-content-v4"
GOOGLE_DOCS_TEXT_EXPORT_EXTRACTOR = "google-docs-text-export-v1"
GOOGLE_DOCS_TEXT_EXPORT_VERSION = "1"
GOOGLE_DOCS_REPAIR_POLICY = "google-docs-public-text-v1"
USER_AGENT = "frontier-lab-intelligence/0.1 artifact-fetch (+local research project)"
RAW_ROOT = artifacts.REPO_ROOT / "data" / "raw" / "artifacts" / "body" / "sha256"
TEXT_ROOT = (
    artifacts.REPO_ROOT / "data" / "derived" / "artifacts" / "text" / "sha256"
)
HTML_LIMIT = 8 * 1024 * 1024
PDF_LIMIT = 32 * 1024 * 1024
ROBOTS_LIMIT = 256 * 1024
MAX_REDIRECTS = 5
MAX_ATTEMPTS = 3
MAX_PDF_PAGES = 500
MAX_TEXT_CHARS = 5_000_000
MIN_HTML_TEXT_CHARS = 80
PLACEHOLDER_MIN_VISIBLE_CHARS = 100
PLACEHOLDER_CHAR_RATIO = 0.90
PLACEHOLDER_CHARS = frozenset({"\u2588", "\ufffd"})
PLACEHOLDER_ERROR_CODE = "extraction_placeholder_content"
NON_CONTENT_ERROR_CODE = "extraction_non_content_shell"
GARBLED_TEXT_ERROR_CODE = "extraction_garbled_text"
JINA_ELIGIBLE_KINDS = frozenset({"announcement", "article", "other"})
JINA_DEFERRED_HOST_SUFFIXES = (
    "docs.google.com",
    "forms.gle",
    "linkedin.com",
    "paperform.co",
    "twitter.com",
    "x.com",
    "youtu.be",
    "youtube.com",
)
CLIENT_SHELL_MARKERS = frozenset(
    {
        "checking your network connection",
        "enable javascript",
        "unable to load the form",
        "using a different browser",
    }
)
RETRYABLE_HTTP = frozenset({408, 425, 429, 500, 502, 503, 504})
REDIRECT_HTTP = frozenset({301, 302, 303, 307, 308})
SAFE_RESPONSE_HEADERS = frozenset(
    {
        "cache-control",
        "content-language",
        "content-length",
        "content-disposition",
        "content-type",
        "etag",
        "last-modified",
    }
)
REDIRECT_HOSTS = frozenset(
    {
        "bit.ly",
        "buff.ly",
        "goo.gle",
        "go.meta.me",
        "lnkd.in",
        "nvda.ws",
        "tinyurl.com",
    }
)
Resolver = Callable[[str, int], Iterable[str]]


@dataclass(frozen=True)
class Retrieved:
    final_url: str
    status_code: int
    redirect_chain: list[dict[str, Any]]
    headers: dict[str, str]
    content_type: str
    charset: str | None
    body: bytes


@dataclass(frozen=True)
class Extraction:
    success: bool
    extractor_contract: str
    extractor_version: str
    title: str | None
    text: str | None
    declared_canonical_url: str | None
    error_code: str | None = None
    error_message: str | None = None


def _signal_text(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def extracted_text_issue(
    text: str,
    *,
    title: str | None = None,
    final_url: str | None = None,
) -> tuple[str, str] | None:
    """Return a deterministic reason when extracted text is not artifact content."""
    visible_chars = [char for char in text if not char.isspace()]
    if len(visible_chars) >= PLACEHOLDER_MIN_VISIBLE_CHARS:
        placeholder_count = sum(char in PLACEHOLDER_CHARS for char in visible_chars)
        if placeholder_count / len(visible_chars) >= PLACEHOLDER_CHAR_RATIO:
            return (
                PLACEHOLDER_ERROR_CODE,
                "Extracted text is dominated by placeholder characters rather than "
                "readable artifact content",
            )

    normalized_title = _signal_text(title)
    normalized_text = _signal_text(text)
    split = urlsplit(str(final_url or ""))
    host = (split.hostname or "").lower()
    path = split.path.lower()

    shell_kind: str | None = None
    if (
        "just a moment" in normalized_title
        or "performing security verification" in normalized_text
        or "security service to protect against malicious bots" in normalized_text
    ):
        shell_kind = "security verification"
    elif (
        "checking your browser" in normalized_title
        or "verifying your browser" in normalized_title
        or "complete the check below to continue" in normalized_text
        or "vercel security checkpoint" in normalized_title
        or "vercel security checkpoint" in normalized_text
    ):
        shell_kind = "browser verification"
    elif "checking your browser - recaptcha" in normalized_title:
        shell_kind = "captcha verification"
    elif (
        "are you a robot" in normalized_title
        or "you've been blocked by network security" in normalized_text
        or (
            "detected unusual activity from your computer network"
            in normalized_text
            and "not a robot" in normalized_text
        )
    ):
        shell_kind = "bot or network security"
    elif (
        "javascript is disabled" in normalized_text
        or "enable javascript in your browser" in normalized_text
        or "javascript must be enabled" in normalized_text
        or "need to enable javascript" in normalized_text
    ) and len(text) < 1_000:
        shell_kind = "client-rendered JavaScript"
    elif "there was an error while loading. please reload this page" in normalized_text:
        shell_kind = "client loading error"
    elif (
        "page not found" in normalized_title
        or re.match(r"^404(?:\s|$)", normalized_title)
        or normalized_text.startswith("404 ")
    ):
        shell_kind = "not-found"
    elif normalized_title.startswith("redirecting") and normalized_text.startswith(
        "redirecting"
    ):
        shell_kind = "redirect"
    elif (
        "not available in your region" in normalized_title
        or "isn't yet available in your region" in normalized_text
    ):
        shell_kind = "region-unavailable"
    elif host in {"consent.google.com", "consent.youtube.com"}:
        shell_kind = "consent"
    elif host == "docs.google.com" and path.startswith("/document/") and (
        (
            "javascript" in normalized_text
            and (
                "file cannot be opened" in normalized_text
                or "file can't be opened" in normalized_text
                or "datei kann" in normalized_text
                or "nicht geöffnet werden" in normalized_text
            )
        )
        or (
            len(text) < 1_500
            and sum(
                marker in normalized_text
                for marker in (
                    "troubleshooting",
                    "accessibility",
                    "fehlerbehebung",
                    "bedienungshilfen",
                    "share",
                    "freigeben",
                )
            )
            >= 3
        )
    ):
        shell_kind = "Google Docs editor"
    elif (
        normalized_title in {
            "sign in",
            "sign in required",
            "google forms: sign-in",
        }
        and len(text) < 2_500
        and (
            "continue with" in normalized_text
            or "email or phone" in normalized_text
            or "sign in to" in normalized_text
            or "securely sign you in" in normalized_text
        )
    ) or (
        normalized_title.startswith("welcome back")
        and len(text) < 2_500
        and ("continue with" in normalized_text or "log in" in normalized_text)
    ) or (
        host == "chatgpt.com"
        and len(text) < 1_000
        and "log in to get answers" in normalized_text
    ) or (path.startswith(("/login", "/signin", "/sign-in")) and len(text) < 2_500):
        shell_kind = "authentication"
    elif "access denied" in normalized_title or normalized_text.startswith(
        "access denied"
    ):
        shell_kind = "access-denied"
    elif "/error/" in path and len(text) < 1_000:
        shell_kind = "error"
    elif host in {"youtube.com", "www.youtube.com", "youtu.be"} and len(text) < 1_000:
        shell_kind = "video site chrome"
    if shell_kind is not None:
        return (
            NON_CONTENT_ERROR_CODE,
            f"Extracted text is a {shell_kind} shell rather than artifact content",
        )

    control_count = sum(
        unicodedata.category(char).startswith("C") and char not in "\n\r\t"
        for char in text
    )
    ascii_printable_count = sum(
        ord(char) < 128 and (char.isprintable() or char in "\n\r\t")
        for char in text
    )
    if (
        control_count >= 10
        and control_count / max(len(text), 1) >= 0.001
        and ascii_printable_count / max(len(text), 1) < 0.5
    ):
        return (
            GARBLED_TEXT_ERROR_CODE,
            "Extracted text contains control-heavy malformed encoding rather than "
            "readable artifact content",
        )
    return None


def validate_extraction(
    extraction: Extraction, *, final_url: str | None = None
) -> Extraction:
    """Fail a successful extraction when its text is not usable artifact content."""
    if not extraction.success or extraction.text is None:
        return extraction
    issue = extracted_text_issue(
        extraction.text,
        title=extraction.title,
        final_url=final_url or extraction.declared_canonical_url,
    )
    if issue is None:
        return extraction
    error_code, error_message = issue
    return replace(
        extraction,
        success=False,
        text=None,
        error_code=error_code,
        error_message=error_message,
    )


class FetchFailure(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _default_resolver(host: str, port: int) -> list[str]:
    try:
        return sorted(
            {
                str(item[4][0])
                for item in socket.getaddrinfo(
                    host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
                )
            }
        )
    except socket.gaierror as exc:
        raise FetchFailure("dns_error", str(exc), retryable=True) from exc


def _validate_hop(url: str, resolver: Resolver) -> None:
    try:
        canonical = artifact_urls.canonicalize_url(url)
    except ValueError as exc:
        raise FetchFailure("unsafe_url", str(exc), retryable=False) from exc
    split = urlsplit(canonical)
    host = split.hostname or ""
    if host.lower() == "localhost":
        raise FetchFailure("unsafe_host", "localhost is not fetchable", retryable=False)
    port = split.port or (443 if split.scheme == "https" else 80)
    addresses = list(resolver(host, port))
    if not addresses:
        raise FetchFailure("dns_empty", f"No address for {host}", retryable=True)
    unsafe = [address for address in addresses if not artifact_urls.is_global_address(address)]
    if unsafe:
        raise FetchFailure(
            "unsafe_address",
            f"{host} resolved to non-global address(es): {', '.join(unsafe)}",
            retryable=False,
        )


def _media_type(value: str | None) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _charset(value: str | None) -> str | None:
    match = re.search(r"charset\s*=\s*['\"]?([^;'\"\s]+)", str(value or ""), re.I)
    return match.group(1).strip() if match else None


def _body_limit(url: str, content_type: str) -> int:
    if content_type == "application/pdf" or urlsplit(url).path.lower().endswith(".pdf"):
        return PDF_LIMIT
    return HTML_LIMIT


def _safe_headers(response: httpx.Response) -> dict[str, str]:
    return {
        key.lower(): value
        for key, value in response.headers.items()
        if key.lower() in SAFE_RESPONSE_HEADERS
    }


def _google_doc_text_export_url(url: str) -> str | None:
    """Return the public text-export endpoint for a Google document URL.

    The export endpoint is retrieval infrastructure only. The original Docs URL
    remains the artifact identity so adding the adapter cannot churn artifact
    IDs or turn a provider download URL into a new canonical artifact.
    """
    split = urlsplit(url)
    if (split.hostname or "").lower() != "docs.google.com":
        return None
    match = re.match(
        r"^/document/(?:u/\d+/)?d/([A-Za-z0-9_-]+)(?:/|$)",
        split.path,
    )
    if match is None or match.group(1) == "e":
        return None
    document_id = match.group(1)
    return f"https://docs.google.com/document/d/{document_id}/export?format=txt"


def _content_disposition_title(value: str | None) -> str | None:
    header = str(value or "")
    extended = re.search(r"(?:^|;)\s*filename\*\s*=\s*UTF-8''([^;]+)", header, re.I)
    if extended is not None:
        filename = unquote(extended.group(1)).strip().strip('"')
    else:
        basic = re.search(r'(?:^|;)\s*filename\s*=\s*"([^"]+)"', header, re.I)
        if basic is None:
            basic = re.search(r"(?:^|;)\s*filename\s*=\s*([^;]+)", header, re.I)
        filename = basic.group(1).strip().strip('"') if basic is not None else ""
    if filename.lower().endswith(".txt"):
        filename = filename[:-4]
    return filename.strip() or None


def _extract_google_doc_text_export(retrieved: Retrieved) -> Extraction:
    """Extract a public Google document's bounded plain-text export."""
    contract = GOOGLE_DOCS_TEXT_EXPORT_EXTRACTOR
    contract_version = GOOGLE_DOCS_TEXT_EXPORT_VERSION
    if retrieved.content_type != "text/plain":
        return Extraction(
            False,
            contract,
            contract_version,
            None,
            None,
            None,
            "google_doc_export_unavailable",
            "Google Docs did not return a public plain-text document export",
        )
    encoding = retrieved.charset or "utf-8"
    if encoding.lower().replace("_", "-") in {"utf-8", "utf8"}:
        encoding = "utf-8-sig"
    try:
        decoded = retrieved.body.decode(encoding, errors="replace")
    except LookupError:
        decoded = retrieved.body.decode("utf-8-sig", errors="replace")
    clean = _normalize_text(decoded)
    if not clean.strip():
        return Extraction(
            False,
            contract,
            contract_version,
            None,
            None,
            None,
            "google_doc_export_empty",
            "Google Docs returned an empty plain-text document export",
        )
    if len(clean) > MAX_TEXT_CHARS:
        return Extraction(
            False,
            contract,
            contract_version,
            None,
            None,
            None,
            "text_too_large",
            f"Extracted text exceeded {MAX_TEXT_CHARS} characters",
        )
    return Extraction(
        True,
        contract,
        contract_version,
        _content_disposition_title(retrieved.headers.get("content-disposition")),
        clean,
        None,
    )


def _safe_get(
    client: httpx.Client,
    url: str,
    *,
    resolver: Resolver,
    max_bytes: int | None = None,
    max_redirects: int = MAX_REDIRECTS,
    accepted_statuses: frozenset[int] = frozenset(),
) -> Retrieved:
    current = url
    visited: set[str] = set()
    chain: list[dict[str, Any]] = []
    for hop in range(max_redirects + 1):
        _validate_hop(current, resolver)
        canonical_hop = artifact_urls.canonicalize_url(current)
        if canonical_hop in visited:
            raise FetchFailure("redirect_loop", "Redirect loop detected", retryable=False)
        visited.add(canonical_hop)
        try:
            with client.stream("GET", current) as response:
                location = response.headers.get("location")
                chain.append(
                    {
                        "url": str(response.request.url),
                        "status": response.status_code,
                        "location": location,
                    }
                )
                if response.status_code in REDIRECT_HTTP:
                    if not location:
                        raise FetchFailure(
                            "redirect_missing_location",
                            "Redirect response has no Location header",
                            retryable=False,
                        )
                    if hop >= max_redirects:
                        raise FetchFailure(
                            "too_many_redirects",
                            f"Exceeded {max_redirects} redirects",
                            retryable=False,
                        )
                    current = urljoin(str(response.request.url), location)
                    continue
                if response.status_code in RETRYABLE_HTTP:
                    raise FetchFailure(
                        f"http_{response.status_code}",
                        f"HTTP {response.status_code}",
                        retryable=True,
                    )
                if not 200 <= response.status_code < 300 and response.status_code not in accepted_statuses:
                    raise FetchFailure(
                        f"http_{response.status_code}",
                        f"HTTP {response.status_code}",
                        retryable=False,
                    )
                final_decision = artifact_urls.classify_candidate(
                    str(response.request.url)
                )
                if final_decision.decision != "accepted":
                    raise FetchFailure(
                        f"final_url_{final_decision.reason_code}",
                        "Final URL is not artifact-eligible: "
                        f"{final_decision.reason_code}",
                        retryable=False,
                    )
                content_type_header = response.headers.get("content-type")
                content_type = _media_type(content_type_header)
                limit = max_bytes or _body_limit(str(response.request.url), content_type)
                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > limit:
                    raise FetchFailure(
                        "body_too_large",
                        f"Declared body is {declared} bytes; limit is {limit}",
                        retryable=False,
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > limit:
                        raise FetchFailure(
                            "body_too_large",
                            f"Decoded body exceeded {limit} bytes",
                            retryable=False,
                        )
                return Retrieved(
                    final_url=str(response.request.url),
                    status_code=response.status_code,
                    redirect_chain=chain,
                    headers=_safe_headers(response),
                    content_type=content_type,
                    charset=_charset(content_type_header),
                    body=bytes(body),
                )
        except FetchFailure:
            raise
        except httpx.TimeoutException as exc:
            raise FetchFailure("timeout", str(exc), retryable=True) from exc
        except httpx.TransportError as exc:
            raise FetchFailure("transport_error", str(exc), retryable=True) from exc
    raise FetchFailure("too_many_redirects", "Redirect limit exceeded", retryable=False)


def _origin(url: str) -> str:
    split = urlsplit(url)
    port = split.port
    default = (split.scheme == "http" and port in {None, 80}) or (
        split.scheme == "https" and port in {None, 443}
    )
    netloc = split.hostname or ""
    if not default and port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((split.scheme, netloc, "", "", ""))


def _robots_allowed(
    client: httpx.Client,
    url: str,
    *,
    resolver: Resolver,
    cache: dict[str, tuple[bool, float]],
) -> tuple[bool, float]:
    origin = _origin(url)
    if origin in cache:
        return cache[origin]
    robots_url = f"{origin}/robots.txt"
    try:
        response = _safe_get(
            client,
            robots_url,
            resolver=resolver,
            max_bytes=ROBOTS_LIMIT,
            max_redirects=2,
            accepted_statuses=frozenset({404}),
        )
        if response.status_code == 404:
            result = (True, 0.25)
        else:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.body.decode("utf-8", errors="replace").splitlines())
            delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0.25
            result = (parser.can_fetch(USER_AGENT, url), min(max(float(delay), 0.25), 10.0))
    except FetchFailure:
        # One public-page attempt may proceed when robots is transiently unavailable.
        result = (True, 0.25)
    cache[origin] = result
    return result


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [line.rstrip() for line in value.split("\n")]
    return "\n".join(lines).strip() + "\n"


def _html_metadata(body: bytes, final_url: str) -> tuple[str | None, str | None]:
    try:
        tree = lxml_html.fromstring(body, base_url=final_url)
    except (ValueError, TypeError, etree.ParserError):
        return None, None
    titles = [str(value).strip() for value in tree.xpath("//title/text()") if str(value).strip()]
    canonicals = tree.xpath(
        "//link[contains(concat(' ', translate(@rel, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
        "'abcdefghijklmnopqrstuvwxyz'), ' '), ' canonical ')]/@href"
    )
    declared = urljoin(final_url, str(canonicals[0]).strip()) if canonicals else None
    return (titles[0] if titles else None), declared


def _sec_archives_text(body: bytes, final_url: str) -> str | None:
    split = urlsplit(final_url)
    host = (split.hostname or "").lower()
    if not (host == "sec.gov" or host.endswith(".sec.gov")):
        return None
    if not split.path.lower().startswith("/archives/edgar/data/"):
        return None
    try:
        tree = lxml_html.fromstring(body, base_url=final_url)
    except (ValueError, TypeError, etree.ParserError):
        return None
    for node in tree.xpath("//script|//style|//noscript"):
        node.drop_tree()
    blocks = []
    for node in tree.xpath("//p|//h1|//h2|//h3|//h4|//li"):
        text = " ".join(node.text_content().replace("\xa0", " ").split())
        if text:
            blocks.append(text)
    if not blocks:
        for node in tree.xpath("//td"):
            text = " ".join(node.text_content().replace("\xa0", " ").split())
            if text:
                blocks.append(text)
    clean = _normalize_text("\n\n".join(blocks))
    return clean if len(clean.strip()) >= MIN_HTML_TEXT_CHARS else None


def extract_content(
    body: bytes,
    *,
    content_type: str,
    charset: str | None,
    final_url: str,
    artifact_kind: str,
) -> Extraction:
    is_pdf = content_type == "application/pdf" or body.startswith(b"%PDF-")
    if is_pdf:
        try:
            reader = PdfReader(io.BytesIO(body))
            if reader.is_encrypted:
                return Extraction(
                    False, "pdf-pypdf-v1", version("pypdf"), None, None, None,
                    "pdf_encrypted", "Encrypted PDFs are not extracted in v1",
                )
            if len(reader.pages) > MAX_PDF_PAGES:
                return Extraction(
                    False, "pdf-pypdf-v1", version("pypdf"), None, None, None,
                    "pdf_too_many_pages", f"PDF has more than {MAX_PDF_PAGES} pages",
                )
            chunks: list[str] = []
            total = 0
            for page in reader.pages:
                text = page.extract_text() or ""
                total += len(text)
                if total > MAX_TEXT_CHARS:
                    return Extraction(
                        False, "pdf-pypdf-v1", version("pypdf"), None, None, None,
                        "text_too_large", f"Extracted text exceeded {MAX_TEXT_CHARS} characters",
                    )
                chunks.append(text)
            clean = _normalize_text("\n\n".join(chunks))
            title = None
            if reader.metadata:
                title = str(reader.metadata.title or "").strip() or None
            if len(clean.strip()) < MIN_HTML_TEXT_CHARS:
                return Extraction(
                    False, "pdf-pypdf-v1", version("pypdf"), title, None, None,
                    "pdf_no_text_layer", "PDF has no substantive extractable text",
                )
            return Extraction(True, "pdf-pypdf-v1", version("pypdf"), title, clean, None)
        except Exception as exc:  # pypdf raises a wide family of parse exceptions
            return Extraction(
                False, "pdf-pypdf-v1", version("pypdf"), None, None, None,
                "pdf_unreadable", str(exc),
            )

    textual = content_type.startswith("text/") or content_type in {
        "application/json",
        "application/ld+json",
        "application/xml",
        "application/xhtml+xml",
        "text/xml",
    }
    htmlish = content_type in {"text/html", "application/xhtml+xml", ""} or b"<html" in body[:4096].lower()
    if htmlish:
        fallback_title, declared = _html_metadata(body, final_url)
        document = trafilatura.bare_extraction(
            body,
            url=final_url,
            output_format="python",
            include_comments=False,
            include_tables=True,
            include_images=False,
            include_links=False,
        )
        title = (str(document.title).strip() or None) if document and document.title else fallback_title
        if artifact_kind == "video":
            return Extraction(
                False, "html-trafilatura-v1", trafilatura.__version__, title, None, declared,
                "video_transcript_unavailable", "Video pages require a later transcript stage",
            )
        clean = _normalize_text(document.text) if document and document.text else ""
        if len(clean.strip()) < MIN_HTML_TEXT_CHARS:
            sec_text = _sec_archives_text(body, final_url)
            if sec_text is not None:
                return Extraction(
                    True,
                    "html-sec-archives-lxml-v1",
                    version("lxml"),
                    title,
                    sec_text,
                    declared,
                )
        if len(clean.strip()) < MIN_HTML_TEXT_CHARS:
            return Extraction(
                False, "html-trafilatura-v1", trafilatura.__version__, title, None, declared,
                "extraction_empty_or_client_rendered",
                "HTML did not contain substantive server-rendered main text",
            )
        lowered = clean.lower()
        shell_markers = sum(marker in lowered for marker in CLIENT_SHELL_MARKERS)
        if len(clean) < 2_000 and shell_markers >= 2:
            return Extraction(
                False,
                "html-trafilatura-v1",
                trafilatura.__version__,
                title,
                None,
                declared,
                "extraction_client_rendered_shell",
                "HTML exposed only a client-rendered error or loading shell",
            )
        return Extraction(
            True, "html-trafilatura-v1", trafilatura.__version__, title, clean, declared
        )
    if textual:
        encoding = charset or "utf-8"
        try:
            decoded = body.decode(encoding, errors="replace")
        except LookupError:
            decoded = body.decode("utf-8", errors="replace")
        clean = _normalize_text(decoded)
        if not clean.strip():
            return Extraction(
                False, "text-v1", "stdlib", None, None, None,
                "text_empty", "Text response was empty",
            )
        return Extraction(True, "text-v1", "stdlib", None, clean, None)
    return Extraction(
        False, "unsupported-v1", "stdlib", None, None, None,
        "unsupported_media_type", f"Unsupported media type: {content_type or 'unknown'}",
    )


def _write_snapshot(root: Path, sha256: str, suffix: str, body: bytes) -> str:
    destination = root / sha256[:2] / f"{sha256}{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        handle = tempfile.NamedTemporaryFile(dir=destination.parent, delete=False)
        try:
            with handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(handle.name, destination)
        finally:
            Path(handle.name).unlink(missing_ok=True)
    try:
        return str(destination.relative_to(artifacts.REPO_ROOT))
    except ValueError:
        return str(destination)


def _stratum(row: dict[str, Any]) -> str:
    host = str(row["host"]).lower()
    if host in REDIRECT_HOSTS:
        return "redirect"
    if row["artifact_kind"] == "paper":
        return "paper"
    if row["artifact_kind"] == "repository":
        return "repository"
    if row["artifact_kind"] == "video":
        return "video"
    if host in {"x.com", "www.x.com"} and "/i/article/" in row["canonical_url"]:
        return "x_article"
    return "html"


def _selection_rows(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """WITH scored AS (
               SELECT candidate.artifact_id, candidate.event_day,
                      candidate.event_id, candidate.source_rank,
                      candidate.day_candidate_count, candidate.expanded_url,
                      CAST(candidate.source_rank - 1 AS REAL) /
                          MAX(candidate.day_candidate_count - 1, 1) AS normalized_rank,
                      ROW_NUMBER() OVER (
                          PARTITION BY candidate.artifact_id
                          ORDER BY
                              CAST(candidate.source_rank - 1 AS REAL) /
                                  MAX(candidate.day_candidate_count - 1, 1),
                              CASE WHEN candidate.source_external_id =
                                  candidate.disclosure_external_id THEN 0 ELSE 1 END,
                              candidate.event_id, candidate.expanded_url
                      ) AS ordinal
               FROM artifact_import_candidate candidate
               WHERE candidate.decision = 'accepted'
           )
           SELECT artifact.*, scored.event_day, scored.event_id,
                  scored.source_rank, scored.normalized_rank,
                  scored.expanded_url AS selected_url,
                  COUNT(DISTINCT observation.source_external_id) AS owner_count
           FROM scored
           JOIN artifact ON artifact.artifact_id = scored.artifact_id
           LEFT JOIN artifact_observation observation
             ON observation.artifact_id = artifact.artifact_id
           WHERE scored.ordinal = 1
           GROUP BY artifact.artifact_id
           ORDER BY scored.normalized_rank, owner_count DESC,
                    artifact.canonical_url"""
    ).fetchall()
    return [dict(row) for row in rows]


def select_cohort(conn: Any, *, limit: int) -> list[dict[str, Any]]:
    rows = _selection_rows(conn)
    if limit <= 0:
        return []
    quota = {
        "html": 12,
        "paper": 5,
        "repository": 4,
        "video": 3,
        "x_article": 3,
        "redirect": 3,
    }
    if limit != 30:
        quota = {key: max(1, round(value * limit / 30)) for key, value in quota.items()}
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    host_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}

    def add(row: dict[str, Any], *, respect_quota: bool) -> bool:
        artifact_id = str(row["artifact_id"])
        if artifact_id in selected_ids:
            return False
        host = str(row["host"])
        event = str(row["event_id"])
        stratum = _stratum(row)
        if host_counts.get(host, 0) >= 4 or event_counts.get(event, 0) >= 2:
            return False
        if respect_quota and sum(1 for item in selected if item["stratum"] == stratum) >= quota[stratum]:
            return False
        item = dict(row)
        item["stratum"] = stratum
        selected.append(item)
        selected_ids.add(artifact_id)
        host_counts[host] = host_counts.get(host, 0) + 1
        event_counts[event] = event_counts.get(event, 0) + 1
        return True

    for stratum in quota:
        for row in rows:
            if len(selected) >= limit:
                break
            if _stratum(row) == stratum:
                add(row, respect_quota=True)
    for row in rows:
        if len(selected) >= limit:
            break
        add(row, respect_quota=False)
    for rank, item in enumerate(selected, 1):
        item["selection_rank"] = rank
    return selected


def select_explicit_artifacts(
    conn: Any, *, artifact_ids: Iterable[str]
) -> list[dict[str, Any]]:
    """Resolve an exact deterministic catalog cohort without widening fetch scope."""
    requested = sorted({str(value or "").strip() for value in artifact_ids})
    if not requested or "" in requested:
        raise ValueError("at least one non-empty artifact_id is required")
    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    unbound: list[str] = []
    for artifact_id in requested:
        artifact = conn.execute(
            "SELECT * FROM artifact WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        if artifact is None:
            missing.append(artifact_id)
            continue
        source = conn.execute(
            """SELECT event_day, event_id, source_rank,
                      day_candidate_count, expanded_url AS selected_url
               FROM artifact_import_candidate
               WHERE artifact_id = ? AND decision = 'accepted'
               ORDER BY source_rank, event_day, event_id
               LIMIT 1""",
            (artifact_id,),
        ).fetchone()
        if source is None:
            source = conn.execute(
                """SELECT event_day, event_id, source_rank,
                          day_candidate_count, ? AS selected_url
                   FROM artifact_event_supplement
                   WHERE artifact_id = ?
                   ORDER BY source_rank, event_day, event_id
                   LIMIT 1""",
                (str(artifact["canonical_url"]), artifact_id),
            ).fetchone()
        if source is None:
            unbound.append(artifact_id)
            continue
        item = dict(artifact)
        item.update(dict(source))
        item["normalized_rank"] = (int(source["source_rank"]) - 1) / max(
            int(source["day_candidate_count"]) - 1, 1
        )
        item["stratum"] = _stratum(item)
        selected.append(item)
    if missing:
        raise ValueError("unknown artifact_id: " + ", ".join(missing))
    if unbound:
        raise ValueError(
            "artifact has no accepted source association: " + ", ".join(unbound)
        )
    for rank, item in enumerate(selected, start=1):
        item["selection_rank"] = rank
    return selected


def restore_pruned_run_items(
    conn: Any,
    *,
    fetch_run_id: str,
    run_items: list[tuple[Any, ...]],
) -> bool:
    """Restore deterministic run membership removed by catalog pruning.

    ``artifact`` deletion cascades into run items and fetch attempts, while the
    parent run remains as immutable history. Reimporting the same canonical
    artifact can therefore recreate the same deterministic run id with missing
    children. The current selection is authoritative in that case.
    """
    selected_ids = {str(item[1]) for item in run_items}
    surviving_ids = {
        str(row["artifact_id"])
        for row in conn.execute(
            """SELECT artifact_id FROM artifact_fetch_run_item
               WHERE fetch_run_id = ?""",
            (fetch_run_id,),
        ).fetchall()
    }
    if surviving_ids == selected_ids:
        return False
    with conn:
        conn.execute(
            "DELETE FROM artifact_fetch_run_item WHERE fetch_run_id = ?",
            (fetch_run_id,),
        )
        conn.executemany(
            """INSERT INTO artifact_fetch_run_item
               (fetch_run_id, artifact_id, selection_rank, stratum,
                selected_url, source_day, source_rank, normalized_rank,
                source_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            run_items,
        )
        conn.execute(
            """UPDATE artifact_fetch_run
               SET expected_count = ?, success_count = 0,
                   failed_retryable_count = 0, failed_terminal_count = 0,
                   completed_at = NULL, status = 'in_progress'
               WHERE fetch_run_id = ?""",
            (len(run_items), fetch_run_id),
        )
    return True


def _create_explicit_fetch_run(
    conn: Any,
    selection: list[dict[str, Any]],
    *,
    fetch_policy: str = FETCH_POLICY,
) -> tuple[str, bool]:
    payload = [
        [item["artifact_id"], item["selected_url"], item["event_id"]]
        for item in selection
    ]
    fingerprint = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
    fetch_run_id = hashlib.sha256(
        _canonical_json(
            [fetch_policy, EXPLICIT_SELECTION_POLICY, fingerprint]
        ).encode()
    ).hexdigest()
    run_items = [
        (
            fetch_run_id,
            item["artifact_id"],
            item["selection_rank"],
            item["stratum"],
            item["selected_url"],
            item["event_day"],
            item["source_rank"],
            item["normalized_rank"],
            item["event_id"],
        )
        for item in selection
    ]
    existing = conn.execute(
        "SELECT status FROM artifact_fetch_run WHERE fetch_run_id = ?",
        (fetch_run_id,),
    ).fetchone()
    if existing is not None:
        if restore_pruned_run_items(
            conn,
            fetch_run_id=fetch_run_id,
            run_items=run_items,
        ):
            return fetch_run_id, False
        if str(existing["status"]) != "complete":
            return fetch_run_id, False
        pending = conn.execute(
            """SELECT 1
               FROM artifact_fetch_run_item item
               WHERE item.fetch_run_id = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM artifact_fetch fetch
                     WHERE fetch.artifact_id = item.artifact_id
                       AND fetch.fetch_policy = ?
                       AND fetch.status IN ('success', 'failed_terminal')
                 )
                 AND COALESCE((
                     SELECT MAX(fetch.attempt_number)
                     FROM artifact_fetch fetch
                     WHERE fetch.artifact_id = item.artifact_id
                       AND fetch.fetch_policy = ?
                 ), 0) < ?
               LIMIT 1""",
            (fetch_run_id, fetch_policy, fetch_policy, MAX_ATTEMPTS),
        ).fetchone()
        if pending is None:
            return fetch_run_id, True
        with conn:
            conn.execute(
                """UPDATE artifact_fetch_run
                   SET status = 'in_progress', completed_at = NULL
                   WHERE fetch_run_id = ?""",
                (fetch_run_id,),
            )
        return fetch_run_id, False
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                status)
               VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, 'in_progress')""",
            (
                fetch_run_id,
                artifacts.SCHEMA_VERSION,
                fetch_policy,
                EXPLICIT_SELECTION_POLICY,
                fingerprint,
                len(selection),
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO artifact_fetch_run_item
               (fetch_run_id, artifact_id, selection_rank, stratum,
                selected_url, source_day, source_rank, normalized_rank,
                source_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            run_items,
        )
    return fetch_run_id, False


def _create_fetch_run(conn: Any, selection: list[dict[str, Any]]) -> tuple[str, bool]:
    # ``fetch --limit N`` names one frozen validation cohort, not an evolving
    # top-N query. Redirect convergence can remove provisional redirect URLs
    # from the live ranking, so always resume the first cohort created for the
    # same policy and size. A future second cohort needs an explicit selection
    # policy/version rather than silently changing this one.
    frozen = conn.execute(
        """SELECT fetch_run_id
           FROM artifact_fetch_run
           WHERE fetch_policy = ? AND selection_policy = ?
             AND expected_count = ?
           ORDER BY started_at, fetch_run_id
           LIMIT 1""",
        (FETCH_POLICY, "stratified-attention-v1", len(selection)),
    ).fetchone()
    if frozen is not None:
        fetch_run_id = str(frozen["fetch_run_id"])
        existing = conn.execute(
            "SELECT status FROM artifact_fetch_run WHERE fetch_run_id = ?",
            (fetch_run_id,),
        ).fetchone()
        assert existing is not None
        if str(existing["status"]) != "complete":
            return fetch_run_id, False
        pending = conn.execute(
            """SELECT 1
               FROM artifact_fetch_run_item item
               WHERE item.fetch_run_id = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM artifact_fetch fetch
                     WHERE fetch.artifact_id = item.artifact_id
                       AND fetch.fetch_policy = ?
                       AND fetch.status IN ('success', 'failed_terminal')
                 )
                 AND COALESCE((
                     SELECT MAX(fetch.attempt_number)
                     FROM artifact_fetch fetch
                     WHERE fetch.artifact_id = item.artifact_id
                       AND fetch.fetch_policy = ?
                 ), 0) < ?
               LIMIT 1""",
            (fetch_run_id, FETCH_POLICY, FETCH_POLICY, MAX_ATTEMPTS),
        ).fetchone()
        if pending is None:
            return fetch_run_id, True
        with conn:
            conn.execute(
                """UPDATE artifact_fetch_run
                   SET status = 'in_progress', completed_at = NULL
                   WHERE fetch_run_id = ?""",
                (fetch_run_id,),
            )
        return fetch_run_id, False

    payload = [
        [
            item["selection_rank"],
            item["selected_url"],
            item["stratum"],
            item["event_day"],
            item["event_id"],
        ]
        for item in selection
    ]
    fingerprint = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
    fetch_run_id = hashlib.sha256(
        _canonical_json([FETCH_POLICY, "stratified-attention-v1", fingerprint]).encode()
    ).hexdigest()

    existing = conn.execute(
        "SELECT status FROM artifact_fetch_run WHERE fetch_run_id = ?", (fetch_run_id,)
    ).fetchone()
    if existing is not None:
        return fetch_run_id, str(existing["status"]) == "complete"
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                status)
               VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, 'in_progress')""",
            (
                fetch_run_id,
                artifacts.SCHEMA_VERSION,
                FETCH_POLICY,
                "stratified-attention-v1",
                fingerprint,
                len(selection),
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO artifact_fetch_run_item
               (fetch_run_id, artifact_id, selection_rank, stratum,
                selected_url, source_day, source_rank, normalized_rank,
                source_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    fetch_run_id,
                    item["artifact_id"],
                    item["selection_rank"],
                    item["stratum"],
                    item["selected_url"],
                    item["event_day"],
                    item["source_rank"],
                    item["normalized_rank"],
                    item["event_id"],
                )
                for item in selection
            ],
        )
    return fetch_run_id, False


def _claim(
    conn: Any,
    *,
    fetch_run_id: str,
    artifact_id: str,
    requested_url: str,
    fetch_policy: str = FETCH_POLICY,
) -> str | None:
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        finished = conn.execute(
            """SELECT 1 FROM artifact_fetch
               WHERE artifact_id = ? AND fetch_policy = ?
                 AND status IN ('success', 'failed_terminal')""",
            (artifact_id, fetch_policy),
        ).fetchone()
        if finished is not None:
            conn.commit()
            return None
        conn.execute(
            """UPDATE artifact_fetch
               SET status = 'failed_retryable', completed_at = ?,
                   error_code = 'lease_expired',
                   error_message = 'Previous worker lease expired', retryable = 1
               WHERE artifact_id = ? AND fetch_policy = ?
                 AND status = 'in_progress' AND lease_expires_at < ?""",
            (now, artifact_id, fetch_policy, now),
        )
        active = conn.execute(
            """SELECT 1 FROM artifact_fetch
               WHERE artifact_id = ? AND fetch_policy = ? AND status = 'in_progress'""",
            (artifact_id, fetch_policy),
        ).fetchone()
        if active is not None:
            conn.commit()
            return None
        attempt = int(
            conn.execute(
                """SELECT COALESCE(MAX(attempt_number), 0) FROM artifact_fetch
                   WHERE artifact_id = ? AND fetch_policy = ?""",
                (artifact_id, fetch_policy),
            ).fetchone()[0]
        ) + 1
        if attempt > MAX_ATTEMPTS:
            conn.commit()
            return None
        request_key = hashlib.sha256(
            _canonical_json([artifact_id, fetch_policy, requested_url]).encode()
        ).hexdigest()
        fetch_id = hashlib.sha256(
            _canonical_json([request_key, attempt]).encode()
        ).hexdigest()
        prior_converged_fetch = conn.execute(
            """SELECT request_key, status, final_url
               FROM artifact_fetch WHERE fetch_id = ?""",
            (fetch_id,),
        ).fetchone()
        if prior_converged_fetch is not None:
            if (
                str(prior_converged_fetch["request_key"]) == request_key
                and str(prior_converged_fetch["status"])
                in {"success", "failed_terminal"}
                and prior_converged_fetch["final_url"]
            ):
                # A previous attempt can move to its redirect target during
                # convergence. If a later catalog import recreates the source
                # short-link row, repair that identity instead of inserting the
                # same deterministic fetch ID a second time.
                artifacts.converge_artifact(
                    conn,
                    source_artifact_id=artifact_id,
                    final_url=str(prior_converged_fetch["final_url"]),
                    seen_at=now,
                )
                conn.commit()
                return None
            raise RuntimeError(
                "deterministic fetch identity already exists without a reusable "
                "redirect convergence"
            )
        lease = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(timespec="seconds")
        conn.execute(
            """INSERT INTO artifact_fetch
               (fetch_id, fetch_run_id, artifact_id, fetch_policy,
                requested_url, request_key, status, attempt_number,
                started_at, lease_expires_at)
               VALUES (?, ?, ?, ?, ?, ?, 'in_progress', ?, ?, ?)""",
            (
                fetch_id,
                fetch_run_id,
                artifact_id,
                fetch_policy,
                requested_url,
                request_key,
                attempt,
                now,
                lease,
            ),
        )
        conn.commit()
        return fetch_id
    except Exception:
        conn.rollback()
        raise


def _finish_failure(conn: Any, fetch_id: str, failure: FetchFailure) -> None:
    status = "failed_retryable" if failure.retryable else "failed_terminal"
    with conn:
        conn.execute(
            """UPDATE artifact_fetch
               SET status = ?, completed_at = ?, lease_expires_at = NULL,
                   error_code = ?, error_message = ?, retryable = ?
               WHERE fetch_id = ? AND status = 'in_progress'""",
            (status, _now(), failure.code, str(failure), int(failure.retryable), fetch_id),
        )


def _finish_retrieved(
    conn: Any,
    *,
    fetch_id: str,
    source_artifact_id: str,
    retrieved: Retrieved,
    extraction: Extraction,
) -> str:
    extraction = validate_extraction(extraction, final_url=retrieved.final_url)
    now = _now()
    raw_sha = _sha256_bytes(retrieved.body)
    raw_ref = _write_snapshot(RAW_ROOT, raw_sha, ".bin", retrieved.body)
    text_sha = None
    text_ref = None
    text_count = None
    if extraction.text is not None:
        text_bytes = extraction.text.encode("utf-8")
        text_sha = _sha256_bytes(text_bytes)
        text_ref = _write_snapshot(TEXT_ROOT, text_sha, ".txt", text_bytes)
        text_count = len(extraction.text)
    status = "success" if extraction.success else "failed_terminal"
    with conn:
        target_artifact_id = artifacts.converge_artifact(
            conn,
            source_artifact_id=source_artifact_id,
            final_url=retrieved.final_url,
            seen_at=now,
        )
        conn.execute(
            """UPDATE artifact_fetch
               SET status = ?, completed_at = ?, lease_expires_at = NULL,
                   final_url = ?, redirect_chain_json = ?, http_status = ?,
                   response_headers_json = ?, content_type = ?, charset = ?,
                   content_length = ?, raw_sha256 = ?, raw_snapshot_ref = ?,
                   extractor_contract = ?, extractor_version = ?,
                   extracted_title = ?, text_sha256 = ?, text_snapshot_ref = ?,
                   text_char_count = ?, text_truncated = 0,
                   declared_canonical_url = ?, error_code = ?,
                   error_message = ?, retryable = 0
               WHERE fetch_id = ? AND status = 'in_progress'""",
            (
                status,
                now,
                retrieved.final_url,
                _canonical_json(retrieved.redirect_chain),
                retrieved.status_code,
                _canonical_json(retrieved.headers),
                retrieved.content_type,
                retrieved.charset,
                len(retrieved.body),
                raw_sha,
                raw_ref,
                extraction.extractor_contract,
                extraction.extractor_version,
                extraction.title,
                text_sha,
                text_ref,
                text_count,
                extraction.declared_canonical_url,
                extraction.error_code,
                extraction.error_message,
                fetch_id,
            ),
        )
        if extraction.title:
            conn.execute(
                """UPDATE artifact SET title = ?, title_fetch_id = ?, updated_at = ?
                   WHERE artifact_id = ?""",
                (extraction.title, fetch_id, now, target_artifact_id),
            )
    return target_artifact_id


def _complete_run(
    conn: Any, fetch_run_id: str, *, fetch_policy: str = FETCH_POLICY
) -> dict[str, Any]:
    items = conn.execute(
        "SELECT artifact_id FROM artifact_fetch_run_item WHERE fetch_run_id = ?",
        (fetch_run_id,),
    ).fetchall()
    states = {"success": 0, "failed_retryable": 0, "failed_terminal": 0}
    for item in items:
        state = conn.execute(
            """SELECT status FROM artifact_fetch
               WHERE artifact_id = ? AND fetch_policy = ?
               ORDER BY CASE status WHEN 'success' THEN 0 WHEN 'failed_terminal' THEN 1
                            WHEN 'failed_retryable' THEN 2 ELSE 3 END,
                        attempt_number DESC
               LIMIT 1""",
            (item["artifact_id"], fetch_policy),
        ).fetchone()
        if state is not None and str(state["status"]) in states:
            states[str(state["status"])] += 1
        else:
            states["failed_retryable"] += 1
    with conn:
        conn.execute(
            """UPDATE artifact_fetch_run
               SET expected_count = ?, success_count = ?,
                   failed_retryable_count = ?, failed_terminal_count = ?,
                   completed_at = ?, status = 'complete'
               WHERE fetch_run_id = ?""",
            (
                len(items),
                states["success"],
                states["failed_retryable"],
                states["failed_terminal"],
                _now(),
                fetch_run_id,
            ),
        )
    return {"fetch_run_id": fetch_run_id, "expected_count": len(items), **states}


def _snapshot_path(snapshot_ref: str) -> Path:
    path = Path(snapshot_ref)
    return path if path.is_absolute() else artifacts.REPO_ROOT / path


def revalidate_successful_fetches(
    *, db_path: Path | str = artifacts.DEFAULT_DB
) -> dict[str, Any]:
    """Quarantine stored successes that fail the current content contract.

    Fetch bodies remain immutable and addressable through ``raw_snapshot_ref``.
    Only the derived normalized text projection and success state are revoked.
    Replaying this operation is idempotent.
    """
    conn = artifacts.connect(db_path)
    rows = conn.execute(
        """SELECT fetch.fetch_id, fetch.fetch_run_id, fetch.artifact_id,
                  fetch.fetch_policy, fetch.requested_url, fetch.final_url,
                  fetch.extracted_title, fetch.text_snapshot_ref
           FROM artifact_fetch AS fetch
           WHERE fetch.status = 'success'
             AND fetch.text_snapshot_ref IS NOT NULL
           ORDER BY fetch.completed_at, fetch.fetch_id"""
    ).fetchall()
    quarantined: list[dict[str, str]] = []
    for row in rows:
        snapshot = _snapshot_path(str(row["text_snapshot_ref"]))
        if not snapshot.is_file():
            issue = (
                "extraction_snapshot_missing",
                f"Normalized text snapshot is missing: {row['text_snapshot_ref']}",
            )
        else:
            issue = extracted_text_issue(
                snapshot.read_text(encoding="utf-8", errors="replace"),
                title=str(row["extracted_title"] or "") or None,
                final_url=str(row["final_url"] or row["requested_url"]),
            )
        if issue is None:
            continue
        error_code, error_message = issue
        quarantined.append(
            {
                "fetch_id": str(row["fetch_id"]),
                "fetch_run_id": str(row["fetch_run_id"]),
                "artifact_id": str(row["artifact_id"]),
                "fetch_policy": str(row["fetch_policy"]),
                "error_code": error_code,
                "error_message": error_message,
            }
        )

    if quarantined:
        now = _now()
        with conn:
            conn.executemany(
                """UPDATE artifact_fetch
                   SET status = 'failed_terminal',
                       text_sha256 = NULL, text_snapshot_ref = NULL,
                       text_char_count = NULL, text_truncated = NULL,
                       error_code = ?, error_message = ?, retryable = 0
                   WHERE fetch_id = ? AND status = 'success'""",
                [
                    (item["error_code"], item["error_message"], item["fetch_id"])
                    for item in quarantined
                ],
            )
            affected_artifacts = sorted(
                {item["artifact_id"] for item in quarantined}
            )
            invalid_fetch_ids = {item["fetch_id"] for item in quarantined}
            for artifact_id in affected_artifacts:
                artifact = conn.execute(
                    "SELECT title_fetch_id FROM artifact WHERE artifact_id = ?",
                    (artifact_id,),
                ).fetchone()
                if artifact is None or str(artifact["title_fetch_id"] or "") not in invalid_fetch_ids:
                    continue
                replacement = conn.execute(
                    """SELECT fetch_id, extracted_title
                       FROM artifact_fetch
                       WHERE artifact_id = ? AND status = 'success'
                         AND extracted_title IS NOT NULL
                         AND trim(extracted_title) != ''
                       ORDER BY completed_at DESC, fetch_id DESC
                       LIMIT 1""",
                    (artifact_id,),
                ).fetchone()
                conn.execute(
                    """UPDATE artifact
                       SET title = ?, title_fetch_id = ?, updated_at = ?
                       WHERE artifact_id = ?""",
                    (
                        str(replacement["extracted_title"]) if replacement else None,
                        str(replacement["fetch_id"]) if replacement else None,
                        now,
                        artifact_id,
                    ),
                )
        affected_runs = sorted(
            {(item["fetch_run_id"], item["fetch_policy"]) for item in quarantined}
        )
        for fetch_run_id, fetch_policy in affected_runs:
            _complete_run(conn, fetch_run_id, fetch_policy=fetch_policy)
        conn.execute("PRAGMA optimize")
    else:
        affected_artifacts = []
        affected_runs = []

    by_error_code: dict[str, int] = defaultdict(int)
    by_fetch_policy: dict[str, int] = defaultdict(int)
    for item in quarantined:
        by_error_code[item["error_code"]] += 1
        by_fetch_policy[item["fetch_policy"]] += 1
    result = {
        "validation_contract": CONTENT_VALIDATION_CONTRACT,
        "scanned_success_count": len(rows),
        "quarantined_count": len(quarantined),
        "artifact_count": len(affected_artifacts),
        "affected_run_count": len(affected_runs),
        "by_error_code": dict(sorted(by_error_code.items())),
        "by_fetch_policy": dict(sorted(by_fetch_policy.items())),
    }
    conn.close()
    return result


def _repo_env_value(name: str, path: Path = DEFAULT_REPO_ENV) -> str | None:
    """Read one explicitly named value from the ignored repo-local env file."""
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ")
        key, separator, raw_value = line.partition("=")
        if not separator or key.strip() != name:
            continue
        parsed = shlex.split(raw_value, posix=True)
        if len(parsed) != 1:
            raise ValueError(f"invalid value for {name} in {path}")
        return parsed[0]
    return None


def jina_api_key(*, env_path: Path = DEFAULT_REPO_ENV) -> str | None:
    """Return the optional Reader key without accepting secrets on CLI flags."""
    return os.environ.get(JINA_API_KEY_ENV) or _repo_env_value(
        JINA_API_KEY_ENV, env_path
    )


def _host_has_suffix(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith(f".{suffix}")


def _jina_eligible(*, url: str, artifact_kind: str) -> bool:
    """Keep Reader scoped to ordinary public pages, not deferred adapters."""
    try:
        canonical = artifact_urls.canonicalize_url(url)
    except ValueError:
        return False
    split = urlsplit(canonical)
    host = (split.hostname or "").lower()
    return (
        artifact_kind in JINA_ELIGIBLE_KINDS
        and split.scheme in {"http", "https"}
        and not any(
            _host_has_suffix(host, suffix)
            for suffix in JINA_DEFERRED_HOST_SUFFIXES
        )
    )


def _jina_candidates(conn: Any) -> list[dict[str, Any]]:
    """Select native-fetch failures that Reader may safely attempt once."""
    rows = conn.execute(
        """WITH native_outcome AS (
               SELECT fetch.artifact_id, fetch.status, fetch.error_code,
                      fetch.attempt_number,
                      ROW_NUMBER() OVER (
                          PARTITION BY fetch.artifact_id
                          ORDER BY fetch.attempt_number DESC, fetch.started_at DESC
                      ) AS ordinal
               FROM artifact_fetch fetch
               WHERE fetch.fetch_policy = ?
           ), source AS (
               SELECT item.artifact_id, item.source_day, item.source_rank,
                      item.normalized_rank, item.source_event_id,
                      ROW_NUMBER() OVER (
                          PARTITION BY item.artifact_id
                          ORDER BY item.source_rank, item.source_event_id
                      ) AS ordinal
               FROM artifact_fetch_run_item item
               JOIN artifact_fetch_run run
                 ON run.fetch_run_id = item.fetch_run_id
               WHERE run.fetch_policy = ?
           )
           SELECT artifact.artifact_id, artifact.canonical_url,
                  artifact.artifact_kind, artifact.host,
                  native_outcome.status AS native_status,
                  native_outcome.error_code AS native_error_code,
                  source.source_day, source.source_rank,
                  source.normalized_rank, source.source_event_id
           FROM artifact
           JOIN native_outcome
             ON native_outcome.artifact_id = artifact.artifact_id
            AND native_outcome.ordinal = 1
           JOIN source
             ON source.artifact_id = artifact.artifact_id
            AND source.ordinal = 1
           WHERE native_outcome.status IN ('failed_retryable', 'failed_terminal')
             AND NOT EXISTS (
                 SELECT 1 FROM artifact_fetch succeeded
                 WHERE succeeded.artifact_id = artifact.artifact_id
                   AND succeeded.status = 'success'
             )
           ORDER BY source.source_rank, artifact.canonical_url""",
        (FETCH_POLICY, FETCH_POLICY),
    ).fetchall()
    return [
        dict(row)
        for row in rows
        if _jina_eligible(
            url=str(row["canonical_url"]),
            artifact_kind=str(row["artifact_kind"]),
        )
    ]


def _create_jina_run(
    conn: Any, selection: list[dict[str, Any]]
) -> tuple[str | None, bool]:
    if not selection:
        return None, True
    payload = [
        [item["artifact_id"], item["canonical_url"], item["native_error_code"]]
        for item in selection
    ]
    fingerprint = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
    fetch_run_id = hashlib.sha256(
        _canonical_json(
            [JINA_READER_POLICY, JINA_READER_SELECTION, fingerprint]
        ).encode()
    ).hexdigest()
    run_items = [
        (
            fetch_run_id,
            item["artifact_id"],
            rank,
            "jina_reader_fallback",
            item["canonical_url"],
            item["source_day"],
            item["source_rank"],
            item["normalized_rank"],
            item["source_event_id"],
        )
        for rank, item in enumerate(selection, 1)
    ]
    existing = conn.execute(
        "SELECT status FROM artifact_fetch_run WHERE fetch_run_id = ?",
        (fetch_run_id,),
    ).fetchone()
    if existing is not None:
        if restore_pruned_run_items(
            conn,
            fetch_run_id=fetch_run_id,
            run_items=run_items,
        ):
            return fetch_run_id, False
        return fetch_run_id, str(existing["status"]) == "complete"
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO artifact_fetch_run
               (fetch_run_id, schema_version, fetch_policy, selection_policy,
                input_fingerprint, expected_count, success_count,
                failed_retryable_count, failed_terminal_count, started_at,
                status)
               VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, 'in_progress')""",
            (
                fetch_run_id,
                artifacts.SCHEMA_VERSION,
                JINA_READER_POLICY,
                JINA_READER_SELECTION,
                fingerprint,
                len(selection),
                now,
            ),
        )
        conn.executemany(
            """INSERT INTO artifact_fetch_run_item
               (fetch_run_id, artifact_id, selection_rank, stratum,
                selected_url, source_day, source_rank, normalized_rank,
                source_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            run_items,
        )
    return fetch_run_id, False


def _resume_jina_run(conn: Any) -> tuple[str, list[dict[str, Any]]] | None:
    """Resume a crashed or retryable Reader run before selecting new work."""
    runs = conn.execute(
        """SELECT fetch_run_id, status, failed_retryable_count
           FROM artifact_fetch_run
           WHERE fetch_policy = ?
           ORDER BY started_at, fetch_run_id""",
        (JINA_READER_POLICY,),
    ).fetchall()
    for run in runs:
        fetch_run_id = str(run["fetch_run_id"])
        should_resume = str(run["status"]) == "in_progress"
        if not should_resume and int(run["failed_retryable_count"]) > 0:
            pending = conn.execute(
                """SELECT 1
                   FROM artifact_fetch_run_item item
                   WHERE item.fetch_run_id = ?
                     AND NOT EXISTS (
                         SELECT 1 FROM artifact_fetch fetch
                         WHERE fetch.artifact_id = item.artifact_id
                           AND fetch.fetch_policy = ?
                           AND fetch.status IN ('success', 'failed_terminal')
                     )
                     AND COALESCE((
                         SELECT MAX(fetch.attempt_number)
                         FROM artifact_fetch fetch
                         WHERE fetch.artifact_id = item.artifact_id
                           AND fetch.fetch_policy = ?
                     ), 0) < ?
                   LIMIT 1""",
                (fetch_run_id, JINA_READER_POLICY, JINA_READER_POLICY, MAX_ATTEMPTS),
            ).fetchone()
            should_resume = pending is not None
        if not should_resume:
            continue
        with conn:
            conn.execute(
                """UPDATE artifact_fetch_run
                   SET status = 'in_progress', completed_at = NULL
                   WHERE fetch_run_id = ?""",
                (fetch_run_id,),
            )
        items = conn.execute(
            """SELECT item.artifact_id, artifact.canonical_url,
                      artifact.artifact_kind, artifact.host,
                      item.source_day, item.source_rank,
                      item.normalized_rank, item.source_event_id
               FROM artifact_fetch_run_item item
               JOIN artifact ON artifact.artifact_id = item.artifact_id
               WHERE item.fetch_run_id = ?
               ORDER BY item.selection_rank""",
            (fetch_run_id,),
        ).fetchall()
        return fetch_run_id, [dict(item) for item in items]
    return None


def _jina_headers(api_key: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "X-Engine": "auto",
        "X-Respond-With": "markdown",
        "X-Retain-Images": "none",
        "X-Retain-Links": "all",
        "X-Timeout": "30",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _jina_read(
    client: httpx.Client, target_url: str, *, api_key: str | None
) -> tuple[Retrieved, Extraction]:
    try:
        response = client.post(
            JINA_READER_URL,
            headers=_jina_headers(api_key),
            json={"url": target_url},
        )
    except httpx.HTTPError as exc:
        raise FetchFailure("jina_transport_error", str(exc), retryable=True) from exc
    if response.status_code in RETRYABLE_HTTP:
        raise FetchFailure(
            f"jina_http_{response.status_code}",
            f"Jina Reader HTTP {response.status_code}",
            retryable=True,
        )
    if not 200 <= response.status_code < 300:
        raise FetchFailure(
            f"jina_http_{response.status_code}",
            f"Jina Reader HTTP {response.status_code}",
            retryable=False,
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise FetchFailure(
            "jina_invalid_json", "Jina Reader returned invalid JSON", retryable=False
        ) from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise FetchFailure(
            "jina_missing_data", "Jina Reader response has no data object", retryable=False
        )
    content = data.get("content")
    if not isinstance(content, str):
        raise FetchFailure(
            "jina_missing_content", "Jina Reader response has no content", retryable=False
        )
    text_value = _normalize_text(content)
    if len(text_value) < MIN_HTML_TEXT_CHARS:
        raise FetchFailure(
            "jina_thin_content",
            f"Jina Reader returned only {len(text_value)} text characters",
            retryable=False,
        )
    final_url = str(data.get("url") or target_url)
    try:
        final_url = artifact_urls.canonicalize_url(final_url)
    except ValueError as exc:
        raise FetchFailure("jina_unsafe_final_url", str(exc), retryable=False) from exc
    title = str(data.get("title") or "").strip() or None
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    headers = {
        **_safe_headers(response),
        "retrieval-provider": "jina_reader",
    }
    if usage.get("tokens") is not None:
        headers["reader-usage-tokens"] = str(usage["tokens"])
    retrieved = Retrieved(
        final_url=final_url,
        status_code=response.status_code,
        redirect_chain=[],
        headers=headers,
        content_type="application/json",
        charset="utf-8",
        body=response.content,
    )
    extraction = Extraction(
        success=True,
        extractor_contract=JINA_READER_EXTRACTOR,
        extractor_version="1",
        title=title,
        text=text_value,
        declared_canonical_url=final_url,
    )
    return retrieved, extraction


def recover_with_jina_reader(
    *,
    db_path: Path | str = artifacts.DEFAULT_DB,
    api_key: str | None = None,
    env_path: Path = DEFAULT_REPO_ENV,
    transport: httpx.BaseTransport | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    """Recover eligible native-fetch failures through Jina Reader.

    The fallback is a separate immutable fetch policy. It never retries known
    deferred adapters (X, LinkedIn, YouTube, forms) and never replaces native
    fetch evidence.
    """
    if workers < 1 or workers > 32:
        raise ValueError("workers must be between 1 and 32")
    conn = artifacts.connect(db_path)
    resumable = _resume_jina_run(conn)
    if resumable is not None:
        fetch_run_id, selection = resumable
        already_complete = False
    else:
        selection = _jina_candidates(conn)
        fetch_run_id, already_complete = _create_jina_run(conn, selection)
    if fetch_run_id is None:
        conn.close()
        return {
            "fetch_run_id": None,
            "expected_count": 0,
            "success": 0,
            "failed_retryable": 0,
            "failed_terminal": 0,
            "reused": True,
        }
    if already_complete:
        row = conn.execute(
            "SELECT * FROM artifact_fetch_run WHERE fetch_run_id = ?",
            (fetch_run_id,),
        ).fetchone()
        assert row is not None
        result = dict(row)
        result["reused"] = True
        conn.close()
        return result
    resolved_key = api_key if api_key is not None else jina_api_key(env_path=env_path)
    worker_count = 1 if transport is not None else min(workers, len(selection))
    chunks = [selection[index::worker_count] for index in range(worker_count)]

    def process_chunk(items: list[dict[str, Any]]) -> None:
        worker_conn = sqlite3.connect(Path(db_path), timeout=60.0)
        worker_conn.row_factory = sqlite3.Row
        worker_conn.execute("PRAGMA foreign_keys = ON")
        worker_conn.execute("PRAGMA busy_timeout = 60000")
        client = httpx.Client(
            trust_env=False,
            timeout=httpx.Timeout(
                45.0, connect=10.0, read=45.0, write=10.0, pool=10.0
            ),
            transport=transport,
        )
        try:
            for item in items:
                artifact_id = str(item["artifact_id"])
                requested_url = str(item["canonical_url"])
                fetch_id = _claim(
                    worker_conn,
                    fetch_run_id=fetch_run_id,
                    artifact_id=artifact_id,
                    requested_url=requested_url,
                    fetch_policy=JINA_READER_POLICY,
                )
                if fetch_id is None:
                    continue
                try:
                    retrieved, extraction = _jina_read(
                        client, requested_url, api_key=resolved_key
                    )
                    _finish_retrieved(
                        worker_conn,
                        fetch_id=fetch_id,
                        source_artifact_id=artifact_id,
                        retrieved=retrieved,
                        extraction=extraction,
                    )
                except FetchFailure as failure:
                    _finish_failure(worker_conn, fetch_id, failure)
        finally:
            client.close()
            worker_conn.close()

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
        for future in as_completed(futures):
            future.result()
    result = _complete_run(
        conn, fetch_run_id, fetch_policy=JINA_READER_POLICY
    )
    result["reused"] = False
    result["authenticated"] = bool(resolved_key)
    conn.close()
    return result


def fetch_cohort(
    *,
    db_path: Path | str = artifacts.DEFAULT_DB,
    limit: int = 30,
    artifact_ids: Iterable[str] | None = None,
    resolver: Resolver = _default_resolver,
    transport: httpx.BaseTransport | None = None,
    _initialize_db: bool = True,
    fetch_policy: str = FETCH_POLICY,
) -> dict[str, Any]:
    if _initialize_db:
        conn = artifacts.connect(db_path)
    else:
        conn = sqlite3.connect(Path(db_path), timeout=60.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 60000")
    if artifact_ids is None:
        if fetch_policy != FETCH_POLICY:
            raise ValueError("a non-default fetch policy requires explicit artifact_ids")
        selection = select_cohort(conn, limit=limit)
        fetch_run_id, already_complete = _create_fetch_run(conn, selection)
    else:
        selection = select_explicit_artifacts(conn, artifact_ids=artifact_ids)
        fetch_run_id, already_complete = _create_explicit_fetch_run(
            conn,
            selection,
            fetch_policy=fetch_policy,
        )
    if already_complete:
        row = conn.execute(
            "SELECT * FROM artifact_fetch_run WHERE fetch_run_id = ?", (fetch_run_id,)
        ).fetchone()
        assert row is not None
        result = {
            "fetch_run_id": fetch_run_id,
            "expected_count": int(row["expected_count"]),
            "success": int(row["success_count"]),
            "failed_retryable": int(row["failed_retryable_count"]),
            "failed_terminal": int(row["failed_terminal_count"]),
            "reused": True,
        }
        conn.close()
        return result
    client = httpx.Client(
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(20.0, connect=10.0, read=20.0, write=10.0, pool=10.0),
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
        transport=transport,
    )
    robots_cache: dict[str, tuple[bool, float]] = {}
    last_origin_request: dict[str, float] = {}
    try:
        items = conn.execute(
            """SELECT item.*, artifact.artifact_kind
               FROM artifact_fetch_run_item item
               JOIN artifact ON artifact.artifact_id = item.artifact_id
               WHERE item.fetch_run_id = ?
               ORDER BY item.selection_rank""",
            (fetch_run_id,),
        ).fetchall()
        for item in items:
            requested_url = str(item["selected_url"])
            current = conn.execute(
                """SELECT artifact.artifact_id, artifact.artifact_kind,
                          artifact.canonical_url
                   FROM artifact
                   LEFT JOIN artifact_alias alias
                     ON alias.artifact_id = artifact.artifact_id
                    AND alias.alias_url = ?
                   WHERE alias.alias_url IS NOT NULL
                      OR artifact.canonical_url = ?
                   ORDER BY CASE WHEN alias.alias_url IS NOT NULL THEN 0 ELSE 1 END
                   LIMIT 1""",
                (requested_url, requested_url),
            ).fetchone()
            if current is None:
                continue
            artifact_id = str(current["artifact_id"])
            fetch_id = _claim(
                conn,
                fetch_run_id=fetch_run_id,
                artifact_id=artifact_id,
                requested_url=requested_url,
                fetch_policy=fetch_policy,
            )
            if fetch_id is None:
                continue
            try:
                allowed, delay = _robots_allowed(
                    client, requested_url, resolver=resolver, cache=robots_cache
                )
                if not allowed:
                    raise FetchFailure(
                        "robots_disallowed",
                        "robots.txt disallows this artifact URL",
                        retryable=False,
                    )
                canonical_url = str(current["canonical_url"])
                google_doc_export_url = _google_doc_text_export_url(canonical_url)
                retrieval_url = google_doc_export_url or requested_url
                origin = _origin(retrieval_url)
                wait = delay - (time.monotonic() - last_origin_request.get(origin, 0.0))
                if wait > 0:
                    time.sleep(wait)
                retrieved = _safe_get(client, retrieval_url, resolver=resolver)
                last_origin_request[origin] = time.monotonic()
                if google_doc_export_url is not None:
                    extraction = _extract_google_doc_text_export(retrieved)
                    retrieved = replace(retrieved, final_url=canonical_url)
                else:
                    extraction = extract_content(
                        retrieved.body,
                        content_type=retrieved.content_type,
                        charset=retrieved.charset,
                        final_url=retrieved.final_url,
                        artifact_kind=str(current["artifact_kind"]),
                    )
                _finish_retrieved(
                    conn,
                    fetch_id=fetch_id,
                    source_artifact_id=artifact_id,
                    retrieved=retrieved,
                    extraction=extraction,
                )
            except FetchFailure as failure:
                _finish_failure(conn, fetch_id, failure)
    finally:
        client.close()
    result = _complete_run(conn, fetch_run_id, fetch_policy=fetch_policy)
    result["reused"] = False
    conn.close()
    return result


def repair_public_google_docs(
    *,
    db_path: Path | str = artifacts.DEFAULT_DB,
    resolver: Resolver = _default_resolver,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Append corrected text exports for every catalogued Google Document.

    This is intentionally a separate fetch policy: prior raw responses remain
    immutable and auditable, while the newest successful snapshot becomes the
    reviewer-facing Artifact preview.
    """
    conn = artifacts.connect(db_path)
    try:
        rows = conn.execute(
            """SELECT artifact_id, canonical_url
               FROM artifact
               WHERE host = 'docs.google.com'
                 AND canonical_url LIKE 'https://docs.google.com/document/%'
               ORDER BY artifact_id"""
        ).fetchall()
        artifact_ids = [
            str(row["artifact_id"])
            for row in rows
            if _google_doc_text_export_url(str(row["canonical_url"])) is not None
        ]
    finally:
        conn.close()
    if not artifact_ids:
        return {
            "fetch_run_id": None,
            "expected_count": 0,
            "success": 0,
            "failed_retryable": 0,
            "failed_terminal": 0,
            "reused": True,
        }
    return fetch_cohort(
        db_path=db_path,
        artifact_ids=artifact_ids,
        resolver=resolver,
        transport=transport,
        fetch_policy=GOOGLE_DOCS_REPAIR_POLICY,
    )


def fetch_all_supported(
    *,
    db_path: Path | str = artifacts.DEFAULT_DB,
    workers: int = 16,
    resolver: Resolver = _default_resolver,
) -> dict[str, Any]:
    """Fetch every directly supported catalog artifact, sharded by host.

    Host sharding keeps each origin polite and sequential while allowing
    independent origins to run concurrently. Existing successes and terminal
    outcomes are reused by ``fetch_cohort``. Videos and arXiv are deferred;
    X Articles are left to their dedicated adapter.
    """
    if workers < 1 or workers > 64:
        raise ValueError("workers must be between 1 and 64")
    # Initialize and validate the store once. Worker connections deliberately
    # skip schema DDL, which otherwise serializes every host batch.
    conn = artifacts.connect(db_path)
    try:
        rows = conn.execute(
            """SELECT artifact_id, host
               FROM artifact
               WHERE artifact_kind != 'video'
                 AND host != 'arxiv.org'
                 AND canonical_url NOT LIKE 'http://x.com/i/article/%'
                 AND canonical_url NOT LIKE 'https://x.com/i/article/%'
               ORDER BY host, artifact_id"""
        ).fetchall()
    finally:
        conn.close()

    by_host: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_host[str(row["host"])].append(str(row["artifact_id"]))
    if not by_host:
        return {
            "selection_policy": "all-supported-by-host-v1",
            "expected_count": 0,
            "success": 0,
            "failed_retryable": 0,
            "failed_terminal": 0,
            "host_batches": 0,
            "reused_host_batches": 0,
            "reused": True,
            "batches": [],
        }

    batch_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(by_host))) as executor:
        futures = {
            executor.submit(
                fetch_cohort,
                db_path=db_path,
                artifact_ids=artifact_ids,
                resolver=resolver,
                _initialize_db=False,
            ): host
            for host, artifact_ids in by_host.items()
        }
        for future in as_completed(futures):
            host = futures[future]
            result = future.result()
            batch_results.append({"host": host, **result})

    batch_results.sort(key=lambda item: str(item["host"]))
    return {
        "selection_policy": "all-supported-by-host-v1",
        "expected_count": sum(int(item["expected_count"]) for item in batch_results),
        "success": sum(int(item["success"]) for item in batch_results),
        "failed_retryable": sum(
            int(item["failed_retryable"]) for item in batch_results
        ),
        "failed_terminal": sum(
            int(item["failed_terminal"]) for item in batch_results
        ),
        "host_batches": len(batch_results),
        "reused_host_batches": sum(bool(item["reused"]) for item in batch_results),
        "reused": all(bool(item["reused"]) for item in batch_results),
        "batches": batch_results,
    }


def inspect_fetches(conn: Any, *, fetch_run_id: str | None = None) -> list[dict[str, Any]]:
    where = "WHERE fetch.fetch_run_id = ?" if fetch_run_id else ""
    params = (fetch_run_id,) if fetch_run_id else ()
    rows = conn.execute(
        f"""SELECT item.selection_rank, item.stratum, item.source_day,
                   item.source_rank, artifact.canonical_url, artifact.title,
                   fetch.fetch_policy, fetch.attempt_number, fetch.status,
                   fetch.retryable,
                   fetch.http_status, fetch.final_url,
                   fetch.content_type, fetch.text_char_count,
                   fetch.error_code, fetch.error_message,
                   fetch.raw_snapshot_ref, fetch.text_snapshot_ref,
                   x_article.request_post_id,
                   x_article.canonical_article_id,
                   x_article.canonical_article_url,
                   x_article.provider_status,
                   x_article.estimated_provider_credits,
                   x_article.content_block_count,
                   x_article.content_blocks_sha256
            FROM artifact_fetch fetch
            JOIN artifact_fetch_run_item item
              ON item.fetch_run_id = fetch.fetch_run_id
             AND item.artifact_id = fetch.artifact_id
            JOIN artifact ON artifact.artifact_id = fetch.artifact_id
            LEFT JOIN artifact_x_article_fetch x_article
              ON x_article.fetch_id = fetch.fetch_id
            {where}
            ORDER BY fetch.started_at DESC, item.selection_rank,
                     fetch.attempt_number DESC""",
        params,
    ).fetchall()
    return [dict(row) for row in rows]
