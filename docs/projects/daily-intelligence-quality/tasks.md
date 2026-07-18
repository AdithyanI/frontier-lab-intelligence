# Daily Intelligence Quality

## Goal

Make the July 5–15 daily briefs chronologically honest and submission-worthy,
starting with a conservative seven-day X evidence window and deterministic
source dates before applying further editorial changes.

## Why / Impact

The daily agent and persistence path work across all eleven evaluated days, but
the overnight audit found that structurally valid output can still present old
evidence as if it happened on the brief day. That weakens freshness,
traceability, signal-to-noise, and the credibility of the final 3–5 Insights—the
parts of the BIT assignment that matter most.

The overnight audit showed that broad old-root resurfacing creates more noise
than useful synthesis in this daily product. Adi chose the conservative rule:

> Raw evidence remains auditable, but daily routing and editorial packets use
> only first-party X sources published no more than seven days before the brief.

## Scope / Non-Goals

### In Scope

- Preserve the full July 5–15 editorial audit as a reproducible project
  baseline.
- Make X-source chronology application-owned in routing, daily workspaces, and
  citation validation using data already present in the Feed store.
- Exclude X sources older than seven days while retaining a current same-author
  quote or reply as the primary source when one exists.
- Project exact disclosure lineage for every workspace artifact and let the
  daily agent audit timing and relevance before citation.
- Require the daily agent to ground every proposed artifact citation in a
  verified excerpt that directly supports the Insight claim.
- Calibrate the change against known failure cases and a known-good control
  before deciding which days need another editorial run.
- Reassess the provisional weak-item and omission queues, then select the
  strongest 3–5 cited Insights for submission proof.

### Out of Scope

- A same-day-only source rule; the allowed X window is seven days inclusive.
- Deleting or rewriting raw Feed and Event evidence.
- A required `development` entity or `development | synthesis` schema field in
  the first version.
- Automatic merging from URLs, embeddings, thresholds, or connected
  components.
- Artifact publication-date inference from retrieval time or from the X post
  that linked the artifact.
- An all-days rerun before the targeted chronology cases pass.
- Model changes, broad source expansion, Registry work, alerts, or unrelated UI
  polish.

## Context / Constraints

- Date started: 2026-07-18.
- Submission deadline: 2026-07-20.
- Full preserved audit: [resources/overnight-audit-2026-07-18.md](resources/overnight-audit-2026-07-18.md).
- Latest complete imported run per day covers July 5–15: 616 Events, 945
  audience pairs, 105 selected Insights, and 685 not-selected pairs.
- There was no tracked active project to archive. All prior trackers were
  already under `docs/projects/archive/`; the empty leftover
  `docs/projects/artifact-content-refresh/` directory was removed because its
  completed tracker is already archived.
- The normalized Feed already holds authoritative X `published_at`,
  `first_discovered_at`, and `first_discovered_day` values. All 2,187 X-source
  references in the canonical workspaces resolve against their bound Feed run.
- Daily workspace v1 freezes routing packets without those dates. Daily
  citation validation currently checks URL membership and date syntax, not
  equality to the stored source date.
- Existing workspaces and imported results remain immutable. Corrected output
  uses workspace v2 and requires a new editorial run only for dates selected
  after calibration.
- `first_discovered_at` is transport discovery, not an artifact publication
  time and not a generic `observed_at` fact.

## Done When

- [x] Every retained X source in a new daily workspace carries deterministic
      publication timing without changing the source routing run or raw Event.
- [x] X sources older than seven days are absent from new routing packets and
      daily workspaces; an old-only candidate is excluded, while a current
      same-author update is promoted to primary evidence.
- [x] Event citation dates are filled from frozen source truth; a conflicting
      agent-supplied date fails validation; an unavailable date remains null.
- [x] Search and inspection make source timing visible enough for the daily
      agent to reason about chronology.
- [x] Skill guidance states the seven-day evidence contract and forbids prose
      that silently turns the brief day into the source day.
- [x] Regression cases for Jul 10, Jul 13, Jul 14, and Jul 15 pass, including
      the inclusive seven-day boundary and old-only exclusion.
- [x] Every workspace artifact exposes exact disclosure lineage so the daily
      agent can audit whether it was available by the brief day.
- [x] Every newly persisted artifact citation includes an excerpt verified
      against the frozen artifact text and a claim-specific support explanation.
- [ ] The provisional weak-item and omission queues are adjudicated, the final
      3–5 submission candidates are named, and remaining findings are either
      fixed or explicitly deferred.
- [ ] Relevant tests and `scripts/check-fast.sh` pass; conceptual docs match the
      implemented boundary; project learnings are reviewed; the tracker is
      archived.

## Milestones

- [x] Milestone 1 — Preserve the audit baseline and separate verified facts
      from reviewer judgment. Acceptance: totals, chronology, cases, quality
      queues, and harness suggestions are recorded with qualifications.
      Validate: direct SQLite checks plus source/skill inspection.
- [x] Milestone 2 — Ship the seven-day X source window plus deterministic
      chronology in routing, the daily workspace, and citation validation.
      Acceptance: raw evidence remains intact, old-only packets are excluded,
      current same-author updates survive, and citations use source truth.
      Validate: targeted routing/editorial tests and workspace inspection.
- [x] Milestone 3 — Calibrate on demonstrated cases before a broad rerun.
      Acceptance: Jul 10 Thinking Machines, Jul 13 CaMeLs, Jul 14 teachers, and
      Jul 15 current-source control behave as specified under the seven-day
      rule. Validate: fresh v2 workspaces and deterministic canary inspection.
- [ ] Milestone 4 — Adjudicate the editorial queues and decide the minimum rerun
      set. Acceptance: every provisional weak item and strongest omission has a
      recorded keep/rewrite/suppress/defer judgment; no all-days rerun occurs
      merely for uniformity.
- [ ] Milestone 5 — Produce and review the final submission proof. Acceptance:
      strongest 3–5 Insights are chronologically accurate, primary-source
      traceable, audience-useful, and defensible against the BIT rubric.
      Validate: focused qualitative audit, product inspection, and fast checks.

## Execution Rules

- Milestones 2–3 are complete. Continue with editorial adjudication rather than
  expanding the chronology harness.
- Preserve existing routing runs and raw Events. New routing freezes apply the
  source window; workspace v2 applies it defensively to already-frozen runs.
- Treat the brief day, X publication time, discovery time, artifact publication
  time, and retrieval time as different facts.
- For X evidence, age beyond seven days is a deterministic exclusion. Artifact
  age remains separate because retrieval or link time is not publication time.
- Reviewer quality labels in the audit are provisional queues, not ground truth.
- Run repo-native validation after each milestone and fix failures before
  advancing.
- Keep `tasks.md` current after every meaningful batch. When `Done When` is
  satisfied, finalize `learnings.md` and archive this project directly.

## Decisions

- 2026-07-18: [SUPERSEDED] The initial proposal allowed arbitrarily old dated
  synthesis. The adopted daily-product window now permits the brief day plus
  seven preceding days; older research belongs in separately cited web/context
  evidence or a future longer-horizon product.
- 2026-07-18: Do not add an Insight-type enum yet. The first change is source
  truth plus validation; add a reader-facing synthesis label only if calibrated
  output remains ambiguous.
- 2026-07-18: For X event citations, make `published_at` deterministic from the
  exact frozen URL. Never substitute the brief day.
- 2026-07-18: Keep artifact chronology separate. The linking post's date and
  artifact retrieval time do not establish the artifact's publication date.
- 2026-07-18: Do not rerun all eleven days until the known chronology failures
  and one current-source control pass.
- 2026-07-18: Adi selected a seven-day inclusive X-source window. Preserve raw
  evidence, exclude old X sources from semantic packets, promote a current
  same-author continuation when available, and exclude the Event when no
  current first-party X source remains.
- 2026-07-18: Keep artifact discovery broad, but make daily use conservative.
  Code owns disclosure timing and exact lineage; the daily agent owns semantic
  relevance. Require a verified excerpt for every artifact citation rather
  than adding another model gate or database entity.

## Open Questions / Blockers

- After accurate source dates are visible, does the reader still need an
  explicit `Synthesis` label, or is honest prose sufficient?
- Which historical days merit a rerun after the targeted calibration? Decide
  from changed output quality, not from a desire for uniformity.
- Which later harness improvements materially improve the final 3–5 before the
  deadline? Everything else remains recorded but deferred.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Project inspectable artifact disclosure lineage into workspace v2 without an automatic artifact gate. | parent | [audit](resources/overnight-audit-2026-07-18.md) |
| done | Require and verify claim-grounding excerpts for artifact citations through the existing client validation path. | parent | [tests](../../../tests/insights/test_editorial.py) |
| done | Update the daily skill and Paper Glider evaluation case, then run all-days and fast validation. | parent | [audit](resources/overnight-audit-2026-07-18.md) |

## Backlog / Remaining Work

- [ ] Adjudicate the 14 provisional weak selected Insights.
- [ ] Review the strongest possible omissions and grouping mistakes.
- [ ] Add cross-day prior-Insight search or story lineage if chronology alone
      does not stop repeated judgments.
- [ ] Add compact source-authority/social-only review cues if they improve
      selection without hard-coding editorial taste.
- [ ] Deduplicate repeated Event members inside exact-artifact groups.
- [ ] Improve generic Event-link and not-selected reasons only where the audit
      surface needs claim-specific explanations.
- [ ] Consider a compact review matrix, web-citation helper, source-family cue,
      machine-readable Engineering stack, and richer BIT company-driver
      context after the submission-critical path is safe.
- [ ] After citation grounding is proven, decide whether semantic artifact
      warnings add value beyond the verified-excerpt requirement.
- [x] Update durable architecture/status docs when the chronology boundary is
      implemented.
- [ ] Review and finalize `learnings.md`, run full milestone validation, and
      archive the project.

## Validation / Test Plan

- Targeted unit tests for workspace timing, source URL matching, date autofill,
  mismatch rejection, null handling, and unchanged routing hashes.
- Jul 10: `https://x.com/miramurati/status/1945166365834535247`
  is pruned; the Jul 10 quote/reply become the current packet.
- Jul 13: `https://x.com/sebkrier/status/2060811780721418707`
  is absent from the v2 workspace because it is older than seven days.
- Jul 14: the old-only OpenAI teacher packet `1991218197530378431` is excluded;
  current Jul 14 evidence remains eligible.
- Jul 15: GPT-Red, Anthropic agentic-misalignment, and Perplexity SPACE remain a
  valid current-day synthesis.
- A synthetic source exactly seven days old remains eligible; one eight days
  old and any future-dated source are excluded.
- `scripts/check-fast.sh` before milestone handoff.

## Progress Log

- 2026-07-18: [DONE] Located project state — every tracked prior project was
  already archived; removed the empty duplicate artifact-content-refresh
  directory.
- 2026-07-18: [DONE] Preserved the overnight multi-reviewer audit, mechanically
  rechecked its baseline and chronology counts, and marked qualitative findings
  as provisional rather than ground truth.
- 2026-07-18: [DONE] Chose deterministic chronology as the minimum first fix;
  explicitly rejected a mandatory current-day anchor, blanket stale filter,
  and premature Insight-type schema expansion.
- 2026-07-18: [SUPERSEDED] After reviewing the old-root distribution and real
  envelopes, Adi chose a seven-day inclusive first-party X window rather than
  warning-only chronology. Raw Events remain intact.
- 2026-07-18: [DONE] Implemented the source-level rule in routing freezes and
  workspace v2, deterministic Event citation dates, and skill/architecture
  guidance. Targeted tests passed; all eleven July 5–15 workspaces prepared.
  Jul 14 excluded four old-only Events and 53 stale X sources; Jul 10 retained
  Mira Murati's current quote/reply while removing the 2025 root.
- 2026-07-18: [IN PROGRESS] Paper Glider exposed a second chronology boundary:
  a Jul 15 disclosure reply was pruned from the Jul 14 workspace, but its
  artifact survived because routing packets did not preserve disclosure
  lineage. The same artifact was then cited generically for an unrelated
  cost/capacity claim. Replanned one bounded fix for timing plus citation
  grounding before any editorial rerun.
- 2026-07-18: [DONE] Projected exact artifact disclosure lineage into all eleven
  fresh workspaces without automatically excluding artifacts. A calibration
  rejected exact-post and date-only artifact gates in favor of agent audit.
  New artifact citations require a non-empty excerpt that occurs in the exact
  frozen Event artifact. Paper Glider remains visible in Jul 14 with its Jul 15
  disclosure, while its future X reply stays outside the semantic packet.
  Focused tests passed 18/18, all eleven workspaces prepared, and the full fast
  suite passed 405 Python tests plus 56 frontend tests, lint, and build.
