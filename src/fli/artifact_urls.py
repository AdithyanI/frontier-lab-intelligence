"""Deterministic URL candidate extraction and conservative identity rules."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


CANONICALIZATION_CONTRACT = "artifact-url-v1"
_TRACKING_KEYS = frozenset(
    {
        "dclid",
        "fbclid",
        "gclid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "mkt_tok",
        "msclkid",
        "oly_anon_id",
        "oly_enc_id",
        "vero_conv",
        "vero_id",
        "_hsenc",
        "_hsmi",
    }
)
_X_HOSTS = frozenset({"x.com", "www.x.com", "twitter.com", "www.twitter.com"})
_SHORT_HOSTS = frozenset({"t.co", "www.t.co"})
_STATUS_PATH = re.compile(r"^/[^/]+/status(?:es)?/\d+(?:/|$)", re.IGNORECASE)
_PROFILE_PATH = re.compile(r"^/[^/]+/?$", re.IGNORECASE)
_ARXIV_DOCUMENT = re.compile(
    r"^/(?:abs|pdf|html)/(?P<identifier>[^/?#]+?)(?:\.pdf)?/?$", re.IGNORECASE
)


@dataclass(frozen=True)
class CandidateDecision:
    decision: str
    reason_code: str
    canonical_url: str | None = None
    artifact_kind: str | None = None


@dataclass(frozen=True)
class UrlEvidence:
    observed_url: str
    expanded_url: str
    source: str
    owner_external_id: str


def artifact_id(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode()).hexdigest()


def _normalized_host(hostname: str | None) -> str:
    if not hostname:
        raise ValueError("URL has no hostname")
    return hostname.rstrip(".").encode("idna").decode("ascii").lower()


def canonicalize_url(url: str) -> str:
    """Return the narrow v1 canonical form or raise ``ValueError``."""
    value = str(url or "").strip()
    split = urlsplit(value)
    scheme = split.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("URL scheme must be http or https")
    if split.username is not None or split.password is not None:
        raise ValueError("URL credentials are not allowed")
    host = _normalized_host(split.hostname)
    try:
        port = split.port
    except ValueError as exc:
        raise ValueError("URL has an invalid port") from exc
    if port not in {None, 80, 443}:
        raise ValueError("URL port must be 80 or 443")
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = host if port is None or default_port else f"{host}:{port}"
    path = split.path or "/"

    if host in {"arxiv.org", "www.arxiv.org"}:
        match = _ARXIV_DOCUMENT.match(path)
        if match:
            host = "arxiv.org"
            netloc = host
            path = f"/abs/{match.group('identifier')}"
            scheme = "https"

    query = [
        (key, value)
        for key, value in parse_qsl(split.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_KEYS
    ]
    if host in {"youtube.com", "www.youtube.com", "youtu.be"}:
        query = [item for item in query if item[0].lower() not in {"si", "feature", "pp"}]
    if host in {"medium.com", "www.medium.com"}:
        query = [item for item in query if item[0].lower() != "source"]
    return urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), ""))


def _artifact_kind(canonical_url: str) -> str:
    split = urlsplit(canonical_url)
    host = (split.hostname or "").lower()
    path = split.path.lower()
    if host == "arxiv.org" or path.endswith(".pdf"):
        return "paper"
    if host in {"github.com", "www.github.com", "gitlab.com", "www.gitlab.com"}:
        return "repository"
    if host in {"youtube.com", "www.youtube.com", "youtu.be", "vimeo.com"}:
        return "video"
    if host in _X_HOSTS and "/i/article/" in path:
        return "article"
    if any(token in path for token in ("/blog/", "/news/", "/article/", "/research/")):
        return "article"
    if any(token in path for token in ("announce", "release", "launch")):
        return "announcement"
    return "other"


def classify_candidate(observed_url: str, expanded_url: str | None = None) -> CandidateDecision:
    """Accept only independently fetchable artifact candidates."""
    observed = str(observed_url or "").strip()
    expanded = str(expanded_url or observed).strip()
    try:
        observed_host = _normalized_host(urlsplit(observed).hostname)
    except (UnicodeError, ValueError):
        return CandidateDecision("failed", "invalid_url")
    if observed_host in _SHORT_HOSTS and expanded == observed:
        return CandidateDecision("excluded", "unresolved_short_url")
    try:
        canonical = canonicalize_url(expanded)
    except ValueError as exc:
        reason = "unsupported_scheme" if "scheme" in str(exc) else "invalid_url"
        return CandidateDecision("failed", reason)
    split = urlsplit(canonical)
    host = (split.hostname or "").lower()
    path = split.path
    if host in _SHORT_HOSTS:
        return CandidateDecision("excluded", "unresolved_short_url")
    if host in _X_HOSTS:
        if "/i/article/" in path.lower():
            return CandidateDecision("accepted", "x_longform_article", canonical, "article")
        if _STATUS_PATH.match(path):
            return CandidateDecision("excluded", "ordinary_x_status")
        if path.lower().startswith("/i/broadcasts/"):
            return CandidateDecision("excluded", "x_broadcast_deferred")
        if _PROFILE_PATH.match(path):
            return CandidateDecision("excluded", "x_profile")
        return CandidateDecision("excluded", "x_internal_url")
    if host in {"pic.twitter.com", "pbs.twimg.com", "video.twimg.com"}:
        return CandidateDecision("excluded", "x_media")
    lowered_path = path.lower()
    if host in {"discord.gg", "www.discord.gg"} or (
        host in {"discord.com", "www.discord.com"}
        and lowered_path.startswith("/invite/")
    ):
        return CandidateDecision("excluded", "invite_url")
    if host in {"google.com", "www.google.com"} and lowered_path == "/search":
        return CandidateDecision("excluded", "search_navigation")
    if host in {"github.com", "www.github.com"}:
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) < 2:
            return CandidateDecision("excluded", "external_profile")
    if host in {"youtube.com", "www.youtube.com"} and (
        lowered_path.startswith("/@")
        or lowered_path.startswith("/channel/")
        or lowered_path.startswith("/c/")
        or lowered_path.startswith("/user/")
    ):
        return CandidateDecision("excluded", "external_profile")
    if host in {"linkedin.com", "www.linkedin.com"} and (
        lowered_path.startswith("/in/") or lowered_path.startswith("/company/")
    ):
        return CandidateDecision("excluded", "external_profile")
    return CandidateDecision("accepted", "external_http_url", canonical, _artifact_kind(canonical))


def url_evidence(payload: dict[str, Any]) -> list[UrlEvidence]:
    """Read entity URL aliases and their true owning posts.

    Provider card metadata is deliberately not a candidate source. A card-only
    short URL cannot be bound safely when one post contains multiple links.
    Quoted and retweeted payloads are traversed recursively so an outer
    disclosure post cannot be mistaken for the post that actually linked the
    artifact.
    """
    found: list[UrlEvidence] = []
    seen: set[tuple[str, str, str, str]] = set()
    stack: list[tuple[Any, str]] = [(payload, "entity")]
    visited: set[int] = set()
    while stack:
        tweet, source = stack.pop()
        if not isinstance(tweet, dict):
            continue
        marker = id(tweet)
        if marker in visited:
            continue
        visited.add(marker)
        owner = str(tweet.get("id") or tweet.get("id_str") or "").strip()
        if not owner:
            continue
        for item in (tweet.get("entities") or {}).get("urls") or []:
            if not isinstance(item, dict):
                continue
            observed = str(item.get("url") or "").strip()
            expanded = str(item.get("expanded_url") or observed).strip()
            if not observed:
                continue
            identity = (observed, expanded, source, owner)
            if identity not in seen:
                seen.add(identity)
                found.append(UrlEvidence(observed, expanded, source, owner))
        stack.append((tweet.get("retweeted_tweet"), "retweeted_entity"))
        stack.append((tweet.get("quoted_tweet"), "quoted_entity"))
    return found


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def is_global_address(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False
