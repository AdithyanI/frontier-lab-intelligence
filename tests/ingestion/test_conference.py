import json

from fli.ingestion import conference as conference_sources
from fli.network import snapshots as following_snapshots
from fli.registry import channels
from fli.registry import store as registry


SOURCE = conference_sources.ConferenceSource(
    source_id="aie-test-2026",
    name="AI Engineer Test 2026",
    conference_url="https://example.com/conference",
    data_url="https://example.com/speakers.json",
    format="speakers-json-v1",
    observed_at="2026-07-02T23:59:59+00:00",
)


class FakeProfileClient:
    def __init__(self):
        self.calls = []

    def fetch_user(self, *, username):
        self.calls.append(username)
        return {
            "id": f"id-{username}",
            "userName": username,
            "name": username.title(),
            "description": f"Bio for {username}",
            "followers": 123,
            "following": 45,
        }


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
        "company_website": "https://example.ai",
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


def test_manifest_sources_can_be_selected_in_requested_order():
    second = conference_sources.ConferenceSource(
        source_id="aie-second",
        name="Second",
        conference_url="https://example.com/second",
        data_url="https://example.com/second.json",
        format="speakers-json-v1",
        observed_at=SOURCE.observed_at,
    )

    selected = conference_sources.select_sources(
        [SOURCE, second], ["aie-second", SOURCE.source_id]
    )

    assert [source.source_id for source in selected] == [
        "aie-second",
        SOURCE.source_id,
    ]


def test_organization_matches_an_existing_official_website(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    organization_id = channels.upsert_entity(
        conn,
        kind="organization",
        slug="example",
        name="Example",
        observed_at=SOURCE.observed_at,
    )
    website_id = channels.upsert_channel(
        conn,
        kind="website",
        key="https://www.example.ai/",
        observed_at=SOURCE.observed_at,
    )
    channels.link_entity_channel(
        conn,
        entity_id=organization_id,
        channel_id=website_id,
        relationship="official",
    )

    result = conference_sources.import_records(
        conn,
        [
            _record(
                company="Example Incorporated",
                company_website="https://example.ai",
            )
        ],
    )

    assert result["organizations_created"] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE kind = 'organization'"
    ).fetchone()[0] == 1


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


def test_import_keeps_unresolvable_company_as_person_fact_only(tmp_path):
    conn = channels.connect(tmp_path / "test.db")

    result = conference_sources.import_records(
        conn,
        [_record(company="Unresolved Label", company_website=None)],
    )

    assert result["organizations_created"] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE kind = 'organization'"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_affiliations"
    ).fetchone()[0] == 0
    assert conn.execute(
        """SELECT value FROM entity_source_facts
           WHERE fact = 'speaker_company'"""
    ).fetchone()[0] == "Unresolved Label"


def test_consolidation_prunes_legacy_channel_less_company_identity(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    conference_sources.import_records(
        conn,
        [_record(company="Unresolved Label", company_website=None)],
    )
    person_id = conn.execute(
        """SELECT entity_id FROM entity_channels ec
           JOIN channels c ON c.id = ec.channel_id
           WHERE c.kind = 'x' AND c.key = 'adaexample'"""
    ).fetchone()[0]
    organization_id = channels.upsert_entity(
        conn,
        kind="organization",
        slug="unresolved-label",
        name="Unresolved Label",
        observed_at=SOURCE.observed_at,
    )
    channels.record_entity_fact(
        conn,
        entity_id=organization_id,
        source=SOURCE.source_id,
        fact="conference_company",
        value="Unresolved Label",
        observed_at=SOURCE.observed_at,
        evidence_url=SOURCE.conference_url,
    )
    channels.record_affiliation(
        conn,
        person_entity_id=person_id,
        organization_entity_id=organization_id,
        relationship="listed_affiliation",
        role_title="Research Engineer",
        source=SOURCE.source_id,
        observed_at=SOURCE.observed_at,
        evidence_url=SOURCE.conference_url,
    )

    result = conference_sources.consolidate_conference_facts(conn)

    assert result["unresolved_conference_affiliations_removed"] == 1
    assert result["unresolved_conference_organizations_pruned"] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE id = ?", (organization_id,)
    ).fetchone()[0] == 0
    assert conn.execute(
        """SELECT value FROM entity_source_facts
           WHERE entity_id = ? AND fact = 'speaker_company'""",
        (person_id,),
    ).fetchone()[0] == "Unresolved Label"


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

    assert conn.execute(
        "SELECT COUNT(*) FROM entity_registry_rejections WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()[0] == 1


def test_import_keeps_only_the_newest_conference_context_per_person(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    older = _record(
        source_id="aie-worldsfair-2024",
        conference_name="AI Engineer World's Fair 2024",
        observed_at="2024-06-27T23:59:59+00:00",
        role="Old role",
        company="Old Company",
        bio="Old bio",
        company_website="https://old.example",
        company_x_candidate="ambiguous_company_handle",
    )
    newer = _record(
        source_id="aie-worldsfair-2026",
        conference_name="AI Engineer World's Fair 2026",
        observed_at="2026-07-02T23:59:59+00:00",
        role="Current role",
        company="Current Company",
        bio="Current bio",
        company_website="https://current.example",
    )

    conference_sources.import_records(conn, [older])
    result = conference_sources.import_records(conn, [newer])

    person_id = conn.execute(
        """SELECT ec.entity_id
           FROM entity_channels ec
           JOIN channels c ON c.id = ec.channel_id
           WHERE c.kind = 'x' AND c.key = 'adaexample'"""
    ).fetchone()[0]
    facts = {
        row["fact"]: row["value"]
        for row in conn.execute(
            """SELECT fact, value FROM entity_source_facts
               WHERE entity_id = ?""",
            (person_id,),
        ).fetchall()
    }
    affiliation = conn.execute(
        "SELECT * FROM entity_affiliations WHERE person_entity_id = ?",
        (person_id,),
    ).fetchone()
    organization = conn.execute(
        "SELECT name FROM entities WHERE id = ?",
        (affiliation["organization_entity_id"],),
    ).fetchone()[0]

    assert facts == {
        "conference_speaker": "AI Engineer World's Fair 2026",
        "speaker_role": "Current role",
        "speaker_company": "Current Company",
        "speaker_bio": "Current bio",
    }
    assert organization == "Current Company"
    assert result["conference_facts_removed"] >= 4
    assert result["conference_affiliations_removed"] == 1
    assert conn.execute(
        """SELECT COUNT(*) FROM entity_source_facts
           WHERE fact = 'company_x_candidate'"""
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM entities WHERE name = 'Old Company'"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM channels WHERE key = 'https://old.example'"
    ).fetchone()[0] == 0
    assert result["orphan_conference_organizations_pruned"] == 1


def test_import_skips_historical_organization_when_newer_context_is_present(
    tmp_path,
):
    conn = channels.connect(tmp_path / "test.db")
    records = [
        _record(
            source_id="aie-worldsfair-2024",
            observed_at="2024-06-27T23:59:59+00:00",
            company="Historical Company",
            company_website="https://historical.example",
        ),
        _record(
            source_id="aie-worldsfair-2026",
            observed_at="2026-07-02T23:59:59+00:00",
            company="Current Company",
            company_website="https://current.example",
        ),
    ]

    result = conference_sources.import_records(conn, records)

    assert result["organizations_created"] == 1
    assert [
        row[0]
        for row in conn.execute(
            "SELECT name FROM entities WHERE kind = 'organization'"
        ).fetchall()
    ] == ["Current Company"]


def test_profile_hydration_is_raw_first_resumable_and_updates_account(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    record = _record()
    conference_sources.import_records(conn, [record])
    client = FakeProfileClient()
    cache = tmp_path / "profile-cache"

    first = conference_sources.hydrate_x_profiles(
        conn,
        [record],
        cache_root=cache,
        client=client,
        workers=1,
        requests_per_second=1000,
    )
    second = conference_sources.hydrate_x_profiles(
        conn,
        [record],
        cache_root=cache,
        client=client,
        workers=1,
        requests_per_second=1000,
    )

    account = conn.execute(
        "SELECT * FROM accounts WHERE handle = 'adaexample'"
    ).fetchone()
    assert first["profiles_fetched"] == 1
    assert first["failures"] == []
    assert second["profiles_fetched"] == 0
    assert second["already_hydrated"] == 1
    assert client.calls == ["adaexample"]
    assert account["x_id"] == "id-adaexample"
    assert account["followers_count"] == 123
    assert (cache / "adaexample.json").exists()


def test_cached_verified_profile_seeds_following_snapshot_without_provider_call(
    tmp_path,
):
    product_db = tmp_path / "product.db"
    conn = channels.connect(product_db)
    record = _record()
    conference_sources.import_records(conn, [record])
    cache = tmp_path / "profile-cache"
    client = FakeProfileClient()
    conference_sources.hydrate_x_profiles(
        conn,
        [record],
        cache_root=cache,
        client=client,
        workers=1,
        requests_per_second=1000,
    )
    conn.close()

    cohort_path = tmp_path / "cohort.json"
    following_snapshots.freeze_cohort(
        product_db=product_db,
        output_path=cohort_path,
        cohort_id="conference-test-cohort",
        created_at=SOURCE.observed_at,
        checkpoint_commit="test-commit",
    )
    snapshot_db = tmp_path / "snapshot.db"
    following_snapshots.initialize_snapshot(
        snapshot_id="conference-test-snapshot",
        cohort_path=cohort_path,
        snapshot_db=snapshot_db,
        created_at=SOURCE.observed_at,
    )

    first = conference_sources.seed_following_snapshot_profiles(
        snapshot_db=snapshot_db,
        records=[record],
        cache_root=cache,
    )
    second = conference_sources.seed_following_snapshot_profiles(
        snapshot_db=snapshot_db,
        records=[record],
        cache_root=cache,
    )

    snapshot = following_snapshots.connect_snapshot(snapshot_db)
    raw_profile = snapshot.execute(
        "SELECT * FROM raw_profile WHERE source_x_id = 'id-adaexample'"
    ).fetchone()
    snapshot.close()
    assert first["profiles_seeded"] == 1
    assert first["profiles_already_present"] == 0
    assert first["failures"] == []
    assert second["profiles_seeded"] == 0
    assert second["profiles_already_present"] == 1
    assert raw_profile is not None
    assert client.calls == ["adaexample"]


def test_provider_confirmed_unavailable_profile_is_reasonably_rejected(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    record = _record()
    conference_sources.import_records(conn, [record])
    cache = tmp_path / "profile-cache"
    conference_sources._write_profile_failure(
        cache,
        handle="adaexample",
        error=conference_sources.sources.SourceCliError(
            code="E_PROVIDER_ERROR",
            message="user not found",
            hint="",
            retryable=False,
        ),
    )

    first = conference_sources.reject_unavailable_conference_profiles(
        conn, [record], cache_root=cache
    )
    second = conference_sources.reject_unavailable_conference_profiles(
        conn, [record], cache_root=cache
    )

    rejection = conn.execute(
        "SELECT * FROM entity_registry_rejections"
    ).fetchone()
    assert first["rejected"] == 1
    assert second["rejected"] == 0
    assert rejection["reason_code"] == "conference_x_unavailable"
    assert rejection["source"] == "twitterapi_io"


def test_provider_confirmed_unavailable_profile_is_rejected_reasonably(tmp_path):
    conn = channels.connect(tmp_path / "test.db")
    record = _record()
    conference_sources.import_records(conn, [record])
    cache = tmp_path / "profile-cache"
    cache.mkdir()
    (cache / "adaexample.json").write_text(
        json.dumps(
            {
                "requested_handle": "adaexample",
                "retrieved_at": SOURCE.observed_at,
                "profile": {
                    "unavailable": True,
                    "unavailableReason": "Suspended",
                },
            }
        )
    )

    result = conference_sources.reject_unavailable_conference_profiles(
        conn, [record], cache_root=cache
    )

    rejection = conn.execute(
        "SELECT * FROM entity_registry_rejections"
    ).fetchone()
    assert result["rejected"] == 1
    assert rejection["reason_code"] == "conference_x_unavailable"
    assert "Suspended" in rejection["reason"]
