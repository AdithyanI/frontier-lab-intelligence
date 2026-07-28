"""B6 layer-2 probe — force a per-company verdict for every gated development.

Read-only. Reads the frozen editorial database, calls the shared LiteLLM
endpoint, and writes JSON under ``tmp/``. It mutates no pipeline state and does
not touch the frozen 17-day corpus.

What it tests
-------------
Finding 16 measured that the full portfolio roster is already in every
Investment editorial prompt, and coverage still correlates with position weight
at rho = 0.205. The hypothesis behind B6 is that *availability is not
consideration*: a model given a roster will skip most of it, but a model
required to return a verdict per company cannot.

This probe isolates that one variable. Same day, same gated developments, same
roster — the only change is that a verdict is mandatory for every company.

Usage
-----
    .venv/bin/python docs/projects/interview-readiness-audit/resources/fanout-probe.py \
        --day 2026-07-21 --limit 5

Start with ``--limit 5`` to check output shape and per-call cost before
spending on all 66. Compare the resulting matrix against what the system
actually published that day; the interesting cells are non-mega-cap companies
with a real mechanism that the current editor never mentioned.

Reading the result
------------------
- A company with a plausible mechanism that never appeared in the published
  brief supports B6.
- If the fan-out mostly returns the same handful of mega-caps, the bottleneck
  is upstream evidence rather than editorial attention, which is a different
  and equally useful finding.
- The negative verdicts are a deliverable in their own right: they turn "why
  nothing on Micron today?" into an auditable row with a reason.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import pathlib
import sqlite3
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from fli import llm_responses  # noqa: E402
from fli.insights import editorial_runs  # noqa: E402
from fli.registry.classification import create_litellm_client  # noqa: E402

EDITORIAL_DB = REPO / "data" / "derived" / "daily-intelligence" / "editorial.db"
OUT_DIR = REPO / "tmp" / "fanout"
MODEL = "gpt-5.4-mini"
EFFORT = "high"
PROMPT_VERSION = "fanout-probe-v1"
CACHE_KEY = f"fli:fanout-probe:{PROMPT_VERSION}"

INSTRUCTIONS = """\
You decide, for one frontier-AI development, which companies in a fixed roster \
are affected by it.

Rules:

1. Return a verdict for EVERY company in the roster, in the roster's order. \
Never omit one.
2. `affected` is true only when a concrete transmission mechanism runs from \
this specific development to that company's economics or competitive position. \
Operating in the same sector is not a mechanism.
3. Be tolerant of plausible links; a later, more expensive stage filters. \
Prefer a well-argued maybe over a miss. Do not invent a mechanism to be \
generous: when there is none, say so.
4. `mechanism` is one sentence naming the actual channel, and is null when \
`affected` is false. `why_not` is one short clause when `affected` is false, \
and null when true.
5. `direction` is the effect on that company: positive, negative, mixed, or \
uncertain. Use `none` only when `affected` is false.
6. Judge only from the development text supplied. Do not use outside knowledge \
of later events, and do not speculate about unannounced products.
7. Position weight tells you how much the fund owns, not whether a mechanism \
exists. Never let weight create a link the development does not support.
"""

OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "company_fanout",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["verdicts"],
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "company",
                        "affected",
                        "direction",
                        "mechanism",
                        "why_not",
                    ],
                    "properties": {
                        "company": {"type": "string"},
                        "affected": {"type": "boolean"},
                        "direction": {
                            "type": "string",
                            "enum": [
                                "positive",
                                "negative",
                                "mixed",
                                "uncertain",
                                "none",
                            ],
                        },
                        "mechanism": {"type": ["string", "null"]},
                        "why_not": {"type": ["string", "null"]},
                    },
                },
            }
        },
    },
}


def roster() -> list[dict]:
    """Coverage roster, preferring the current factsheet weight when disclosed."""
    context = editorial_runs.investment_context()
    current = {
        holding["name"]: holding["weight_pct"]
        for holding in context["portfolio_current_top_ten"]["holdings"]
    }
    baseline = {
        holding["name"]: holding["weight_pct"]
        for holding in context["portfolio"]["holdings"]
    }
    rows = []
    for profile in context["company_profiles"]:
        name = profile["name"]
        analyst = profile["analyst_context"]
        rows.append(
            {
                "name": name,
                "ticker": profile["ticker"],
                "weight_pct": current.get(name, baseline.get(name)),
                "weight_basis": "2026-06-30" if name in current else "2025-12-31",
                "business": analyst["business_summary"],
                "channels": [
                    channel["channel"] for channel in analyst["frontier_ai_channels"]
                ],
            }
        )
    return rows


def roster_block(rows: list[dict]) -> str:
    """Stable cached prefix. Keep this byte-identical across calls."""
    lines = [
        "ROSTER — BIT Global Technology Leaders.",
        "`weight` is position size in the fund. `basis` is the disclosure date:",
        "2026-06-30 is the current factsheet top ten; 2025-12-31 is the last",
        "complete audited portfolio and is not confirmed current.",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row['name']} ({row['ticker']}) — {row['weight_pct']}% "
            f"[basis {row['weight_basis']}]"
        )
        lines.append(f"  business: {row['business']}")
        lines.append(f"  known AI channels: {'; '.join(row['channels'])}")
    return "\n".join(lines)


def development_block(packet: dict) -> str:
    lines = [
        f"DEVELOPMENT — {packet['day']} — event {packet['event_id'][:16]}",
        "",
    ]
    for source in packet["sources"]:
        who = source.get("author") or source.get("title") or ""
        lines.append(f"[{source['relation']}] {who} {source.get('posted') or ''}".strip())
        lines.append(source.get("text") or "")
        if source.get("url"):
            lines.append(source["url"])
        lines.append("")
    return "\n".join(lines)


def gated_candidates(day: str) -> tuple[str, list[dict]]:
    """Only developments the routing gate already passed for Investment."""
    db = sqlite3.connect(f"file:{EDITORIAL_DB}?mode=ro", uri=True)
    run_id = db.execute(
        "SELECT run_id FROM editorial_run WHERE day=? AND status='complete' "
        "ORDER BY created_at DESC LIMIT 1",
        (day,),
    ).fetchone()[0]
    rows = db.execute(
        "SELECT event_id, feed_rank, packet_json, investment_reason "
        "FROM editorial_candidate WHERE run_id=? AND investment_relevant=1 "
        "ORDER BY feed_rank",
        (run_id,),
    ).fetchall()
    db.close()
    return run_id, [
        {
            "event_id": row[0],
            "feed_rank": row[1],
            "packet": json.loads(row[2]),
            "gate_reason": row[3],
        }
        for row in rows
    ]


def call_one(client, prefix: str, item: dict) -> dict:
    request = {
        "model": MODEL,
        "instructions": INSTRUCTIONS,
        "input": prefix + "\n\n" + development_block(item["packet"]),
        "prompt_cache_key": CACHE_KEY,
        **llm_responses.litellm_prompt_cache_kwargs(MODEL),
        "reasoning": {"effort": EFFORT},
        "max_output_tokens": 16000,
        "text": {"format": OUTPUT_FORMAT},
        "store": False,
        "extra_headers": {"x-litellm-tags": "fli,fanout-probe"},
    }
    started = time.time()
    raw = client.responses.with_raw_response.create(**request)
    data = llm_responses.as_dict(raw.parse())
    payload = json.loads(llm_responses.output_text(data))
    usage = data.get("usage") or {}
    return {
        "event_id": item["event_id"],
        "feed_rank": item["feed_rank"],
        "gate_reason": item["gate_reason"],
        "verdicts": payload["verdicts"],
        "input_tokens": usage.get("input_tokens"),
        "cached_tokens": (usage.get("input_tokens_details") or {}).get("cached_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cost_usd": llm_responses.reported_cost(raw.headers),
        "seconds": round(time.time() - started, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default="2026-07-21")
    parser.add_argument("--limit", type=int, default=0, help="0 runs every candidate")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    rows = roster()
    prefix = roster_block(rows)
    run_id, items = gated_candidates(args.day)
    if args.limit:
        items = items[: args.limit]

    print(f"day={args.day} run={run_id}")
    print(f"roster={len(rows)} companies  developments={len(items)}")
    print(f"cached prefix ~{len(prefix)} chars\n")

    client = create_litellm_client()
    results: list[dict] = []
    failures: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        pending = {pool.submit(call_one, client, prefix, item): item for item in items}
        for index, future in enumerate(futures.as_completed(pending), 1):
            item = pending[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                failures.append({"event_id": item["event_id"], "error": repr(exc)})
                print(f"  [{index}/{len(items)}] FAIL {item['event_id'][:12]} {exc}")
                continue
            results.append(result)
            hits = sum(1 for verdict in result["verdicts"] if verdict["affected"])
            print(
                f"  [{index}/{len(items)}] rank {result['feed_rank']:>3}  "
                f"{hits:>2}/{len(result['verdicts'])} affected  "
                f"cached={result['cached_tokens']}  {result['seconds']}s"
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"fanout-{args.day}.json"
    out_path.write_text(
        json.dumps(
            {
                "day": args.day,
                "run_id": run_id,
                "model": MODEL,
                "effort": EFFORT,
                "prompt_version": PROMPT_VERSION,
                "roster": rows,
                "results": results,
                "failures": failures,
            },
            indent=1,
        )
        + "\n"
    )
    cost = sum(result["cost_usd"] or 0 for result in results)
    cached = sum(result["cached_tokens"] or 0 for result in results)
    supplied = sum(result["input_tokens"] or 0 for result in results)
    print(f"\nwrote {out_path}")
    print(f"ok={len(results)} failed={len(failures)}")
    print(f"cost=${cost:.4f}  cache_hit={100 * cached / supplied if supplied else 0:.1f}%")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
