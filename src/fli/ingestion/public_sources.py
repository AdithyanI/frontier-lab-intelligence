"""Data-gathering spike: fetch raw public output for a few labs.

Deliberately coarse — the goal is real payloads in the raw layer so the
schema can be designed from evidence, not theory. Sources per lab:
blog/news RSS, recent arXiv papers (API), GitHub releases (API).
"""

import datetime as dt
import json
import urllib.request
import xml.etree.ElementTree as ET

from fli import store

USER_AGENT = "fli/0.1 (research prototype; contact: local)"

# Minimal fetch targets — just enough for the fetcher to know where to look.
# This is NOT the registry; the real seed/registry design comes after we've
# seen the data.
LABS = {
    "anthropic": {
        # No news RSS exists (probed 2026-07-08); the sitemap lists /news/
        # URLs with lastmod dates. Coarse but official.
        "sitemap_news": "https://www.anthropic.com/sitemap.xml",
        "arxiv_query": 'all:"Anthropic"',
        "github_org": "anthropics",
    },
    "openai": {
        "blog_rss": "https://openai.com/news/rss.xml",
        "arxiv_query": 'all:"OpenAI"',
        "github_org": "openai",
    },
    "deepmind": {
        "blog_rss": "https://deepmind.google/blog/rss.xml",
        "arxiv_query": 'all:"Google DeepMind"',
        "github_org": "google-deepmind",
    },
}

ATOM = "{http://www.w3.org/2005/Atom}"


def _get(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def parse_rss(xml_bytes: bytes) -> list[dict]:
    """Coarse RSS/Atom parse: keep every child element as raw text."""
    root = ET.fromstring(xml_bytes)
    items = root.findall(".//item") or root.findall(f".//{ATOM}entry")
    out = []
    for item in items:
        record: dict = {}
        for child in item:
            tag = child.tag.split("}")[-1]
            if tag == "link" and not child.text and child.get("href"):
                record[tag] = child.get("href")
            else:
                record[tag] = (child.text or "").strip()
        out.append(record)
    return out


def parse_arxiv(xml_bytes: bytes) -> list[dict]:
    """Coarse arXiv Atom parse; keeps authors and links explicitly."""
    root = ET.fromstring(xml_bytes)
    out = []
    for entry in root.findall(f"{ATOM}entry"):
        get = lambda tag: (entry.findtext(f"{ATOM}{tag}") or "").strip()
        out.append(
            {
                "id": get("id"),
                "title": get("title"),
                "summary": get("summary"),
                "published": get("published"),
                "updated": get("updated"),
                "authors": [
                    (a.findtext(f"{ATOM}name") or "").strip()
                    for a in entry.findall(f"{ATOM}author")
                ],
            }
        )
    return out


def fetch_blog(lab: str, cfg: dict, conn) -> tuple[int, int]:
    if "sitemap_news" in cfg:
        return fetch_sitemap_news(lab, cfg, conn)
    items = parse_rss(_get(cfg["blog_rss"]))
    new = sum(
        store.insert_raw(
            conn,
            source="blog",
            lab=lab,
            external_id=item.get("link") or item.get("guid") or json.dumps(item)[:200],
            fetched_at=_now(),
            payload=item,
        )
        for item in items
    )
    return new, len(items)


SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def fetch_sitemap_news(lab: str, cfg: dict, conn) -> tuple[int, int]:
    """Fallback for labs without RSS: /news/ URLs from the sitemap."""
    root = ET.fromstring(_get(cfg["sitemap_news"]))
    items = [
        {
            "link": url.findtext(f"{SITEMAP_NS}loc"),
            "lastmod": url.findtext(f"{SITEMAP_NS}lastmod"),
        }
        for url in root.findall(f"{SITEMAP_NS}url")
        if "/news/" in (url.findtext(f"{SITEMAP_NS}loc") or "")
    ]
    new = sum(
        store.insert_raw(
            conn,
            source="blog",
            lab=lab,
            external_id=item["link"],
            fetched_at=_now(),
            payload=item,
        )
        for item in items
    )
    return new, len(items)


def fetch_arxiv(lab: str, cfg: dict, conn, max_results: int = 50) -> tuple[int, int]:
    url = (
        "http://export.arxiv.org/api/query?search_query="
        + urllib.request.quote(cfg["arxiv_query"])
        + f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    items = parse_arxiv(_get(url))
    new = sum(
        store.insert_raw(
            conn,
            source="arxiv",
            lab=lab,
            external_id=item["id"],
            fetched_at=_now(),
            payload=item,
        )
        for item in items
    )
    return new, len(items)


def fetch_github(lab: str, cfg: dict, conn, per_repo: int = 5) -> tuple[int, int]:
    """Releases across the org's most recently pushed repos."""
    org = cfg["github_org"]
    repos = json.loads(
        _get(
            f"https://api.github.com/orgs/{org}/repos?sort=pushed&per_page=10",
            accept="application/vnd.github+json",
        )
    )
    new = total = 0
    for repo in repos:
        releases = json.loads(
            _get(
                f"https://api.github.com/repos/{repo['full_name']}/releases?per_page={per_repo}",
                accept="application/vnd.github+json",
            )
        )
        for rel in releases:
            total += 1
            new += store.insert_raw(
                conn,
                source="github",
                lab=lab,
                external_id=rel["html_url"],
                fetched_at=_now(),
                payload={
                    "repo": repo["full_name"],
                    "tag": rel.get("tag_name"),
                    "name": rel.get("name"),
                    "body": rel.get("body"),
                    "published_at": rel.get("published_at"),
                    "author": (rel.get("author") or {}).get("login"),
                    "html_url": rel.get("html_url"),
                },
            )
    return new, total


FETCHERS = {"blog": fetch_blog, "arxiv": fetch_arxiv, "github": fetch_github}


def fetch_all(conn, labs: dict | None = None) -> None:
    for lab, cfg in (labs or LABS).items():
        for source, fn in FETCHERS.items():
            try:
                new, total = fn(lab, cfg, conn)
                print(f"{lab:10s} {source:7s} {new:4d} new / {total:4d} fetched")
            except Exception as exc:  # spike: report and continue
                print(f"{lab:10s} {source:7s} FAILED: {exc}")
