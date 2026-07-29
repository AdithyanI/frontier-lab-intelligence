#!/usr/bin/env python3
"""Rebuild the consolidated company-memo corpus from the archived full memos.

The full memos carried eight sections; only two ever reached a reader. This
script keeps the company summary and the standing bets, precomputes the size
magnitudes that used to be extracted from the dropped sections, and archives
the originals unchanged.

Idempotent:  .venv/bin/python scripts/simplify-company-memos.py
"""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "docs" / "references" / "archive" / "company-memos-full"
OUTPUT = REPO_ROOT / "docs" / "references" / "company-memos.json"
DIRECTION_LEDGER = (
    REPO_ROOT / "docs" / "references" / "company-bet-directions.json"
)

SCHEMA_VERSION = "company-memos-v3"
DIRECTION_LEDGER_SCHEMA_VERSION = "company-bet-directions-v1"
MAX_WATCHPOINTS = 2


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _source_records(paths: list[Path]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        ticker = str(raw["company"]["ticker"])
        for index, item in enumerate(
            raw["memo"].get("frontier_ai_transmission_paths") or [],
            start=1,
        ):
            records.append(
                {
                    "bet_id": f"{ticker}-B{index}",
                    "ticker": ticker,
                    "if": str(item["development"]),
                    "exposure": str(item["company_exposure"]),
                    "then": str(item["financial_consequence"]),
                    "threshold": str(item["materiality_condition"]),
                }
            )
    return records


def _directions(paths: list[Path]) -> dict[str, str]:
    if not DIRECTION_LEDGER.is_file():
        raise SystemExit(
            "Missing binary direction ledger. Run "
            "scripts/classify-company-bet-directions.py first."
        )
    payload = json.loads(DIRECTION_LEDGER.read_text(encoding="utf-8"))
    if payload.get("schema_version") != DIRECTION_LEDGER_SCHEMA_VERSION:
        raise SystemExit("Unsupported company bet direction ledger")
    records = _source_records(paths)
    source_sha256 = _sha256(records)
    if payload.get("source_sha256") != source_sha256:
        raise SystemExit(
            "The direction ledger does not match the archived memo source. "
            "Re-run scripts/classify-company-bet-directions.py."
        )
    classifications = payload.get("classifications")
    if not isinstance(classifications, dict):
        raise SystemExit("Direction ledger has no classifications")
    expected = {item["bet_id"] for item in records}
    if set(classifications) != expected:
        raise SystemExit("Direction ledger does not cover the exact source bet set")
    directions = {
        bet_id: str(item["direction"])
        for bet_id, item in classifications.items()
    }
    invalid = {
        bet_id: direction
        for bet_id, direction in directions.items()
        if direction not in {"upside", "downside"}
    }
    if invalid:
        raise SystemExit(f"Direction ledger contains invalid values: {invalid}")
    return directions


def _bets(
    ticker: str,
    memo: dict[str, Any],
    directions: dict[str, str],
) -> list[dict[str, Any]]:
    bets = []
    paths = memo.get("frontier_ai_transmission_paths") or []
    for index, path in enumerate(paths, start=1):
        bet_id = f"{ticker}-B{index}"
        bets.append(
            {
                "id": bet_id,
                "direction": directions[bet_id],
                "if": path["development"],
                "exposure": path["company_exposure"],
                "then": path["financial_consequence"],
                "threshold": path["materiality_condition"],
                "watch": list(path.get("watchpoints") or [])[:MAX_WATCHPOINTS],
                "sources": path.get("sources") or [],
            }
        )
    return bets


def build() -> dict[str, Any]:
    paths = sorted(SOURCE_DIR.glob("*.json"))
    if not paths:
        raise SystemExit(f"No memos found in {SOURCE_DIR}")
    directions = _directions(paths)

    companies: dict[str, Any] = {}
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        company = raw["company"]
        memo = raw["memo"]
        ticker = company["ticker"]
        if ticker in companies:
            raise SystemExit(f"Duplicate memo for {ticker}")

        business = memo["business_and_economics"]
        companies[ticker] = {
            "ticker": ticker,
            "name": company["name"],
            "summary": business["summary"],
            "summary_sources": business.get("sources") or [],
            "bets": _bets(ticker, memo, directions),
            "source_ledger": memo["source_ledger"],
            "researched_at": (raw.get("provenance") or {})["research_date"],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "company_count": len(companies),
        "bet_count": sum(len(c["bets"]) for c in companies.values()),
        "companies": companies,
    }


def main() -> int:
    payload = build()
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = sum(
        len(path.read_text(encoding="utf-8")) for path in SOURCE_DIR.glob("*.json")
    )
    after = len(OUTPUT.read_text(encoding="utf-8"))
    print(f"companies  {payload['company_count']}")
    print(f"bets       {payload['bet_count']}")
    print(f"chars      {before:,} -> {after:,} ({100 - after * 100 // before}% smaller)")
    print(f"wrote      {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
