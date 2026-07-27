# Attention ranking redesign

## Goal

Cleanly replace `attention-v1.1` with an evidence-backed daily Event ranking,
replay the saved evidence, and refresh every downstream product output so the
working system and interview explanation agree.

## Why / Impact

The live `attention-v1.1` score works as an ordering aid, but its weighted
percentile lanes are harder to explain than the product thesis. A proposed
replacement then mixed an open-ended trusted-participant sum with fixed
`+0.25` adjustments. At realistic network sizes those adjustments become
negligible, so the formula did not express a coherent tradeoff.

A weak redesign would make the score look arbitrary under questioning. A good
one should make its ranking objective, scale, failure modes, and limits obvious
without claiming that attention equals importance or relevance.

## Scope / Non-Goals

### In Scope

- Correct the implementation spec so ranking is computed over the complete
  Event, not over an individual post selected afterward.
- Replace the old weighted score with the approved layered `daily-rank-v2`
  contract and no backward-compatibility path.
- Replay all 17 saved days from the evidence already stored locally and select
  each day's new top 100.
- Refresh audience routing, per-Event audience Insights, daily editorial
  briefs, PDFs, and UI projections downstream of the new rank.
- Reuse an existing model judgment only when its Event, audience, evidence,
  prompt contract, and model contract are exactly reusable.
- Align backend schemas, API contracts, UI disclosure, How narrative, tests,
  architecture/reference docs, validation evidence, and cost telemetry.

### Out of Scope

- Expanding the Registry from roughly 2,500 to 5,000 entities.
- Adding another source beyond X.
- Training a learned ranker.
- Treating routing labels as human ground truth.
- Public deployment or external communication.
- A separate ranks 101–200 recall probe; it may be done later and does not
  block this migration.

## Context / Constraints

- Date started: 2026-07-26.
- As of 2026-07-26, three working days remain before the Thursday BIT
  follow-up interview and case discussion. This is interview-hardening work,
  not an open-ended scoring research project.
- The interview is expected to probe design choices, trade-offs, what should
  be built next, how Adi used agents and AI tools, how data was obtained, and
  the token/API cost of the workflow. Ranking work must strengthen that
  explanation directly.
- The pre-migration product used versioned `attention-v1.1`: 55%
  tracked-amplification percentile, 25% author-support percentile, and 20%
  public-interaction percentile. The approved overnight task replaces it
  cleanly.
- The Feed rank selects where to look first. It does not claim truth, novelty,
  relevance, usefulness, or investment importance.
- Each canonical Registry entity may contribute at most once to one Event.
- Current routing labels cover the existing judged cohort and are censored by
  the top-100 gate. Precision metrics are diagnostic, not ground truth.
- The saved data and offline replay harness should be used before changing
  production.
- The earlier candidate
  `sum(1 + 0.5 × trust percentile) + 0.25 organization + up to 0.25 public`
  is rejected because it combines an unbounded primary term with fixed
  adjustments that vanish as participation grows.
- Relevant sources:
  - `docs/references/signal-feed.md`
  - `docs/references/scoring-validation.md`
  - `src/fli/scoring/attention.py`
  - `src/fli/scoring/evaluation.py`
  - `frontend/src/features/system/HowNarrative.tsx`
  - `frontend/src/features/system/DecisionFigures.tsx`

## Approved Overnight Execution Contract

This contract was approved and explicitly started in conversation on
2026-07-26. Adi asked the agent to continue through completion without pausing
for routine approval.

- Work through implementation, replay, downstream refresh, validation,
  documentation, and final product proof without pausing for routine status
  approval.
- Adi authorizes the model/API spend needed to complete this refresh, with no
  project-specific spend cap.
- X API calls are also authorized if genuinely required, but they are not
  expected: use the saved evidence snapshot by default and do not refresh X
  merely to recompute rank.
- External publication, deployment, submission, email, or contact remains
  prohibited without separate explicit approval.
- A comparison against the old top 100 is optional diagnostic work, not a
  prerequisite. Correctness of the new contract and the completed refreshed
  product are the priority.
- Intended morning outcome: the new ranking and all downstream outputs are
  ready for Adi to inspect.

## Done When

- [x] The ranking question and invariants are explicit and internally
      consistent.
- [x] The new rank is computed once per complete Event from the union of its
      distinct canonical-day trusted voters.
- [x] All 17 saved days are reranked and each day's new top 100 is materialized
      without requiring an X refetch.
- [ ] Audience routing, per-Event Insights, daily briefs, PDFs, and UI
      projections agree with the new top-100 cohorts and ranks.
- [x] Exact reusable routing and per-Event Insight judgments are preserved;
      every missing or invalidated routing/Insight output is regenerated.
- [ ] Every missing or invalidated daily editorial output is regenerated.
- [ ] Code, API contracts, rank disclosure, How narrative,
      architecture/reference docs, tests, built SPA assets, and cost telemetry
      agree on the same versioned contract.
- [ ] `scripts/check-fast.sh` passes and the relevant local UI is visually
      verified.

## Milestones

- [x] Milestone 1 — Audit the old score and approve the layered replacement.
      Acceptance: the measured saturation defect, rejected alternatives, and
      selected ordering are documented.
- [x] Milestone 2 — Implement and replay `daily-rank-v2`.
      Acceptance: the complete Event is the scoring boundary, all 17 saved
      days produce deterministic ranks, and each new top 100 is materialized.
- [ ] Milestone 3 — Refresh all downstream intelligence.
      Acceptance: routing, per-Event Insights, daily editorial briefs, PDFs,
      and UI projections refer to the new cohorts and ranks; exact cached
      judgments are reused where valid.
- [ ] Milestone 4 — Validate, document, and archive.
      Acceptance: backend/frontend checks and local product proof pass, costs
      and residual limits are documented, `learnings.md` is reviewed, and the
      tracker moves to `docs/projects/archive/attention-ranking-redesign/`.

## Execution Rules

- Keep work scoped to the current milestone unless the tracker explicitly
  expands scope.
- Run validation after each milestone or risky batch and fix failures before
  advancing.
- Continue until the scoped project is done or a true blocker requires human
  input.
- Replace `attention-v1.1` cleanly once the overnight task is explicitly
  started; do not add a dual read, legacy fallback, or compatibility toggle.
- Reject formulas whose terms cannot be compared or whose intended signals
  disappear accidentally at realistic scale.
- Do not optimize solely against routing labels; inspect concrete ranking
  behavior and known limitations.
- Update this tracker after every meaningful batch and before ending a project
  turn.
- Use `Current Batch` as the primary resume point.
- When `Done When` is satisfied, finalize `learnings.md` and archive the
  project rather than leaving it active.

## Decisions

- The primary product question is: “What did the trusted AI network pay
  independent attention to on this day?”
- Breadth means distinct canonical Registry entities, with one contribution
  per entity per Event.
- Attention ranking remains separate from audience relevance and editorial
  importance.
- The open-ended participant sum plus fixed `+0.25` adjustments is rejected.
- Organization authorship and public engagement will not receive arbitrary raw
  bonuses. Their role must be either scale-comparable or explicitly secondary.
- Production remains unchanged while candidates are evaluated.
- The old rank-order figure and a formula explanation answer different
  questions; the rank-order figure must remain.
- Candidate reasoning belongs in this tracker and its resources until a
  formula is selected. The public How page should describe implemented
  behavior honestly.
- 2026-07-26: the successor is **layered, not weighted**. Order by trusted
  vote count; break ties by average voter network position, then author
  network position, then public interactions. See
  `resources/layered-score-proposal.md`.
- 2026-07-26: the `1 + 0.5 × trust` participant weight is dropped in the
  layered design. Averaging is affine, so the constants provably cannot change
  the ordering; they would be an unjustifiable number doing no work. Layer 2
  uses raw network position.
- 2026-07-26: an organization or first-party seed vote is **rejected on
  evidence**. 577 org-authored zero-vote Events across 15 days are ~70% vendor
  marketing, and frontier labs already clear 1+ vote 66% of the time versus 30%
  for other organizations.
- 2026-07-26: production is **not** rescored. Reranking would invalidate the
  five frozen submission Insights and `scoring-validation.md`. The deliverable
  is a measured self-audit plus a tested versioned successor.
- 2026-07-26 (superseded, same day): Adi directed a **clean migration**
  instead. The databases are snapshotted, so `daily-rank-v2` replaces
  `attention-v1.1` outright with no backward compatibility, no dual-read, and
  no legacy toggle; rollback is a snapshot restore. The later overnight
  contract makes an old-versus-new comparison optional rather than blocking
  the migration.
- 2026-07-26: the unit of ranking is the complete same-day Event. Layer 1 uses
  the union of distinct trusted voters across all Event members, with the
  source author excluded. Do not score posts independently and then select a
  winning member.
- 2026-07-26: layer 2 uses the mean entity-level network position of those
  voters. Layer 3 uses the canonical source/root author's entity-level network
  position.
- 2026-07-27: network position is the six-decimal fraction of ranked canonical
  entities with strictly lower entity-union support. Equal support receives
  equal position; raw support magnitude and dense-rank spacing are excluded.
- 2026-07-26: layer 4 is the maximum same-day public interaction count among
  the Event's member posts, where one post's count is
  `likes + reposts + replies + quotes`. It is a tie-breaker, not a blended
  popularity weight.
- 2026-07-26: Adi approved the complete downstream refresh and the required
  LLM/API spend. Existing evidence should be reused; X calls are permitted if
  actually necessary but are not expected.

## Open Questions / Blockers

- No design or spending blocker remains.
- No open blocker. The migration is active.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Correct the implementation spec around the Event boundary, entity-level network positions, layer semantics, and downstream refresh | parent | `resources/implementation-spec.md` |
| done | Audit the exact downstream refresh commands, reuse boundaries, dates, and completion checks without changing files or data | explorer |  |
| done | Audit the Event projection seam, affected contracts, and highest-risk regression tests without changing files | explorer |  |
| done | Implement the clean `daily-rank-v2` backend/API migration and replay all 17 saved days | parent | `resources/implementation-spec.md` |
| done | Materialize the 17 exact-rank routing cohorts and refresh every routed-positive per-Event Insight | parent | `resources/replay-validation.md` |
| in_progress | Import 17 exact-lineage v3 daily briefs, then rebuild PDFs and product projections | parent |  |

## Backlog / Remaining Work

- [ ] Optional old-versus-new mover comparison for interview discussion.
- [ ] Optional ranks 101–200 recall probe after the migration.
- [ ] Consider Registry expansion and additional sources as later projects.

## Validation / Test Plan

- `python -m pytest -q tests/scoring`
- `.venv/bin/fli daily-rank evaluate --json --no-input`
- Candidate-specific unit tests for monotonicity, scale behavior, ties, and
  entity deduplication.
- Named replay inspection for low-, medium-, and high-participation Events,
  organization-authored Events, and high-public-engagement outliers.
- `npm --prefix frontend run test`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run build`
- Local `/how#why-rank` and Feed rank-disclosure visual checks.
- Downstream completeness checks for all 17 routing cohorts, per-Event
  Insights, daily briefs, PDFs, and UI projections.
- `scripts/check-fast.sh`

## Progress Log

- 2026-07-26: [IN-PROGRESS] Created the project after rejecting a
  scale-incoherent candidate that mixed an open-ended participant sum with
  fixed `+0.25` adjustments.
- 2026-07-26: [DONE] Preserved the original rank-order figure separately from
  the candidate-formula figure; both answer different questions.
- 2026-07-26: [DONE] Designed the layered `daily-rank-v2` contract, rejected
  the seed-vote and `1 + 0.5 x trust` variants on evidence, shipped the visual
  `ScoreLayersFigure` on `/how#why-rank`, and wrote
  `resources/implementation-spec.md` for an overnight implementation pass.
  Adi directed a clean migration with no backward compatibility.
- 2026-07-26: [DONE] Audited live `attention-v1.1` behaviour across seven
  briefed days (`resources/v1-1-behaviour-audit.md`). The percentile transform
  over a zero-inflated amplifier count turns the 55% primary lane into a
  near-binary "amplified at all?" flag: 0→1 amplifier is worth +40.9 points
  while 2→111 amplifiers is worth +2.3. Inside the top-100 routing gate the
  nominally 25% author-support lane out-discriminates it on five of seven
  days, and 11 Events with ≥3 trusted amplifiers miss the gate on 2026-07-15
  while 37 Events with ≤1 amplifier are admitted. This is a stronger and more
  checkable case for the redesign than the original explainability argument.
- 2026-07-26: [CONTEXT] Three working days remain before Thursday's BIT
  follow-up interview. Reframed the project as bounded interview hardening:
  defensible explanation, replay evidence, working-method narrative, and
  token/API cost clarity outrank platform breadth or a rushed production
  score migration.
- 2026-07-26: [APPROVED, NOT STARTED] Adi approved a clean overnight
  `daily-rank-v2` migration and full downstream refresh, including the model
  and API spend required to finish it. X calls are permitted if required but
  are not expected because the evidence snapshot is already stored. The old
  top-100 comparison is optional. Per Adi's instruction, no implementation,
  replay, or external call starts until he explicitly assigns the overnight
  task.
- 2026-07-26: [DONE] Implemented `daily-rank-v2` at the complete Event
  boundary, added rank-versioned routing lineage, exact cross-lineage Insight
  reuse, input-matched prior annotations, and multi-lineage historical brief
  orchestration. All 486 backend and 66 frontend tests pass. The 17-day replay
  covers 19,657 Events and 1,700 top-100 rows; historical censored usefulness
  rates in the final current routing cohort rise from 34.3% at one vote to
  72.1% at five or more votes.
- 2026-07-26: [DONE] Refreshed all 17 `daily-rank-v2` routing stores with
  1,674/1,674 complete and zero failures. Exact Event/evidence/input reuse
  supplied 976 rows; 698 new GPT-5.4-mini/high calls cost $2.961695
  incrementally. No X call was made.
- 2026-07-26: [DONE] Refreshed the Event-native artifact projection and all
  1,482 routed-positive per-Event Insight rows. The Insight pass reused 524
  exact prior Event/audience outputs, completed 958 new Terra/high calls for
  $15.561773 incremental proxy cost, and resumed one transient timeout to zero
  failures.
- 2026-07-26: [IN PROGRESS] Launched the resumable 17-day
  `daily-intelligence run-batch` with three concurrent GPT-5.6-sol/xhigh
  Standard tasks over frozen current routing and `daily-rank-v2` workspaces.
- 2026-07-27: [DONE] Corrected network position to a tie-aware entity-support
  percentile, reran all 19,657 Events, and bound every full day's exact Event
  rank inputs into one SHA. The final routing correction completed 1,674/1,674
  rows with 1,647 exact reuses, 27 new calls, zero failures, and $0.089051
  incremental cost. The artifact projection remains 6,298 accepted
  observations, 5,378 artifacts, and zero failures; no X call was needed.
- 2026-07-27: [DONE] Refreshed the final routed-positive Insight cohort:
  1,474/1,474 Event/audience decisions across 965 Events, with 1,451 exact
  reuses, 23 Terra/high calls, zero failures, and $0.361769 incremental cost.
  The current cohort contains 619 surfaced and 855 suppressed decisions.
- 2026-07-27: [DONE] Independent read-only review caught and fixed three
  downstream lineage gaps before the authoritative brief replay: stale
  editorials now fail closed, weekly Event responses no longer expose a
  misleading single-day rank SHA, and normal one-day orchestration resumes
  require the same Event/Feed/routing/cohort/rank lineage as batch runs.
- 2026-07-27: [IN PROGRESS] Launched the authoritative 17-day
  `daily-orchestration-v3` batch with four concurrent GPT-5.6-sol/xhigh
  Standard tasks over the final routing and Insight cohort.
