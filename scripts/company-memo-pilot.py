"""One-company memo research pilot.

This intentionally writes only to tmp/. It does not mutate the canonical
Investment context packet. Long-running research uses the Responses API
background contract so the proxy request is not held open for the full run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fli import llm_responses
from fli.registry import classification as entity_kinds


CONTEXT_PATH = (
    ROOT
    / ".agents"
    / "skills"
    / "fli-daily-intelligence"
    / "references"
    / "bit-investment-context.json"
)
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_POLL_INTERVAL_SECONDS = 30.0
MAX_RETRIEVE_FAILURES = 6
PROMPT_VERSION = "company-memo-pilot-v1"
PROMPT_CACHE_KEY = f"fli:company-memo:{PROMPT_VERSION}"


INSTRUCTIONS = """
You are preparing durable prior context for an investment research agent that
reads frontier-AI Events and decides whether they have a credible, material
connection to a public company.

The assignment
--------------
Frontier Lab Intelligence tracks frontier AI labs and people, groups their
public output into Events, ranks those Events, and produces separate briefs for
an investment team and an AI engineering team. This task concerns only the
investment side. The eventual reader needs to answer:

1. What changed?
2. Which public company could it affect?
3. Through which explicit operating mechanism?
4. Which financial variable could move?
5. Does the evidence support, challenge, mix, or leave unclear an attributable
   public BIT Capital thesis?
6. What should an analyst inspect next?

This company memo is prior context, not a conclusion about any particular
Event. It should let a later agent cold-start without repeatedly researching
the stable foundations of the company. It must not make every AI development
sound relevant.

Research method
---------------
Use web search. Prefer current primary sources:

- company filings, annual reports, quarterly results, investor presentations,
  earnings materials, product documentation, and official company pages;
- public BIT Capital material when it genuinely discusses this company;
- named customer, supplier, partner, or regulator sources when they establish
  a relationship;
- high-quality secondary reporting only when primary evidence is unavailable
  or when independent context is necessary.

Do not treat search-result snippets as evidence. Do not infer a BIT Capital
view from portfolio ownership, portfolio weight, sector labels, or generic
marketing language. Preserve the supplied BIT view unless a better attributable
public source directly supports a correction. When no public BIT thesis exists,
say so; do not manufacture one.

Separate sourced facts from analytical transmission hypotheses. A hypothesis
may explain how frontier AI could affect the company, but its mechanism must be
explicit and its materiality condition must be falsifiable. Avoid generic
claims such as "AI improves efficiency" unless you identify the workflow, the
operating variable, and the financial consequence.

Durability boundary
-------------------
Capture information that is useful across many future Events:

- how the company makes money and who pays;
- the operating variables that govern revenue, volume, pricing, product mix,
  gross margin, operating cost, capital intensity, cash flow, or risk;
- important customers or end markets, suppliers, partners, competitors,
  substitutes, infrastructure dependencies, and regulatory dependencies;
- management's durable strategy and committed actions relevant to frontier AI;
- credible routes from a frontier-AI development to an operating driver and
  then to a financial consequence;
- attributable public BIT thesis evidence and the conditions that would support
  or challenge it;
- important uncertainties, missing evidence, and triggers for future research.

Do not turn the reusable memo into a live market-data snapshot. Exclude share
price, valuation multiples, consensus forecasts, and transient daily news.
Include a dated current fact only when it anchors strategy, capacity, customer
exposure, or another durable operating condition. State its date.

Required causal discipline
--------------------------
For every frontier-AI transmission path, make the chain inspectable:

frontier-AI development
-> company exposure or dependency
-> affected operating driver
-> possible financial consequence
-> condition under which the effect becomes material
-> observable watchpoints.

The direction can be upside, downside, or mixed. Give a time horizon of near
term, medium term, long term, or unclear. Classify the effect on the public BIT
thesis as supports, challenges, mixed, unclear, or no_public_thesis. This is a
classification of the hypothetical mechanism, not a claim that the mechanism
has already occurred.

Source discipline
-----------------
Every substantive object must include one or more HTTPS source URLs. Reuse URLs
when several claims depend on the same source. Dates should be ISO YYYY-MM-DD
when the exact date is known and null when it is not. The source ledger should
contain every URL used elsewhere in the memo and no unrelated links.

Write concise analyst prose. Prefer three to five high-value items over long,
overlapping lists. Return only the requested structured object. The company
name and ticker are envelope metadata supplied separately, so do not repeat
them inside the memo.
""".strip()


SOURCE_REF = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "claim_date": {"type": ["string", "null"]},
    },
    "required": ["url", "claim_date"],
    "additionalProperties": False,
}

OUTPUT_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "company_investment_memo",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "business_and_economics": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "revenue_engines": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {
                            "type": "object",
                            "properties": {
                                "engine": {"type": "string"},
                                "who_pays": {"type": "string"},
                                "economic_logic": {"type": "string"},
                                "sources": {
                                    "type": "array",
                                    "minItems": 1,
                                    "items": SOURCE_REF,
                                },
                            },
                            "required": [
                                "engine",
                                "who_pays",
                                "economic_logic",
                                "sources",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "sources": {
                        "type": "array",
                        "minItems": 1,
                        "items": SOURCE_REF,
                    },
                },
                "required": ["summary", "revenue_engines", "sources"],
                "additionalProperties": False,
            },
            "operating_and_financial_drivers": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "driver": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "financial_lines": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "string",
                                "enum": [
                                    "revenue",
                                    "volume",
                                    "pricing",
                                    "product_mix",
                                    "gross_margin",
                                    "operating_cost",
                                    "capital_expenditure",
                                    "working_capital",
                                    "cash_flow",
                                    "balance_sheet",
                                    "risk",
                                ],
                            },
                        },
                        "sources": {
                            "type": "array",
                            "minItems": 1,
                            "items": SOURCE_REF,
                        },
                    },
                    "required": [
                        "driver",
                        "why_it_matters",
                        "financial_lines",
                        "sources",
                    ],
                    "additionalProperties": False,
                },
            },
            "ecosystem": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "relationship": {
                            "type": "string",
                            "enum": [
                                "customer_or_end_market",
                                "supplier",
                                "partner",
                                "competitor",
                                "substitute",
                                "infrastructure_dependency",
                                "regulatory_dependency",
                            ],
                        },
                        "entities_or_group": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "sources": {
                            "type": "array",
                            "minItems": 1,
                            "items": SOURCE_REF,
                        },
                    },
                    "required": [
                        "relationship",
                        "entities_or_group",
                        "why_it_matters",
                        "sources",
                    ],
                    "additionalProperties": False,
                },
            },
            "strategy_and_committed_actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "investment_relevance": {"type": "string"},
                        "sources": {
                            "type": "array",
                            "minItems": 1,
                            "items": SOURCE_REF,
                        },
                    },
                    "required": ["action", "investment_relevance", "sources"],
                    "additionalProperties": False,
                },
            },
            "frontier_ai_transmission_paths": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "development": {"type": "string"},
                        "company_exposure": {"type": "string"},
                        "affected_driver": {"type": "string"},
                        "financial_consequence": {"type": "string"},
                        "direction": {
                            "type": "string",
                            "enum": ["upside", "downside", "mixed"],
                        },
                        "materiality_condition": {"type": "string"},
                        "time_horizon": {
                            "type": "string",
                            "enum": [
                                "near_term",
                                "medium_term",
                                "long_term",
                                "unclear",
                            ],
                        },
                        "thesis_effect": {
                            "type": "string",
                            "enum": [
                                "supports",
                                "challenges",
                                "mixed",
                                "unclear",
                                "no_public_thesis",
                            ],
                        },
                        "watchpoints": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 5,
                            "items": {"type": "string"},
                        },
                        "sources": {
                            "type": "array",
                            "minItems": 1,
                            "items": SOURCE_REF,
                        },
                    },
                    "required": [
                        "development",
                        "company_exposure",
                        "affected_driver",
                        "financial_consequence",
                        "direction",
                        "materiality_condition",
                        "time_horizon",
                        "thesis_effect",
                        "watchpoints",
                        "sources",
                    ],
                    "additionalProperties": False,
                },
            },
            "investment_thesis_and_tests": {
                "type": "object",
                "properties": {
                    "public_bit_view_status": {
                        "type": "string",
                        "enum": [
                            "explicit_thesis",
                            "commentary",
                            "no_public_view",
                        ],
                    },
                    "attributable_public_thesis": {
                        "type": ["string", "null"],
                    },
                    "what_would_support_it": {
                        "type": "array",
                        "maxItems": 5,
                        "items": {"type": "string"},
                    },
                    "what_would_challenge_it": {
                        "type": "array",
                        "maxItems": 5,
                        "items": {"type": "string"},
                    },
                    "sources": {
                        "type": "array",
                        "items": SOURCE_REF,
                    },
                },
                "required": [
                    "public_bit_view_status",
                    "attributable_public_thesis",
                    "what_would_support_it",
                    "what_would_challenge_it",
                    "sources",
                ],
                "additionalProperties": False,
            },
            "uncertainties_and_research_triggers": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "uncertainty": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "next_research_trigger": {"type": "string"},
                        "sources": {
                            "type": "array",
                            "minItems": 1,
                            "items": SOURCE_REF,
                        },
                    },
                    "required": [
                        "uncertainty",
                        "why_it_matters",
                        "next_research_trigger",
                        "sources",
                    ],
                    "additionalProperties": False,
                },
            },
            "source_ledger": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "publisher": {"type": "string"},
                        "published_at": {"type": ["string", "null"]},
                        "source_type": {
                            "type": "string",
                            "enum": [
                                "company_primary",
                                "bit_primary",
                                "counterparty_primary",
                                "regulator_primary",
                                "high_quality_secondary",
                            ],
                        },
                    },
                    "required": [
                        "url",
                        "title",
                        "publisher",
                        "published_at",
                        "source_type",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "business_and_economics",
            "operating_and_financial_drivers",
            "ecosystem",
            "strategy_and_committed_actions",
            "frontier_ai_transmission_paths",
            "investment_thesis_and_tests",
            "uncertainties_and_research_triggers",
            "source_ledger",
        ],
        "additionalProperties": False,
    },
}


def _usage_value(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(field) or 0)
    return int(getattr(usage, field, 0) or 0)


def _input_detail(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    details = (
        usage.get("input_tokens_details")
        if isinstance(usage, dict)
        else getattr(usage, "input_tokens_details", None)
    )
    return _usage_value(details, field)


def _output_detail(usage: Any, field: str) -> int:
    if usage is None:
        return 0
    details = (
        usage.get("output_tokens_details")
        if isinstance(usage, dict)
        else getattr(usage, "output_tokens_details", None)
    )
    return _usage_value(details, field)


def _profile(ticker: str) -> dict[str, Any]:
    packet = json.loads(CONTEXT_PATH.read_text())
    normalized = ticker.strip().upper()
    matches = [
        profile
        for profile in packet["company_profiles"]
        if profile["ticker"].upper() == normalized
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one profile for ticker {normalized!r}")
    return matches[0]


def _validate_urls(memo: dict[str, Any]) -> None:
    ledger_urls = {item["url"] for item in memo["source_ledger"]}
    if not ledger_urls or not all(url.startswith("https://") for url in ledger_urls):
        raise ValueError("source ledger must contain only HTTPS URLs")

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) == {"url", "claim_date"}:
                url = value["url"]
                if not url.startswith("https://"):
                    raise ValueError(f"claim source is not HTTPS: {url}")
                if url not in ledger_urls:
                    raise ValueError(f"claim source is absent from ledger: {url}")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(memo)


def research(
    ticker: str,
    *,
    model: str,
    reasoning_effort: str,
    poll_interval_seconds: float,
) -> Path:
    profile = _profile(ticker)
    client = entity_kinds.create_litellm_client()
    tags = (
        "app:frontier-lab-intelligence",
        "pipeline:investment-company-context",
        "job:company-memo-pilot",
        "scope:single-company",
        f"prompt:{PROMPT_VERSION}",
        f"company:{profile['ticker'].lower()}",
        f"model:{model}",
        f"reasoning:{reasoning_effort}",
    )
    request = {
        "model": model,
        "instructions": INSTRUCTIONS,
        "input": json.dumps(
            {
                "research_date": dt.date.today().isoformat(),
                "company_envelope": {
                    "name": profile["name"],
                    "ticker": profile["ticker"],
                    "aliases": profile["aliases"],
                    "listing_status": profile["listing_status"],
                },
                "existing_company_packet": {
                    "bit_public_view": profile["bit_public_view"],
                    "analyst_context": profile["analyst_context"],
                    "identity_sources": profile["identity_sources"],
                },
            },
            ensure_ascii=False,
        ),
        "prompt_cache_key": PROMPT_CACHE_KEY,
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "tools": [
            {
                "type": "web_search",
                "search_context_size": "high",
                "return_token_budget": "unlimited",
            }
        ],
        "tool_choice": llm_responses.required_web_search_tool_choice(model),
        "include": ["web_search_call.action.sources"],
        "reasoning": {"effort": reasoning_effort},
        "text": {"format": OUTPUT_FORMAT},
        "background": True,
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }

    response = client.responses.create(**request)
    creation_response_id = response.id
    retrieve_failures = 0
    print(f"background response status={response.status}", file=sys.stderr, flush=True)
    while response.status in {"queued", "in_progress"}:
        time.sleep(poll_interval_seconds)
        try:
            response = client.responses.retrieve(creation_response_id)
        except Exception as exc:
            retrieve_failures += 1
            print(
                "background response retrieve_error="
                f"{type(exc).__name__} attempt={retrieve_failures}/"
                f"{MAX_RETRIEVE_FAILURES}",
                file=sys.stderr,
                flush=True,
            )
            if retrieve_failures >= MAX_RETRIEVE_FAILURES:
                raise
            continue
        retrieve_failures = 0
        print(f"background response status={response.status}", file=sys.stderr, flush=True)

    response_data = llm_responses.as_dict(response)
    if response_data.get("status") != "completed":
        raise RuntimeError(
            f"response status {response_data.get('status')!r}: "
            f"{response_data.get('incomplete_details')!r}"
        )
    memo = json.loads(llm_responses.output_text(response_data))
    _validate_urls(memo)
    actions, consulted_sources = llm_responses.web_evidence(
        response_data,
        cited_urls=[item["url"] for item in memo["source_ledger"]],
        require_search_action=True,
    )
    usage = getattr(response, "usage", None) or response_data.get("usage")
    result = {
        "schema_version": "company-memo-pilot-result-v1",
        "company": {
            "name": profile["name"],
            "ticker": profile["ticker"],
        },
        "memo": memo,
        "provenance": {
            "research_date": dt.date.today().isoformat(),
            "model": model,
            "reasoning_effort": reasoning_effort,
            "prompt_version": PROMPT_VERSION,
            "prompt_cache_key": PROMPT_CACHE_KEY,
            "response_id": creation_response_id,
            "response_model": getattr(response, "model", None),
            "input_tokens": _usage_value(usage, "input_tokens"),
            "cached_tokens": _input_detail(usage, "cached_tokens"),
            "cache_write_tokens": _input_detail(usage, "cache_write_tokens"),
            "output_tokens": _usage_value(usage, "output_tokens"),
            "reasoning_tokens": _output_detail(usage, "reasoning_tokens"),
            "reported_cost_usd": None,
            "web_actions": actions,
            "consulted_sources": consulted_sources,
            "request_tags": list(tags),
        },
    }
    model_slug = model.replace("/", "-").replace(".", "-")
    output_path = (
        ROOT
        / "tmp"
        / (
            f"company-memo-pilot-{profile['ticker']}-"
            f"{model_slug}-{reasoning_effort}.json"
        )
    )
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="IREN")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="seconds between background response retrievals",
    )
    args = parser.parse_args()
    if args.poll_interval <= 0:
        parser.error("--poll-interval must be greater than zero")
    output_path = research(
        args.ticker,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        poll_interval_seconds=args.poll_interval,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
