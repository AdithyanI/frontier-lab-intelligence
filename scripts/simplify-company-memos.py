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
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "docs" / "references" / "archive" / "company-memos-full"
OUTPUT = REPO_ROOT / "docs" / "references" / "company-memos.json"

SCHEMA_VERSION = "company-memos-v2"
MAX_WATCHPOINTS = 2

def _bets(ticker: str, memo: dict[str, Any]) -> list[dict[str, Any]]:
    bets = []
    paths = memo.get("frontier_ai_transmission_paths") or []
    for index, path in enumerate(paths, start=1):
        bets.append(
            {
                "id": f"{ticker}-B{index}",
                "if": path["development"],
                "exposure": path["company_exposure"],
                "then": path["financial_consequence"],
                "material_when": path["materiality_condition"],
                "watch": list(path.get("watchpoints") or [])[:MAX_WATCHPOINTS],
                "direction": path["direction"],
                "sources": path.get("sources") or [],
            }
        )
    return bets


def build() -> dict[str, Any]:
    paths = sorted(SOURCE_DIR.glob("*.json"))
    if not paths:
        raise SystemExit(f"No memos found in {SOURCE_DIR}")

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
            "bets": _bets(ticker, memo),
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
