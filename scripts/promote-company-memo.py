"""Promote an audited company-memo pilot result into the durable UI packet."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DESTINATION_ROOT = ROOT / "docs" / "references" / "company-memos"
SCHEMA_VERSION = "company-memo-pilot-result-v1"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path} is not a {SCHEMA_VERSION} result")
    company = payload.get("company")
    memo = payload.get("memo")
    provenance = payload.get("provenance")
    if not isinstance(company, dict) or not isinstance(memo, dict):
        raise ValueError(f"{path} is missing company or memo")
    if not isinstance(provenance, dict):
        raise ValueError(f"{path} is missing provenance")
    ticker = company.get("ticker")
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError(f"{path} is missing a ticker")
    ledger = memo.get("source_ledger")
    if not isinstance(ledger, list) or not ledger:
        raise ValueError(f"{path} is missing a source ledger")
    urls = {item.get("url") for item in ledger if isinstance(item, dict)}
    if None in urls or any(not str(url).startswith("https://") for url in urls):
        raise ValueError(f"{path} contains an invalid source-ledger URL")
    return payload


def promote(path: Path) -> Path:
    payload = _load(path)
    ticker = str(payload["company"]["ticker"]).upper()
    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)
    destination = DESTINATION_ROOT / f"{ticker}.json"
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=DESTINATION_ROOT,
        prefix=f".{ticker}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(rendered)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+", type=Path)
    args = parser.parse_args()
    for result in args.results:
        print(promote(result.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
