"""Tests for the modeled graph layer."""

import csv
from pathlib import Path

from fli import graph

RANKINGS_FIELDS = [
    "rank", "username", "display_name", "role", "cohort", "score",
    "tech_ranked_followers", "followers_count", "bio", "x_id", "github_url",
    "category_rank", "digg_url",
]
EDGE_FIELDS = [
    "from_username", "from_display_name", "from_x_id", "from_followers_count",
    "to_username", "to_display_name", "to_x_id", "evidence_url",
]


def _write_fixture(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True)
    with (raw_dir / "rankings.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RANKINGS_FIELDS)
        w.writeheader()
        w.writerow({
            "rank": "1", "username": "Karpathy", "display_name": "Andrej Karpathy",
            "role": "Research Engineer", "cohort": "ai", "score": "758",
            "tech_ranked_followers": "758", "followers_count": "3195900",
            "bio": "nets", "x_id": "33836629",
            "github_url": "https://github.com/karpathy",
            "category_rank": "1", "digg_url": "https://digg.com/u/x/karpathy",
        })
    with (raw_dir / "top_follower_edges.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EDGE_FIELDS)
        w.writeheader()
        row = {
            "from_username": "ylecun", "from_display_name": "Yann LeCun",
            "from_x_id": "48008938", "from_followers_count": "1231807",
            "to_username": "karpathy", "to_display_name": "Andrej Karpathy",
            "to_x_id": "33836629",
            "evidence_url": "https://digg.com/api/profile/karpathy/followers",
        }
        w.writerow(row)
        w.writerow(row)  # duplicate must be deduped


def test_load_digg_normalizes_and_dedupes(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_fixture(raw_dir)
    conn = graph.connect(tmp_path / "test.db")

    counts = graph.load_digg(conn, raw_dir)
    assert counts["accounts"] == 2  # karpathy stored once despite 3 mentions
    assert counts["edges"] == 1     # duplicate edge deduped
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM channels WHERE kind = 'x'"
    ).fetchone()["n"] == 2

    acct = conn.execute(
        "SELECT * FROM accounts WHERE handle = 'karpathy'"
    ).fetchone()
    assert acct["display_name"] == "Andrej Karpathy"
    assert acct["followers_count"] == 3195900

    rank = conn.execute(
        """SELECT value FROM account_source_facts f
           JOIN accounts a ON a.id = f.account_id
           WHERE a.handle = 'karpathy' AND f.source = 'digg' AND f.fact = 'rank'"""
    ).fetchone()
    assert rank["value"] == "1"
    obs = conn.execute(
        """SELECT o.value FROM channel_observations o
           JOIN channels c ON c.id = o.channel_id
           WHERE c.kind = 'x' AND c.key = 'karpathy'
             AND o.source = 'digg' AND o.metric = 'rank'"""
    ).fetchone()
    assert obs["value"] == "1"

    # reload is idempotent
    counts2 = graph.load_digg(conn, raw_dir)
    assert counts2 == counts


def test_pagerank_ranks_followed_account_highest(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_fixture(raw_dir)
    conn = graph.connect(tmp_path / "test.db")
    graph.load_digg(conn, raw_dir)

    result = graph.compute_pagerank(conn)
    assert result["nodes"] == 2

    rows = conn.execute(
        """SELECT a.handle, f.value FROM account_source_facts f
           JOIN accounts a ON a.id = f.account_id
           WHERE f.source = 'graph' AND f.fact = 'pagerank_rank'
           ORDER BY CAST(f.value AS INTEGER)"""
    ).fetchall()
    # karpathy is followed, ylecun only follows → karpathy must rank first
    assert [r["handle"] for r in rows] == ["karpathy", "ylecun"]

    # recompute is idempotent (old graph-source rows replaced, not duplicated)
    graph.compute_pagerank(conn)
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM account_source_facts WHERE source = 'graph'"
    ).fetchone()["n"]
    assert n == 4  # 2 accounts x (pagerank + pagerank_rank)
    obs_n = conn.execute(
        "SELECT COUNT(*) AS n FROM channel_observations WHERE source = 'graph'"
    ).fetchone()["n"]
    assert obs_n == 4
