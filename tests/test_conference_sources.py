import json

from fli import channels, conference_sources, registry


SOURCE = conference_sources.ConferenceSource(
    source_id="aie-test-2026",
    name="AI Engineer Test 2026",
    conference_url="https://example.com/conference",
    data_url="https://example.com/speakers.json",
    format="speakers-json-v1",
    observed_at="2026-07-02T23:59:59+00:00",
)


def _record(**overrides):
    values = {
        "source_id": SOURCE.source_id,
        "conference_name": SOURCE.name,
        "conference_url": SOURCE.conference_url,
        "observed_at": SOURCE.observed_at,
        "name": "Ada Example",
        "x_handle": "adaexample",
        "role": "Research Engineer",
        "company": "Example AI",
        "bio": "Builds agent systems.",
        "website": "https://ada.example",
        "blog": "https://ada.example/blog",
        "session_titles": ("An excellent talk",),
        "company_website": None,
        "company_x_candidate": None,
    }
    values.update(overrides)
    return conference_sources.SpeakerRecord(**values)


def test_parses_official_json_without_using_linkedin_as_identity():
    payload = json.dumps(
        {
            "speakers": [
                {
                    "name": "Ada Example",
                    "twitter": "https://x.com/AdaExample",
                    "linkedin": "https://linkedin.com/in/ada-example",
                    "role": "Research Engineer",
                    "company": "Example AI",
                    "bio": "Builds agent systems.",
                    "website": "https://ada.example",
                    "sessions": [{"title": "An excellent talk"}],
                },
                {
                    "name": "No X Speaker",
                    "linkedin": "https://linkedin.com/in/no-x",
                    "company": "Another AI",
                },
            ]
        }
    ).encode()

    records = conference_sources.parse_source(SOURCE, payload)

    assert records[0].x_handle == "adaexample"
    assert records[0].role == "Research Engineer"
    assert records[0].company == "Example AI"
    assert records[0].session_titles == ("An excellent talk",)
    assert records[1].x_handle is None


def test_monitorable_selection_is_stable_unique_and_limited():
    records = [
        _record(name="No X", x_handle=None),
        _record(name="Ada First"),
        _record(name="Ada Duplicate"),
        _record(name="Grace", x_handle="grace"),
        _record(name="Lin", x_handle="lin"),
    ]

    selected = conference_sources.select_monitorable_records(records, limit=2)

    assert [(row.name, row.x_handle) for row in selected] == [
        ("Ada First", "adaexample"),
        ("Grace", "grace"),
    ]


def test_import_writes_lean_facts_affiliation_and_is_idempotent(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    record = _record()

    first = conference_sources.import_records(conn, [record])
    second = conference_sources.import_records(conn, [record])

    assert first["people_created"] == 1
    assert first["organizations_created"] == 1
    assert second["people_created"] == 0
    assert second["organizations_created"] == 0
    facts = {
        row["fact"]: row["value"]
        for row in conn.execute(
            "SELECT fact, value FROM entity_source_facts ORDER BY fact"
        ).fetchall()
    }
    assert facts == {
        "conference_company": "Example AI",
        "conference_speaker": "AI Engineer Test 2026",
        "speaker_bio": "Builds agent systems.",
        "speaker_company": "Example AI",
        "speaker_role": "Research Engineer",
    }
    assert "speaker_website" not in facts
    assert "session_titles" not in facts
    affiliation = conn.execute("SELECT * FROM entity_affiliations").fetchone()
    assert affiliation["relationship"] == "listed_affiliation"
    assert affiliation["role_title"] == "Research Engineer"
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_affiliations"
    ).fetchone()[0] == 1


def test_import_does_not_revive_an_existing_rejected_identity(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    record = _record()
    conference_sources.import_records(conn, [record])
    entity_id = conn.execute(
        "SELECT entity_id FROM entity_channels LIMIT 1"
    ).fetchone()[0]
    registry.reject_entity(
        conn,
        entity_id=entity_id,
        reason_code="not_relevant",
        reason="Previously reviewed and rejected.",
        source="manual_review",
        rejected_at="2026-07-03T00:00:00+00:00",
    )

    conference_sources.import_records(conn, [record])

    assert registry.read_entities(conn)[0]["registry_state"] == "rejected"
