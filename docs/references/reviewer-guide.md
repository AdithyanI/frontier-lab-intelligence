# Reviewer Guide

How to inspect the current case-study system. This guide describes implemented
behavior; unfinished deliverables are listed explicitly below.

## Quick start
```bash
python3.13 -m venv .venv
. .venv/bin/activate
.venv/bin/pip install -e '.[dev]'
scripts/check-fast.sh
fli web
```

Then open `http://127.0.0.1:8797`. The tracked build is served by the Python
app; no separate frontend server is required. Data-collection and model calls
are explicit, resumable commands and are not part of the reviewer quick start.

## What to look at, in weighted order
1. **Registry (20%)** — the entity/channel spine and structural-kind pass are
   implemented. The cleaned Registry contains 2,220 observed identities: 2,104
   active people, 93 active organizations, and 23 reversible rejections with
   explicit reasons. Open an entity to inspect its observed profile,
   classification reason, and channels. Exact rules live in
   `docs/references/registry-curation.md`.
2. **Signal-vs-noise (20%)** — inspect the immutable following snapshot,
   entity-overlap ranking, exact event grouping, Feed daily-score inputs, and
   keep/drop decisions. The accepted overlap run covers 2,456,305 edges;
   PageRank remains a measured diagnostic. Triage evaluated 8,097 envelopes
   with reason-bearing decisions, but downstream insight quality remains the
   submission-critical test.
3. **Scoring + validation (20%)** — the daily score is an explainable candidate
   ordering aid, not importance or truth. The missing proof is whether primary-cited extracted
   insights survive citation checks and human worth-attention judgment.
4. **Actionable delivery (15%)** — the Insights surface, daily briefing, and
   local alert/outbox proof are the active missing delivery boundary. No
   external alert or submission is performed by the demo.
5. **Ingestion (10%)** and **extraction (10%)** — X discovery, immutable raw
   evidence, exact deduplication, triage, canonical artifact identity, and a
   bounded content-fetch proof exist. Cited insight extraction is not yet
   implemented; broad scheduled multi-source ingestion is deliberately
   deferred.
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
- `docs/STATUS.md` — current conceptual handoff, critical unproven claim, and
  submission finish line.
- `docs/projects/archive/` — completed phase trackers and reusable learnings.

## Known limitations

- X is the only implemented discovery source; missing activity that the
  tracked network never exposes is outside current recall.
- Exact event grouping intentionally uses provider-declared relations. It does
  not attempt semantic clustering of separately worded posts about one event.
- The artifact fetcher records access failures rather than bypassing robots,
  authentication, or publisher controls. Only inspectable primary evidence can
  support a shipped primary-cited insight.
- The five-record extraction oracle, second-day blind pass, Insights surface,
  daily briefing, local alert/outbox proof, workflow tokenomics summary, public
  reviewer landing page, final report, and package smoke path remain.
