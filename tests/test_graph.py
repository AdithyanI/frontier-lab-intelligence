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

    # reload is idempotent
    counts2 = graph.load_digg(conn, raw_dir)
    assert counts2 == counts
