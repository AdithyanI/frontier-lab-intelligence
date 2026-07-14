# Canonical Artifact Library

## Goal

Build and close a small, replayable Artifact Store v1 that turns links found in
corrected kept X envelopes into one deduplicated, fetchable record per
underlying paper, blog post, repository, announcement, or other primary page;
preserve exactly which X posts pointed to it and store reusable raw and clean
text snapshots.

## Why / Impact

The Feed currently knows what the network discussed, and raw X records already
preserve post permalinks plus most expanded outbound URLs. Cited insights need
the next boundary: fetch an underlying primary source once, cite it reliably,
and reuse it when several posts point to the same thing. If this is modeled
incorrectly, every short link becomes a duplicate, event regrouping can lose
provenance, and later source adapters would require a replacement schema.

## Scope / Non-Goals

### In Scope

- An X-first canonical artifact catalog under
  `data/derived/artifacts/artifacts.db`.
- Deterministic URL extraction, expansion, conservative canonicalization, and
  alias preservation for URLs already present in stored X records.
- Independently traceable mappings from an X post to an artifact.
- Resumable HTTP fetch metadata plus content-addressed snapshots for selected
  artifacts.
- A bounded real-data fetch/extraction cohort selected from the highest-
  attention kept envelopes, expanded only after manual quality review.
- A source-aware contract that can accept another source kind later without
  changing artifact identity.

### Out of Scope

- RSS, GitHub, arXiv, or blog ingestion in this project’s first implementation.
- A generic connector framework or premature adapter abstraction.
- An artifact-library UI or separate artifact Feed.
- Broad crawling, web search, or automatically fetching every URL in the
  stored X corpus before the bounded cohort is audited.
- LLM categorization, insight generation, or semantic duplicate merging.
- Treating every ordinary X status permalink as an artifact.
- Cited-insight generation, an Insights API/page, reports, alerts, or persona
  implications. Those remain in the separate `cited-insights` project.

## Context / Constraints

- Date started: 2026-07-13.
- The prerequisite `temporal-event-projection` project completed and archived
  on 2026-07-14. Its corrected recursive relations and snapshot-bound kept
  envelopes are now the trusted import boundary for this project.
- Raw X evidence remains immutable in `data/raw/x/x-content.db`.
- Ordinary X status URLs already live on `x_post.url`; the derived Feed also
  carries them on `feed_post.url`, and triage runs freeze the root URL. These
  are source-evidence addresses, not artifact identities.
- Outbound links already live in `x_post.raw_json` under
  `entities.urls[]`, usually with both the observed `t.co` URL and
  `expanded_url`.
- An X long-form article may be a real artifact. A quote, reply, retweet, media
  self-link, profile URL, or ordinary status permalink remains source context.
- The first future consumer is `cited-insights`, but this project ends at a
  trustworthy artifact/read-text boundary. Submission scope remains a narrow
  X-first proof, not multi-source breadth.
- See [data-model.md](resources/data-model.md) for the frozen logical boundary
  proposed for Milestone 1.

## Done When

- [x] A canonical URL maps to exactly one artifact and every observed alias is
  retained.
- [x] Multiple X posts pointing to the same page create multiple source
  observations but only one artifact and one reusable fetched snapshot.
- [x] An ordinary X status permalink remains source evidence rather than a
  duplicate artifact; an X long-form article is handled explicitly.
- [x] Event merges/splits do not duplicate or orphan artifacts because source
  observations bind to stable post IDs, not mutable envelope IDs.
- [x] Import and fetch operations are idempotent, resumable, and preserve
  failures without corrupting accepted rows.
- [x] A manually audited real-data cohort has reproducible title and clean-text
  extraction, or a truthful terminal fetch/extraction error, and every record
  links back to all discovering source posts.
- [x] All locally resolvable candidates from corrected kept envelopes can be
  indexed without fetching them; a bounded high-attention cohort can be
  fetched resumably without duplicate network work.
- [x] Schema, canonicalization, idempotency, provenance, and fetch-failure
  tests pass; `scripts/check-fast.sh` passes; architecture and build log are
  updated.

## Milestones

- [x] M1 — Freeze the X-first artifact contract from real corrected URLs.
  Acceptance: table boundaries, identity rules, alias rules, X-status
  exception, fetch policy, snapshot paths, and at least 20 representative URL
  fixtures are reviewed. Validate: corpus/fixture audit plus schema tests.
- [x] M2 — Implement the local catalog and deterministic importer. Acceptance:
  all eligible kept-envelope URLs index without network access, repeated import
  is byte-stable at the logical row level, duplicate aliases converge, and
  observations retain stable X provenance. Validate: focused pytest suite,
  replay, and SQLite integrity/foreign-key checks.
- [x] M3 — Fetch, snapshot, and clean a bounded real-data cohort. Acceptance:
  selected primary artifacts have successful content-addressed raw/text
  snapshots or explicit terminal errors; titles, clean text, hashes, retries,
  and request telemetry are reproducible. Validate: replay without duplicate
  network work plus stratified manual artifact inspection.
- [x] M4 — Harden and close Artifact Store v1. Acceptance: inspection CLI/API
  contracts, query indexes, architecture, operational reference, limitations,
  build log, and project learnings are current. Validate:
  `scripts/check-fast.sh`, database audit, and archive the tracker.

## Execution Rules

- Keep the first implementation X-first. “Future RSS/GitHub” is a schema
  compatibility test, not authorization to build those ingestors now.
- Treat raw provider records as immutable and derived catalog rows as safely
  rebuildable.
- Do URL identity work deterministically; do not use an LLM to canonicalize a
  URL.
- Remove only known tracking parameters. Do not erase meaningful query
  parameters to make two URLs look equal.
- Do not auto-merge different canonical URLs solely because their current
  content hashes match; record a possible duplicate for later review.
- Bind provenance to a stable source kind/provider/external ID. Derive an
  event-to-artifact view through event membership; never make an envelope the
  artifact owner.
- Index every locally resolvable eligible link, but fetch only a bounded
  high-attention cohort first. Expand only after the first cohort's extraction
  quality and failure modes are reviewed. Cost is telemetry, not a quality gate.
- Run validation after each milestone, update this tracker after meaningful
  batches, and archive it when Done When is satisfied.

## Decisions

- 2026-07-13: X is the only ingestion source implemented first. The schema
  carries `source_kind` so a later RSS entry or GitHub release can use the same
  observation boundary, but no generic adapter framework is built now.
- 2026-07-13: Separate **source evidence** from **artifacts**. An X post is a
  source record addressed by its status permalink; an outbound primary page is
  an artifact. X long-form articles are the explicit exception.
- 2026-07-13: Artifact identity is the conservative canonical URL. Original,
  short, expanded, redirected, and declared-canonical URLs remain aliases so
  every transformation is auditable.
- 2026-07-13: Source observations are post-owned, not envelope-owned. Corrected
  daily/weekly envelopes may project artifact associations without changing
  the underlying catalog.
- 2026-07-13: The first physical store is
  `data/derived/artifacts/artifacts.db`; raw fetched bodies are
  content-addressed outside catalog rows, with their hashes and storage
  references recorded in the database.
- 2026-07-13: Tags are a separate optional relation added only when a concrete
  consumer needs them; category is not baked into artifact identity.
- 2026-07-14: Index every locally resolvable eligible URL, but stop the v1 fetch
  proof at one frozen 30-artifact cohort. Its 19/19 successful clean texts were
  usable; expanding across 642 hosts before a cited consumer proves demand
  would be crawler breadth rather than submission progress.
- 2026-07-14: Treat client-rendered loading/error shells as terminal extraction
  failures. A response body and title are preserved for audit, but no clean
  text snapshot is published.
- 2026-07-14: Report network attempts separately from per-artifact outcomes.
  Retryables reopen the same frozen run up to three attempts; success and
  terminal outcomes never repeat.

## Open Questions / Blockers

- None. Snapshot-path and extraction-library choices are part of the active M1
  evidence audit and must be frozen before implementation.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| completed | Freeze Artifact Store v1 around catalog-all / fetch-bounded behavior, excluding cited insights and UI. | parent | [data-model.md](resources/data-model.md) |
| completed | Audit the real kept-envelope URL corpus, domain/type distribution, exclusions, duplicate patterns, and representative fixtures. | explorer | `resources/url-corpus-audit-2026-07-14.md` |
| completed | Audit available extraction dependencies and implement deterministic HTML/PDF/text snapshots with bounded failures. | explorer | `resources/content-extraction-review-2026-07-14.md` |
| completed | Adversarially review schema, canonicalization, idempotency, source provenance, fetch replay, and future-source compatibility. | explorer | `resources/artifact-model-adversarial-review-2026-07-14.md` |
| completed | Rebuild, fetch, retry, and manually audit the frozen 30-artifact cohort. | parent | `resources/fetch-cohort-audit-2026-07-14.md` |

## Backlog / Remaining Work

- [x] Accept the archived `temporal-event-projection` adversarial proof and its
  corrected kept-envelope inputs as the M1 source boundary.
- [x] Freeze real URL fixtures, snapshot paths, fetch policy, and extraction
  library choices from the active audits.
- [x] Implement schema migrations, catalog queries, deterministic import, and
  non-interactive inspection commands.
- [x] Implement bounded fetch/raw snapshot/clean-text/replay behavior.
- [x] Import every eligible link from corrected kept envelopes; fetch and
  manually audit the bounded high-attention cohort before deciding whether to
  expand.
- [x] Update `docs/architecture/overview.md` when the runtime boundary lands.
- [x] Defer RSS/GitHub/blog adapters and an artifact Feed UI until the X-first
  cited path proves useful yield.
- [x] Review project learnings and archive the tracker after closeout.

## Validation / Test Plan

- Focused unit fixtures: `t.co` alias, direct HTTPS URL, redirect chain,
  tracking parameters, fragments, arXiv abs/pdf normalization, GitHub release
  URL, X long-form article, ordinary X status permalink, media self-link, and
  repeated observation.
- Integration: two posts with different observed aliases resolve to one
  artifact and two observations; a rebuilt/merged event still resolves both.
- Replay: a second identical import performs no duplicate writes or fetches.
- SQLite: `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, and unique-index
  assertions.
- Repository gate: `scripts/check-fast.sh`.

## Progress Log

- 2026-07-13: [DONE] Created the project and froze an intentionally narrow
  X-first/source-aware boundary; no runtime code, database, network fetch, RSS,
  or GitHub ingestion was implemented.
- 2026-07-14: [UNBLOCKED] The temporal projection repair completed with nine
  deterministic days, zero structural audit failures, and snapshot-bound
  triage. Representative URL fixture work can now begin from corrected kept
  envelopes.
- 2026-07-14: [IN-PROGRESS] Adi authorized the full Artifact Store v1 execution
  as a long-running goal. Re-scoped the project to stop at canonical artifacts,
  fetch snapshots, titles, and clean text; cited insights and UI remain a later
  project. The execution doctrine is catalog all locally resolvable eligible
  links, fetch a bounded high-attention cohort first, audit real failures, then
  expand only when justified.
- 2026-07-14: [DONE] Implemented and cleanly replayed Artifact Store v1. The
  importer evaluated 3,072 URL candidates, accepted 2,911 occurrences, retained
  161 reason-bearing exclusions, and produced 1,739 independently traceable
  source observations/disclosures. Redirect convergence left 1,566 canonical
  artifacts. The frozen 30-artifact fetch run completed with 19 usable
  clean-text snapshots, four explicit terminal failures, and seven retryable
  failures exhausted after three attempts. Import replay and a fourth fetch
  replay performed no duplicate work; SQLite integrity and foreign keys pass.
  The operational reference, architecture, query indexes, stable JSON CLI,
  tests, and manual cohort audit are current. RSS/GitHub ingestion, artifact UI,
  and cited insight generation remain deliberately deferred.
