# Submission Sprint

## Goal

Deliver a truthful, coherent, locally reproducible BIT Capital case-study package by 2026-07-20 that proves the system surfaces 3–5 genuinely useful, primary-cited frontier-AI insights for Investment and AI Engineering readers while keeping noise out.

## Why / Impact

The core evidence, ranking, routing, and per-audience Insight path is implemented and evaluated, but the reviewer story and submission artifacts lag behind the product. The remaining time should convert substantial engineering into legible proof against the weighted rubric, not expand infrastructure. Failure means a strong system reads as unfinished or its central signal-quality claim remains unproven.

## Scope / Non-Goals

### In Scope

- Reconcile repository docs, runtime behavior, real data, and the assignment rubric into one truthful gap audit.
- Consolidate semantically overlapping Events for editorial review and select 3–5 excellent developments with primary-source citations, audience-specific value, and honest limitations.
- Add the minimum human evaluation needed to defend signal/noise, insight quality, citation grounding, and scoring/ranking choices.
- Complete the missing local delivery proof: readable report/PDF and local alert/outbox behavior for both audiences, reusing the shared intelligence core.
- Produce the reviewer landing path, final report, architecture/prompt/evaluation/tokenomics material, database guidance, and a clean local demo/package smoke.
- Polish only the desktop product moments used in the demo or needed to make the selected proof understandable.
- Prepare, but do not send, the submission email and optional demo recording plan.

### Out of Scope

- Broad new RSS, GitHub, arXiv, blog, or video ingestion.
- Attention-score v2, learned ranking, broad semantic clustering, or a new Insight prompt generation contract.
- Large Registry/graph expansion, production deployment, mobile polish, or real external notifications.
- Publishing, uploading, granting access, sending email, or submitting without Adi's explicit current-session approval.

## Context / Constraints

- Date started: 2026-07-17.
- Deadline: 2026-07-20, assumed end of day Europe/Berlin unless Lars clarifies otherwise.
- `docs/STATUS.md` (last verified 2026-07-16) records a complete July 5–15 path: 1,100 audience-routing decisions and 947 audience Insight decisions, of which 404 surfaced and 543 were suppressed.
- `docs/projects/archive/insight-format-v10/tasks.md` is the latest completed project. It passed 354 backend tests, 43 frontend tests, frontend lint, and production build.
- The previous active tracker was correctly archived, but `docs/STATUS.md` still points to it as active and `docs/references/reviewer-guide.md` describes an obsolete pre-Insights state. Reconciliation is the first batch.
- The working tree was clean and `main` matched `origin/main` at project start.
- The always-on built SPA is `http://127.0.0.1:8797`; rebuild with `npm --prefix frontend run build` before visual verification.
- Cost is telemetry, not a quality gate. External actions remain approval-gated.

## Done When

- [ ] A cold reviewer can follow one public-facing landing document to install/run the app, inspect the real databases, reproduce checks, understand architecture and trade-offs, and find every required deliverable.
- [ ] The final report presents 3–5 non-duplicative, primary-cited real insights and explains why each matters to its intended audience.
- [ ] Signal/noise and insight-quality claims are supported by a documented human evaluation with examples, failure analysis, and defensible metrics or judgment criteria.
- [ ] Both audiences have a coherent in-app view plus a local report/PDF and alert/outbox proof; no external notification is sent.
- [ ] Architecture, model/prompt rationale, evaluation, tokenomics, limitations, data inventory, and next steps are current and internally consistent.
- [ ] `scripts/check-fast.sh`, the package/demo smoke, citation/link checks, and desktop visual review pass from the documented reviewer path.
- [ ] Private/local-only material is excluded from the reviewer path, repository state is clean, and submission text/artifacts are prepared for Adi's review.
- [ ] Adi has an explicit final approval gate before any external submission action.

## Milestones

- [ ] M0 — Freeze the truthful submission gap and three-day critical path. Acceptance: every rubric requirement is mapped to implemented proof, missing proof, or explicit limitation; stale handoff claims are identified. Validate: compare runtime/data, `docs/STATUS.md`, assignment prompt, and reviewer path.
- [ ] M1 — Prove the editorial intelligence claim. Acceptance: obvious cross-Event duplicates are consolidated for review; 3–5 final developments are selected; a human evaluation and citation audit support quality/noise claims. Validate: deterministic selection artifact plus manual primary-source checks.
- [ ] M2 — Complete minimum delivery proof. Acceptance: both persona outputs can be rendered as a readable report/PDF and placed into a local alert/outbox with citations and no network side effect. Validate: focused tests plus end-to-end local smoke.
- [ ] M3 — Assemble the submission package. Acceptance: landing document, final report, architecture, prompts, evaluation, tokenomics, data inventory, limitations, and reviewer guide are current, cross-linked, and rubric-mapped. Validate: cold-start walkthrough and link/claim audit.
- [ ] M4 — Final rehearsal and release gate. Acceptance: full checks pass, built desktop UI is visually reviewed, demo script works, private/process-only material is excluded, and draft submission text is ready. Validate: `scripts/check-fast.sh` plus documented package smoke; external action remains blocked pending Adi approval.

## Execution Rules

- Optimize for the weighted rubric and the central question: did it surface something genuinely worth knowing while keeping noise out?
- Keep work sequential across shared product/editorial boundaries: freeze the gap, then the selected intelligence proof, then delivery/package integration.
- New infrastructure or prompt work requires evidence that it materially improves submission proof within the deadline.
- Treat exact Event grouping and per-Event Insight generation as frozen. Consolidation is a downstream editorial boundary.
- Keep every public claim backed by current runtime/data evidence or label it as a limitation.
- Keep `tasks.md` single-writer; delegated read-heavy audits may write only topic-based resources.
- Run validation after each milestone or risky batch and fix failures before advancing.
- Continue until the project is done or a true blocker needs Adi; do not stop after one task while actionable scoped work remains.
- Update this tracker after every meaningful batch and archive it once Done When is satisfied.

## Decisions

- 2026-07-17: Start a new submission-sprint tracker rather than reopening the completed Insight-format tracker.
- 2026-07-17: Treat packaging, editorial selection, evaluation, and delivery proof as the critical path; defer broader product expansion.
- 2026-07-17: Use the existing July 5–15 evaluated cohort as submission evidence. Do not spend time on a wider collection window unless the audit finds a fatal evidence gap.
- 2026-07-17: Keep semantic consolidation downstream and editorial; do not change exact evidence grouping or per-Event prompt contracts.
- 2026-07-17: Consolidation consumes only surfaced current-contract Insights,
  preserves the immutable per-Event notes, groups semantic duplicates, and
  chooses the strongest existing representative before any optional synthesis.
- 2026-07-17: The submission proof is 3–5 unique developments total, with one
  or both audience treatments where the evidence genuinely supports them; it
  is not 3–5 unrelated items per audience.

## Open Questions / Blockers

- Final 3–5 selection and exact consolidation rule require evidence review; this is current work, not a user blocker.
- Whether to record an optional short demo video is a Day 3 decision after the package smoke is stable.
- External submission method/access and sending remain approval-gated; they do not block local package preparation.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| in_progress | Reconcile rubric, docs, runtime/data, and reviewer path into a prioritized submission gap audit. | parent | `resources/submission-gap-audit.md` |
| pending | Define the smallest reversible consolidation contract and audit duplicate/non-duplicate controls. | parent | `resources/insight-editorial-audit.md` |
| pending | Select and source-check the strongest 3–5 unique developments. | parent | `resources/final-insight-selection.md` |
| pending | Measure useful yield, citation validity, duplicate rate, persona fit, and workflow telemetry. | parent | `resources/submission-evaluation.md` |
| pending | Implement and verify the briefing/PDF/local-outbox delivery proof. | parent | product + focused tests |

## Backlog / Remaining Work

- [ ] Rebuild `docs/STATUS.md` Current Direction and `docs/references/reviewer-guide.md` from verified reality.
- [ ] Implement or formalize downstream consolidation and produce the reviewed unique-development candidate set.
- [ ] Run and document human quality/citation evaluation; select final 3–5.
- [ ] Implement minimum report/PDF plus local alert/outbox proof for both audiences.
- [ ] Create the explicit public/reviewer landing document required by the assignment.
- [ ] Write the rubric-mapped final report, limitations, tokenomics, data inventory, and model/prompt rationale.
- [ ] Perform desktop visual polish only where the demo journey needs it; rebuild tracked SPA.
- [ ] Run cold-start, package, link, citation, privacy, and full-check validation.
- [ ] Prepare submission email text and optional video plan; do not send or upload without approval.
- [ ] Review project learnings and archive this tracker after completion.

## Validation / Test Plan

- Baseline and final: `scripts/check-fast.sh`.
- Targeted backend/frontend tests for every new delivery or consolidation boundary.
- Query current SQLite stores and local APIs for all quantitative claims.
- Use the built SPA at `http://127.0.0.1:8797` for the documented desktop demo path.
- Render and visually inspect every generated PDF page.
- Open every final 3–5 primary citation and verify it supports the exact claim.
- Execute the reviewer quick start/package smoke from the landing document in a clean-enough local environment.
- Search public-facing artifacts for private context, stale project paths, unsupported claims, and machine-specific absolute paths.

## Progress Log

- 2026-07-17: [IN-PROGRESS] Returned after a rest day; reconciled the case prompt, system status, archived Insight-format tracker, Git history, and project workflow. Confirmed that the implementation is materially ahead of the reviewer/package story and opened the submission sprint.
