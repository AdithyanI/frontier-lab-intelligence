# Evidence Audience Routing

## Goal

Define and prove the smallest auditable decision that turns one complete,
correctly attributed Evidence envelope into a keep/drop result and explicit
AI Engineering and/or Investment audience assignments, before any new Insight
generation is designed or run.

## Why / Impact

The archived Audience Insights v2 project mixed routing, extraction,
editorial selection, verification, reconciliation, and publication before the
first product decision was easy to inspect. That made failures hard to reason
about with Adi and created multiple apparent sources of truth.

This project restores one visible boundary: inspect the Evidence, make one
small structured routing decision, and prove it on real envelopes. If this
boundary is wrong, every later Insight is noise; if it is clear and stable, a
separate Insight-generation project can build on it without reviving the old
stack.

## Scope / Non-Goals

### In Scope

- Define the exact immutable Evidence-envelope blocks presented to the router,
  preserving the author, relationship, source URL, and provenance of each
  root, continuation, reply, quote-post, and accepted artifact block.
- Decide the minimal structured routing schema. The current candidate has an
  explicit `decision` (`keep` or `drop`) and `audiences` containing zero, one,
  or both of `ai_engineering` and `investment`.
- Decide whether keep/drop is an independent model judgment or an
  application-derived consequence of audience assignment.
- Write the routing prompt with Adi, keeping the two audience standards
  distinct and excluding Feed rank, engagement, prominence, and other outcome
  hints from the model input.
- Implement one authoritative, versioned storage/API path only after the input,
  schema, and prompt are approved.
- Inspect one exact envelope end to end, calibrate representative Engineering,
  Investment, both, and neither cases, then run and audit one complete day.
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
  It assumed Feed alone owned keep/drop; Adi's current proposal reopens that
  boundary and may store keep/drop beside audience assignment.
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

## Candidate Schema — Not Frozen

```json
{
  "decision": "keep",
  "audiences": ["ai_engineering", "investment"],
  "reason": "Short evidence-grounded explanation."
}
```

Candidate application invariants to review:

- `drop` implies an empty `audiences` list.
- `keep` implies at least one audience.
- “Both” is represented by the two audience values, not a special third value.
- IDs, hashes, prompt versions, model/run telemetry, and timestamps are
  application-owned fields, never model-authored fields.
- Mechanically invalid evidence packets fail before routing; they are not
  classified as `drop`.

## Done When

- [ ] Adi approves a documented envelope-input contract, including the exact
  treatment of root text, same-author continuations, replies, quotes, and
  artifacts.
- [ ] Adi approves the minimal routing schema, semantics, consistency rules,
  and short prompt after inspecting the exact first envelope.
- [ ] One versioned routing path stores and returns a single authoritative
  decision per envelope/run with evidence hash, prompt version, model, cost,
  and rationale; no live product reads old Insight tables for this decision.
- [ ] The first envelope is routed and reviewed with Adi, with its input blocks
  and output visible and traceable in the UI/API.
- [ ] A small calibration set covers Engineering only, Investment only, both,
  and neither; disagreements and prompt changes are recorded.
- [ ] One complete day is routed and every output is human-audited before any
  bulk expansion.
- [ ] Focused tests, `bash scripts/check-fast.sh`, live API proof, and rendered
  desktop QA pass; architecture/status docs reflect the final boundary.
- [ ] Project learnings are finalized and the tracker is archived before the
  next Insight-generation project begins.

## Milestones

- [ ] Milestone 1 — Freeze the one-envelope architecture with Adi. Acceptance:
  exact input blocks, schema semantics, consistency rules, and prompt are
  documented and approved. Validate: render and inspect envelope
  `56ec1710...bef56d`; make no bulk model call.
- [ ] Milestone 2 — Implement one-envelope vertical slice. Acceptance: one
  authoritative run/storage/API path returns a traceable structured decision
  for the approved packet. Validate: focused unit/API tests plus manual record
  inspection.
- [ ] Milestone 3 — Calibrate and audit one day. Acceptance: the four audience
  outcomes are represented or explicitly assessed, every routed envelope is
  reviewed, and prompt/schema changes are versioned. Validate: deterministic
  rerun, reconciliation query, and rendered UI audit.
- [ ] Milestone 4 — Freeze the routing boundary and close out. Acceptance:
  architecture, status, model/prompt references, evaluation evidence, and
  limitations are current; Insight generation is a separate explicit next
  project. Validate: `bash scripts/check-fast.sh` and archive this tracker.

## Execution Rules

- Keep work scoped to the current milestone; do not restore the archived
  multi-stage pipeline to solve a routing problem.
- Work sequentially across shared contracts: input packet, schema, prompt,
  storage, one envelope, then one day.
- Stop for Adi's decision before freezing schema/prompt semantics or scaling
  beyond the first envelope.
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
- The first proof is one envelope, followed by one day—not all available data.
- Feed rank remains display/order provenance and must not influence the model's
  routing judgment.
- The current two-field schema is a candidate, not a frozen contract.
- The next engineer must surface disagreements with the archived design rather
  than inheriting its assumption that Feed alone owns keep/drop.

## Open Questions / Blockers

- Should `decision` be a genuinely independent keep/drop judgment, or should
  the application derive it from whether `audiences` is empty? Storing both is
  easy to understand but creates invalid combinations unless one is derived or
  strict validation rejects contradictions.
- Should `audiences` be one array or two independent audience booleans? The
  array is compact; independent booleans can preserve separate reasoning.
- Is one shared `reason` enough, or does each audience need its own short
  reason—especially when an envelope is useful for one audience but not the
  other?
- Which reply and quote-post blocks belong in the model packet, and when does a
  deterministic size bound become necessary? Inspect real packet sizes before
  choosing a top-N rule.
- Does the new routing decision replace the current Feed triage result, coexist
  as an explicit comparison during calibration, or live only downstream of
  accepted Feed envelopes? Decide before naming the table/API fields.
- Where should the new authoritative routing records live? Choose one clean
  database/schema and prohibit UI fallback to archived Insight data.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| todo | Inspect and render the exact first envelope from current Evidence and artifact stores, listing every attributed block and packet-size fact. | parent | `resources/first-envelope-audit.md` |
| todo | Review with Adi whether keep/drop is independent or derived, then freeze the smallest consistent schema and rationale shape. | parent | `resources/routing-contract.md` |
| todo | Draft the shortest audience-routing prompt from the approved contract; do not run it until Adi reviews the exact input and output shape. | parent | `resources/routing-prompt.md` |

## Backlog / Remaining Work

- [ ] Implement the approved one-envelope runner, storage contract, and API.
- [ ] Add deterministic packet-integrity and schema-consistency validation.
- [ ] Run the first envelope and record human review plus any prompt revision.
- [ ] Build a small four-outcome calibration set from current Evidence.
- [ ] Route and audit one complete day before any bulk expansion.
- [ ] Add the minimal inspectable UI only after API/storage semantics are stable.
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
