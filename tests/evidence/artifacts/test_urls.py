import json

from fli.evidence.artifacts import store as artifacts
from fli.evidence.artifacts import urls as artifact_urls


def test_canonicalization_is_conservative_and_tracks_reviewed_equivalence():
    assert artifact_urls.canonicalize_url(
        "HTTP://Arxiv.org:80/pdf/2603.18073.pdf?utm_source=x#page=72"
    ) == "https://arxiv.org/abs/2603.18073"
    assert artifact_urls.canonicalize_url(
        "https://www.youtube.com/watch?v=abc&si=share&t=42"
    ) == "https://www.youtube.com/watch?v=abc&t=42"
    assert artifact_urls.canonicalize_url(
        "https://example.com/story?id=7&source=meaningful#section"
    ) == "https://example.com/story?id=7&source=meaningful"


def test_candidate_rules_exclude_navigation_and_accept_artifacts():
    cases = {
        "https://x.com/lab/status/123": "ordinary_x_status",
        "https://x.com/i/broadcasts/abc": "x_broadcast_deferred",
        "https://github.com/cadene": "external_profile",
        "https://www.youtube.com/@lab": "external_profile",
        "https://discord.gg/example": "invite_url",
        "https://www.google.com/search?q=ai": "search_navigation",
        "https://www.amazon.science/search": "search_navigation",
    }
    for url, reason in cases.items():
        result = artifact_urls.classify_candidate(url)
        assert result.decision == "excluded"
        assert result.reason_code == reason

    accepted = artifact_urls.classify_candidate(
        "https://t.co/alias", "https://arxiv.org/pdf/2603.18073#page=72"
    )
    assert accepted.decision == "accepted"
    assert accepted.canonical_url == "https://arxiv.org/abs/2603.18073"

    specific_document = artifact_urls.classify_candidate(
        "https://example.com/research/searching-for-truth"
    )
    assert specific_document.decision == "accepted"


def test_url_evidence_binds_nested_link_to_actual_owner():
    payload = {
        "id": "wrapper",
        "entities": {"urls": []},
        "quoted_tweet": {
            "id": "owner",
            "entities": {
                "urls": [
                    {
                        "url": "https://t.co/paper",
                        "expanded_url": "https://arxiv.org/abs/2603.18073",
                    }
                ]
            },
            "card": {"url": "https://t.co/unbound-card"},
        },
    }

    evidence = artifact_urls.url_evidence(payload)

    assert len(evidence) == 1
    assert evidence[0].owner_external_id == "owner"
    assert evidence[0].source == "quoted_entity"
    assert evidence[0].expanded_url == "https://arxiv.org/abs/2603.18073"


def test_artifact_admission_rejects_a_link_owned_by_a_quoted_reaction():
    payload = {
        "id": "root",
        "entities": {"urls": []},
        "quoted_tweet": {
            "id": "other-author",
            "entities": {
                "urls": [
                    {
                        "url": "https://t.co/tool",
                        "expanded_url": "https://example.com/unrelated-tool",
                    }
                ]
            },
        },
    }

    assert artifacts._matching_primary_evidence(
        json.dumps(payload),
        "https://example.com/unrelated-tool",
        post_id="root",
    ) is None


def test_artifact_admission_rejects_an_event_only_unbound_link():
    payload = {"id": "root", "entities": {"urls": []}}

    assert artifacts._matching_primary_evidence(
        json.dumps(payload),
        "https://example.com/stale-event-preview",
        post_id="root",
    ) is None
