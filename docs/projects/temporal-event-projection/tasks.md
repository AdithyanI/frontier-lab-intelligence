# Temporal Event Projection

## Goal

Make one real-world event remain one canonical envelope while daily and weekly
Feed views expose temporally correct, reproducible snapshots of that envelope.

## Why / Impact

The current exact grouping correctly assigns one stable `event_id`, but a day
view loads every member later observed in the complete materialized run. A
Monday envelope can therefore contain Tuesday-through-Saturday evidence and
look identical to the same event on Tuesday. This leaks future information,
inflates daily evidence, repeats model inputs, and makes later daily insights
hard to interpret.

The correction is foundational: daily reporting needs an as-of-day view,
weekly reporting needs one deduplicated envelope through week-end, and later
sources need a stable event identity to attach evidence to.

## Scope / Non-Goals

### In Scope

- Preserve one stable canonical event and root across all time windows.
- Repair nested provider-declared quote/retweet chains before clustering so an
  embedded quote cannot become a competing event when its canonical target is
  already present.
- Materialize or query cumulative as-of-day event snapshots.
- Surface an event on each day that receives new activity; show the canonical
  root plus evidence observed no later than that day's UTC cutoff.
- Distinguish evidence newly observed on the selected day from prior context.
- Keep the default Feed quiet: render the canonical root and selected day's
  additions, add one muted `Continued from <date>` label, and place earlier
  evidence behind a closed `Show earlier context` disclosure inside Follow.
- Preserve day-specific attention scoring while preventing future evidence
  from affecting historical presentation.
- Define a weekly projection as the same canonical event accumulated through
  week-end, with posts and Registry participants deduplicated.
- Version downstream triage inputs by event plus snapshot content hash so an
  unchanged snapshot reuses its decision and a material change remains
  auditable.
- Rebuild the seven stored days and record before/after counts and examples.

### Out of Scope

- Cited-insight extraction, primary-artifact fetching, or an Insights page.
- New RSS, blog, GitHub, arXiv, or X ingestion.
- Semantic/LLM event clustering beyond existing exact provider relationships.
- Attention-weight changes.
- Mobile/responsive UI work.

## Context / Constraints

- Date started: 2026-07-13.
- The current corpus contains seven complete UTC days, 10,552 Feed posts,
  7,563 envelope-day rows, and 6,909 unique exact events.
- 581 events appear on multiple days: 519 span two days, 54 span three, six
  span four, one spans five, and one spans six.
- Those multi-day events occupy 1,235 Feed rows. At least 655 historical rows
  currently expose evidence newer than their selected day.
- The bounded triage run contains 6,445 rows but only 5,846 unique event IDs;
  452 repeated `(event_id, input_sha256)` inputs produced zero decision
  conflicts.
- Raw X evidence and normalized Feed/Event stores remain immutable/rebuildable.
  The correction belongs in the derived projection and its API contract.
- The cited-insights project is paused until this project restores trustworthy
  time semantics. No cited extraction should begin as part of this work.

## Done When

- [ ] A canonical event has one stable ID and root across every daily/weekly
  projection.
- [ ] Nested quote chains are transitively connected before clustering; the
  OpenAI → Greg Brockman → Ben Hylak regression produces one envelope and one
  triage input.
- [ ] A selected day contains no evidence published after that UTC day.
- [ ] A multi-day event appears on each active day as one cumulative revision:
  prior context plus evidence newly observed that day.
- [ ] The default card does not expand historical evidence: it shows the stable
  root, today's delta, and at most one continuation label; earlier context is
  available on demand through the existing Follow disclosure.
- [ ] Daily attention uses only the selected day's activity; weekly aggregation
  deduplicates posts and Registry participants.
- [ ] Feed API fields make canonical identity, cutoff, continuation state,
  daily delta, and lifetime/as-of counts explicit.
- [ ] Existing triage decisions are reused only when the snapshot content hash
  is unchanged; changed snapshots are identifiable for a later bounded rerun.
- [ ] The seven-day store is rebuilt and the Anthropic global-workspace event
  passes a Monday/Tuesday regression test.
- [ ] Architecture/reference docs and build log reflect the landed contract,
  and `scripts/check-fast.sh` passes.

## Milestones

- [ ] M1 — Freeze the temporal contract. Acceptance: canonical event, daily
  activity, cumulative snapshot, and weekly rollup invariants are documented
  with exact API/schema fields. Validate against the audit examples in
  `resources/cross-day-envelope-audit-2026-07-13.md`.
- [ ] M2 — Implement as-of projections. Acceptance: event members are bounded
  by the requested UTC cutoff, canonical roots remain stable, daily deltas are
  explicit, and query indexes support the projection. Validate with focused
  signal-event and web-event tests.
- [ ] M3 — Rebuild and migrate derived state. Acceptance: seven days rebuild
  deterministically, old future-leaking projections are replaced cleanly, and
  triage reuse/invalidations are reported by content hash. Validate with a
  repeat-build fingerprint and SQLite integrity checks.
- [ ] M4 — Polish and prove the Feed. Acceptance: continuing events communicate
  prior context versus today's additions without duplicating the story, and
  daily/weekly API examples are inspectable. Validate at
  `http://127.0.0.1:8797` plus `scripts/check-fast.sh`.

## Execution Rules

- One event identity, many time-indexed observations. Never manufacture a new
  event merely because its activity crosses a calendar boundary.
- Daily snapshots are cumulative as of the selected day, never as of the
  latest materialized run.
- An event appears on a day only when at least one qualifying member/activity
  belongs to that day.
- Keep the canonical root stable. Mark it as prior context when it predates the
  selected day; highlight the selected day's delta separately.
- Do not add a timeline, new history mode, animation, or separate weekly UI in
  this project. Reuse the existing Follow disclosure for earlier context.
- Weekly views roll up the same event revisions and deduplicate by post ID and
  canonical Registry entity before scoring or display.
- Preserve raw evidence. Replace unfinished derived schemas cleanly rather
  than adding compatibility reads for the future-leaking projection.
- Do not start cited extraction or broaden ingestion in this project.
- Update this tracker after each milestone; archive it once Done When is met.

## Decisions

- 2026-07-13: Adi chose cumulative daily snapshots. Monday shows evidence
  known through Monday; Tuesday shows the same canonical event through Tuesday,
  including Monday as context and Tuesday as the visible continuation.
- 2026-07-13: Weekly reporting uses one envelope accumulated through week-end,
  not seven duplicated daily envelopes.
- 2026-07-13: Repetition across active days is meaningful attention history,
  not duplicate event identity. Stable `event_id` plus a snapshot cutoff/content
  hash distinguishes the two dimensions.
- 2026-07-13: The current full-run member join is a bug because it exposes
  future evidence in historical day views. It must be corrected before cited
  extraction or new-source expansion.
- 2026-07-13: Keep the first UI deliberately minimal. A continuing day's card
  shows the canonical root and that day's new activity, one muted
  `Continued from <date>` label, and a closed `Show earlier context` control in
  Follow. The cumulative history exists in data without dominating the Feed.
- 2026-07-13: The Greg Brockman/OpenAI duplicate is a normalization defect, not
  a second meaningful event. Provider-declared relations must be traversed
  transitively before event clustering; attention can rank an event but cannot
  choose its canonical identity.

## Open Questions / Blockers

- None. The daily cumulative and weekly rollup semantics are decided.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| todo | Repair recursive provider-relation normalization and add the OpenAI → Greg → Ben false-split regression before changing the temporal read model. | parent | [nested quote audit](resources/nested-quote-split-audit-2026-07-13.md) |
| todo | Freeze the schema/API contract for canonical events, daily activity deltas, cumulative cutoffs, and weekly rollups. | parent | [cross-day audit](resources/cross-day-envelope-audit-2026-07-13.md) |
| todo | Add regression fixtures for one event spanning Monday and Tuesday, including a prohibited Saturday member. | parent | — |
| todo | Implement the cutoff-correct projection and supporting indexes without changing attention weights. | parent | — |

## Backlog / Remaining Work

- [ ] Rebuild all seven stored days and compare counts/fingerprints.
- [ ] Report event-cluster merges after restoring the 750 currently recoverable
  nested quote edges, and audit the top affected envelopes for false merges.
- [ ] Audit triage snapshot hashes; reuse unchanged decisions and enumerate
  changed inputs without silently applying stale decisions.
- [ ] Audit the continuation affordance against a two-day and a six-day event;
  remove anything more complex than the agreed label/disclosure.
- [ ] Document the landed architecture and operational rebuild command.
- [ ] Run `scripts/check-fast.sh` and visually verify Monday/Tuesday plus a
  single-day event.
- [ ] Review project learnings and archive the tracker when complete.

## Validation / Test Plan

- Focused unit tests for canonical root stability, day cutoff, daily delta,
  repeated-day membership, weekly deduplication, and rejected Registry members.
- API tests asserting no `published_at` or `latest_evidence_at` exceeds the
  selected day cutoff.
- Deterministic rebuild: identical input produces the same run and projection
  fingerprints.
- SQLite `PRAGMA integrity_check` on rebuilt Feed/Event stores.
- Browser verification using the Anthropic global-workspace event on July 6
  and July 7.
- Full repository check: `scripts/check-fast.sh`.

## Progress Log

- 2026-07-13: [IN-PROGRESS] Audited the cross-day projection, quantified its
  prevalence, froze cumulative daily plus single-envelope weekly semantics,
  and created the project tracker. No runtime data or UI behavior changed.
- 2026-07-13: [DECISION] Froze the minimal UI: root plus today's additions by
  default, one continuation label, and prior evidence collapsed inside Follow.
  Requirements collection continues before overnight execution begins.
- 2026-07-13: [DIAGNOSIS] Traced the Greg Brockman/OpenAI screenshot to a lost
  nested quote edge. The one-level Feed normalizer preserved Ben → Greg but
  dropped Greg → OpenAI, splitting one story into two Event clusters and two
  independently triaged envelopes. Audited 750 distinct recoverable missing
  nested quote edges; 720 currently bridge separate clusters. Captured the
  repair contract and regression oracle in the linked audit resource.
