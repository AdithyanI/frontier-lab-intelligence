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
1. **Registry (20%)** — inspect the entity/channel spine, reversible admission
   state, Network-support position, public-reach position, and reason-bearing
   manual intake. The dated checkpoint totals and graph coverage live in
   `docs/STATUS.md`; the UI and `/api/registry` are the live read contract.
2. **Signal-vs-noise (20%)** — start in Network Ranking, then open Feed. Each
   row is one stable Event, not one raw post. Provider-declared relations form
   exact structural Events; independent posts are never merged by topic. Open
   the daily-score disclosure to inspect tracked amplification,
   author-network support, public engagement, weights, and limitations.
3. **Scoring + validation (20%)** — change Feed Status to compare Relevant,
   Not relevant, and Not evaluated Events. Open `View reasons` to inspect the
   independent AI Engineering and Investment judgments. Ranking is an
   ordering aid; routing and final editorial selection are separate decisions.
4. **Actionable delivery (15%)** — inspect both audience views in Insights.
   Imported days show the newest complete, ranked, cited daily editorial run.
   Each supporting source links back to the exact Feed Event; artifact
   citations retain their frozen text provenance. Candidate-level Suppressed
   and All views remain an audit fallback, not the final daily product. The
   top-right actions download the selected audience PDF or open an explicit
   Slack/email confirmation. Those final send buttons call real configured
   providers; do not confirm a send unless you intend to notify the displayed
   destination.
5. **Ingestion (10%)** and **extraction (10%)** — inspect Artifacts for
   canonical source links disclosed by first-party Event evidence, retrieval
   state, normalized text snapshots, and the exact originating Event. X is the
   implemented discovery source; artifacts add papers, repositories, articles,
   documents, and videos without pretending they are independent discovery.
6. **Web interface (5%)** — use System → Architecture to inspect the actual
   dependency order and System → Status for the checkpoint composed from live
   product APIs. There is deliberately no second static backend status model.

## Evidence to check

- `data/fli.db` — inspectable SQLite database with real source, entity, channel,
  observation, raw-item, classifier provenance, and reason-bearing Registry
  rejection tables. The fresh following graph is isolated in its immutable
  snapshot rather than copied into this database.
- `docs/references/registry-evaluation.md` — exact evaluator modules, commands,
  storage boundaries, resumability, artifact checksums, and invariants.
- `docs/architecture/overview.md` — current system shape and implemented schema.
- `docs/references/delivery.md` — exact Slack/email behavior, configuration,
  proof, and limitations.
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
  authentication, or publisher controls. Only inspectable evidence can support
  a shipped citation.
- The daily editorial corpus is implemented, but final human adjudication of
  the strongest three to five Insights and the rubric-mapped submission package
  remain. Nothing is submitted to BIT by the demo. Manual Slack and email
  actions are live and can deliver only after an explicit final confirmation.
