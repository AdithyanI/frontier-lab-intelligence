"""Hand-curated lab seed data.

The lab list is deliberately hand-curated: the case prompt names the labs
that matter (OpenAI, Anthropic, GDM, Meta, xAI, Mistral, DeepSeek, Qwen,
stealth spin-offs). Curating ~10 rows is judgment, not automation — the
automation story is *discovery*: org-like accounts in the follow graph that
top-ranked researchers point at are candidates for new labs (SSI and
Thinking Machines already appear in the frozen seed graph this way).

Each lab row carries official channel hints (org X handle, blog/feed, GitHub
org, arXiv query). `fli.channels` turns those hints into first-class entities,
channels, and entity-channel links.
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from fli import channels, graph, store

SCHEMA = """
CREATE TABLE IF NOT EXISTS labs (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,         -- stable key, e.g. 'openai'
    name TEXT NOT NULL,
    status TEXT NOT NULL,              -- 'frontier' | 'emerging'
    x_handle TEXT,                     -- official org X handle (lowercased)
    x_account_id INTEGER REFERENCES accounts (id),  -- link into the graph, if present
    website TEXT,
    blog_feed TEXT,                    -- RSS/Atom feed or sitemap fallback
    github_org TEXT,
    arxiv_query TEXT,                  -- affiliation search string for arXiv API
    notes TEXT,                        -- why tracked / channel caveats
    seeded_at TEXT NOT NULL
);
"""

# Hand-curated seed: the labs the case prompt names, plus the two known
# stealth spin-offs. Channels probed manually; missing values mean the lab
# has no such official channel (or none worth fetching yet).
SEED_LABS = [
    {
        "slug": "openai",
        "name": "OpenAI",
        "status": "frontier",
        "x_handle": "openai",
        "website": "https://openai.com",
        "blog_feed": "https://openai.com/news/rss.xml",
        "github_org": "openai",
        "arxiv_query": 'all:"OpenAI"',
        "notes": "Named in case prompt.",
    },
    {
        "slug": "anthropic",
        "name": "Anthropic",
        "status": "frontier",
        "x_handle": "anthropicai",
        "website": "https://www.anthropic.com",
        "blog_feed": "https://www.anthropic.com/sitemap.xml",
        "github_org": "anthropics",
        "arxiv_query": 'all:"Anthropic"',
        "notes": "No news RSS (probed 2026-07-08); sitemap /news/ fallback.",
    },
    {
        "slug": "deepmind",
        "name": "Google DeepMind",
        "status": "frontier",
        "x_handle": "googledeepmind",
        "website": "https://deepmind.google",
        "blog_feed": "https://deepmind.google/blog/rss.xml",
        "github_org": "google-deepmind",
        "arxiv_query": 'all:"Google DeepMind"',
        "notes": "Named in case prompt.",
    },
    {
        "slug": "meta",
        "name": "Meta",
        "status": "frontier",
        "x_handle": "aiatmeta",
        "website": "https://ai.meta.com",
        "blog_feed": "https://ai.meta.com/blog/rss/",
        "github_org": "facebookresearch",
        "arxiv_query": 'all:"Meta AI" OR all:"FAIR"',
        "notes": "Named in case prompt; AI at Meta is an official Meta channel.",
    },
    {
        "slug": "spacex",
        "name": "SpaceX",
        "status": "frontier",
        "x_handle": "spacexai",
        "x_handles": ["spacex", "spacexai"],
        "website": "https://x.ai",
        "blog_feed": None,
        "github_org": "xai-org",
        "arxiv_query": 'all:"xAI"',
        "notes": (
            "Named in the case prompt as xAI; now consolidated under SpaceX. "
            "The x.ai news page needs scraping and publishes little on arXiv."
        ),
    },
    {
        "slug": "mistral",
        "name": "Mistral AI",
        "status": "frontier",
        "x_handle": "mistralai",
        "website": "https://mistral.ai",
        "blog_feed": None,
        "github_org": "mistralai",
        "arxiv_query": 'all:"Mistral AI"',
        "notes": "Named in case prompt. News page has no stable RSS (probe again).",
    },
    {
        "slug": "deepseek",
        "name": "DeepSeek",
        "status": "frontier",
        "x_handle": "deepseek_ai",
        "website": "https://www.deepseek.com",
        "blog_feed": None,
        "github_org": "deepseek-ai",
        "arxiv_query": 'all:"DeepSeek-AI" OR all:"DeepSeek"',
        "notes": "Ships via GitHub + papers more than blog.",
    },
    {
        "slug": "alibaba",
        "name": "Alibaba",
        "status": "frontier",
        "x_handle": "alibaba_qwen",
        "website": "https://qwenlm.github.io",
        "blog_feed": "https://qwenlm.github.io/index.xml",
        "github_org": "QwenLM",
        "arxiv_query": 'all:"Qwen Team"',
        "notes": "Named in the case prompt through Alibaba's Qwen model family.",
    },
    {
        "slug": "ssi",
        "name": "Safe Superintelligence Inc.",
        "status": "emerging",
        "x_handle": "ssi",
        "website": "https://ssi.inc",
        "blog_feed": None,
        "github_org": None,
        "arxiv_query": None,
        "notes": "Stealth (Sutskever). Near-zero public output; signal is hiring + graph attention.",
    },
    {
        "slug": "thinking-machines",
        "name": "Thinking Machines Lab",
        "status": "emerging",
        "x_handle": "thinkymachines",
        "website": "https://thinkingmachines.ai",
        "blog_feed": None,
        "github_org": "thinking-machines-lab",
        "arxiv_query": None,
        "notes": "Murati spin-off. Discovered-in-graph example: org account already in the seed graph.",
    },
]


def connect(db_path: Path | str = store.DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = channels.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def seed(conn: sqlite3.Connection, labs: list[dict] | None = None) -> dict[str, int]:
    """Upsert the hand-curated lab seed; link org X accounts found in the graph."""
    seeded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    linked = 0
    labs = labs if labs is not None else SEED_LABS
    for lab in labs:
        account_id = None
        if lab.get("x_handle"):
            row = conn.execute(
                "SELECT id FROM accounts WHERE platform = 'x' AND handle = ?",
                (lab["x_handle"],),
            ).fetchone()
            account_id = row["id"] if row else None
            linked += account_id is not None
        conn.execute(
            """INSERT INTO labs
               (slug, name, status, x_handle, x_account_id, website, blog_feed,
                github_org, arxiv_query, notes, seeded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (slug) DO UPDATE SET
                   name = excluded.name,
                   status = excluded.status,
                   x_handle = excluded.x_handle,
                   x_account_id = excluded.x_account_id,
                   website = excluded.website,
                   blog_feed = excluded.blog_feed,
                   github_org = excluded.github_org,
                   arxiv_query = excluded.arxiv_query,
                   notes = excluded.notes""",
            (
                lab["slug"], lab["name"], lab["status"], lab.get("x_handle"),
                account_id, lab.get("website"), lab.get("blog_feed"),
                lab.get("github_org"), lab.get("arxiv_query"), lab.get("notes"),
                seeded_at,
            ),
        )
    conn.commit()
    channel_counts = channels.sync_all(conn)
    configured_x_channels = _claim_configured_x_channels(
        conn,
        labs=labs,
        observed_at=seeded_at,
    )
    n = conn.execute("SELECT COUNT(*) AS n FROM labs").fetchone()["n"]
    return {
        "labs": n,
        "x_linked": linked,
        "configured_x_channels": configured_x_channels,
        **channel_counts,
    }


def _claim_configured_x_channels(
    conn: sqlite3.Connection,
    *,
    labs: list[dict],
    observed_at: str,
) -> int:
    """Attach every explicitly configured X account to its lab entity.

    ``labs.x_handle`` remains the primary provider/account lookup. The optional
    source-only ``x_handles`` list expresses the real one-organization-to-many-
    X-accounts relationship without flattening those accounts into one channel.
    """
    from fli import registry

    claimed = 0
    for lab in labs:
        handles = lab.get("x_handles") or [lab.get("x_handle")]
        handles = [handle for handle in handles if handle]
        if not handles:
            continue
        entity = conn.execute(
            "SELECT id FROM entities WHERE slug = ?", (lab["slug"],)
        ).fetchone()
        if entity is None:
            raise RuntimeError(f"seeded lab entity {lab['slug']!r} is missing")
        for handle in dict.fromkeys(handle.lower() for handle in handles):
            channel_id = channels.upsert_channel(
                conn,
                kind="x",
                key=handle,
                observed_at=observed_at,
            )
            owner = conn.execute(
                """SELECT e.id, e.kind
                   FROM entity_channels ec
                   JOIN entities e ON e.id = ec.entity_id
                   WHERE ec.channel_id = ?""",
                (channel_id,),
            ).fetchone()
            if (
                owner is not None
                and owner["id"] != entity["id"]
                and owner["kind"] != "unknown"
            ):
                registry.merge_entity_into(
                    conn,
                    canonical_entity_id=entity["id"],
                    duplicate_entity_id=owner["id"],
                    observed_at=observed_at,
                )
            registry.claim_channel(
                conn,
                entity_id=entity["id"],
                channel_id=channel_id,
                relationship="official",
                confidence=1.0,
                evidence_url=f"https://x.com/{handle}",
                notes="Official X account from the curated lab seed.",
                observed_at=observed_at,
            )
            claimed += 1
    conn.commit()
    return claimed


def summary(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """SELECT l.slug, l.status, l.x_handle, l.x_account_id,
                  a.followers_count
           FROM labs l LEFT JOIN accounts a ON a.id = l.x_account_id
           ORDER BY l.status, a.followers_count DESC"""
    ).fetchall()
    lines = []
    for r in rows:
        link = f"linked, {r['followers_count']:,} followers" if r["x_account_id"] else "not in graph"
        lines.append(f"{r['slug']:18s} {r['status']:9s} @{r['x_handle'] or '-':16s} {link}")
    return lines


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="fli labs")
    parser.add_argument("action", choices=["seed", "summary"])
    parser.add_argument("--db", default=None)
    args = parser.parse_args(argv)

    conn = connect(args.db) if args.db else connect()
    if args.action == "seed":
        counts = seed(conn)
        print(f"labs: {counts['labs']}, org accounts linked into graph: {counts['x_linked']}")
    for line in summary(conn):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
