import json

from fli import store
from fli.ingestion.public_sources import parse_arxiv, parse_rss

RSS_SAMPLE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Lab Blog</title>
<item><title>New model released</title><link>https://lab.example/post-1</link>
<pubDate>Tue, 08 Jul 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""

ATOM_ARXIV_SAMPLE = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2507.00001v1</id><title>A Paper</title>
<summary>Abstract text.</summary><published>2026-07-01T00:00:00Z</published>
<updated>2026-07-01T00:00:00Z</updated>
<author><name>Jane Researcher</name></author>
<author><name>Bob Scientist</name></author></entry>
</feed>"""


def test_parse_rss():
    items = parse_rss(RSS_SAMPLE)
    assert items == [
        {
            "title": "New model released",
            "link": "https://lab.example/post-1",
            "pubDate": "Tue, 08 Jul 2026 10:00:00 GMT",
        }
    ]


def test_parse_arxiv():
    (item,) = parse_arxiv(ATOM_ARXIV_SAMPLE)
    assert item["id"] == "http://arxiv.org/abs/2507.00001v1"
    assert item["authors"] == ["Jane Researcher", "Bob Scientist"]


def test_store_raw_dedup(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    kwargs = dict(
        source="blog",
        lab="anthropic",
        external_id="https://lab.example/post-1",
        fetched_at="2026-07-08T12:00:00+00:00",
        payload={"title": "x"},
    )
    assert store.insert_raw(conn, **kwargs) is True
    assert store.insert_raw(conn, **kwargs) is False  # deduped
    rows = store.raw_counts(conn)
    assert len(rows) == 1 and rows[0]["n"] == 1
    payload = json.loads(
        conn.execute("SELECT payload FROM raw_items").fetchone()["payload"]
    )
    assert payload == {"title": "x"}
