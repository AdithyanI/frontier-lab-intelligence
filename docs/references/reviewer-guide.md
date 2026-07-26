# Reviewer Guide

How to inspect the current case-study system. This guide describes implemented
behavior and the intentionally bounded release.

## Open the live product

[Open Frontier Lab Intelligence](https://frontier-lab-intelligence.adithyan.io/).
This is the primary reviewer experience and requires no local setup. The live
[How it works](https://frontier-lab-intelligence.adithyan.io/how)
view maps the assignment to a five-step inspection path. The
[Architecture view](https://frontier-lab-intelligence.adithyan.io/system/architecture)
provides the deeper technical map.

## Reproduce it locally

```bash
./demo.command
```

The command verifies and restores the frozen reviewer data, installs the local
app, opens `http://127.0.0.1:8797`, and enforces read-only mode. It needs Python
3.13 and an internet connection on the first run, but no API keys. No separate
frontend server is required. See [`demo-release.md`](demo-release.md) for the
exact object, checksum, included data, and clean-checkout proof.

## What to look at, in weighted order
1. **Registry (20%)** — inspect the entity/channel spine, reversible admission
   state, Network-support position, public-reach position, and reason-bearing
   manual intake. The dated checkpoint totals and graph coverage live in
   `docs/STATUS.md`; the UI and `/api/registry` are the live read contract.
2. **Signal-vs-noise (20%)** — start in Network Ranking, then open Feed. Each
   row is one stable Event, not one raw post. Provider-declared relations form
   exact structural Events; independent posts are never merged by topic. Open
   the rank disclosure to inspect the complete-Event voter union, voter-network
   position, source-author position, same-day public-interaction tiebreak, and
   limitations. The four evidence layers are applied in order, not blended.
3. **Scoring + validation (20%)** — change Feed Status to compare Relevant,
   Not relevant, and Not evaluated Events. Open `View reasons` to inspect the
   independent AI Engineering and Investment judgments. Ranking is an
   ordering aid; routing and final editorial selection are separate decisions.
4. **Actionable delivery (15%)** — inspect both audience views in Insights.
   Imported days show the newest complete, ranked, cited daily editorial run.
   Each supporting source links back to the exact Feed Event; artifact
   citations retain their frozen text provenance. Candidate-level Suppressed
   and All views remain an audit fallback, not the final daily product. The
   top-right actions download the selected audience PDF or show delivery
   options. Slack and email are real operator actions. Inspect the delivery
   flow, but do not confirm a send during passive review.
5. **Ingestion (10%)** and **extraction (10%)** — inspect Artifacts for
   canonical source links disclosed by first-party Event evidence, retrieval
   state, normalized text snapshots, and the exact originating Event. X is the
   implemented discovery source; artifacts add papers, repositories, articles,
   documents, and videos without pretending they are independent discovery.
6. **Web interface (5%)** — use How it works for the complete reviewer path,
   System → Architecture for the actual dependency order, and System → Status
   for the checkpoint composed from live product APIs. There is
   deliberately no second static backend status model.

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
- `docs/references/demo-release.md` — immutable snapshot, checksum, exclusions,
  read-only boundary, and reproduction proof.
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
- The final five submission Insights were human-adjudicated and locked. They
  are a proof set, not an unbiased estimate of unattended editorial precision.
  Opening the application does not trigger Registry intake or delivery; both
  remain explicit operator actions.
