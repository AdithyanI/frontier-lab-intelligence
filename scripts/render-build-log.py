#!/usr/bin/env python3
"""Render docs/references/build-log.md from docs/references/build-log.jsonl.

The JSONL file is the source of truth for the Build Timeline: agents append
one JSON object per entry and never hand-edit the table (hand-edited markdown
tables kept breaking on GitHub). Everything outside the timeline section
(intro, learning notes, budget log) is preserved from the existing markdown.

Idempotent: only writes the file when the rendered output differs.
Exit code 0 always (rendering is a build step, not a check).

Entry fields: date, title, intent, action, evidence, impact_next, tools_spend.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JSONL = REPO_ROOT / "docs/references/build-log.jsonl"
MD = REPO_ROOT / "docs/references/build-log.md"

BEGIN = "<!-- BEGIN GENERATED: build timeline (edit build-log.jsonl, then run scripts/render-build-log.py) -->"
END = "<!-- END GENERATED -->"

REQUIRED = ("date", "title", "intent", "action", "evidence", "impact_next", "tools_spend")


def cell(value: str) -> str:
    """Make a value safe inside a markdown table cell."""
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_timeline(entries: list[dict]) -> str:
    lines = [
        BEGIN,
        "",
        "| Date | Intent / trigger | Decision / action | Evidence | Impact / next | Tools / spend |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for e in entries:
        lines.append(
            "| "
            + " | ".join(
                cell(e[k])
                for k in ("date", "intent", "action", "evidence", "impact_next", "tools_spend")
            )
            + " |"
        )
    lines += ["", END]
    return "\n".join(lines)


def main() -> int:
    entries = []
    for i, line in enumerate(JSONL.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"build-log.jsonl line {i}: invalid JSON ({exc})", file=sys.stderr)
            return 1
        missing = [k for k in REQUIRED if not entry.get(k)]
        if missing:
            print(f"build-log.jsonl line {i}: missing fields {missing}", file=sys.stderr)
            return 1
        entries.append(entry)

    entries.sort(key=lambda e: e["date"])

    text = MD.read_text()
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        new_text = head + render_timeline(entries) + tail
    else:
        # First run: replace everything between the timeline heading and the
        # next section with the generated block.
        heading = "## Build Timeline"
        next_section = "## Learning Notes"
        head, rest = text.split(heading, 1)
        _, tail = rest.split(next_section, 1)
        new_text = (
            head + heading + "\n\n" + render_timeline(entries) + "\n\n" + next_section + tail
        )

    if new_text != text:
        MD.write_text(new_text)
        print(f"render-build-log: regenerated ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
