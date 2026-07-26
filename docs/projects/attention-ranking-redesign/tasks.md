# Attention ranking redesign

## Goal

Produce an evidence-backed, scale-coherent daily Event ranking that answers
which developments received the strongest independent attention from the
trusted AI network, and explain it plainly enough to defend in the interview.

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

- Define the exact question the daily rank answers.
- Define invariants for entity counting, author treatment, trust weighting,
  public engagement, daily scope, and ties.
- Compare a small set of coherent candidate families against the frozen saved
  days.
- Inspect top-ranked Events, large movers, organization-authored Events,
  high-participation Events, and viral public outliers.
- Produce a recommendation with a plain-language formula, worked examples,
  limitations, and evidence.
- Keep the How page honest while the candidate is unresolved.
- Implement a selected production score only after Adi approves the product
  tradeoff.

### Out of Scope

- Expanding the Registry from roughly 2,500 to 5,000 entities.
- Adding another source beyond X.
- Replacing audience relevance judgment or editorial selection.
- Training a learned ranker.
- Treating routing labels as human ground truth.
- Public deployment or external communication.

## Context / Constraints

- Date started: 2026-07-26.
- As of 2026-07-26, three working days remain before the Thursday BIT
  follow-up interview and case discussion. This is interview-hardening work,
  not an open-ended scoring research project.
- The interview is expected to probe design choices, trade-offs, what should
  be built next, how Adi used agents and AI tools, how data was obtained, and
  the token/API cost of the workflow. Ranking work must strengthen that
  explanation directly.
- A bounded replay and a clear limitation are more valuable in this window
  than broad platform changes or a rushed production migration.
- Production remains on versioned `attention-v1.1`: 55% tracked-amplification
  percentile, 25% author-support percentile, and 20% public-interaction
  percentile.
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

## Done When

- [ ] The ranking question and invariants are explicit and internally
      consistent.
- [ ] At least 3 coherent candidate families are replayed on the same frozen
      days with their component scales and tie rules documented.
- [ ] The comparison reports rank stability, top-window precision diagnostics,
      large movers, and named failure cases rather than one aggregate metric.
- [ ] Organization authorship and public engagement each have an explicit
      role: primary component, comparable normalized lane, tie-breaker, or
      context only.
- [ ] One recommendation can be explained with a worked low-, medium-, and
      high-participation example without a component becoming accidentally
      meaningless.
- [ ] Adi reviews the evidence-backed recommendation and the decision is
      recorded here.
- [ ] If approved, code, score disclosure, How narrative, architecture or
      reference docs, tests, and built SPA assets agree on the same versioned
      contract.
- [ ] `scripts/check-fast.sh` passes and the relevant local UI is visually
      verified.

## Milestones

- [ ] Milestone 1 — Restore an honest baseline and freeze the design question.
      Acceptance: the rejected fixed-bonus proposal is not presented as a
      viable How-page formula; the original rank-order figure remains; the
      objective and invariants are recorded here. Validate:
      `npm --prefix frontend run test && npm --prefix frontend run build`.
- [ ] Milestone 2 — Build a bounded candidate comparison.
      Acceptance: at least a network-primary lexicographic candidate, a
      coherent normalized-lane candidate, and a saturating-network candidate
      replay the same frozen Events with deterministic outputs. Validate:
      targeted scoring tests plus the replay command.
- [ ] Milestone 3 — Stress-test and recommend.
      Acceptance: the comparison includes organization-authored, 1-participant,
      many-participant, and high-public-engagement cases; the recommendation
      states what each non-primary signal can and cannot change.
- [ ] Milestone 4 — Record Adi's decision and, if approved, implement the
      versioned contract. Acceptance: all product surfaces and durable docs
      describe exactly the implemented score; no candidate language is
      presented as live.
- [ ] Milestone 5 — Validate, finalize learnings, and archive.
      Acceptance: fast checks and local product proof pass, residual limits are
      documented, `learnings.md` is reviewed, and the tracker moves to
      `docs/projects/archive/attention-ranking-redesign/`.

## Execution Rules

- Keep work scoped to the current milestone unless the tracker explicitly
  expands scope.
- Run validation after each milestone or risky batch and fix failures before
  advancing.
- Continue until the scoped project is done or a true blocker requires human
  input.
- Keep production on `attention-v1.1` until the evidence-backed product choice
  is approved.
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

## Open Questions / Blockers

- Product decision after replay: should organization authorship affect the
  primary score, act only as an explicit tie-breaker, or remain visible context?
- Product decision after replay: should public engagement affect rank at all,
  or remain a displayed diagnostic?
- These questions do not block candidate construction and replay.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Remove the rejected fixed-bonus proposal from the How narrative while preserving the original rank-order figure | parent |  |
| done | Audit what `attention-v1.1` actually does across the seven briefed days | parent | `resources/v1-1-behaviour-audit.md` |
| done | Design the layered successor and reject the seed-vote and trust-constant variants on evidence | parent | `resources/layered-score-proposal.md` |
| todo | Implement the layered score and replay it over the 15 saved days | parent | `resources/layered-score-proposal.md` |
| todo | Run the bounded recall probe on ranks 101–200 for one day | parent | `docs/references/scoring-validation.md` |
| todo | Write the interview defense: audit, fix, validation, and why production was not rescored | parent |  |

## Backlog / Remaining Work

- [ ] Produce the evidence-backed recommendation and worked examples.
- [ ] Review the recommendation with Adi and record the decision.
- [ ] Implement and version the selected score only if approved.
- [ ] Align How, Feed disclosure, architecture/reference docs, and tests.
- [ ] Run full validation and visual proof.
- [ ] Review `learnings.md`, close out, and archive the project.

## Validation / Test Plan

- `python -m pytest -q tests/scoring`
- `python -m fli.cli attention-score evaluate --json --no-input`
- Candidate-specific unit tests for monotonicity, scale behavior, ties, and
  entity deduplication.
- Named replay inspection for low-, medium-, and high-participation Events,
  organization-authored Events, and high-public-engagement outliers.
- `npm --prefix frontend run test`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run build`
- Local `/how#why-rank` and Feed score-disclosure visual checks.
- `scripts/check-fast.sh`

## Progress Log

- 2026-07-26: [IN-PROGRESS] Created the project after rejecting a
  scale-incoherent candidate that mixed an open-ended participant sum with
  fixed `+0.25` adjustments.
- 2026-07-26: [DONE] Preserved the original rank-order figure separately from
  the candidate-formula figure; both answer different questions.
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
