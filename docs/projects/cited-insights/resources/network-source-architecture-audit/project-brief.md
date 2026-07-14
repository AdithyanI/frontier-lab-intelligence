# Network Source Architecture Audit Workstream

Canonical execution owner: `../../tasks.md`. This brief is the frozen shared
contract for the bounded audit workstream; it does not compete with the active
Cited Insights tracker.

## Goal

Determine and validate a defensible architecture for monitored-source
membership, within-network support, source role/priority, and multi-channel
entity ranking, then implement only the changes supported by that review.

## Why / Impact

The Registry currently contains 2,197 active identities and acts as both the
daily X monitoring cohort and the screened population whose follow behavior
supplies network-support evidence. The underlying evidence is real and
inspectable, but the product currently places several different questions too
close together:

1. Should this identity be monitored at all?
2. How much support does it receive from the monitored network?
3. Is it a primary source, specialist, commentator, aggregator, or other role?
4. How important is it operationally as a source of useful intelligence?
5. How should several official channels owned by one entity count together?

The current Registry UI projects the best global X-account position from a
463,180-target discovery ranking onto each entity. That number is not a rank
within the 2,197 active identities and can be misleadingly large. It also uses
the best owned account rather than unioning support across all official
channels of a multi-channel organization. Meanwhile, the broad 2,197-source
cohort is relevance-screened but has not been proven to be the optimal 500,
1,000, or 2,197 sources for information yield.

If these concepts remain conflated, the interface can imply importance that
the evidence does not establish, a numerical cutoff can become circular, and
organizations or quiet first-hand researchers can be treated unfairly. If the
review is done well, the interview explanation becomes simple: what the
Registry contains, what network support measures, what source priority means,
and which parts have been validated.

## Scope / Non-Goals

### In Scope

- Reconstruct the exact provenance and admission path for the 2,197 active
  Registry identities and assess coverage, bias, and known omissions.
- Audit the current ranking code and read model end to end, including source
  deduplication, target-side entity aggregation, snapshot freshness, tie
  semantics, rank scope, and UI terminology.
- Define the distinct contracts for Registry membership, monitoring cohort,
  network support, source role/priority, public reach, and observed information
  yield.
- Compare credible alternatives, including broad monitoring with descriptive
  support, tiered source roles, entity-level support aggregation, and bounded
  core cohorts.
- Design and run a small real-data evaluation capable of rejecting a proposed
  architecture: coverage, unique useful signal, noise, first-hand evidence,
  cohort stability, and sensitivity to source selection.
- Record an accepted architecture decision, migration/rollback plan, and
  interview explanation before changing production semantics.
- After the decision is accepted, implement the smallest supported change with
  focused tests, documentation, and live-product verification.

### Out of Scope

- Choosing 500 or 1,000 merely because the number looks clean.
- Boosting every organization solely because its structural kind is
  `organization`.
- Treating follower count, network support, or list membership as proven source
  quality.
- Re-crawling the complete X following graph before the current immutable
  snapshot has been fully audited.
- Reopening general Registry relevance cleanup without evidence of a concrete
  admission failure.
- Retuning Feed attention weights or changing the accepted one-entity/one-vote
  amplification rule as part of this audit unless evaluation exposes a direct
  failure.
- Allowing this secondary architecture review to displace the submission's
  active cited-insights critical path without an explicit priority decision.

## Context / Constraints

- Date started: 2026-07-14.
- Submission deadline: 2026-07-20. This is a bounded secondary audit; the
  current critical path remains `docs/projects/cited-insights/tasks.md`.
- Current canonical Registry: 2,220 identities = 2,104 active people, 93 active
  organizations, and 23 reversible rejections; 2,197 active identities total.
- Latest daily X collection cohort: 2,234 active X accounts. Organizations may
  own multiple channels, so account and identity totals intentionally differ.
- Immutable outgoing-follow snapshot: 2,219 complete source accounts,
  2,197 voting entities, 2,456,305 edges, and 463,180 distinct target accounts.
- The Registry came from multiple candidate sources (Digg-observed candidates,
  AI High Signal, smol.ai preferred people, seeded labs, and reviewed coverage
  corrections), followed by structural classification, identity resolution,
  relevance screening, and reversible cleanup. It is broad and screened, but
  not a proven optimal watchlist.
- During the measured 2026-07-07 through 2026-07-13 Feed window, 1,309 active
  Registry identities authored direct evidence. A quiet seven-day window is
  not sufficient evidence for removal.
- Accepted current amplification rule: each active canonical Registry entity
  may contribute one flat vote per target/event and cannot amplify itself.
  Adi has explicitly said the flat vote is not the concern under review.
- Current network support is descriptive candidate-generation evidence, not a
  quality, importance, or admission score.
- Current Registry projection uses the best global position among an entity's
  owned X accounts. A correct entity-level alternative must explicitly decide
  whether and how to union source supporters across official channels.
- No UI or Feed cohort change was made during the conversation that opened this
  project.
- Canonical problem statement and agent entry point: `problem-statement.md`.

## Done When

- [ ] The current source-selection, monitoring, ranking, entity aggregation,
  and UI paths are reconciled against code and live data with no unexplained
  denominator or stale-snapshot mismatch.
- [ ] Registry membership, monitored cohort, network support, source role,
  source priority, X reach, and observed yield each have one non-overlapping
  definition and owner.
- [ ] At least three plausible architectures are compared on real evidence,
  including the current design as a baseline and an explicit no-change option.
- [ ] The review records what would make a 500/1,000/core cohort better than the
  broad 2,197-source cohort; no cutoff is adopted without that evidence.
- [ ] Multi-channel organizations and people are handled by a documented,
  deterministic entity-level rule with adversarial examples and tie behavior.
- [ ] A small source-yield evaluation measures useful unique signal and noise,
  not only graph centrality or audience size.
- [ ] Adi accepts one architecture decision or explicitly chooses no change;
  the decision includes limitations, migration, rollback, and interview-ready
  language.
- [ ] Any accepted implementation has focused backend/frontend tests,
  `scripts/check-fast.sh` passes, relevant architecture/product docs are
  current, and the live product is visually verified where semantics are shown.
- [ ] Workstream learnings are reviewed and its completion is recorded in the
  parent Cited Insights tracker; the resources archive with that project.

## Milestones

- [x] M0 — Freeze the problem and evidence boundary. Acceptance: this brief
  states the exact ambiguity, known counts, non-goals, and agent work lanes
  without presupposing a cutoff or ranking formula. Validate: tracker and
  and `problem-statement.md` agree.
- [ ] M1 — Audit current reality. Acceptance: one evidence-backed map covers
  Registry provenance, active collection membership, follow-graph ranking,
  multi-channel projection, snapshot freshness, and UI semantics. Validate:
  cited SQL reconciliations plus focused code-path references.
- [ ] M2 — Obtain independent architectural reviews. Acceptance: local
  implementation, product/data-science, and adversarial perspectives each
  produce a durable resource that answers the same decision questions and
  identifies falsifiable risks.
- [ ] M3 — Compare alternatives with a bounded evaluation. Acceptance: current
  design, entity-level support, and at least one tier/core alternative are
  tested on real data using predeclared measures; results include sensitivity
  and counterexamples.
- [ ] M4 — Record the architecture decision. Acceptance: one ADR-quality
  synthesis defines scopes, denominators, aggregation, roles, terminology,
  migration, rollback, and explicitly deferred work; Adi's decision is
  recorded.
- [ ] M5 — Implement and validate only the accepted delta. Acceptance: focused
  tests, repo fast checks, documentation, live UI verification where relevant,
  and no silent change to Feed collection or voting semantics.
- [ ] M6 — Close out. Acceptance: residual risks and learnings are current and
  the parent Cited Insights tracker records the workstream outcome.

## Execution Rules

- Audit first. Do not implement a cohort cutoff, organization boost, rank
  rescope, or label change before M4 records the accepted contract.
- Treat the current system as the baseline, not as wrong by default. Every
  claimed defect must identify the violated product meaning or measured
  consequence.
- Do not infer source quality from one proxy. Separate graph recognition,
  first-hand authority, public reach, activity, and downstream information
  yield.
- Structural kind is not source importance. If frontier labs or other primary
  sources receive guaranteed treatment, encode that as an explicit role/tier
  with evidence—not as a blanket organization multiplier.
- Avoid circular evaluation. Do not choose a core using network support and
  then validate it only with the same network-support ranking.
- Preserve full ties and disclose denominators whenever an ordinal is used.
- Keep raw snapshots immutable; derived alternatives belong in isolated,
  reproducible artifacts.
- The parent `../../tasks.md` is single-writer. Other agents should read it and
  this brief but write topic-based findings beside this file and report their
  resource path to the parent agent.
- Independent agents should challenge the stated hypotheses and may recommend
  no change. Agreement is not the goal; decision-quality evidence is.
- Run milestone-specific validation and checkpoint this tracker after every
  meaningful audit or implementation batch.
- Continue until the scoped project is complete or a true product decision
  requires Adi; do not leave a completed project active instead of archiving.

## Decisions

- Open this as a separate architecture-audit project rather than continuing to
  improvise UI labels in the cited-insights task.
- Keep the existing 2,197-source monitoring cohort and Feed behavior unchanged
  during the audit.
- Treat the user's concern as source-architecture validation, not primarily a
  UI-polish request.
- Preserve the accepted flat one-entity/one-vote rule as a constraint for the
  first review pass.
- Keep `network support` descriptive and distinct from `source priority` unless
  the evaluation supports a different contract.
- Do not assume organizations deserve an automatic numerical boost; evaluate
  explicit primary-source roles and correct multi-channel aggregation instead.

## Open Questions / Blockers

- What exact job should the public Registry's network ordinal perform:
  descriptive recognition, within-Registry navigation, monitoring priority, or
  admission evidence?
- Should the monitored cohort remain the full relevance-screened Registry, or
  should collection, voting, and display use different explicit cohorts?
- What evidence makes a source Tier 1: official frontier-lab role, first-hand
  output, recurring useful yield, network support, or a deterministic
  combination of independent gates?
- How should one organization with several official X accounts accumulate
  support without receiving duplicate votes from the same source identity?
- What minimum real-data evaluation is strong enough to justify shrinking or
  tiering the cohort before the submission deadline?
- Is the current derived following analysis stale relative to all 23 current
  rejections, and if so, which product projections are affected?

## Audit Work Board

The parent tracker's `Current Batch` is canonical. This table defines the
workstream split and expected output files.

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Freeze the architectural problem, known evidence, non-goals, and audit questions. | parent | `problem-statement.md` |
| todo | Reconcile the current code/data path and denominators, including snapshot freshness and multi-channel behavior. | explorer | `current-state-audit.md` |
| todo | Independently assess the product/measurement architecture and propose alternatives without assuming a cutoff. | product reviewer | `product-architecture-review.md` |
| todo | Adversarially review bias, circularity, role treatment, and likely failure cases; recommend no change if that is strongest. | adversarial reviewer | `adversarial-review.md` |
| todo | Design the smallest non-circular source-yield evaluation that can compare broad, core, and tiered cohorts. | evaluation reviewer | `evaluation-plan.md` |

## Audit Backlog / Remaining Work

- [ ] Synthesize independent reviews and explicitly record disagreements.
- [ ] Rebuild `Current Batch` for the bounded real-data comparison after the
  shared alternatives and measures are frozen.
- [ ] Run the accepted comparison with reproducible cohort manifests and
  preserve counterexamples.
- [ ] Write the architecture decision and obtain Adi's product decision.
- [ ] Implement only the accepted delta, with migration and rollback.
- [ ] Update `PRODUCT.md`, `DESIGN.md`, `docs/architecture/overview.md`, and
  `docs/STATUS.md` only where the accepted conceptual boundary changes them.
- [ ] Run focused tests, `scripts/check-fast.sh`, and live browser verification
  for any affected surface.
- [ ] Review and finalize `learnings.md`, record residual risks, and close the
  workstream in the parent tracker.

## Validation / Test Plan

- Reconcile Registry identity/account/channel/rejection totals from
  `data/fli.db`.
- Reconcile collection-cohort membership from
  `data/derived/x-daily-collection.db`.
- Reconcile source accounts, voting entities, edges, targets, Registry mapping,
  ties, and run/checkpoint hashes from the immutable following snapshot and
  derived analysis database.
- Trace `/api/registry`, `/api/rankings`, Feed score assembly, and the Registry
  frontend to exact fields and denominators.
- Use small synthetic graphs to test multi-account organizations, duplicate
  source follows, people versus organizations, ties, rejection changes, and
  missing/protected accounts before changing production code.
- Predeclare real-data comparison measures before selecting cohort thresholds:
  primary-source coverage, unique useful events/insights, noise, redundancy,
  stability, and important omissions.
- Run `bash scripts/check-fast.sh` after any repository implementation or
  durable-doc batch that affects rendered docs.
- Use the always-on app at `http://127.0.0.1:8797` for final semantic/UI proof;
  do not start another preview server.

## Progress Log

- 2026-07-14: [DONE] Opened the architecture-audit project after recognizing
  that the question is not primarily UI polish. Froze the exact ambiguity:
  broad monitored membership, descriptive network support, source role and
  operational priority, multi-channel aggregation, and global-versus-Registry
  rank are related but different contracts. Current Feed collection and voting
  behavior remain unchanged while independent audits are gathered.
