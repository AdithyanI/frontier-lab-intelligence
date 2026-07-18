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
- Add one repo-owned, date-keyed orchestration command that runs the existing
  deterministic evidence, routing, and workspace stages before handing the
  prepared workspace to a visible Codex App Server task.
- Persist enough orchestration state to make retries safe and to link each day
  to its exact evidence run, routing run, workspace, Codex thread, and imported
  editorial run.
- Prove the boundary incrementally on one new day: deterministic preparation
  first, then one explicitly named Codex task under the
  `frontier-lab-intelligence` Desktop project.

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
- Scheduling, multi-day fan-out, remote execution, a permanent App Server
  daemon, or a generalized workflow engine in the first orchestration version.

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
- Workspace v3 is the only executable authoring contract. It carries
  application-owned source dates and Event-native `semantic_snapshot_sha256`
  keys. Historical packets remain files only; no runtime command upgrades,
  opens, or resumes them.
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
- [x] One machine-readable command can prepare a requested date through the
      deterministic handoff, resume without duplicating completed stages, and
      optionally launch a persisted, named Codex App Server task with an active
      daily-intelligence goal.
- [x] A one-day canary proves that the deterministic outputs are inspectable
      before task launch and that the resulting task is visible under the
      repository in Codex Desktop with its thread id recorded durably.
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
      rule. Validate: fresh current workspaces and deterministic canary inspection.
- [x] Milestone 4 — Ship and canary the minimal daily orchestrator. Acceptance:
      one command prepares a date through existing deterministic stages,
      checkpoints exact identifiers, and launches one persisted App Server
      thread with repository cwd, explicit name, active goal, and initial turn.
      Validate: contract tests, stop-after-prepare run, live July 16 task, and
      durable task/run inspection. The canary froze 59 Events / 95 audience
      pairs and imported 15 Insights; retries close from the durable import
      without reopening a task later reused for review.
- [ ] Milestone 5 — Adjudicate the editorial queues and decide the minimum rerun
      set. Acceptance: every provisional weak item and strongest omission has a
      recorded keep/rewrite/suppress/defer judgment; no all-days rerun occurs
      merely for uniformity.
- [ ] Milestone 6 — Produce and review the final submission proof. Acceptance:
      strongest 3–5 Insights are chronologically accurate, primary-source
      traceable, audience-useful, and defensible against the BIT rubric.
      Validate: focused qualitative audit, product inspection, and fast checks.

## Execution Rules

- Milestones 2–3 are complete. Continue with editorial adjudication rather than
  expanding the chronology harness.
- Preserve existing routing runs and raw Events. New routing freezes apply the
  source window; fresh workspace v3 packets apply it defensively to
  already-frozen current routing runs.
- Treat the brief day, X publication time, discovery time, artifact publication
  time, and retrieval time as different facts.
- For X evidence, age beyond seven days is a deterministic exclusion. Artifact
  age remains separate because retrieval or link time is not publication time.
- Reviewer quality labels in the audit are provisional queues, not ground truth.
- Run repo-native validation after each milestone and fix failures before
  advancing.
- Keep `tasks.md` current after every meaningful batch. When `Done When` is
  satisfied, finalize `learnings.md` and archive this project directly.
- Keep the deterministic handoff and Codex reasoning separate: the command may
  collect, route, freeze, and launch, but the daily task remains responsible for
  editorial research, validation, import, and final inspection through the
  existing `$fli-daily-intelligence` skill.

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
- 2026-07-18: Use a short-lived stdio `codex app-server` client for orchestration
  v1. Create a non-ephemeral thread with the exact repo `cwd`, set its visible
  name, start one explicit full-objective turn, attach the persisted active goal,
  and follow native goal continuations to completion. Do not use `codex exec`, a
  daemon, or an SDK abstraction for the first canary.
- 2026-07-18: Prove the deterministic stages separately before spending a Codex
  turn. The first command contract must support a stop-after-prepare boundary
  and stable JSON inspection.
- 2026-07-18: Workspace v3 is the sole executable packet contract. Remove the
  in-place v2 upgrader and prepare fresh current packets instead of maintaining
  a dual-read or compatibility path.
- 2026-07-18: The imported editorial run, not a task's later mutable goal state,
  is terminal orchestration proof. Reconciliation checks the exact workspace's
  complete run before any App Server resume.

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
| done | Freeze the orchestration contract and map existing stage/CLI boundaries. | parent | [contract](resources/codex-daily-orchestration.md) |
| done | Implement the date-keyed command, resumable ledger, and App Server client with contract tests. | parent | [contract](resources/codex-daily-orchestration.md) |
| done | Run a stop-after-prepare canary, then one live visible Codex task for July 16. | parent | [contract](resources/codex-daily-orchestration.md) |
| in_progress | Adjudicate the editorial quality queues and select the minimum rerun set. | parent | [audit](resources/overnight-audit-2026-07-18.md) |

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
- [ ] After the one-day canary, decide whether scheduling, multi-day fan-out, or
      a persistent App Server transport is justified; none is required for v1.

## Validation / Test Plan

- Targeted unit tests for workspace timing, source URL matching, date autofill,
  mismatch rejection, null handling, and unchanged routing hashes.
- Jul 10: `https://x.com/miramurati/status/1945166365834535247`
  is pruned; the Jul 10 quote/reply become the current packet.
- Jul 13: `https://x.com/sebkrier/status/2060811780721418707`
  is absent from a fresh current workspace because it is older than seven days.
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
  current workspaces, deterministic Event citation dates, and skill/architecture
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
