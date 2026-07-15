import pytest
from fastapi.testclient import TestClient

from fli.web import insights as insight_store
from fli.web.app import app


client = TestClient(app)


@pytest.mark.parametrize("audience", ["investment", "ai_engineering"])
def test_successor_insight_store_is_honestly_empty(audience):
    dates = insight_store.insight_dates_payload(audience=audience)
    items = insight_store.insights_payload(audience=audience, day="2026-07-15")

    assert dates == {
        "available": False,
        "reason": f"No successor {audience.replace('_', ' ')} Insight run has been generated yet.",
        "audience": audience,
        "latest_date": None,
        "dates": [],
    }
    assert items == {
        "available": False,
        "reason": dates["reason"],
        "audience": audience,
        "run": None,
        "items": [],
    }


def test_current_ui_routes_use_the_successor_empty_boundary():
    dates = client.get(
        "/api/insights/extracted/dates?audience=ai_engineering"
    ).json()
    items = client.get(
        "/api/insights/extracted?audience=ai_engineering&date=2026-07-15"
    ).json()

    assert dates["available"] is False
    assert dates["audience"] == "ai_engineering"
    assert items["available"] is False
    assert items["items"] == []


def test_invalid_audiences_are_rejected_at_python_and_http_boundaries():
    with pytest.raises(ValueError, match="unsupported Insight audience"):
        insight_store.insight_dates_payload(audience="general")

    response = client.get("/api/insights/dates?audience=general")
    assert response.status_code == 422
