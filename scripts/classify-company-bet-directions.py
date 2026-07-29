#!/usr/bin/env python3
"""Classify every standing company bet as upside or downside.

This is a one-time, reproducible corpus migration. The model sees the same
four fields for every bet, the complete decision ledger is checked in, and the
memo simplifier refuses to run when the ledger no longer matches its source.

Usage:
    .venv/bin/python scripts/classify-company-bet-directions.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fli import llm_responses
from fli.registry import classification as entity_kinds


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "docs" / "references" / "archive" / "company-memos-full"
LEDGER_PATH = REPO_ROOT / "docs" / "references" / "company-bet-directions.json"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "projects"
    / "bet-linked-insights"
    / "resources"
    / "direction-reclassification.md"
)
TMP_ROOT = REPO_ROOT / "tmp" / "company-bet-direction-classification"

SCHEMA_VERSION = "company-bet-directions-v1"
PROMPT_VERSION = "company-bet-direction-v2"
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_EFFORT = "xhigh"
DEFAULT_BATCH_SIZE = 44
MAX_ATTEMPTS = 3
PROMPT_CACHE_KEY = "fli:company-bet-direction:v2"

INSTRUCTIONS = """You classify pre-registered public-equity hypotheses.

Each item is one standing bet written before any daily news event. Assign
exactly one direction: upside or downside. Do not use mixed, neutral, unclear,
or conditional.

The fixed question is:

If the bet's stated world condition occurs and its threshold is crossed, is
the primary tested economic consequence better or worse for the named company?

This is not a forecast of whether the condition will occur. It is not a view
on the current share price, valuation, consensus expectations, portfolio
weight, or whether an analyst should buy or sell the security. It is only a
stable polarity for the named causal hypothesis. The same bet must keep the
same direction when it is cited by different daily events.

Use all four supplied fields:

- if: the world condition that could occur;
- exposure: the part of the company through which it transmits;
- then: the expected financial or strategic consequence;
- threshold: the condition that makes the consequence important enough to
  matter to the thesis.

The threshold is the anchor. A threshold that tests whether revenue, demand,
share, pricing, margin, cash flow, returns, retention, or moat improve is
upside. A threshold that tests whether those outcomes deteriorate, costs or
risks rise, capacity goes unused, or a moat weakens is downside.

Apply this decision procedure in order:

1. Read the threshold first. Identify the concrete company outcome the
   threshold says must become large, persistent, measurable, or visible.
2. Ask whether that outcome improves or worsens the company's economics or
   strategic position. This usually determines the answer.
3. Use then to confirm the causal consequence and exposure to confirm which
   business line carries it.
4. Use if only to understand the world-side trigger. Do not classify a bet
   from whether the trigger itself sounds exciting, risky, or technical.
5. Separate the primary consequence from execution conditions, mitigating
   factors, and second-order effects.
6. If the old prose truly contains two co-equal mechanisms, choose the side
   tested most explicitly by the threshold and mark ambiguous true.

Common upside outcomes:

- incremental paid demand, usage, bookings, recurring revenue, attach, or
  retention;
- higher utilization, pricing power, margins, cash generation, or return on
  invested capital;
- market-share gains, stronger distribution, a more valuable installed base,
  or a more defensible moat;
- lower cost to serve when the saving is expected to improve company
  economics rather than merely reduce customer spending;
- a new product or capacity becoming billable at attractive utilization and
  pricing.

Common downside outcomes:

- demand destruction, substitution, cannibalization, churn, lower usage, or
  weaker pricing;
- margin compression, higher structural cost, excess capital intensity,
  underutilization, write-downs, or weaker cash conversion;
- share loss, commoditization, disintermediation, loss of distribution, or a
  weakened moat;
- security, regulatory, legal, reliability, or trust failures when the
  threshold tests measurable economic damage to the company;
- efficiency gains elsewhere that reduce the company's units, content,
  transactions, or infrastructure required per unit of customer value.

Execution risk does not reverse an upside bet. A sentence may say that ramp
costs, weak adoption, latency, integration, or bundled alternatives could
prevent an upside from arriving; that remains an upside bet when the threshold
tests successful adoption or improved economics.

Mitigation does not reverse a downside bet. A sentence may say that volume
growth, interoperability, diversification, pricing, or a countermeasure could
offset a downside; that remains a downside bet when the threshold tests damage
to the company.

Do not use these shortcuts:

- Do not copy the old direction. It is supplied only for the later audit and
  is deliberately absent from the model input.
- Do not call a bet downside merely because its prose mentions risk. Every
  useful upside has a failure mode.
- Do not call a bet upside merely because AI adoption grows. Adoption may
  cannibalize a premium product, move demand to a substitute, or reduce units.
- Do not call a capacity expansion upside unless the threshold tests billable
  utilization and acceptable economics. A bet whose threshold tests stranded
  capacity or weak returns is downside.
- Do not classify from tone. Words such as opportunity, risk, pressure,
  constraint, investment, or uncertainty are not the answer by themselves.
- Do not treat a smaller model or efficiency improvement as automatically
  positive or negative. Follow the named company's exposure and threshold.
- Do not turn uncertainty into ambiguous. Ambiguous is reserved for two
  genuinely different company mechanisms inside one bet.

Some old bets combine two genuine mechanisms. You must still choose one side.
Choose the side most directly tested by the threshold. If both sides are
equally explicit, choose the consequence that is more specific to the named
exposure and mark ambiguous true. Ambiguous means the bet should eventually be
split; it does not permit a third direction.

Examples:

1. If production agents expand, a security vendor can attach paid controls;
   the threshold asks for paid production adoption and measurable expansion.
   Direction: upside. Weak native alternatives are execution risk.

2. If algorithmic efficiency reduces chips per unit of useful work, a foundry
   may face lower wafer demand; the threshold asks whether efficiency
   persistently outpaces usage growth and leaves capacity underused.
   Direction: downside. Elastic usage is mitigation.

3. If bundled observability becomes good enough, an independent vendor may
   lose pricing power; the threshold asks for lower retention or paid usage.
   Direction: downside. Interoperability is mitigation.

4. If frontier demand grows faster than deployed compute, a cloud provider can
   sell more accelerated capacity; the threshold asks for commissioned,
   billable capacity at utilization and pricing that cover the capital base.
   Direction: upside. Build delays and underutilization are execution risks.

5. If a company commits heavily to AI infrastructure before demand is proven,
   cash flow and returns may weaken; the threshold asks whether unused capacity
   or financing costs persist. Direction: downside. Future demand absorption
   is mitigation.

6. If cheaper AI features increase engagement but also replace a premium
   subscription upgrade, inspect the threshold. If it tests net bookings and
   retention improvement, choose upside. If it tests premium cannibalization
   or weaker unit economics, choose downside. Mark ambiguous only when both
   tests are equally explicit in the same threshold.

7. If custom accelerators lower training cost for a cloud vendor and improve
   its model economics, while reducing demand for a merchant GPU supplier,
   those are two company-specific bets with different directions. The cloud
   vendor's bet is upside; the merchant supplier's substitution bet is
   downside. Never assign one cross-company direction from the technology
   alone.

Return every supplied bet exactly once through the strict schema. Keep each
rationale to one short sentence that names the threshold-side consequence.
Do not cite sources, use outside knowledge, or rewrite the bet.
"""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _source_bets() -> list[dict[str, Any]]:
    paths = sorted(SOURCE_DIR.glob("*.json"))
    if not paths:
        raise SystemExit(f"No archived company memos found in {SOURCE_DIR}")

    bets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        ticker = str(raw["company"]["ticker"])
        for index, item in enumerate(
            raw["memo"].get("frontier_ai_transmission_paths") or [],
            start=1,
        ):
            bet_id = f"{ticker}-B{index}"
            if bet_id in seen:
                raise SystemExit(f"Duplicate bet id {bet_id}")
            seen.add(bet_id)
            bets.append(
                {
                    "bet_id": bet_id,
                    "ticker": ticker,
                    "previous_direction": str(item["direction"]),
                    "if": str(item["development"]),
                    "exposure": str(item["company_exposure"]),
                    "then": str(item["financial_consequence"]),
                    "threshold": str(item["materiality_condition"]),
                }
            )
    return bets


def _output_format(batch_size: int) -> dict[str, Any]:
    item = {
        "type": "object",
        "properties": {
            "bet_id": {"type": "string"},
            "direction": {
                "type": "string",
                "enum": ["upside", "downside"],
            },
            "ambiguous": {"type": "boolean"},
            "rationale": {"type": "string"},
        },
        "required": ["bet_id", "direction", "ambiguous", "rationale"],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "name": PROMPT_VERSION.replace("-", "_"),
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "classifications": {
                    "type": "array",
                    "minItems": batch_size,
                    "maxItems": batch_size,
                    "items": item,
                }
            },
            "required": ["classifications"],
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


def _classify_batch(
    batch: list[dict[str, Any]],
    *,
    model: str,
    effort: str,
    batch_number: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    client = entity_kinds.create_litellm_client()
    if hasattr(client, "with_options"):
        client = client.with_options(max_retries=0)
    model_items = [
        {
            key: item[key]
            for key in ("bet_id", "ticker", "if", "exposure", "then", "threshold")
        }
        for item in batch
    ]
    tags = (
        "app:frontier-lab-intelligence",
        "pipeline:company-bet-direction",
        f"prompt:{PROMPT_VERSION}",
        f"model:{model}",
        f"reasoning:{effort}",
        f"batch:{batch_number:02d}",
    )
    request = {
        "model": model,
        "instructions": INSTRUCTIONS,
        "input": (
            "Classify this batch. The variable batch is appended after the "
            "stable instructions so repeated calls can reuse the prompt "
            "prefix.\n\n"
            + json.dumps({"bets": model_items}, ensure_ascii=False)
        ),
        "reasoning": {"effort": effort},
        "max_output_tokens": 16_000,
        "text": {"format": _output_format(len(batch))},
        "prompt_cache_key": PROMPT_CACHE_KEY,
        **llm_responses.litellm_prompt_cache_kwargs(model),
        "store": False,
        "extra_body": {"metadata": {"tags": list(tags)}},
        "extra_headers": {"x-litellm-tags": ",".join(tags)},
    }

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw_api = getattr(client.responses, "with_raw_response", None)
            if raw_api is None:
                response = client.responses.create(**request)
                cost = None
            else:
                raw_response = raw_api.create(**request)
                response = raw_response.parse()
                cost = llm_responses.reported_cost(raw_response.headers)
            response_data = llm_responses.as_dict(response)
            if response_data.get("status") not in (None, "completed"):
                raise RuntimeError(
                    f"response status {response_data.get('status')!r}: "
                    f"{response_data.get('incomplete_details')!r}"
                )
            result = json.loads(llm_responses.output_text(response_data))
            classifications = result["classifications"]
            expected = {item["bet_id"] for item in batch}
            returned = [str(item["bet_id"]) for item in classifications]
            if set(returned) != expected or len(returned) != len(expected):
                raise ValueError(
                    "classification batch omitted, repeated, or invented a bet id"
                )
            for item in classifications:
                if item["direction"] not in {"upside", "downside"}:
                    raise ValueError(
                        f"{item['bet_id']} returned invalid direction"
                    )
                if not str(item["rationale"]).strip():
                    raise ValueError(
                        f"{item['bet_id']} returned an empty rationale"
                    )
            usage = getattr(response, "usage", None) or response_data.get("usage")
            telemetry = {
                "batch": batch_number,
                "response_id": (
                    getattr(response, "id", None) or response_data.get("id")
                ),
                "input_tokens": _usage_value(usage, "input_tokens"),
                "cached_tokens": _input_detail(usage, "cached_tokens"),
                "cache_write_tokens": _input_detail(usage, "cache_write_tokens"),
                "output_tokens": _usage_value(usage, "output_tokens"),
                "reported_cost_usd": cost,
            }
            return classifications, telemetry, {
                "request": request,
                "response": response_data,
            }
        except Exception as exc:
            last_error = exc
            if attempt >= MAX_ATTEMPTS:
                break
            time.sleep(min(2 ** (attempt - 1), 8))
    assert last_error is not None
    raise last_error


def _cached_batch(
    batch: list[dict[str, Any]],
    *,
    model: str,
    effort: str,
    batch_number: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]] | None:
    """Reuse the newest completed raw call for this exact batch."""
    expected = {item["bet_id"] for item in batch}
    for path in sorted(TMP_ROOT.glob("*/batch-*.json"), reverse=True):
        try:
            trace = json.loads(path.read_text(encoding="utf-8"))
            request = trace["request"]
            response = trace["response"]
            if (
                request.get("model") != model
                or (request.get("reasoning") or {}).get("effort") != effort
                or response.get("status") not in (None, "completed")
            ):
                continue
            variable = json.loads(str(request["input"]).rsplit("\n\n", 1)[-1])
            supplied = {str(item["bet_id"]) for item in variable["bets"]}
            if supplied != expected:
                continue
            results = json.loads(llm_responses.output_text(response))[
                "classifications"
            ]
            returned = [str(item["bet_id"]) for item in results]
            if set(returned) != expected or len(returned) != len(expected):
                continue
            usage = response.get("usage") or {}
            return results, {
                "batch": batch_number,
                "response_id": response.get("id"),
                "input_tokens": _usage_value(usage, "input_tokens"),
                "cached_tokens": _input_detail(usage, "cached_tokens"),
                "cache_write_tokens": _input_detail(usage, "cache_write_tokens"),
                "output_tokens": _usage_value(usage, "output_tokens"),
                "reported_cost_usd": None,
                "reused_local_trace": path.relative_to(REPO_ROOT).as_posix(),
            }, trace
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return None


def _report(ledger: dict[str, Any]) -> str:
    records = [
        {"bet_id": bet_id, **item}
        for bet_id, item in ledger["classifications"].items()
    ]
    flips = [
        item
        for item in records
        if item["previous_direction"] != item["direction"]
    ]
    ambiguous = [item for item in records if item["ambiguous"]]
    lines = [
        "# Standing-bet direction reclassification",
        "",
        f"Generated: {ledger['generated_at']}",
        f"Model: `{ledger['model']}` / `{ledger['reasoning_effort']}`",
        f"Prompt: `{ledger['prompt_version']}`",
        f"Source SHA-256: `{ledger['source_sha256']}`",
        "",
        "## Spread",
        "",
        f"- Before: {ledger['counts_before']}",
        f"- After: {ledger['counts_after']}",
        f"- Changed labels: {len(flips)} of {ledger['bet_count']}",
        f"- Marked ambiguous for future splitting: {len(ambiguous)}",
        "",
        "## Every changed label",
        "",
        "| Bet | Before | After | Rationale |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        "| {bet_id} | {previous_direction} | {direction} | {rationale} |".format(
            **{
                **item,
                "rationale": str(item["rationale"]).replace("|", "\\|"),
            }
        )
        for item in flips
    )
    if ambiguous:
        lines.extend(
            [
                "",
                "## Ambiguous bets to split later",
                "",
                "| Bet | Direction | Rationale |",
                "| --- | --- | --- |",
            ]
        )
        lines.extend(
            "| {bet_id} | {direction} | {rationale} |".format(
                **{
                    **item,
                    "rationale": str(item["rationale"]).replace("|", "\\|"),
                }
            )
            for item in ambiguous
        )
    return "\n".join(lines) + "\n"


def classify(
    *,
    model: str,
    effort: str,
    batch_size: int,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch size must be positive")
    bets = _source_bets()
    source_sha256 = _sha256(
        [
            {
                key: item[key]
                for key in ("bet_id", "ticker", "if", "exposure", "then", "threshold")
            }
            for item in bets
        ]
    )
    classifications: dict[str, dict[str, Any]] = {}
    telemetry: list[dict[str, Any]] = []
    run_root = TMP_ROOT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root.mkdir(parents=True, exist_ok=True)

    batches = [
        bets[start : start + batch_size]
        for start in range(0, len(bets), batch_size)
    ]
    def accept_batch(
        batch_number: int,
        batch: list[dict[str, Any]],
        results: list[dict[str, Any]],
        call: dict[str, Any],
        trace: dict[str, Any],
    ) -> None:
        nonlocal classifications
        source_by_id = {item["bet_id"]: item for item in batch}
        for result in results:
            bet_id = str(result["bet_id"])
            source = source_by_id[bet_id]
            classifications[bet_id] = {
                "ticker": source["ticker"],
                "previous_direction": source["previous_direction"],
                "direction": result["direction"],
                "ambiguous": bool(result["ambiguous"]),
                "rationale": str(result["rationale"]).strip(),
            }
        telemetry.append(call)
        (run_root / f"batch-{batch_number:02d}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"batch {batch_number}/{len(batches)} "
            f"bets={len(batch)} cached={call['cached_tokens']}",
            file=sys.stderr,
            flush=True,
        )

    first_batch = batches[0]
    first = _cached_batch(
        first_batch,
        model=model,
        effort=effort,
        batch_number=1,
    )
    if first is None:
        first = _classify_batch(
            first_batch,
            model=model,
            effort=effort,
            batch_number=1,
        )
    accept_batch(1, first_batch, *first)

    with ThreadPoolExecutor(max_workers=min(3, len(batches) - 1)) as executor:
        futures = {}
        for batch_number, batch in enumerate(batches[1:], start=2):
            cached = _cached_batch(
                batch,
                model=model,
                effort=effort,
                batch_number=batch_number,
            )
            if cached is not None:
                accept_batch(batch_number, batch, *cached)
                continue
            future = executor.submit(
                _classify_batch,
                batch,
                model=model,
                effort=effort,
                batch_number=batch_number,
            )
            futures[future] = (batch_number, batch)
        for future in as_completed(futures):
            batch_number, batch = futures[future]
            results, call, trace = future.result()
            accept_batch(batch_number, batch, results, call, trace)

    expected = {item["bet_id"] for item in bets}
    if set(classifications) != expected:
        raise RuntimeError("completed ledger does not match the source bet set")

    before = Counter(item["previous_direction"] for item in bets)
    after = Counter(item["direction"] for item in classifications.values())
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "reasoning_effort": effort,
        "prompt_version": PROMPT_VERSION,
        "prompt_cache_key": PROMPT_CACHE_KEY,
        "source_sha256": source_sha256,
        "bet_count": len(bets),
        "counts_before": dict(sorted(before.items())),
        "counts_after": dict(sorted(after.items())),
        "telemetry": sorted(telemetry, key=lambda item: item["batch"]),
        "classifications": dict(sorted(classifications.items())),
    }
    LEDGER_PATH.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_report(ledger), encoding="utf-8")
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    ledger = classify(
        model=args.model,
        effort=args.effort,
        batch_size=args.batch_size,
    )
    print(f"bets       {ledger['bet_count']}")
    print(f"before     {ledger['counts_before']}")
    print(f"after      {ledger['counts_after']}")
    print(f"wrote      {LEDGER_PATH.relative_to(REPO_ROOT)}")
    print(f"report     {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
