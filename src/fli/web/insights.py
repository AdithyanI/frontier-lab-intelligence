"""Read-only UI seam for the successor audience Insight stage.

No successor run has been executed or persisted yet. These payloads preserve
the existing Insights screen's audience/date transport while refusing to read
the superseded Insight databases. The first real run will add a new store
behind this boundary and publish items ordered by application-owned Feed rank.
"""

from __future__ import annotations

from typing import Any

from fli import insight_generation


DEFAULT_AUDIENCE = insight_generation.InsightAudience.INVESTMENT.value


def _audience(value: str) -> str:
    return insight_generation.require_audience(value).value


def _reason(audience: str) -> str:
    label = audience.replace("_", " ")
    return f"No successor {label} Insight run has been generated yet."


def _dates_payload(audience: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": _reason(audience),
        "audience": audience,
        "latest_date": None,
        "dates": [],
    }


def _items_payload(audience: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": _reason(audience),
        "audience": audience,
        "run": None,
        "items": [],
    }


def insight_dates_payload(
    *, audience: str = DEFAULT_AUDIENCE, run_root: object | None = None
) -> dict[str, Any]:
    """Return an honest empty date view until the successor store exists."""
    del run_root
    return _dates_payload(_audience(audience))


def insights_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    day: str | None = None,
    db_path: object | None = None,
    run_root: object | None = None,
) -> dict[str, Any]:
    """Return no legacy rows; successor publication has not run yet."""
    del day, db_path, run_root
    return _items_payload(_audience(audience))


def extraction_dates_payload(
    *, audience: str = DEFAULT_AUDIENCE, run_root: object | None = None
) -> dict[str, Any]:
    """Serve the current UI route from the same successor empty boundary."""
    return insight_dates_payload(audience=audience, run_root=run_root)


def extraction_insights_payload(
    *,
    audience: str = DEFAULT_AUDIENCE,
    day: str | None = None,
    db_path: object | None = None,
    run_root: object | None = None,
) -> dict[str, Any]:
    """Serve the current UI route without reading superseded state."""
    return insights_payload(
        audience=audience,
        day=day,
        db_path=db_path,
        run_root=run_root,
    )
