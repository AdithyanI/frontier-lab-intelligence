# Evidence Audience Routing

## Goal

Define and prove the smallest auditable decision that assigns one complete,
correctly attributed, Feed-kept Evidence envelope to AI Engineering,
Investment, both, or neither before any new Insight generation is designed or
run. Existing Feed triage remains the sole general keep/drop gate.

## Why / Impact

The archived Audience Insights v2 project mixed routing, extraction,
editorial selection, verification, reconciliation, and publication before the
first product decision was easy to inspect. That made failures hard to reason
about with Adi and created multiple apparent sources of truth.

This project restores one visible boundary: inspect kept Evidence, make two
audience-specific relevance judgments in one model call, and prove them on
real envelopes. If this boundary is wrong, every later Insight is noise; if it
is clear and stable, a separate Insight-generation project can consume only
positive routes without reviving the old stack.

## Scope / Non-Goals

### In Scope

- Define the exact immutable Evidence-envelope blocks presented to the router,
  preserving the author, relationship, source URL, and provenance of each
  root, continuation, reply, quote-post, and accepted artifact block.
- Use one combined routing call with two independently reasoned audience
  judgments: AI Engineering relevant/not relevant and Investment relevant/not
  relevant, each with one short evidence-grounded reason.
- Keep existing Feed triage as the only keep/drop decision. The audience
  router does not write a second keep/drop field.
- Write the routing prompt with Adi, keeping the two audience standards
  distinct and excluding Feed rank, engagement, prominence, and other outcome
  hints from the model input.
- Implement one authoritative, versioned storage/API path only after the input,
  schema, and prompt are approved.
- Inspect one exact envelope end to end, then run a small frozen cohort of
  top-ranked kept envelopes to inspect Engineering, Investment, both, and
  neither behavior before broader evaluation.
- Add a compact Feed audience filter and per-envelope routing disclosure so
  Adi can inspect the first real outputs in the existing evidence workspace.
- Keep the decision traceable from the UI/API back to the exact Evidence
  envelope and model/run provenance.

### Out of Scope

- Writing or publishing audience Insight prose.
- Restoring the deleted Audience Insights v2 databases or treating archived
  reviewer/editor/publication machinery as the current contract.
- Daily editorial ranking, independent publication audit, reconciliation,
  briefing/export, alerts, or delivery.
- Bulk nine-day generation before the one-envelope and one-day reviews pass.
- Expanding the Registry, following graph, collection cohort, or artifact
  acquisition policy.
- External submission, publication, or contact without Adi's explicit
  current-session approval.

## Context / Constraints

- Date started: 2026-07-15.
- Submission deadline: 2026-07-20. Optimize for a coherent, defensible case
  study and a small excellent proof, not platform completeness.
- The superseded implementation and its learnings are archived at
  [`../archive/audience-insights-v2/tasks.md`](../archive/audience-insights-v2/tasks.md).
- The prior design draft is historical input, not authority:
  [`../archive/audience-insights-v2/resources/minimal-envelope-routing-v0.md`](../archive/audience-insights-v2/resources/minimal-envelope-routing-v0.md).
  Its recommendation that Feed alone owns keep/drop was reconfirmed with Adi
  on 2026-07-15. The new router lives downstream of kept Feed envelopes.
- Generated Audience Insights v2 data was intentionally deleted. Do not add
  compatibility reads, dual writes, old-schema fallbacks, or legacy database
  migrations unless Adi explicitly requests them.
- Canonical artifacts must come from the cleaned primary-author lineage.
  Reaction text may be independently useful, but reaction-owned links must not
  become root-author artifacts or claims.
- The first prompt-design envelope is
  `56ec1710fbc2f39b18aad549d21b38581a115b5dcf09d9b79dd4522d56bef56d`
  on 2026-07-12. It contains Satya Nadella's root post, the full linked X
  Article, and independently authored quote-posts. Fetch live data rather than
  trusting archived counts or ranks.
- Work tightly with Adi at each shared-boundary decision. Do not infer approval
  to scale a prompt from approval of one example.
- All LLM calls must use the shared LiteLLM path and required metadata/cost
  telemetry. Stable long prefixes should follow the repository's cache-key
  contract.

## Routing Schema — Approved For First Cohort

```json
{
  "ai_engineering": {
    "relevant": true,
    "reason": "Short evidence-grounded explanation."
  },
  "investment": {
    "relevant": false,
    "reason": "Short evidence-grounded explanation."
  }
}
```

Application invariants:

- Both judgments are required and independently reasoned in one model call.
- The application derives the convenient audience list and the four display
  outcomes; the model does not author those redundant fields.
- A `neither` audience result remains a valid result for a Feed-kept envelope;
  it does not rewrite or contradict Feed triage.
- IDs, hashes, prompt versions, model/run telemetry, and timestamps are
  application-owned fields, never model-authored fields.
- Mechanically invalid evidence packets fail before routing; they are not
  classified as `drop`.

## Done When

- [ ] Adi approves a documented envelope-input contract, including the exact
  treatment of root text, same-author continuations, replies, quotes, and
  artifacts.
- [x] Adi approves the routing semantics: one combined call, two independent
  audience judgments with separate reasons, and no second keep/drop field.
- [ ] Adi reviews the short prompt and exact first-cohort outputs.
- [ ] One versioned routing path stores and returns one authoritative pair of
  audience judgments per envelope/run with evidence hash, prompt version,
  model, cost, and rationales; no live product reads old Insight tables.
- [ ] The first envelope is routed and reviewed with Adi, with its input blocks
  and output visible and traceable in the UI/API.
- [ ] A small frozen top-kept cohort is routed with Luna-medium; outcomes,
  prompt-cache reads, response cost, and qualitative disagreements are
  recorded before any expansion.
- [ ] Feed exposes audience filters and compact reasons without generating
  Insight prose or changing the existing triage result.
- [ ] Focused tests, `bash scripts/check-fast.sh`, live API proof, and rendered
  desktop QA pass; architecture/status docs reflect the final boundary.
- [ ] Project learnings are finalized and the tracker is archived before the
  next Insight-generation project begins.

## Milestones

- [ ] Milestone 1 — Freeze and implement the first-cohort architecture.
  Acceptance: exact input blocks, approved schema, short prompt, immutable
  run storage, and API projection work on the Satya envelope. Validate:
  focused packet/runner/API tests and exact record inspection.
- [ ] Milestone 2 — Run and inspect a small top-kept cohort. Acceptance:
  Luna-medium outputs, cache/cost telemetry, outcome distribution, and
  qualitative review are recorded. Validate: resumable rerun and direct
  database/API comparison.
- [ ] Milestone 3 — Expose routing in Feed. Acceptance: existing triage filters
  remain authoritative while audience filters, badges, and short reasons make
  the cohort inspectable. Validate: production build and rendered desktop QA.
- [ ] Milestone 4 — Freeze the routing boundary and close out. Acceptance:
  architecture, status, model/prompt references, evaluation evidence, and
  limitations are current; Insight generation is a separate explicit next
  project. Validate: `bash scripts/check-fast.sh` and archive this tracker.

## Execution Rules

- Keep work scoped to the current milestone; do not restore the archived
  multi-stage pipeline to solve a routing problem.
- Work sequentially across shared contracts: input packet, schema, prompt,
  storage, first envelope, then the small frozen cohort.
- Stop for Adi's qualitative review before scaling beyond the first cohort.
- Prefer one source of truth and a clean migration. Do not add compatibility
  shims or silent fallback reads.
- Preserve evidence exactly. The model may classify it but may not rewrite,
  merge authors, or manufacture source attribution.
- Run validation after each risky batch and fix failures before advancing.
- Append meaningful implementation chunks to
  `docs/references/build-log.jsonl` and update architecture/status when the
  boundary changes.
- Keep `Current Batch` as the live resume point and update this tracker before
  every handoff.
- Finalize `learnings.md` and archive the project when `Done When` is met.

## Decisions

- This is a fresh project. The archived Audience Insights v2 project is
  historical evidence, not an active tracker to resume.
- Routing comes before Insight generation; no Insight prose belongs in this
  project.
- Feed triage remains the sole general keep/drop gate. Audience routing runs
  downstream on kept envelopes and never overwrites triage.
- One combined Luna-medium call returns two independent audience judgments and
  separate reasons. “Independent” does not mean separate routing calls.
- The first proof is one envelope followed by a small frozen top-kept cohort,
  not a full day or all available data.
- Feed rank remains display/order provenance and must not influence the model's
  routing judgment.
- Insight generation remains a separate follow-up stage and may use a higher
  reasoning effort only after routing is qualitatively understood.
- The v2 review renderer uses a human-readable YAML-style hierarchy rather
  than XML/CDATA. It decodes HTML entities, represents link-only primary posts
  by their artifact relationship, omits pure retweets and transport-only
  links, excludes reactions shorter than 40 characters, and removes reactions
  whose text is at least 80% duplicated by supplied primary evidence.

## Open Questions / Blockers

- Which reply and quote-post blocks belong in the model packet, and when does a
  deterministic size bound become necessary? Inspect real packet sizes before
  choosing a top-N rule.
- Where should the new authoritative routing records live? Choose one clean
  database/schema and prohibit UI fallback to archived Insight data.
- What small cohort size is sufficient for the first qualitative review? Start
  with the top kept envelopes and stop before a broad run.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Implement the independent packet/schema/prompt and minimal resumable Luna-medium run record without old Insight-table dependencies. | parent | `resources/satya-routing-v1.md` |
| done | Map the narrowest reuse points across triage runs, artifact packet assembly, API projection, and Feed types without editing shared files. | explorer | — |
| done | Implement the isolated audience-routing model boundary, prompt, and unit tests; do not touch runner, CLI, tracker, or shared integration files. | worker | `resources/satya-routing-v1.md` |
| in_progress | Review the exact, unexecuted Satya v2 request with Adi; run it only after the hierarchical input is accepted. | parent | `resources/satya-routing-v2-attempt.md`; `../../../src/fli/prompts/audience_routing_v2.txt` |

## Backlog / Remaining Work

- [ ] Add deterministic packet-integrity and schema-consistency validation.
- [ ] Audit a bounded sample of existing Feed drops later to estimate whether
  the upstream gate hides audience-relevant evidence.
- [ ] Expand beyond the first cohort only after Adi's qualitative review.
- [ ] Add the read-only API projection and compact Feed audience filters,
  badges, and reasons only after Adi reviews the quick sample.
- [ ] Update architecture, status, model-routing/prompt references, and build log.
- [ ] Run focused tests, `bash scripts/check-fast.sh`, API proof, and desktop QA.
- [ ] Review and finalize `learnings.md`, then archive this project.

## Validation / Test Plan

- Run focused packet, runner, storage, API, and frontend regression tests as
  each boundary is introduced.
- Run `bash scripts/check-fast.sh` at every milestone and before handoff.
- Query the canonical routing database directly and compare it with the API for
  the same envelope/run; no UI-only rank or stale fallback may alter results.
- Verify the first envelope deep-link resolves to the exact dated Evidence
  envelope and that its displayed decision matches the canonical record.
- Use `$agent-browser` against `http://127.0.0.1:8797` for rendered desktop QA
  after frontend behavior exists.

## Progress Log

- 2026-07-15: [IN-PROGRESS] Created the fresh Evidence Audience Routing tracker
  after archiving Audience Insights v2. Captured the candidate two-field schema,
  the disagreement with the archived keep/drop assumption, the first exact
  envelope, strict non-goals, milestone gates, and the cold-resume sequence for
  another engineer.
- 2026-07-15: [REPLANNED] Adi clarified the intended stepwise product boundary:
  existing Feed triage remains the sole keep/drop gate; one Luna-medium call
  assigns each kept envelope independently to AI Engineering and Investment;
  Insight generation follows later only for positive routes. Replaced the
  full-day promise with a small frozen top-kept cohort and made Feed inspection
  part of the first proof.
- 2026-07-15: [IN-PROGRESS] Implemented a fresh envelope-level audience router
  and resumable run database with no old Insight-table dependency. Ran exactly
  one authorized Luna-medium call for the Satya envelope: 16 attributed blocks
  (root, 14 quote-posts, full self-published X Article) routed to both audiences
  for $0.005958. The exact input, schema, raw output, hashes, and telemetry are
  frozen in `resources/satya-routing-v1.md`; no additional call or UI work will
  proceed before Adi's qualitative review.
- 2026-07-15: [IN-PROGRESS] Drafted a context-first v2 routing prompt for Adi's
  review after the v1 prompt was rejected as pipeline-centric and overbuilt.
  The draft explains the product, current X evidence collection, packet
  assembly, artifacts and reactions, then defines the two audience decisions
  and approved schema. It is intentionally not wired or executed yet.
- 2026-07-15: [APPROVED] Adi approved the context-first v2 prompt for the first
  comparison and requested sequential review of top kept envelopes. The first
  v2 run is limited to the Satya envelope; it will establish the shared cache
  prefix, and the next envelope will run only after qualitative review.
- 2026-07-15: [IN-PROGRESS] Wired the approved prompt to a semantic hierarchy
  that groups the primary post, first-party artifact, and continuations before
  separately authored reactions. The first cohort uses one stable cache lane;
  internal refs and pure retweets are omitted from model input. Frozen the
  exact unexecuted Satya request in `resources/satya-routing-v2-attempt.md` for
  Adi's review before any v2 model call.
- 2026-07-15: [IN-PROGRESS] Replaced the XML/CDATA attempt with readable YAML
  and conservative deterministic cleanup. The frozen Satya request now renders
  8 substantive reactions from 14 collected quote-posts after removing one
  URL-only reaction, two sub-40-character reactions, and three reactions that
  mostly repeated the full supplied article. No v2 model call has been made.
- 2026-07-15: [VALIDATED] Confirmed the attempt file exactly matches the
  runtime prompt and rendered input, including its hashes and 8-reaction
  count. `scripts/check-fast.sh` passed with 473 Python and 37 frontend tests;
  the four existing Fast Refresh lint warnings remain non-blocking.
