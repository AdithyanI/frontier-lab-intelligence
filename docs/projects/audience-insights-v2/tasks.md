# Audience Insights v2

## Goal

Ship two genuinely audience-specific cited-insight products—Investment and AI
Engineering—over the same frozen evidence and citation core, covering the nine
complete Feed days from 2026-07-05 through 2026-07-13 without combining the two
audiences into one compromise record.

## Why / Impact

The v1 prototype proved exact cited extraction but asked one prompt to choose a
claim for both audiences and displayed both implications together. BIT asks for
one shared intelligence core with tailored last-mile outputs. V2 must show that
the same evidence system can independently surface what changes an investment
thesis and what changes engineering practice, while keeping noise out.

## Scope / Non-Goals

### In Scope

- One shared immutable evidence-packet builder and application-owned exact
  citation binder.
- Independent versioned Investment and AI Engineering prompts, schemas, run
  metadata, cache namespaces, and evaluation evidence.
- Independent claims are allowed: one envelope may yield an Investment insight,
  an Engineering insight, both with different claims, or neither.
- A per-audience daily editorial pass that selects and orders 3–5 verified
  candidates, removes same-day redundancy, and may return fewer on a thin day.
  It returns runner-owned IDs plus short audit reasons; it cannot rewrite claims,
  citations, or factual analysis.
- Candidate breadth from already-triaged evidence. Begin with kept envelopes
  inside each day's top 50 stable Feed ranks (360 envelopes / 720 audience
  extraction calls), audit ranks 51–100 and a small stratified drop sample for
  recall, and widen per day to top 75 and then top 100 when yield, diversity, or
  useful misses justify it. The hard top-100 bound is 664 kept envelopes across
  nine complete days, approximately 1,328 audience extraction calls.
- Provider-backed X Article retrieval through the existing canonical artifact
  library: raw response preservation, deterministic normalized text, source
  provenance, retries, cost telemetry, and exact-citation eligibility.
- A two-view Insights UI with separate Investment and AI Engineering routes or
  query state, audience-specific copy and fields, per-day counts, and exact
  citations.
- Two-day quality gate (known 2026-07-11 plus one blind day), followed by all
  nine days automatically if the gate passes.
- Prompt-quality evaluation, citation validity, daily yield, redundancy,
  cache/usage/cost telemetry, architecture docs, tests, and browser proof.

### Out of Scope

- HTML/PDF briefing generation, alerts, external delivery, or sending.
- Registry or following-graph expansion, role weighting, or Feed-score tuning.
- New discovery sources such as RSS, GitHub, arXiv, blogs, LinkedIn, or general
  web-search evidence.
- Mobile polish, submission packaging, or final-report completion.
- A generic summarization layer before measured context-limit failures exist.

## Context / Constraints

- Date started: 2026-07-14.
- Predecessor: `docs/projects/archive/cited-insights-v1/tasks.md`.
- V1 resources remain under `docs/projects/cited-insights/resources/` because
  tracked following manifests reference that stable path.
- The current nine complete triage runs contain 664 kept envelopes within daily
  ranks 1–100. No extraction sees Feed score, engagement, follower count, or
  Registry prominence; attention selects the bounded cohort, content decides.
  Feed rank remains secondary provenance and never becomes editorial rank.
- Default model is `gpt-5.6-luna` at medium reasoning through LiteLLM. Cost is
  observed telemetry, never a quality gate. Stable prompt content precedes
  variable evidence and uses audience-specific prompt-cache namespaces.
- Adi authorized the in-scope provider and model calls needed for the long run
  and prefers quality over minimizing spend. Use Luna-medium for the proven
  per-envelope extraction boundary and Luna-high for the low-volume comparative
  daily editor; escalate failed or ambiguous extraction cases only when recorded
  calibration evidence justifies it.
- X Articles are currently catalogued but not body-fetched. TwitterAPI.io's
  documented article endpoint accepts the article tweet ID, returns structured
  `contents`, and costs 100 provider credits per article.
- No external publishing or sending is authorized.

## Done When

- [ ] Investment and AI Engineering use independent prompt/schema versions and
  can emit different cited claims from the same evidence packet.
- [ ] Every displayed insight has an application-bound exact quote and immutable
  source URL; citation failures and unavailable evidence are never published.
- [ ] The 2026-07-11 known day and one blind day pass the recorded quality gate
  for both audiences before expansion.
- [ ] All nine complete days are materialized for both audiences after the gate,
  with 3–5 selected items when supported and no forced padding on thin days.
- [ ] Same-day duplicates are removed and each selected item's audience value is
  inspectable without inventing a numeric importance score.
- [ ] The daily editor selects only verified candidate IDs, and its displayed
  order is distinct from the original Feed rank retained in provenance.
- [ ] Relevant X Article bodies in the bounded cohort are provider-fetched or
  carry a durable explicit terminal reason; article previews alone do not support
  published article claims.
- [ ] Insights has separate Investment and AI Engineering views with stable URLs,
  date navigation, audience-specific fields, and visible exact citations.
- [ ] Evaluation records citation validity, audience usefulness, actionability,
  unsupported-inference failures, yield, redundancy, cache reads, tokens, and
  provider-reported cost.
- [ ] `scripts/check-fast.sh` passes and the two audience views are browser-checked.
- [ ] Tracker, learnings, architecture, status, and build log are current; archive
  the project only when this insight-only scope is genuinely complete.

## Milestones

- [ ] M1 — Evidence completeness and X Articles. Acceptance: audit the bounded
  cohort's evidence gaps; implement and test a resumable TwitterAPI.io article
  adapter that preserves request Post ID, canonical Article identity, raw
  response, block order, normalized text, hashes, and fetch time in the artifact
  library. Validate: focused provider/artifact tests plus a small real canary.
- [ ] M2 — Audience contracts and calibration. Acceptance: freeze independent
  prompt/schema contracts and quality rubrics; run the v1 oracle plus a blind
  sample for both audiences; audit a small kept lower-rank and dropped sample;
  retain prompt-version comparisons and exact-citation results. Validate:
  fixtures, an independent Luna-high rubric pass, and an agent spot-check.
- [ ] M3 — Resumable audience runs and daily editor. Acceptance: freeze selected
  cohorts, run both audiences independently, select runner-owned IDs into 3–5
  item daily sets without duplicate stories, and preserve full telemetry.
  Validate: two-day gate, resumability tests, and deterministic selection checks.
- [ ] M4 — Nine-day expansion. Acceptance: after M3 passes, complete all nine
  days for both audiences with no unhandled failures and record yield/quality.
  Validate: run reconciliation and stratified audit.
- [ ] M5 — Audience Insights UI. Acceptance: separate stable Investment and AI
  Engineering views, audience-specific rows, exact citations, and date counts.
  Validate: API/frontend tests, production build, and local browser proof.
- [ ] M6 — Evaluation and closeout. Acceptance: durable evaluation report,
  architecture/status/build-log sync, check-fast, learnings, and tracker archive.

## Execution Rules

- Continue through successive milestones without stopping for permission once
  Adi explicitly hands off the project; stop only for a true blocker, destructive
  action, missing secret, or a product decision outside the frozen contract.
- Do not stop after implementing schemas, a canary, one audience, one day, or
  the UI shell while later actionable milestones remain.
- Use the two-day quality gate to prevent scaling a bad prompt. If it fails,
  diagnose, version, and rerun bounded calibration rather than broadening scope.
- The gate is autonomous and deterministic; it never pauses overnight for Adi.
  Require zero citation/attribution failures, zero same-day duplicate stories,
  and at least 80% of selected items passing the recorded audience usefulness
  and actionability rubric. Freeze the best of at most three prompt versions.
- Never pad a thin day to hit a quota and never promote preview metadata into an
  article-body claim.
- Keep prompt iterations and failed runs as provenance; do not overwrite history.
- Keep one tracker writer. Delegate only bounded read-heavy audits or isolated
  implementation after shared contracts are frozen.
- Checkpoint this file after every meaningful batch and run repo-native tests at
  each milestone boundary.

## Decisions

- 2026-07-14: Archive v1 and start a clean v2 tracker because the audience
  contract materially changed and the 725-line tracker obscured the live work.
- 2026-07-14: One shared evidence/citation core, two independent editorial
  products. This satisfies the assignment's “shared core, tailored outputs”
  boundary without duplicating ingestion.
- 2026-07-14: Delivery is deferred. V2 proves insight quality and in-app audience
  separation before briefing/export work resumes.
- 2026-07-14: Freeze Registry and Feed ranking during v2. Missing output quality
  is first treated as an extraction/editorial problem, not solved by adding more
  monitored accounts.
- 2026-07-14: Use a provider article endpoint rather than browser scraping for X
  Articles; raw evidence and exact citation remain mandatory.
- 2026-07-14: Use daily top-100 kept candidates, not v1's top-20 limit, as the
  hard ceiling because prior audits found substantive lower-ranked evidence.
  Start execution at top-50 and widen per day to top-75/top-100 when a
  predeclared yield, diversity, and recall audit finds useful misses.
- 2026-07-14: Daily editorial order is an audience-specific product decision,
  not another opaque score. Editors may select and order only verified IDs;
  original Feed rank stays visible as secondary provenance.
- 2026-07-14: Full artifact evidence remains verbatim. Measured context outliers
  use deterministic source-hashed sections or chunks; an LLM summary is never
  treated as the primary cited source.
- 2026-07-14: Implement the product contract as versioned code, schemas,
  validators, and resumable runners rather than manual result files. Preserve
  the working v1 code as historical proof, but make v2 a clean target model
  without compatibility shims.
- 2026-07-14: Quality-first model routing is authorized: Luna-medium remains the
  evaluated extraction baseline, while the 18 low-volume daily editorial calls
  may use Luna-high. Record cache reads, tokens, reasoning effort, and reported
  cost for every run.

## Open Questions / Blockers

- Awaiting Adi's answers to the product-contract questions in the planning chat:
  audience naming/default, ticker policy, audience overlap, daily quota behavior,
  intended reader within each audience, editorial selection, model escalation,
  candidate breadth, deduplication across days, and autonomy when qualitative
  outputs are merely mediocre rather than technically failed.
- No implementation blocker. The provider article endpoint and current secrets
  path appear sufficient, but a paid one-article canary begins only after handoff.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| in_progress | Freeze the v2 product contract with Adi and convert answers into decisions and acceptance rubrics. | parent | `tasks.md` |
| todo | Audit the nine-day candidate/evidence cohort, especially X Articles and long-context outliers. | explorer | `resources/evidence-cohort-audit.md` |
| todo | Draft independent Investment and AI Engineering schema/prompt/evaluation contracts for bounded calibration. | parent | `resources/audience-contracts.md` |

## Backlog / Remaining Work

- [ ] Complete M1–M6 in order, respecting the two-day gate.
- [ ] Record provider and LLM spend after every paid batch.
- [ ] Review and finalize `learnings.md` before archive.
- [ ] Revisit delivery only in a successor project after v2 is proven.

## Validation / Test Plan

- Focused tests for article response normalization, raw hashing, retries,
  resumability, schema validation, prompt routing, citation binding, audience
  isolation, daily selection IDs, API filtering, and frontend state.
- Citation binding rejects non-unique quote matches unless the model-provided
  evidence block/section disambiguates the exact source location.
- Bounded real article canary before cohort retrieval.
- Known-day and blind-day autonomous rubric review plus agent spot-check before
  nine-day expansion; do not wait for Adi overnight.
- Morning MVP floor: both audiences work end to end on known 2026-07-11 plus
  blind 2026-07-09 with separate stable UI URLs, 3–5 selected items or an
  explicit honest thin-day result, uniquely bound citations, no duplicate
  stories, article terminal states, resumability, telemetry, tests, build, and
  browser proof. The target remains all nine days after this gate; breadth must
  not displace the credible two-day product.
- Run-store reconciliation: expected, complete, failed, selected, verified,
  token, cache, and cost counts.
- Local browser proof at `http://127.0.0.1:8797/insights` after frontend build.
- `scripts/check-fast.sh` before handoff and closeout.

## Progress Log

- 2026-07-14: [PLANNING] Archived the superseded blended v1 tracker, opened the
  audience-specific v2 project, confirmed nine complete days and 664 kept
  top-100 candidates, and identified the documented provider X Article endpoint.
  Product-contract questions remain open before the long autonomous handoff.
- 2026-07-14: [PLANNING] Three independent reviews converged on the shared-core,
  split-extractor, ID-only daily-editor architecture. They added bounded recall
  auditing, audience-isolated run storage/API state, explicit Feed-rank
  provenance, non-unique quote protection, and verbatim long-context handling.
- 2026-07-14: [PLANNING] Adi granted broad implementation judgment, authorized
  in-scope API/model calls, and set a solid working MVP tomorrow morning as the
  handoff bar. Product decisions that change the audience contract remain the
  only questions to settle before the explicit autonomous start.
- 2026-07-14: [VALIDATION] The planning/archive checkpoint passed 255 backend
  tests, 17 frontend regression tests, frontend lint (four pre-existing Fast
  Refresh warnings only), and the production frontend build via
  `scripts/check-fast.sh`.
