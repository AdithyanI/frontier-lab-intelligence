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
- Submission deadline: 2026-07-20. This was a bounded secondary audit under the
  archived `docs/projects/archive/cited-insights-v1/tasks.md`; its successor was
  the now-archived `docs/projects/archive/audience-insights-v2/tasks.md`.
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

## Decision Addendum — 2026-07-14 (accepted direction)

Recorded after Adi's session with the reviewing architect. This addendum
supersedes the work board below where they conflict; the parent tracker's
`Current Batch` is canonical for execution.

### Diagnosis (evidence, reproduced from live data)

- The Registry `Network rank` displays `ranking_result.position`, a
  `ROW_NUMBER` over the 463,180-target discovery universe ordered by
  `cohort_follow_count DESC, lower(handle) ASC`. Integer votes create massive
  tie blocks: 290,408 targets share exactly one vote and occupy positions
  172,773–463,180 in **alphabetical order**. Low-support Registry members
  therefore show alphabet-noise ordinals (observed: Josh Bersin #308,612 with
  1 vote). Two identical-support accounts can differ by 100k+ positions.
- A tie-aware `score_rank` (DENSE_RANK) already exists in `analysis.db` but is
  not displayed.
- Blast radius is display-only: `src/fli/web/feed.py` consumes
  `cohort_follow_count`, never `position`; the daily score is unaffected.
- Multi-channel target aggregation uses the best owned account
  (`entity_network_ranks` in `src/fli/web/rankings.py`, MIN position) instead
  of unioning distinct supporting entities across official channels. Measured
  undercounts: SpaceX 491→728 (+48%), Google 1,087→1,201, Microsoft 537→632,
  Anthropic 1,156→1,215, OpenAI 1,406→1,428. Union does not reorder the top
  labs; it is a correctness fix, not a ranking shake-up.
- Snapshot label drift: 2,204 "active" entities in the analysis graph vs 2,197
  currently active identities; disclose snapshot date/denominator in UI.

### Accepted deltas (implement now)

1. **Registry support display.** Primary value is the support count with an
   explicit denominator ("followed by N of 2,197 tracked entities"), plus a
   tie-aware ordinal scoped to active Registry entities only. Never render a
   tiebreak `position` as an entity's rank. The 463k discovery ordering stays
   in the Ranking view, labeled as candidate generation.
2. **Entity-level union support.** Support for an entity = count of distinct
   eligible Registry entities following **any** of its official X channels,
   self excluded. Symmetric with the source-side rule: one entity, one vote,
   on both sides of the edge. Deterministic; document tie behavior.
3. **AIE World's Fair 2026 speaker source.** Direct-admission candidate
   source; see `aie-worldsfair-2026-source.md` for the implementation spec.
   Coverage query runs **before** admission.

### Explicitly deferred (post-submission; record in ADR)

- Cohort cutoffs (500/1,000), tier taxonomy, and yield-based source
  evaluation. The ADR records the designed seed → discover → admit → measure
  yield → feed back loop and interview-ready limitation language instead.
- The four-lane independent review program (M2) is collapsed: the diagnosis
  above answered the audit's core question directly.

Adi subsequently authorized a full incremental following refresh for the
newly admitted identities. That refresh is complete; it does not change the
remaining deferral on cohort cutoffs, tiers, or yield-based source policy.

### Architect opinion (for the reviewing engineer)

The architecture is sound in three of four layers — identity ownership,
collection, and source-side vote deduplication are correct. The defect is a
presentation contract: a tiebreak position was shown as a rank. Fix the
display semantics, apply the same one-entity-one-vote rule target-side, and
resist any weight-based importance scheme: authority belongs in explicit
roles/affiliations (badges, guarantees, routing), never blended into
descriptive counts, because checkability is the product thesis. The AIE
speaker list is worth ingesting primarily as a **non-circular external
validation cohort** (coverage-before-admission) and as curated affiliation
data; treating it only as "more sources" would waste its best value.

## Audit Work Board

Superseded 2026-07-14 by the Decision Addendum above and the parent tracker's
`Current Batch`. Original review-lane plan preserved for provenance:

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Freeze the architectural problem, known evidence, non-goals, and audit questions. | parent | `problem-statement.md` |
| done | Reconcile the current code/data path and denominators, including snapshot freshness and multi-channel behavior. | parent (direct diagnosis) | Decision Addendum above |
| dropped | Independently assess the product/measurement architecture and propose alternatives without assuming a cutoff. | product reviewer | — |
| dropped | Adversarially review bias, circularity, role treatment, and likely failure cases; recommend no change if that is strongest. | adversarial reviewer | — |
| deferred | Design the smallest non-circular source-yield evaluation that can compare broad, core, and tiered cohorts. | evaluation reviewer | post-submission; AIE coverage report is the bounded near-term substitute |

## Audit Backlog / Remaining Work

- [x] Implement the Registry display delta: entity-union support with
  denominator, tie-aware within-Registry ordinal, discovery ordering confined
  to the Ranking view; focused tests plus live UI verification.
- [x] Ingest the AIE World's Fair 2026 and 2024 speaker directories per
  `aie-worldsfair-2026-source.md`: raw snapshot, identity resolution,
  pre-admission coverage query, direct admission with provenance and
  role/employer facts.
- [x] Write the coverage/miss report and the ADR (accepted deltas, deferrals,
  yield-feedback loop design, interview-ready language).
- [x] Update `PRODUCT.md`, `DESIGN.md`, `docs/architecture/overview.md`, and
  `docs/STATUS.md` only where the accepted conceptual boundary changes them.
- [ ] Run focused tests, `scripts/check-fast.sh`, and live browser verification
  for any affected surface.
- [x] Review the accepted boundary, record residual risks, and close the
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
- 2026-07-14: [DECIDED] Direct diagnosis replaced the four-lane review
  program. Root cause of the anomalous ordinals confirmed (alphabetical
  tiebreak positions inside a 290,408-account one-vote tie block, displayed as
  ranks); blast radius confirmed display-only. Adi accepted: entity-union
  support with denominators and tie-aware within-Registry ordinal, no
  organization weighting (roles carry authority), AIE World's Fair 2026
  speakers as a direct-admission candidate source with coverage measured
  before insertion, and deferral of cohort cutoffs/tiers/yield evaluation and
  new-admit voting to post-submission. See the Decision Addendum above and
  `aie-worldsfair-2026-source.md`.
- 2026-07-14: [IMPLEMENTED] The accepted display correction and
  `entity-overlap-v3` target union are live. The 2026/2024 import retained 423
  people but only 96 channel-backed company identities; 195 unresolved company
  labels remain person context rather than Registry organizations. The
  incremental snapshot completed with 2,558 source accounts, 2,521 voting
  entities, 2,832,858 edges, and explicit zero-support Registry rows. See
  `architecture-decision.md`.
