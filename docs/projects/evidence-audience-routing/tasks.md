# Evidence Audience Routing

## Goal

Define and prove the smallest auditable decision that assigns one complete,
correctly attributed Evidence envelope to AI Engineering, Investment, both, or
neither before any new Insight generation is designed or run. Audience routing
is the only live model judgment over Feed evidence; the superseded general
keep/drop gate is removed rather than displayed or maintained in parallel.

## Why / Impact

The archived Audience Insights v2 project mixed routing, extraction,
editorial selection, verification, reconciliation, and publication before the
first product decision was easy to inspect. That made failures hard to reason
about with Adi and created multiple apparent sources of truth.

This project restores one visible boundary: inspect Evidence, make two
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
  relevant, each with a concise evidence-grounded explanation. The current
  prompt aims for roughly 40–50 words but treats that as guidance, not a limit.
- Remove the superseded Feed keep/drop model, live projection, filter, reason,
  CLI entry point, and generated run data. Do not preserve a compatibility
  read or let new routing depend on its records.
- Write the routing prompt with Adi, keeping the two audience standards
  distinct and excluding Feed rank, engagement, prominence, and other outcome
  hints from the model input.
- Implement one authoritative, versioned storage/API path only after the input,
  schema, and prompt are approved.
- Inspect one exact envelope end to end, then run a small frozen review cohort
  to inspect Engineering, Investment, both, and neither behavior before broader
  evaluation.
- Add compact per-envelope audience marks, a routing disclosure, and one
  derived Status control so Adi can inspect the first real outputs in the
  existing evidence workspace without creating another model judgment.
- Keep the decision traceable from the UI/API back to the exact Evidence
  envelope and model/run provenance.

### Out of Scope

- Writing or publishing audience Insight prose.
- Restoring the deleted Audience Insights v2 databases or treating archived
  reviewer/editor/publication machinery as the current contract.
- Preserving the superseded Feed keep/drop path for backward compatibility.
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
  Its recommendation that Feed owns keep/drop was superseded by Adi on
  2026-07-15 after reviewing the combined UI. The router now consumes ranked
  Evidence envelopes directly and is the only live model judgment in Feed.
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
    "reason": "Concise evidence-grounded explanation, aiming for roughly 40 to 50 words."
  },
  "investment": {
    "relevant": false,
    "reason": "Concise evidence-grounded explanation, aiming for roughly 40 to 50 words."
  }
}
```

Application invariants:

- Both judgments are required and independently reasoned in one model call.
- The application derives the convenient audience list and the four display
  outcomes; the model does not author those redundant fields.
- A `neither` audience result remains a valid completed routing result. It is
  distinct from an envelope that has not yet been routed.
- IDs, hashes, prompt versions, model/run telemetry, and timestamps are
  application-owned fields, never model-authored fields.
- The reason schema requires a non-empty string but imposes no maximum length.
  The roughly 40–50-word guidance is a prompt preference, not a truncation or
  rejection rule; the model should use more when clarity requires it and should
  not add filler to reach it.
- Mechanically invalid evidence packets fail before routing; they are not
  classified as `drop`.

## Done When

- [ ] Adi approves a documented envelope-input contract, including the exact
  treatment of root text, same-author continuations, replies, quotes, and
  artifacts.
- [x] Adi approves the routing semantics: one combined call and two independent
  audience judgments with separate reasons; no general keep/drop judgment.
- [ ] Adi reviews the short prompt and exact first-cohort outputs.
- [x] One versioned routing path stores and returns one authoritative pair of
  audience judgments per envelope/run with evidence hash, prompt version,
  model, cost, and rationales; no live product reads old Insight tables.
- [x] The first envelope is routed and reviewed with Adi, with its input blocks
  and output visible and traceable in the UI/API.
- [x] A small frozen review cohort is routed with Luna-medium; outcomes,
  prompt-cache reads, response cost, and qualitative disagreements are
  recorded before any expansion.
- [x] Feed exposes audience marks, one derived Status control, and compact
  reasons without generating Insight prose or displaying a superseded result.
- [x] The live Feed, API, routing runner, CLI, and generated current data contain
  no dependency on or link to the superseded keep/drop run.
- [x] Focused tests, `bash scripts/check-fast.sh`, live API proof, and rendered
  desktop QA pass; architecture/status docs reflect the final boundary.
- [ ] Project learnings are finalized and the tracker is archived before the
  next Insight-generation project begins.

## Milestones

- [ ] Milestone 1 — Freeze and implement the first-cohort architecture.
  Acceptance: exact input blocks, approved schema, short prompt, immutable
  run storage, and API projection work on the Satya envelope. Validate:
  focused packet/runner/API tests and exact record inspection.
- [x] Milestone 2 — Run and inspect a small review cohort. Acceptance:
  Luna-medium outputs, cache/cost telemetry, outcome distribution, and
  qualitative review are recorded. Validate: resumable rerun and direct
  database/API comparison.
- [x] Milestone 3 — Expose routing in Feed. Acceptance: audience marks, derived
  controls, and short reasons make the cohort inspectable. Validate: production
  build and rendered desktop QA.
- [x] Milestone 3b — Remove the superseded keep/drop path. Acceptance: routing
  freezes ranked Evidence directly; the live API/UI/CLI expose no triage fields,
  controls, or reasons; current routing records carry only Evidence/run
  provenance. Validate: repository search, direct-run tests, API proof, and
  rendered desktop QA.
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
- Adi superseded the Feed keep/drop gate after seeing both judgments together.
  Audience routing now runs directly over ranked Evidence and is the only live
  model decision shown in Feed.
- One combined GPT-5.4-mini/high call returns two independent audience judgments and
  separate reasons. “Independent” does not mean separate routing calls.
- After the first proof, Adi authorized the top 10 ranked envelopes for every
  complete Feed day from July 5–13 as the qualitative audit cohort.
- Feed rank remains display/order provenance and must not influence the model's
  routing judgment.
- Insight generation remains a separate follow-up stage and may use a higher
  reasoning effort only after routing is qualitatively understood.
- The v2 review renderer introduced a human-readable YAML-style hierarchy
  rather than XML/CDATA. It decoded HTML entities, represented link-only
  primary posts by their artifact relationship, omitted pure retweets and
  transport-only links, excluded reactions shorter than 40 characters, and
  removed reactions whose text was at least 80% duplicated by supplied primary
  evidence.
- The rank-1 review disproved the v2 length rule: it removed the specific claim
  “Grok 4.5 is Opus class for browser use.” Runtime v3 therefore has no minimum
  or maximum reaction length. It keeps short reactions and omits only pure
  retweets, transport-only links, and reactions whose text is at least 80%
  duplicated by supplied primary evidence.
- Runtime v3 asks for roughly three to four sentences per audience reason with
  no schema maximum. Its stable instructions are 8,188 characters and 1,180
  whitespace-delimited words, comfortably beyond the 1,024-token cache
  threshold without padding.
- Audience routing uses one stable prompt-level key and sequential execution.
  It stores no per-item key or sharding column, adds no padding, and requests no
  retention override. Partitioning is justified only if future throughput
  approaches the documented routing threshold.

## Open Questions / Blockers

- GPT-5.5 and GPT-5.6 still return zero prefix reads on the controlled v4 path,
  but GPT-5.4 mini is proven working: the nine-day run produced 88 hits across
  90 requests and a 49.93% token read ratio. Keep this model-specific evidence
  visible; do not generalize one deployment's result to another.
- Which reply and quote-post blocks belong in the model packet, and when does a
  deterministic size bound become necessary? Inspect real packet sizes before
  choosing a top-N rule.
- The contextual audit found two likely Investment false negatives and an
  inconsistent Engineering boundary for temporary access/rate-limit changes.
  Adi must decide whether to adopt the narrow clarification proposed in
  `resources/top10-contextual-audit-v1.md` before a targeted rerun.
- One Claude Code article was extracted as redacted block characters. Add
  deterministic artifact-content validation so an incomplete packet does not
  silently look like a substantive `neither` result.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Simplify production audience routing to GPT-5.4 mini with one stable prompt key, sequential execution, and no sharding, retention override, or padding. | parent | `resources/audience-routing-v3-cache-diagnostic.md` |
| done | Freeze and route the top 10 ranked Evidence envelopes for every available Feed day at high reasoning. | parent | `resources/top10-every-day-v4-mini.md` |
| done | Verify per-day completeness, cache reads, cost, audience distribution, and existing Feed projection. | parent | `resources/top10-every-day-v4-mini.md` |
| done | Contextually audit 26 stratified packets against the exact stored evidence and approved audience standards. | parent | `resources/top10-contextual-audit-v1.md` |
| in_progress | Decide whether to add the two narrow boundary clarifications and rerun only the five disputed/borderline packets. | parent | `resources/top10-contextual-audit-v1.md` |

## Backlog / Remaining Work

- [ ] Add deterministic packet-integrity and schema-consistency validation.
- [x] Audit a stratified sample of both, single-audience, and `neither`
  outcomes from the authorized top-10 cohort.
- [ ] After the current boundary decision, audit a bounded sample of difficult
  low-ranked Evidence before any full-catalog expansion.
- [x] Expand the audit cohort to the authorized top 10 for every complete day.
- [x] Add the read-only API projection and compact positive Feed audience marks
  and reasons without reading archived Insight data.
- [x] Update architecture, status, model-routing/prompt references, and build log.
- [x] Run focused tests, `bash scripts/check-fast.sh`, API proof, and desktop QA.
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
- 2026-07-15: [IN-PROGRESS] With Adi's explicit approval, ran exactly the
  reviewed Satya v2 request through Luna-medium. Both audiences were relevant.
  The call used 3,171 input and 119 output tokens, cost $0.003885, and completed
  in 4.172 seconds. It reported zero cache reads and zero cache-write tokens,
  so caching remains unproven until one approved next envelope reuses the same
  prefix. SQLite integrity is `ok`; exact results are in
  `resources/satya-routing-v2-result.md`.
- 2026-07-15: [IN-PROGRESS] With Adi's approval, routed exactly one next kept
  envelope: Feed rank 1, an attributed browser-use model comparison. Both
  audiences were relevant. The call used 1,860 input and 121 output tokens,
  cost $0.002586, and again reported zero cached and zero cache-write tokens
  despite reusing the exact v2 prompt hash and cache key. The run also exposed
  that a length-only reaction filter can discard a specific material claim;
  exact evidence is in `resources/rank1-routing-v2-result.md`.
- 2026-07-15: [VALIDATED] Promoted runtime v3 after Adi rejected any reaction
  length limit. The renderer now retains short substantive reactions, including
  the previously lost Grok claim, while the prompt requests roughly three to
  four sentences per audience reason and the schema retains no maximum length.
  A controlled cache diagnostic proved that LiteLLM's exact-response cache
  works at zero incremental proxy spend, but Azure returned zero prefix reads
  for both the v3 different-input test and two fresh inputs through the
  previously successful Feed-triage prefix. The adapter fields and cache key
  were forwarded unchanged to one deployment, isolating the miss upstream.
- 2026-07-15: [VALIDATED] Repeated the v3 different-input test on the available
  GPT-5.5 Responses deployment with an explicit shared cache key and 24-hour
  retention. The 1,920-token cold request and 3,256-token follow-up both
  returned zero cached tokens, broadening the failure from Luna-specific to the
  Azure Responses cache path or its current interaction through LiteLLM. The
  two calls cost $0.058070; no further paid cache probes are justified now.
- 2026-07-15: [VALIDATED] Routed the frozen July 12 top-eight kept cohort
  sequentially through Luna-medium and projected it into the existing Feed.
  All eight records completed: five route to both audiences, one to AI
  Engineering only, two to Investment only, and none to neither. The run used
  21,365 input and 2,646 output tokens, cost $0.037241, and again reported zero
  provider cache reads or writes. The Feed now shows 13 positive-only `AI`/`INV`
  marks and keeps Feed triage plus both audience reasons in one disclosure. The
  API returned all eight exact snapshot-bound records; focused tests, the full
  fast check, production build, and rendered desktop inspection passed. Adi's
  qualitative audit and a later bounded hard-negative sample remain the live
  resume point; exact evidence is in `resources/jul12-top8-v3-routing.md`.
- 2026-07-15: [REPLANNED] After reviewing the combined disclosure, Adi rejected
  the old Feed keep/drop judgment as redundant and asked for a clean migration
  with no useless live links. Audience routing is now the only model judgment
  over Feed evidence. The active batch removes the legacy filter/reason/API/CLI
  and generated triage data, changes the routing runner to freeze ranked
  Evidence directly, and migrates the current new outputs to Evidence/run-only
  provenance before qualitative review resumes.
- 2026-07-15: [VALIDATED] Closed the remaining prompt-cache diagnostic gap with
  a two-request Luna-medium v4 canary. Different packets used the exact same
  forced cache key sequentially; the 3,289-token cold request and 1,953-token
  follow-up both reported zero cached tokens. The stable prompt and runner are
  correct, but Azure prefix reuse is not currently observable. A broader run
  should be budgeted as uncached while retaining the 32-lane schedule and cache
  telemetry; the two calls cost $0.008626.
- 2026-07-15: [VALIDATED] Repeated the same current-prompt canary live on
  GPT-5.5 at Adi's request. Two different v4 packets used one fresh forced key
  sequentially; the 3,289-token cold call and 1,953-token follow-up again
  returned zero cached tokens and zero cache-write telemetry. This rules out
  the earlier GPT-5.5 miss being an obsolete-v3 artifact. The retry cost
  $0.049730.
- 2026-07-15: [VALIDATED] The identical current-prompt canary succeeded on
  GPT-5.4 mini. Its cold call read zero cached tokens; the sequential
  different-input follow-up used the same fresh key and read 1,280 of 1,953
  input tokens from the provider cache. This positive control proves the v4
  request and shared LiteLLM path are sound and localizes the miss to the
  current GPT-5.5/GPT-5.6 routes or backing deployments. The two mini calls
  cost $0.00592950.
- 2026-07-15: [VALIDATED] Removed event sharding, per-item cache keys, prompt
  padding, and the retention override from the live audience router. A clean
  implicit-only mini canary missed twice; adding one stable prompt-level key
  produced a 1,280-token read on call two. OpenAI, Azure, and LiteLLM docs agree
  that the key is an optional routing hint, while the live A/B establishes it
  as the minimal reliable control on this route.
- 2026-07-15: [VALIDATED] Routed the top 10 ranked envelopes for all nine
  complete Feed days with GPT-5.4 mini at high reasoning. All 90 completed with
  zero failures: 44 both, six Engineering-only, eight Investment-only, and 32
  neither. Eighty-eight requests hit the provider cache, reading 152,576 of
  305,600 input tokens. Eighty-nine cost headers total $0.462966; one July 13
  call omitted the header. All databases have integrity `ok`, no sharding
  column, and the Feed API selects the exact 10-record run on every day.
- 2026-07-15: [REVIEWED] Contextually audited 26 packets across all four
  outcomes against their exact stored sources. Twenty-one were clear
  agreements, three exposed an underdefined access/rate-limit boundary, and
  two were likely Investment false negatives caused by imposing a stronger
  verification requirement than the prompt. Fifteen repeated events had zero
  label conflicts, reasons stayed near the requested length, and no reviewed
  reason clearly invented or misattributed packet evidence. Also identified a
  redacted Claude Code artifact as an upstream input-integrity failure. The
  proposed narrow clarification and exact cases are recorded in
  `resources/top10-contextual-audit-v1.md`; Adi's boundary decision remains the
  project closeout blocker.
