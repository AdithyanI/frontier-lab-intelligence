# BIT Capital Case Study — Implementation Tracker

Implementation repo for the "Frontier Lab Intelligence" take-home case study
from BIT Capital (sent by Lars, 2026-07-07). This is the code/build repo; the
career/control-plane tracker stays at
`~/GitHub/adi/projects/bit-capital-case-study-2026/tasks.md`.

## Prompt
Full verbatim prompt: `docs/references/case-prompt.md`.
Original PDF + extracted text: `docs/references/source-material/`.

- **Deadline:** 2026-07-20 (confirm with Lars; see career tracker for reply status).
- **Deliverable:** working system (register, ingestion, extraction, scoring,
  reports + alerts for two personas, small web UI) + code + DB + write-ups.
- **Weighted rubric:** registry 20% · signal-vs-noise 20% · scoring/validation
  20% · actionable delivery 15% · ingestion 10% · extraction 10% · web UI 5%.

## Status
- [x] Repo scaffolded from the agent-native template (2026-07-07).
- [x] Case prompt + source material copied in verbatim.
- [ ] Stack decision (Python core; SQLite/Postgres; scheduling approach).
- [ ] Design pass on top-3 weighted areas: registry schema + entity
      resolution, signal/noise filtering concept, scoring model + validation plan.
- [ ] Ingestion pipeline (multi-source, scheduled, dedup, rate-limited).
- [ ] Extraction into structured, cited insights.
- [ ] Scoring/rating model with documented validation approach.
- [ ] Reports (in-app + PDF export) + alerts (Slack/email), persona-tailored.
- [ ] Minimal web interface.
- [ ] Evaluation write-up (extraction quality, hallucination control, scoring
      validation, ground-truth approach).
- [ ] Tokenomics write-up (token usage + $ cost per workflow).
- [ ] Final report (what works, what's next, learnings, 3–5 real insights).
- [ ] Working-log of AI-tool usage + €100 budget receipts.
- [ ] Self-review against every explicit prompt requirement.
- [ ] Submission package prepared for Adi's review (no external send from here).

## Proof of Work
Before handoff, record:

- Commands run:
- Results:
- Files/artifacts reviewed:
- Known limitations:
- Prompt requirements satisfied:
- Prompt requirements not satisfied / blocked:
- Submission package path:

## Decisions
- 2026-07-07 — Scaffolded as a separate repo per the agent-native template
  rule (runnable code, DB, web UI, and evals are explicitly required by the
  prompt). Career-tracker project in `~/GitHub/adi` stays the control-plane
  record and the source of the original prompt capture.
