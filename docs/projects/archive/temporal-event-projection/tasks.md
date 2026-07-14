# Temporal Event Projection

## Goal

Make provider-linked evidence resolve into one canonical envelope as of each
cutoff while daily and weekly Feed views remain reproducible when later raw
evidence is added.

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

- Preserve one stable event identity and root for the same cutoff-visible exact
  component. A relationship first disclosed later may merge later projections,
  but cannot rewrite an earlier projection.
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
- Define a weekly projection directly from the full provider-edge envelope
  visible through week-end, with posts and Registry participants deduplicated.
  It is not a concatenation of seven daily projections.
- Version downstream triage inputs by event plus snapshot content hash so an
  unchanged snapshot reuses its decision and a material change remains
  auditable.
- Rebuild the seven stored days and record before/after counts and examples.
- After the repaired seven-day rebuild passes its adversarial audit, collect
  the two newly complete UTC days (2026-07-12 and 2026-07-13) for the current
  frozen Registry cohort, refresh the derived Feed/Event projections, and use
  them as the first fresh-data proof of the corrected pipeline.

### Out of Scope

- Cited-insight extraction, primary-artifact fetching, or an Insights page.
- Ongoing ingestion expansion or new RSS, blog, GitHub, or arXiv sources. The
  only new X collection in scope is the bounded 2026-07-12 through 2026-07-13
  post-repair proof over the existing Registry cohort.
- Expanding the Registry/follow-graph cohort. Before that happens, the
  snapshot roll-forward and ranking effective-date boundary must be closed as
  a separate follow-up rather than improvised during this repair.
- Semantic/LLM event clustering beyond existing exact provider relationships.
- Attention-weight changes.
- Mobile/responsive UI work.

## Context / Constraints

- Date started: 2026-07-13.
- The pre-repair baseline contained seven complete UTC days, 10,552 Feed
  posts, 7,563 envelope-day rows, and 6,909 unique exact events.
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

- [x] The same cutoff-visible exact component has one stable ID and root across
  deterministic rebuilds and future range extensions.
- [x] Nested quote chains are transitively connected before clustering; the
  OpenAI → Greg Brockman → Ben Hylak regression produces one envelope and one
  triage input.
- [x] A selected day contains no evidence, embedded content, or relationship
  first disclosed after that UTC day, even when the underlying post carries an
  older publication timestamp.
- [x] A multi-day event appears on each active day as one cumulative revision:
  prior context plus evidence newly observed that day.
- [x] The default card does not expand historical evidence: it shows the stable
  root, today's delta, and at most one continuation label; earlier context is
  available on demand through the existing Follow disclosure.
- [x] Daily attention uses only the selected day's activity; the weekly view
  projects one full envelope through week-end and deduplicates posts and
  Registry participants.
- [x] Feed API fields make canonical identity, cutoff, continuation state,
  daily delta, and lifetime/as-of counts explicit.
- [x] After final regrouping, triage is reconciled against the rebuilt
  envelopes: unchanged exact snapshot and rendered-input hashes are reused,
  while every new or changed envelope is rerun before final publication.
- [x] The seven-day store is rebuilt and the Anthropic global-workspace event
  passes a Monday/Tuesday regression test. Extending the raw store either
  leaves historical fingerprints unchanged or produces an exhaustively
  documented diff made only of newly discovered immutable evidence.
- [x] After the repaired rebuild passes, UTC days 2026-07-12 and 2026-07-13 are
  collected resumably, projected with the same corrected contracts, triaged by
  snapshot hash, and manually audited for useful signal and structural errors.
- [x] An adversarial structural audit finds no remaining provider-declared
  relationship loss, competing top-level envelopes for absorbed evidence, or
  independently triaged duplicates in a representative high-attention sample.
- [x] Architecture/reference docs and build log reflect the landed contract,
  and `scripts/check-fast.sh` passes.

## Milestones

- [x] M1 — Freeze the temporal contract. Acceptance: canonical event, daily
  activity, cumulative snapshot, and weekly rollup invariants are documented
  with exact API/schema fields. Validate against the audit examples in
  `resources/cross-day-envelope-audit-2026-07-13.md`.
- [x] M2 — Implement as-of projections. Acceptance: event members, embedded
  content, and relations are bounded by first disclosure at the requested UTC
  cutoff; same-cutoff identities remain stable; daily deltas are explicit; and
  query indexes support the projection. Validate with focused signal-event and
  web-event tests, including a later wrapper that discloses an older relation.
- [x] M3 — Rebuild and migrate derived state. Acceptance: seven days rebuild
  deterministically, old future-leaking projections are replaced cleanly, and
  triage reuse/invalidations are reported by content hash. Validate with a
  repeat-build fingerprint and SQLite integrity checks.
- [x] M4 — Polish and prove the Feed. Acceptance: continuing events communicate
  prior context versus today's additions without duplicating the story;
  daily/weekly API examples are inspectable; and the same repaired pipeline
  successfully ingests, projects, triages, and audits the newly complete UTC
  days 2026-07-12 and 2026-07-13. Validate at `http://127.0.0.1:8797` plus
  `scripts/check-fast.sh`.

## Execution Rules

- One provider-edge graph, many cutoff-indexed projections. Daily identity is
  derived from the connected component visible by that cutoff; a future bridge
  may merge later projections but must not rewrite an earlier one.
- Quote targets, retweet targets, and explicit reply parents are the only
  grouping edges. Conversation IDs remain metadata and never merge branches.
- Daily snapshots are cumulative as of the selected day, never as of the
  latest materialized run.
- An event appears on a day only when at least one qualifying member/activity
  belongs to that day.
- Keep the canonical root stable for the same cutoff-visible structural
  component. A root first captured later may become canonical only at and after
  its disclosure; it must not rewrite an earlier day. Mark prior roots as
  context and highlight the selected day's delta separately.
- Do not add a timeline, new history mode, animation, or separate weekly UI in
  this project. Reuse the existing Follow disclosure for earlier context.
- Weekly views project the full provider-edge envelope visible through
  week-end and deduplicate by post ID and canonical Registry entity before
  scoring or display. They do not concatenate daily projections.
- Preserve raw evidence. Replace unfinished derived schemas cleanly rather
  than adding compatibility reads for the future-leaking projection.
- Do not start cited extraction or broaden ingestion in this project.
- Do not rerun or trust bulk triage as final routing until normalized relations,
  event clustering, and snapshot projection pass the adversarial audit. Triage
  cannot repair an envelope assembled from incomplete evidence.
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
- 2026-07-13: Adi requires an adversarial review after the repair, covering the
  full data path rather than only the reported examples. The review should
  challenge normalization depth, relation completeness, canonical-root choice,
  duplicate suppression, temporal cutoffs, and triage reuse before downstream
  extraction resumes.
- 2026-07-14: Keep the first fresh-data extension inside this project rather
  than opening another tracker. Only after the existing seven days pass the
  structural and temporal audit, collect complete UTC days 2026-07-12 and
  2026-07-13 for the unchanged Registry cohort, rebuild derived state, rerun
  only new or changed triage inputs, and audit the result. This is a bounded
  pipeline proof, not authorization for continuous ingestion or Registry
  expansion.
- 2026-07-14: Exact grouping is provider-edge-only. Recursive quote/retweet and
  explicit reply-parent relations may connect posts; a shared provider
  conversation ID may not. Daily projections re-componentize members and
  relations visible by the selected cutoff, and weekly output projects the
  full visible envelope through week-end.
- 2026-07-14: Final triage follows the last regrouping and rebuild. Reuse is
  permitted only for unchanged exact snapshot and rendered-input hashes; all
  new or changed envelopes must be rerun before closeout.

## Open Questions / Blockers

- None. The daily cumulative and weekly rollup semantics are decided.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| completed | Finished resumable collection of complete UTC days 2026-07-12 and 2026-07-13 for the frozen 2,234-account Registry cohort; 0 pending and 0 failed. | parent | [pipeline operational review](resources/pipeline-operational-review-2026-07-14.md) |
| completed | Rebuilt and published the final nine-day Feed v8 / Event v3 provider-edge projection; overlap and repeat-build fingerprints are deterministic. | parent | [rebuild audit](resources/rebuild-adversarial-audit-2026-07-14.md) |
| completed | Reconciled triage by exact snapshot/input hash and recorded complete cost/cache/failure telemetry. | parent | [rebuild audit](resources/rebuild-adversarial-audit-2026-07-14.md) |
| completed | Completed full-corpus structural/temporal adversarial audit, API/latency proof, repository checks, residual risks, and learnings. | parent | [learnings](learnings.md) |

## Backlog / Remaining Work

- [x] Preserve the seven-day Feed v7 / Event v2 rebuild only as an intermediate
  baseline; replace its closeout claims with final Feed v8 / Event v3 evidence.
- [x] After the repaired seven-day corpus passes, collect raw X evidence for
  complete UTC days 2026-07-12 and 2026-07-13 using the existing resumable
  provider store; record provider requests, cache reuse, and reported spend.
- [x] Refresh Feed/Event state through 2026-07-13 using provider edges only;
  prove daily cutoff-visible cumulative projection and weekly full-envelope
  projection before rerunning triage.
- [x] Rerun or exactly reuse triage only after final regrouping, then manually
  compare Sunday/Monday yield, duplicates, roots, continuation behavior, and
  false keep/drop decisions with the repaired historical corpus.
- [x] Run an adversarial review after rebuilding: programmatic invariants over
  the complete seven-day corpus plus independent manual audits of false splits,
  false merges, missing roots, duplicate top-level envelopes, and stale triage
  decisions. Preserve concrete counterexamples and before/after counts.
- [x] Audit the continuation affordance against a two-day and a six-day event;
  remove anything more complex than the agreed label/disclosure.
- [x] Document the landed architecture and operational rebuild command.
- [x] Run `scripts/check-fast.sh`; verify Monday/Tuesday and single-day behavior
  through API/product regressions. Direct final Browser control was unavailable
  and is explicitly disclosed.
- [x] Review project learnings and archive the tracker when complete.

## Validation / Test Plan

- Focused unit tests for canonical root stability, day cutoff, daily delta,
  repeated-day membership, weekly deduplication, and rejected Registry members.
- API tests asserting no `published_at`, first-disclosure timestamp, relation
  discovery timestamp, or `latest_evidence_at` exceeds the selected cutoff.
- Regression where Monday posts A and B are separate and a Wednesday wrapper C
  first discloses A → B: Wednesday may merge them, while Monday's IDs, roots,
  members, links, snapshot hashes, and rendered content remain unchanged.
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
- 2026-07-13: [REQUIREMENT] Captured Adi's overnight acceptance gate: after the
  repair, adversarially review the complete normalization → clustering →
  temporal projection → triage path. Do not mistake model routing for data
  correctness, and do not proceed to cited extraction while duplicate or
  incomplete envelopes remain possible.
- 2026-07-14: [REQUIREMENT] Added a bounded post-repair freshness proof: once
  the seven stored days are correct, ingest complete UTC Sunday 2026-07-12 and
  Monday 2026-07-13 with the unchanged Registry cohort, rebuild the same
  derived stages, rerun only new/changed triage snapshots, and audit how the
  pipeline performs on data that was not part of the original repair corpus.
- 2026-07-14: [IN-PROGRESS] Started the long-running execution goal. The parent
  owns shared contracts and integration while three independent adversarial
  reviews examine relation integrity, temporal/index correctness, and
  rebuild/triage/ingestion safety before implementation is considered proven.
- 2026-07-14: [MILESTONE] Rebuilt and locally published the corrected seven-day
  corpus on immutable recursive evidence. Feed run `12b7bc1e...` contains
  16,078 posts and 9,622 relations; Event run `280c7aee...` contains 4,035
  clusters and 13,902 members. All daily and weekly structural fingerprints,
  SQLite integrity checks, and adversarial relation/cutoff invariants pass.
- 2026-07-14: [MILESTONE] Completed corrected seven-day triage for every
  available top-1,000 daily envelope: 6,312 results, 5,062 exact hash reuses,
  1,250 fresh calls, zero failures, and $1.896023 proxy-reported cost. Started
  the frozen-cohort July 12–13 collection; final nine-day publication remains
  gated on complete coverage and a reviewed July 5–11 diff.
- 2026-07-14: [FINDING] Fresh provider pages legitimately exposed a small set
  of previously unseen July 5–11 posts from existing Registry channels. A
  growing immutable raw store can therefore add historical evidence without
  rewriting any prior observation. Closeout will prove common observations are
  byte-stable, enumerate every historical addition and affected envelope, and
  prove a repeat build is deterministic after collection freezes; it will not
  hide valid evidence merely to preserve an older fingerprint.
- 2026-07-14: [FIX] The provider can explicitly return
  `has_next_page=false` while leaving an inert cursor. The collector now treats
  the explicit terminal flag as authoritative, preventing up to 100 redundant
  requests per quiet account, and has focused regression coverage for both
  fresh fetches and cached resume planning.
- 2026-07-14: [DECISION] Froze the final projection doctrine: provider
  quote/retweet/explicit reply-parent edges only; conversation IDs are metadata,
  daily projections are cumulative connected components visible by cutoff, and
  weekly output is one deduplicated full-envelope projection through week-end.
  Final July 12–13 collection, nine-day rebuild, post-regrouping triage,
  adversarial proof, product proof, and archival remain pending.
- 2026-07-14: [COMPLETE] Finished the frozen-cohort July 12–13 collection over
  2,234 accounts: 2,225 fetched, nine reconciled from cache, 2,256 accepted
  pages, 3,147 provider requests, zero pending accounts, and zero failures. An
  idempotent replay issued no provider calls.
- 2026-07-14: [COMPLETE] Published final Feed v8 run `adb2b494…` and Event v3
  run `f8999fcd…` for July 5–13. Both candidate databases pass integrity and
  foreign-key checks; all structural/temporal audit failures are zero. An
  independent seven-day build has the same July 5–11 fingerprints inside the
  nine-day range, and repeat builds reproduce the same semantic audit hashes.
- 2026-07-14: [COMPLETE] Reconciled 8,097 triage inputs by exact snapshot and
  rendered-input hash: 1,516 exact reuses, 6,581 fresh `gpt-5.4-mini` calls,
  4,402 keeps, 3,695 drops, zero failures, $8.72954610 proxy-reported fresh
  cost, and zero API hash mismatches. Manual fresh-day review found the gate
  useful but intentionally permissive for borderline AI-adjacent leads.
- 2026-07-14: [COMPLETE] Closed the full-corpus adversarial review, including
  the OpenAI ← Greg ← Ben nested-quote regression, largest components,
  rejected bridges, opaque anchors, cutoff leakage, conversation non-grouping,
  weekly deduplication, and 16–24 ms local date-read latency. Repository checks
  pass. Direct final in-app Browser control was unavailable, so closeout claims
  API/build proof rather than invented visual proof.
