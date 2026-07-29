"""File-backed BIT company context for the Investment agent.

Reads the skill-owned investment context packet and the promoted company
memos from disk. Holds no run store, no model calls, and no network access,
so the BIT Lens read model stays available independently of any run.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
INVESTMENT_CONTEXT_SCHEMA_VERSION = "bit-investment-context-v5"
COMPANY_MEMO_SCHEMA_VERSION = "company-memos-v3"
COMPANY_MEMO_PATH = REPO_ROOT / "docs" / "references" / "company-memos.json"
BIT_PUBLIC_VIEW_GRADES = {"explicit_thesis", "commentary", "none"}
BIT_PUBLIC_VIEW_SOURCE_SCOPES = {"firm", "flagship", "other_product", "mixed", "none"}
EVENT_COMPANY_CONNECTION_TYPES = {"direct", "indirect", "none"}

EVENT_COMPANY_THESIS_EFFECTS = {
    "supports",
    "challenges",
    "mixed",
    "unclear",
    "no_public_thesis",
}


INVESTMENT_CONTEXT_PATH = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "fli-daily-intelligence"
    / "references"
    / "bit-investment-context.json"
)


class CompanyProfileNotFound(ValueError):
    """The exact company name, ticker, or alias is absent from the packet."""

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def investment_context() -> dict[str, Any]:
    """Load the skill-owned, structured BIT Investment reference packet."""
    path = INVESTMENT_CONTEXT_PATH
    value = _read_json(path)
    if not isinstance(value, dict):
        raise ValueError("Investment context packet must be an object")
    if value.get("schema_version") != INVESTMENT_CONTEXT_SCHEMA_VERSION:
        raise ValueError("Investment context packet uses an unsupported schema version")
    _validate_company_profiles(value)
    return value


def company_context(query: str) -> dict[str, Any]:
    """Return one exact reusable company lens by canonical name, ticker, or alias."""
    normalized = " ".join(query.split()).casefold()
    if not normalized:
        raise ValueError("company query must not be empty")
    context = investment_context()
    matches: list[tuple[dict[str, Any], str]] = []
    for profile in context["company_profiles"]:
        candidates = {
            "name": [profile["name"]],
            "ticker": [profile["ticker"]],
            "alias": profile["aliases"],
        }
        for match_type, values in candidates.items():
            if any(" ".join(value.split()).casefold() == normalized for value in values):
                matches.append((profile, match_type))
                break
    if not matches:
        raise CompanyProfileNotFound(f"no company profile matches {query!r}")
    if len(matches) != 1:
        raise ValueError(f"company query {query!r} is ambiguous")
    profile, match_type = matches[0]
    holding = next(
        item for item in _covered_holdings(context) if item["name"] == profile["name"]
    )
    current = context.get("portfolio_current_top_ten")
    current_holding = None
    if isinstance(current, dict) and isinstance(current.get("holdings"), list):
        current_holding = next(
            (
                item
                for item in current["holdings"]
                if isinstance(item, dict) and item.get("name") == profile["name"]
            ),
            None,
        )
    return {
        "context_schema_version": context["schema_version"],
        "company_profiles_reviewed_at": context["company_profiles_reviewed_at"],
        "query": query,
        "matched_by": match_type,
        "portfolio_holding": holding,
        "current_top_ten_holding": current_holding,
        "profile": profile,
    }


def _covered_holdings(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Audited baseline holdings plus later-disclosed positions, in disclosure order.

    The 31 December 2025 annual report is the last complete public portfolio. The
    monthly factsheet discloses only a current top ten, so positions opened during
    2026 appear there and nowhere else. Both are kept with their own provenance
    rather than merged into one undated list.
    """
    holdings = [item for item in context["portfolio"]["holdings"] if isinstance(item, dict)]
    seen = {item.get("name") for item in holdings}
    current = context.get("portfolio_current_top_ten")
    if isinstance(current, dict) and isinstance(current.get("holdings"), list):
        for item in current["holdings"]:
            if isinstance(item, dict) and item.get("name") not in seen:
                holdings.append(item)
                seen.add(item.get("name"))
    return holdings


def _validate_company_profiles(context: dict[str, Any]) -> None:
    """Require one source-graded reusable lens for every working holding."""
    portfolio = context.get("portfolio")
    if not isinstance(portfolio, dict) or not isinstance(portfolio.get("holdings"), list):
        raise ValueError("Investment context packet is missing portfolio holdings")
    mapping_policy = context.get("event_company_mapping")
    if not isinstance(mapping_policy, dict) or set(mapping_policy) != {
        "candidate_universe",
        "connection_types",
        "thesis_effects",
        "shortlist_rule",
        "publication_rule",
    }:
        raise ValueError(
            "Investment context packet is missing event_company_mapping"
        )
    if mapping_policy["candidate_universe"] != "all_profiles":
        raise ValueError("event_company_mapping.candidate_universe must be all_profiles")
    _validate_string_list(
        mapping_policy["connection_types"],
        "event_company_mapping.connection_types",
        allow_empty=False,
    )
    if set(mapping_policy["connection_types"]) != EVENT_COMPANY_CONNECTION_TYPES:
        raise ValueError(
            "event_company_mapping.connection_types must define direct, indirect, and none"
        )
    _validate_string_list(
        mapping_policy["thesis_effects"],
        "event_company_mapping.thesis_effects",
        allow_empty=False,
    )
    if set(mapping_policy["thesis_effects"]) != EVENT_COMPANY_THESIS_EFFECTS:
        raise ValueError(
            "event_company_mapping.thesis_effects must define the complete thesis-effect set"
        )
    for key in ("shortlist_rule", "publication_rule"):
        if not isinstance(mapping_policy[key], str) or not mapping_policy[key].strip():
            raise ValueError(f"event_company_mapping.{key} must be non-empty")
    profiles = context.get("company_profiles")
    if not isinstance(profiles, list):
        raise ValueError("Investment context packet is missing company_profiles")
    reviewed_at = context.get("company_profiles_reviewed_at")
    if not isinstance(reviewed_at, str):
        raise ValueError("Investment context packet is missing company_profiles_reviewed_at")
    try:
        datetime.strptime(reviewed_at, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("company_profiles_reviewed_at must be an ISO date") from exc

    covered = _covered_holdings(context)
    holding_names = [item.get("name") for item in covered]
    profile_names = [item.get("name") for item in profiles if isinstance(item, dict)]
    if len(holding_names) != len(covered) or any(
        not isinstance(name, str) or not name for name in holding_names
    ):
        raise ValueError("Investment context portfolio contains an invalid holding name")
    if profile_names != holding_names:
        raise ValueError("Investment company_profiles must match portfolio holding order exactly")

    tickers: set[str] = set()
    lookup_owners: dict[str, str] = {}
    for index, profile in enumerate(profiles):
        path = f"company_profiles[{index}]"
        if not isinstance(profile, dict):
            raise ValueError(f"{path} must be an object")
        required = {
            "name",
            "ticker",
            "aliases",
            "listing_status",
            "bit_public_view",
            "analyst_context",
            "identity_sources",
        }
        if set(profile) != required:
            raise ValueError(f"{path} must contain exactly {sorted(required)}")
        ticker = profile["ticker"]
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError(f"{path}.ticker must be a non-empty string")
        if ticker in tickers:
            raise ValueError(f"{path}.ticker duplicates {ticker}")
        tickers.add(ticker)
        if profile["listing_status"] != "public":
            raise ValueError(f"{path}.listing_status must be public")
        _validate_string_list(profile["aliases"], f"{path}.aliases", allow_empty=True)
        for lookup_value in (profile["name"], profile["ticker"], *profile["aliases"]):
            lookup_key = " ".join(lookup_value.split()).casefold()
            prior_owner = lookup_owners.get(lookup_key)
            if prior_owner is not None and prior_owner != profile["name"]:
                raise ValueError(
                    f"{path} lookup value {lookup_value!r} duplicates {prior_owner}"
                )
            lookup_owners[lookup_key] = profile["name"]

        bit_view = profile["bit_public_view"]
        if not isinstance(bit_view, dict) or set(bit_view) != {
            "grade",
            "source_scope",
            "thesis",
            "edge",
            "signals",
            "countercase",
            "sources",
        }:
            raise ValueError(f"{path}.bit_public_view has an invalid shape")
        if bit_view["grade"] not in BIT_PUBLIC_VIEW_GRADES:
            raise ValueError(f"{path}.bit_public_view.grade is invalid")
        if bit_view["source_scope"] not in BIT_PUBLIC_VIEW_SOURCE_SCOPES:
            raise ValueError(f"{path}.bit_public_view.source_scope is invalid")
        for key in ("thesis", "edge", "countercase"):
            value = bit_view[key]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{path}.bit_public_view.{key} must be null or text")
        _validate_string_list(
            bit_view["signals"],
            f"{path}.bit_public_view.signals",
            allow_empty=True,
        )
        _validate_source_refs(
            bit_view["sources"],
            f"{path}.bit_public_view.sources",
            allow_empty=True,
        )
        if bit_view["grade"] == "none" and any(
            bit_view[key] not in (None, [], "")
            for key in ("thesis", "edge", "signals", "countercase", "sources")
        ):
            raise ValueError(f"{path}.bit_public_view must be empty when grade is none")
        if (bit_view["grade"] == "none") != (bit_view["source_scope"] == "none"):
            raise ValueError(f"{path}.bit_public_view none grade and scope must match")
        if bit_view["grade"] != "none" and not bit_view["sources"]:
            raise ValueError(f"{path}.bit_public_view requires a BIT source")

        analyst = profile["analyst_context"]
        if not isinstance(analyst, dict) or set(analyst) != {
            "business_summary",
            "operating_drivers",
            "frontier_ai_channels",
            "cautions",
        }:
            raise ValueError(f"{path}.analyst_context has an invalid shape")
        if not isinstance(analyst["business_summary"], str) or not analyst[
            "business_summary"
        ].strip():
            raise ValueError(f"{path}.analyst_context.business_summary is required")
        _validate_string_list(
            analyst["operating_drivers"],
            f"{path}.analyst_context.operating_drivers",
        )
        _validate_string_list(
            analyst["cautions"],
            f"{path}.analyst_context.cautions",
            allow_empty=True,
        )
        channels = analyst["frontier_ai_channels"]
        if not isinstance(channels, list) or not channels:
            raise ValueError(f"{path}.analyst_context.frontier_ai_channels is required")
        for channel_index, channel in enumerate(channels):
            channel_path = f"{path}.analyst_context.frontier_ai_channels[{channel_index}]"
            if not isinstance(channel, dict) or set(channel) != {
                "channel",
                "potential_upside",
                "potential_downside",
                "watchpoints",
            }:
                raise ValueError(f"{channel_path} has an invalid shape")
            for key in ("channel", "potential_upside", "potential_downside"):
                if not isinstance(channel[key], str) or not channel[key].strip():
                    raise ValueError(f"{channel_path}.{key} is required")
            _validate_string_list(
                channel["watchpoints"],
                f"{channel_path}.watchpoints",
            )
        _validate_source_refs(profile["identity_sources"], f"{path}.identity_sources")


def _validate_string_list(value: Any, path: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{path} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{path} must contain only non-empty strings")


def _validate_source_refs(value: Any, path: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{path} must be a non-empty list")
    for index, source in enumerate(value):
        if not isinstance(source, dict) or set(source) != {"label", "url"}:
            raise ValueError(f"{path}[{index}] must contain label and url")
        if any(
            not isinstance(source[key], str) or not source[key].strip()
            for key in ("label", "url")
        ):
            raise ValueError(f"{path}[{index}] must contain non-empty strings")


def portfolio_reference_payload() -> dict[str, Any]:
    """Return the compact reader disclosure derived from the canonical packet."""
    context = investment_context()
    portfolio = context.get("portfolio")
    if not isinstance(portfolio, dict):
        raise ValueError("Investment context packet is missing portfolio")
    source = portfolio.get("source")
    if not isinstance(source, dict):
        raise ValueError("Investment context packet is missing portfolio.source")
    return {
        "basis": str(portfolio["basis"]),
        "as_of": str(portfolio["as_of"]),
        "source_label": str(source["label"]),
        "source_url": str(source["url"]),
        "reader_note": str(context["reader_note"]),
    }


def _investment_company_memos() -> dict[str, dict[str, Any]]:
    """Load the consolidated, source-bearing company memos keyed by ticker."""
    if not COMPANY_MEMO_PATH.exists():
        return {}

    payload = _read_json(COMPANY_MEMO_PATH)
    if not isinstance(payload, dict):
        raise ValueError(f"{COMPANY_MEMO_PATH} must be an object")
    if payload.get("schema_version") != COMPANY_MEMO_SCHEMA_VERSION:
        raise ValueError(f"{COMPANY_MEMO_PATH} uses an unsupported schema version")
    companies = payload.get("companies")
    if not isinstance(companies, dict) or not companies:
        raise ValueError(f"{COMPANY_MEMO_PATH} has no companies")

    memos: dict[str, dict[str, Any]] = {}
    for ticker, memo in companies.items():
        if not isinstance(memo, dict):
            raise ValueError(f"Company memo {ticker} must be an object")
        if memo.get("ticker") != ticker:
            raise ValueError(f"Company memo {ticker} disagrees with its key")
        if not str(memo.get("summary") or "").strip():
            raise ValueError(f"Company memo {ticker} has no summary")
        bets = memo.get("bets")
        if not isinstance(bets, list) or not bets:
            raise ValueError(f"Company memo {ticker} has no bets")
        for bet in bets:
            missing = [
                field
                for field in ("id", "direction", "if", "exposure", "then", "threshold")
                if not str(bet.get(field) or "").strip()
            ]
            if missing:
                raise ValueError(
                    f"Company memo {ticker} bet {bet.get('id')} is missing "
                    f"{', '.join(missing)}"
                )
            if bet["direction"] not in {"upside", "downside"}:
                raise ValueError(
                    f"Company memo {ticker} bet {bet.get('id')} has an "
                    "invalid direction"
                )
        source_ledger = memo.get("source_ledger")
        if not isinstance(source_ledger, list) or not source_ledger:
            raise ValueError(f"Company memo {ticker} has no source ledger")
        memos[ticker] = memo
    return memos


def investment_company_universe_payload() -> dict[str, Any]:
    """Return the complete, dated company-context read model for BIT Lens."""
    context = investment_context()
    promoted_memos = _investment_company_memos()
    audited = context["portfolio"]
    current = context["portfolio_current_top_ten"]
    audited_by_name = {
        item["name"]: item
        for item in audited["holdings"]
        if isinstance(item, dict)
    }
    current_by_name = {
        item["name"]: {**item, "rank": rank}
        for rank, item in enumerate(current["holdings"], start=1)
        if isinstance(item, dict)
    }

    companies = []
    for profile in context["company_profiles"]:
        name = profile["name"]
        audited_holding = audited_by_name.get(name)
        current_holding = current_by_name.get(name)
        reference_holding = current_holding or audited_holding
        reference_basis = (
            "current_top_ten" if current_holding else "audited_baseline"
        )
        companies.append(
            {
                **profile,
                "research_memo": promoted_memos.get(profile["ticker"]),
                "portfolio_context": {
                    "reference_holding": {
                        "as_of": (
                            current["as_of"]
                            if current_holding
                            else audited["as_of"]
                        ),
                        "weight_pct": reference_holding["weight_pct"],
                        "basis": reference_basis,
                        "currently_confirmed": current_holding is not None,
                    },
                    "current_top_ten": (
                        {
                            "as_of": current["as_of"],
                            "rank": current_holding["rank"],
                            "weight_pct": current_holding["weight_pct"],
                        }
                        if current_holding
                        else None
                    ),
                    "audited_baseline": (
                        {
                            "as_of": audited["as_of"],
                            "weight_pct": audited_holding["weight_pct"],
                        }
                        if audited_holding
                        else None
                    ),
                },
            }
        )

    grade_counts = {
        grade: sum(
            profile["bit_public_view"]["grade"] == grade
            for profile in context["company_profiles"]
        )
        for grade in ("explicit_thesis", "commentary", "none")
    }
    channel_count = sum(
        len(profile["analyst_context"]["frontier_ai_channels"])
        for profile in context["company_profiles"]
    )
    later_additions = sum(
        company["portfolio_context"]["current_top_ten"] is not None
        and company["portfolio_context"]["audited_baseline"] is None
        for company in companies
    )
    return {
        "schema_version": "investment-company-universe-v5",
        "source_context_schema_version": context["schema_version"],
        "profiles_reviewed_at": context["company_profiles_reviewed_at"],
        "mapping_policy": context["event_company_mapping"],
        "disclosures": {
            "current_top_ten": {
                "as_of": current["as_of"],
                "position_count": current["position_count"],
                "visible_holding_count": len(current["holdings"]),
                "source": {
                    "label": current["source"]["label"],
                    "url": current["source"]["url"],
                },
            },
            "audited_baseline": {
                "as_of": audited["as_of"],
                "visible_holding_count": len(audited["holdings"]),
                "source": {
                    "label": audited["source"]["label"],
                    "url": audited["source"]["url"],
                },
            },
        },
        "counts": {
            "companies": len(companies),
            "current_top_ten": len(current["holdings"]),
            "audited_baseline": len(audited["holdings"]),
            "later_top_ten_additions": later_additions,
            "research_memos": len(promoted_memos),
            "frontier_ai_channels": channel_count,
            "bit_public_views": grade_counts["explicit_thesis"]
            + grade_counts["commentary"],
            "bit_public_view_grades": grade_counts,
        },
        "companies": companies,
    }
