# Auditable Development Insights

## Goal

Build and validate the next pipeline boundary: turn current-lineage routed
Developments into audience-specific Insight decisions whose evidence,
company/build-surface mapping, suppression, uncertainty, citations, and
ordering rationale are inspectable.

## Why / Impact

The upstream path is now defensible enough to hold stable:

- exact Events remain the provenance unit;
- same-day originals about one release-specific artifact form a Development;
- `daily-development-rank-v1` orders Developments without a weighted score;
- `audience-routing-v13` routes the July 21 top 100 with Luna/medium.

A positive route only means "this may deserve downstream investigation." It
does not yet prove that the Development changes an investment thesis or an
engineering decision. The next interview-critical question is whether the
system can make that final connection with visible evidence and honest
negative decisions, rather than hiding it inside one opaque editorial call.

## Scope / Non-Goals

### In Scope

- Audit the existing Investment v10 and AI Engineering v7 Insight contracts
  against current Development lineage before reusing or replacing them.
- Freeze one exact Development packet and one audience context packet behind
  every model judgment, with hashes and run identity.
- Investment: evaluate every Development against the complete 37-company
  candidate universe, retrieve full company memos only for plausible matches,
  and preserve direct/indirect/none plus thesis-effect judgments.
- AI Engineering: define a small public, repo-grounded build-surface roster and
  preserve affected/not-affected judgments before writing an Insight.
- Emit a strict surface-or-suppress decision with a concise reason; negative
  verdicts are first-class auditable output.
- Define and evaluate a defensible Insight rating or ordering contract without
  an arbitrary weighted sum.
- Repair or add the smallest repeatable operator tooling needed to render
  packets, run fixed cohorts, resume failures, audit outputs, and reconcile
  telemetry. Do not leave the production workflow dependent on throwaway
  scripts or manual database edits.
- Calibrate on a small July 21 cohort, then run the complete routable top 100
  only after the sample is good.
- Project current-lineage decisions into the existing Insights audit UI without
  relabeling historical Event-lineage outputs.
- Record model, reasoning, prompt-cache telemetry, token usage, cost, and
  qualitative evaluation.

### Out of Scope

- Retuning `daily-development-rank-v1` or `audience-routing-v13` during the
  initial Insight calibration.
- Refetching X, rebuilding the Registry/follow graph, or refetching artifacts.
- Regenerating the 37 company research memos unless a concrete source defect is
  found.
- Cross-day novelty, ranks 101–200 recall, new ingestion sources, or Registry
  expansion.
- Daily editorial consolidation, PDF regeneration, Slack/email delivery, or
  external publication. Those follow only after this per-Development boundary
  is proven.
- Backward-compatibility shims. Historical runs remain immutable evidence;
  current readers fail closed on incompatible lineage.

## Context / Constraints

- Date started: 2026-07-28.
- Interview: Thursday 30 July 2026.
- Case requirement: one shared intelligence core with distinct Investment and
  AI Engineering last-mile outputs; every Insight must be attributable, cited,
  useful, and filtered with taste.
- Current routing proof:
  `routing-2026-07-21-development-v13-luna-medium-top100`, 97/97 complete,
  55 both, 10 Engineering-only, 11 Investment-only, 21 neither.
- Routing is recall-oriented. Its 76 any-audience positives are candidates,
  not final intelligence.
- The complete company universe and source-bearing memos are available through
  BIT Lens and `docs/references/company-memos/`.
- Exact model, caching, and cost rules live in
  `docs/references/model-routing.md`,
  `docs/references/prompt-caching.md`, and
  `docs/references/tokenomics.md`.
- Route every model call through the shared LiteLLM Responses endpoint.
- No external send or publication without Adi's explicit approval in the
  current session.

## Done When

- [ ] One documented current-lineage input/output contract exists for each
      audience and names every application-owned versus model-owned field.
- [ ] Every completed decision can reproduce the exact Development evidence,
      audience context, prompt/schema version, model, reasoning effort, and
      response telemetry.
- [ ] Investment decisions preserve the evaluated 37-company universe,
      shortlist verdicts, full-memo inputs for plausible matches, thesis
      relationship, and a reason for both matches and suppressions.
- [ ] AI Engineering decisions preserve the evaluated build-surface roster,
      affected/not-affected verdicts, and a bounded experiment or a suppression
      reason.
- [ ] Insight rating or ordering is simple, inspectable, and evaluated against
      a small human-reviewed cohort; no unvalidated weighted composite is used.
- [ ] A fixed July 21 calibration sample has a recorded error audit and no
      ungrounded company, thesis, technical, or citation claim.
- [ ] The complete July 21 routable top-100 cohort finishes or every failure is
      explicitly accounted for; aggregate lane, suppression, cost, and cache
      telemetry are recorded.
- [ ] Insight operator tooling is non-interactive, resumable, machine-readable,
      covered by focused tests, and documented at the canonical CLI boundary.
- [ ] The live Insights audit surface exposes only current compatible
      Development-lineage decisions while historical proof remains preserved.
- [ ] Focused tests, `scripts/check-fast.sh`, and live API/browser verification
      pass.

## Milestones

- [ ] Milestone 1 — Freeze the Insight decision contract before model work.
      Acceptance: current v10/v7 behavior is audited; proposed per-audience
      schemas, exact input packets, application/model ownership, suppression
      semantics, and rating alternatives are written with no unresolved
      lineage ambiguity. Validate: focused schema/request tests and one
      deterministic packet rendering.
- [ ] Milestone 2 — Calibrate Investment on a small fixed cohort.
      Acceptance: 5–10 Developments include clear positives, clear negatives,
      and router-borderline cases; every company verdict is inspectable; only
      shortlisted companies load full memos; every surfaced claim is grounded.
      Validate: human audit table plus exact run telemetry.
- [ ] Milestone 3 — Calibrate AI Engineering on the same evidence standard.
      Acceptance: a small repo-grounded build-surface roster is frozen; sample
      outputs name a concrete technical decision and bounded evaluation, or
      suppress with a specific missing hook. Validate: human audit table plus
      exact run telemetry.
- [ ] Milestone 4 — Implement the canonical resumable run and read path.
      Acceptance: one clean current schema/store/CLI/API/UI path persists
      inputs, negative and positive decisions, lineage, cost, and failures;
      incompatible historical data cannot appear as current output. Validate:
      focused backend/frontend tests and restart-safe resume proof.
- [ ] Milestone 5 — Run and audit the July 21 top 100.
      Acceptance: all 97 currently routable Developments complete or have
      explicit failures; aggregate labels and a stratified sample are reviewed;
      ordering/rating behavior is defensible; no upstream data is refetched.
      Validate: live Feed-to-Insight drill-down, telemetry reconciliation, and
      `scripts/check-fast.sh`.
- [ ] Milestone 6 — Close out the proven boundary.
      Acceptance: architecture, status, model-routing, tokenomics, and project
      learnings reflect reality; unresolved downstream work is explicitly
      deferred; the complete project directory is archived.

## Execution Rules

- Hold Development grouping, rank, and v13 routing fixed during initial
  calibration. Record an upstream issue, but do not tune around one downstream
  example.
- Start with a small labeled cohort. Do not launch the full top 100 until both
  audience contracts are understandable from their stored outputs.
- Preserve all negative mapping and suppression decisions; do not keep only
  surfaced prose.
- Keep exact Event/Development evidence separate from reusable audience
  context and from model-generated interpretation.
- Treat company memos and build-surface descriptions as prior context, never
  as evidence that the current Development matters.
- Require the model to distinguish reported fact, attributed claim,
  inference, and open question.
- Keep prompts stable-prefix first and variable Development evidence last, but
  choose models by measured quality rather than cache hits alone.
- Treat repeated manual work, tool failure, or ambiguous telemetry as a harness
  defect. Fix the owning tool and add a regression in the same batch.
- Keep `tasks.md` the sole project tracker and update it after every meaningful
  batch.
- Run validation after each milestone and fix failures before advancing.
- Continue until the scoped project is complete or a true blocker requires
  Adi; do not stop after one successful model example.
- When `Done When` is satisfied, finalize `learnings.md` and archive the whole
  directory with the Project skill archive workflow.

## Decisions

- The Luna/medium router is frozen as the upstream candidate gate for this
  project. Its positives are not called Insights.
- The project proves per-Development audience judgment before daily editorial,
  PDF, or delivery replay.
- Investment begins from all 37 sourced companies; there is no static company
  exclusion. Relevance is decided for each Development.
- Compact context may shortlist; full company memos are retrieved only for
  plausible matches so the model sees rich context without one undifferentiated
  mega-prompt.
- AI Engineering will use a named build-surface roster symmetric to the
  Investment company universe, grounded in public requirements and this repo's
  architecture without inventing private BIT systems.
- A negative verdict is part of the deliverable.
- No weighted scalar will be introduced merely to make Insights look scored.
  Rating and ordering must be calibrated against human-reviewed examples.
- Terra/high is the initial quality baseline for deep Insight judgment. A model
  comparison occurs only if the fixed sample reveals a quality, latency, or
  cost reason to change.

## Open Questions / Blockers

- Should mapping and final surface/suppress judgment be one structured Terra
  call or two explicit stages? Resolve with the fixed Investment sample by
  comparing inspectability, evidence use, and cost—not architectural taste.
- What is the smallest Insight rating contract that adds rigor without
  laundering model judgment into a pseudo-objective number? Resolve before the
  full top-100 run.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| todo | Audit current Investment v10 / Engineering v7 requests, schemas, stores, and UI against Development lineage | parent | `resources/contract-audit.md` |
| todo | Freeze a 5–10 Development calibration cohort spanning clear and borderline routes | parent | `resources/calibration-cohort.md` |
| todo | Draft the smallest Investment mapping + Insight contract and compare one-call versus two-stage execution | parent | `resources/investment-contract.md` |
| todo | Audit the current Insight CLI/run tooling and specify the minimal render, pilot, resume, audit, and telemetry commands | parent | `resources/tooling-contract.md` |

## Backlog / Remaining Work

- [ ] Calibrate the AI Engineering build-surface roster and output contract.
- [ ] Choose and validate the Insight rating/ordering contract.
- [ ] Implement the clean resumable current-lineage store, CLI, API, and UI.
- [ ] Run the complete July 21 routable top-100 cohort.
- [ ] Reconcile cost/cache telemetry and qualitative errors.
- [ ] Update durable architecture/status/model/cost docs.
- [ ] Finalize `learnings.md`, run full validation, and archive the project.

## Validation / Test Plan

- Focused request/schema/store tests under `tests/insights/`.
- Routing and Development lineage regression tests under `tests/routing/` and
  `tests/evidence/`.
- `npm --prefix frontend test`, lint, and production build for UI changes.
- `bash scripts/check-fast.sh` at every implementation handoff.
- Live API and browser drill-down on `http://127.0.0.1:8797`, with temporary
  captures only under `tmp/`.
- Exact SQLite run counts, lineage hashes, token/cache usage, cost, and failure
  reconciliation before promotion.

## Progress Log

- 2026-07-28: [IN-PROGRESS] Created the project after validating the
  Luna/medium July 21 top-100 router. Archived the superseded
  `interview-readiness-audit` tracker with its unfinished ideas preserved.
  The active boundary is now current-lineage Development-to-Insight judgment.
- 2026-07-28: [DONE] Repaired the canonical Project skill archive helper after
  it failed on the normal case where `docs/projects/archive/` already exists.
  Added a regression that preserves older archives while atomically moving the
  requested project; the skill validator, five focused tests, and the agents
  control-plane `scripts/check-fast.sh` pass.
