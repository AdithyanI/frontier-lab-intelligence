# Reviewer Guide

How to inspect this case study submission. Fill in as the build progresses.

## Quick start
```bash
# TODO once stack is chosen: setup, install, run instructions
```

## What to look at, in weighted order
1. **Registry (20%)** — `docs/references/solution-architecture.md` §Registry;
   `src/bit_case_study/schema.py` and seed data under `data/`.
2. **Signal-vs-noise (20%)** — filtering logic and the judgment calls behind
   it; see `docs/references/solution-architecture.md` §Signal-vs-noise.
3. **Scoring + validation (20%)** — the scoring model and how it was
   validated against ground truth/human judgment; avoid "arbitrary weighted
   sum" — the write-up should defend the model directly.
4. **Actionable delivery (15%)** — reports (in-app + PDF) and alerts, tailored
   per persona (investment team vs. AI team), with citations.
5. **Ingestion (10%)** and **extraction (10%)** — scheduled multi-source
   ingestion, dedup, and structured/cited extraction.
6. **Web interface (5%)** — minimal browse/config UI, not over-polished.

## Evidence to check
- `docs/references/final-report.md` — what works, what's next, learnings,
  and the 3–5 most interesting real insights the system surfaced.
- `docs/references/tokenomics.md` — token usage and $ cost per workflow.
- Evaluation write-up — extraction quality, hallucination control, scoring
  validation, ground-truth approach.
- Working-log — AI tool usage and €100 budget receipts.

## Known limitations
- TODO — populate before submission.
