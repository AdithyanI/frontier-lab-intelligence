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
   implemented. The cleaned Registry contains 2,220 observed identities: 2,104
   active people, 93 active organizations, and 23 reversible rejections with
   explicit reasons. Open an entity to inspect its observed profile,
   classification reason, and channels. Exact rules live in
   `docs/references/registry-curation.md`.
2. **Signal-vs-noise (20%)** — filtering logic and the judgment calls behind
   it, plus the fresh trusted-follow ranking. The accepted overlap run covers
   2,456,305 edges and 460,927 discovered accounts; PageRank remains a measured
   diagnostic. See the Ranking page and `docs/architecture/overview.md`.
3. **Scoring + validation (20%)** — the scoring model and how it was
   validated against ground truth/human judgment; avoid "arbitrary weighted
   sum" — the write-up should defend the model directly.
4. **Actionable delivery (15%)** — reports (in-app + PDF) and alerts, tailored
   per persona (investment team vs. AI team), with citations.
5. **Ingestion (10%)** and **extraction (10%)** — scheduled multi-source
   ingestion, dedup, and structured/cited extraction.
6. **Web interface (5%)** — minimal browse/config UI, not over-polished.

## Evidence to check

- `data/fli.db` — inspectable SQLite database with real source, entity, channel,
  observation, raw-item, classifier provenance, and reason-bearing Registry
  rejection tables. The fresh following graph is isolated in its immutable
  snapshot rather than copied into this database.
- `docs/references/registry-evaluation.md` — exact evaluator modules, commands,
  storage boundaries, resumability, artifact checksums, and invariants.
- `docs/architecture/overview.md` — current system shape and implemented schema.
- `docs/references/registry-curation.md` — identity/kind/curation boundaries,
  model contract, evaluation outcome, usage, and cost.
- `docs/references/build-log.md` — build history, AI tool usage, learning
  notes, cache behavior, and spend telemetry.
- `docs/projects/archive/` — completed phase trackers and reusable learnings.

## Known limitations

- Structural kind, Registry admission, and channel collectability are separate
  decisions. The v3 evaluator is implemented and resumable, but its ignored
  raw run artifacts currently exist only on the development machine.
- The graph and Ranking page work, but the central product thesis is still
  unproven: ranked active/discovered sources have not yet been compared on
  useful intelligence yield.
- Raw blog, arXiv, and GitHub items exist, but entity-linked deduplication,
  cited insight extraction, scoring validation, reports, and alerts remain.
- The final report, workflow-level tokenomics summary, and submission package
  are not complete yet.
