# Reviewer Guide

How to inspect the current case-study system. This guide describes implemented
behavior; unfinished deliverables are listed explicitly below.

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
1. **Registry (20%)** — the entity/channel spine and structural-kind pass are
   implemented. The Registry contains 2,966 observed identities: 2,639 people,
   182 organizations, and 145 explicit abstentions. Open an entity to inspect
   its observed profile and classification reason. Exact rules live in
   `docs/references/registry-curation.md`.
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

- `data/fli.db` — inspectable SQLite database with real graph, entity, channel,
  observation, raw-item, and classifier provenance tables.
- `docs/architecture/overview.md` — current system shape and implemented schema.
- `docs/references/registry-curation.md` — identity/kind/curation boundaries,
  model contract, evaluation outcome, usage, and cost.
- `docs/references/build-log.md` — build history, AI tool usage, learning
  notes, and €100 budget receipts.
- `docs/projects/archive/` — completed phase trackers and reusable learnings.

## Known limitations

- Structural kind is not tracking relevance; graph-based relevance curation is
  the next registry step.
- Raw blog, arXiv, and GitHub items exist, but entity-linked deduplication,
  cited insight extraction, scoring validation, reports, and alerts remain.
- The final report, workflow-level tokenomics summary, and submission package
  are not complete yet.
