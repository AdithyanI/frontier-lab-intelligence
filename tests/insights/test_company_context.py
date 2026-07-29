from __future__ import annotations

import pytest

from fli.insights import company_context


def test_investment_context_validates_the_skill_owned_packet():
    context = company_context.investment_context()

    assert context["schema_version"] == company_context.INVESTMENT_CONTEXT_SCHEMA_VERSION
    assert context["company_profiles"]
    assert context["portfolio"]["holdings"]


def test_company_universe_covers_every_profile_with_its_memo():
    payload = company_context.investment_company_universe_payload()
    companies = payload["companies"]

    assert payload["schema_version"]
    assert len(companies) == len(company_context.investment_context()["company_profiles"])
    assert all(company["ticker"] for company in companies)
    assert all("portfolio_context" in company for company in companies)
    memo_backed = [company for company in companies if company["research_memo"]]
    assert memo_backed, "at least one company must carry a promoted research memo"


def test_company_lookup_resolves_by_ticker_and_rejects_unknown_names():
    resolved = company_context.company_context("NTSK")

    assert resolved["profile"]["ticker"] == "NTSK"
    with pytest.raises(company_context.CompanyProfileNotFound):
        company_context.company_context("not-a-real-company")


def test_promoted_memos_are_keyed_by_unique_ticker():
    memos = company_context._investment_company_memos()

    assert memos
    assert all(
        payload["schema_version"] == company_context.COMPANY_MEMO_SCHEMA_VERSION
        for payload in memos.values()
    )
    assert all(ticker == payload["company"]["ticker"] for ticker, payload in memos.items())
