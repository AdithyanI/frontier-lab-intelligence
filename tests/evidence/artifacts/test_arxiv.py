from fli.evidence.artifacts import arxiv as artifact_arxiv


def test_parse_feed_and_render_metadata_text():
    body = b"""<?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns='http://www.w3.org/2005/Atom'
          xmlns:arxiv='http://arxiv.org/schemas/atom'>
      <entry>
        <id>http://arxiv.org/abs/2402.12875v4</id>
        <title> A useful paper </title>
        <summary> The abstract text. </summary>
        <published>2024-02-20T10:11:03Z</published>
        <updated>2024-09-21T06:48:45Z</updated>
        <category term='cs.LG'/>
        <arxiv:comment>Accepted</arxiv:comment>
        <author><name>Ada Lovelace</name></author>
      </entry>
    </feed>"""

    records = artifact_arxiv._parse_feed(body)
    assert set(records) == {"2402.12875"}
    text = artifact_arxiv._render_text(records["2402.12875"])
    assert "A useful paper" in text
    assert "Authors: Ada Lovelace" in text
    assert "Abstract\n\nThe abstract text." in text


def test_arxiv_id_normalizes_version_and_pdf_suffix():
    assert artifact_arxiv._arxiv_id("https://arxiv.org/abs/2402.12875v4") == "2402.12875"
    assert artifact_arxiv._arxiv_id("https://arxiv.org/pdf/2402.12875.pdf") == "2402.12875"
