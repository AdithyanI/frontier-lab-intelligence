# Reviewer Guide

How to inspect this case study submission. Fill in as the build progresses.

## Quick start
```bash
python3.13 -m venv .venv
. .venv/bin/activate
.venv/bin/pip install -e '.[dev]'
scripts/check-fast.sh
fli fetch
fli web
```

## What to look at, in weighted order
1. **Registry (20%)** — `docs/architecture/overview.md` §Pipeline and §Target Data Model Sketch;
   implementation is pending. Current evidence lives in `data/fli.db`
   (`raw_items`) and the next step is a reviewable candidate table before
   committing `fli.registry`/modeled schema code.
2. **Signal-vs-noise (20%)** — filtering logic and the judgment calls behind
   it; see `docs/architecture/overview.md` §Signal Funnel.
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
- `docs/references/build-log.md` — build history, AI tool usage, learning
  notes, and €100 budget receipts.

## Known limitations
- The modeled registry/extraction/scoring schema is not implemented yet.
- The current database is a raw evidence corpus, not the final submission DB.
- Frontend polish is intentionally deferred until real modeled output exists.
