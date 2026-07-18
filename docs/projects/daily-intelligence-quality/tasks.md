# Daily Intelligence Quality

## Goal

Make the July 5–15 daily briefs chronologically honest and submission-worthy,
starting with deterministic source dates and then applying only the smallest
editorial changes proven necessary by calibration.

## Why / Impact

The daily agent and persistence path work across all eleven evaluated days, but
the overnight audit found that structurally valid output can still present old
evidence as if it happened on the brief day. That weakens freshness,
traceability, signal-to-noise, and the credibility of the final 3–5 Insights—the
parts of the BIT assignment that matter most.

The immediate correction must not impose the opposite error. A periodic brief
may contain a useful synthesis built from older evidence. The durable rule is:

> The run date says when the memo was selected; source dates say when the
> evidence occurred.

## Scope / Non-Goals

### In Scope

- Preserve the full July 5–15 editorial audit as a reproducible project
  baseline.
- Make X-source chronology application-owned in daily workspaces and citation
  validation using data already present in the Feed store.
- Keep fresh-development and older-evidence synthesis Insights valid without a
  blanket age rule.
- Calibrate the change against known failure cases and a known-good control
  before deciding which days need another editorial run.
- Reassess the provisional weak-item and omission queues, then select the
  strongest 3–5 cited Insights for submission proof.

### Out of Scope

- A mandatory current-day source for every Insight.
- A blanket age cutoff or automatic stale suppression.
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
  requires a new workspace contract and, only after calibration, targeted
  reruns.
- `first_discovered_at` is transport discovery, not an artifact publication
  time and not a generic `observed_at` fact.

## Done When

- [ ] Every frozen X source in a new daily workspace carries deterministic
      publication and discovery timing without changing the routing packet or
      its evidence hashes.
- [ ] Event citation dates are filled from frozen source truth; a conflicting
      agent-supplied date fails validation; an unavailable date remains null.
- [ ] Search and inspection make source timing visible enough for the daily
      agent to reason about chronology.
- [ ] Skill guidance explicitly permits dated synthesis while forbidding prose
      that silently turns the brief day into the source day.
- [ ] Regression cases for Jul 10, Jul 13, Jul 14, and Jul 15 pass, including an
      entirely older-evidence synthesis that remains valid when honestly dated.
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
- [ ] Milestone 2 — Ship deterministic X chronology in the daily workspace and
      citation validator. Acceptance: actual dates are application-owned and
      routing hashes remain unchanged. Validate: targeted editorial tests and
      workspace inspection.
- [ ] Milestone 3 — Calibrate on demonstrated cases before a broad rerun.
      Acceptance: Jul 10 Thinking Machines, Jul 13 CaMeLs, Jul 14 teachers, and
      Jul 15 current-source control behave as specified; old synthesis is still
      allowed. Validate: fresh v2 workspaces, validation canaries, and manual
      draft inspection.
- [ ] Milestone 4 — Adjudicate the editorial queues and decide the minimum rerun
      set. Acceptance: every provisional weak item and strongest omission has a
      recorded keep/rewrite/suppress/defer judgment; no all-days rerun occurs
      merely for uniformity.
- [ ] Milestone 5 — Produce and review the final submission proof. Acceptance:
      strongest 3–5 Insights are chronologically accurate, primary-source
      traceable, audience-useful, and defensible against the BIT rubric.
      Validate: focused qualitative audit, product inspection, and fast checks.

## Execution Rules

- Keep work on Milestone 2 until chronology passes its tests; do not mix in the
  longer harness backlog.
- Preserve the frozen routing packet and hashes. Add a daily-workspace timing
  sidecar or equivalent derived projection rather than mutating routing truth.
- Treat the brief day, X publication time, discovery time, artifact publication
  time, and retrieval time as different facts.
- Age may produce a warning or review cue, never an automatic error by itself.
- Reviewer quality labels in the audit are provisional queues, not ground truth.
- Run repo-native validation after each milestone and fix failures before
  advancing.
- Keep `tasks.md` current after every meaningful batch. When `Done When` is
  satisfied, finalize `learnings.md` and archive this project directly.

## Decisions

- 2026-07-18: Do not require every daily Insight to contain a current-day
  development. Periodic synthesis is valid when its evidence is accurately
  dated and the prose is honest about chronology.
- 2026-07-18: Do not add an Insight-type enum yet. The first change is source
  truth plus validation; add a reader-facing synthesis label only if calibrated
  output remains ambiguous.
- 2026-07-18: For X event citations, make `published_at` deterministic from the
  exact frozen URL. Never substitute the brief day.
- 2026-07-18: Keep artifact chronology separate. The linking post's date and
  artifact retrieval time do not establish the artifact's publication date.
- 2026-07-18: Do not rerun all eleven days until the known chronology failures
  and one current-source control pass.

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
| todo | Add a versioned daily-workspace timing projection from the bound Feed run without mutating routing packets or hashes. | parent | [audit](resources/overnight-audit-2026-07-18.md) |
| todo | Make Event citation dates deterministic and add mismatch/missing-date tests. | parent | [audit](resources/overnight-audit-2026-07-18.md) |
| todo | Update the daily skill's chronology rule and exercise the four calibration cases. | parent | [audit](resources/overnight-audit-2026-07-18.md) |

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
- [ ] Update durable architecture/status docs when the chronology boundary is
      implemented.
- [ ] Review and finalize `learnings.md`, run full milestone validation, and
      archive the project.

## Validation / Test Plan

- Targeted unit tests for workspace timing, source URL matching, date autofill,
  mismatch rejection, null handling, and unchanged routing hashes.
- Jul 10: `https://x.com/miramurati/status/1945166365834535247`
  resolves to 2025-07-15, not the 2026-07-10 brief day.
- Jul 13: `https://x.com/sebkrier/status/2060811780721418707`
  resolves to 2026-05-30.
- Jul 14: OpenAI teacher post `1991218197530378431` resolves to 2025-11-19;
  Claude teacher post `2077047278078931243` resolves to 2026-07-14.
- Jul 15: GPT-Red, Anthropic agentic-misalignment, and Perplexity SPACE remain a
  valid current-day synthesis.
- A synthetic all-historical Insight validates when dates are correct and prose
  does not claim a same-day release.
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

