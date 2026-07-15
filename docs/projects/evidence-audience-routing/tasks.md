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

- Define the exact immutable Evidence-envelope blocks presented to the router:
  one original source post, substantive posts authored by that same author
  (including replies, thread continuations, and quote-post commentary), and
  accepted first-party artifacts. Independently authored reactions and pure
  reposts remain Feed activity evidence but never enter the semantic packet.
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
- Expanding the Registry, following graph, or collection cohort; broad reply
  ingestion and reaction-owned artifact acquisition remain out of scope.
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

- [x] Adi approves a documented envelope-input contract, including the exact
  treatment of root text, same-author continuations, replies, quotes, and
  artifacts.
- [x] Adi approves the routing semantics: one combined call and two independent
  audience judgments with separate reasons; no general keep/drop judgment.
- [x] Adi reviews the short prompt and exact first-cohort outputs.
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

- [x] Milestone 1 — Freeze and implement the first-cohort architecture.
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
- [ ] Milestone 4b — Publish each semantic envelope once. Acceptance: every
  Event has one canonical Feed day and rank; later activity appends to that
  Event without another routing or Insight candidate; routing and Insight
  packets contain only the original source and accepted first-party artifacts.
  Validate: focused projection/packet tests, rebuilt live data, API proof, and
  rendered Feed/Insight QA.

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
- Treat this tracker as the normal work record and follow the root `AGENTS.md`
  build-log threshold; do not separately log routine work. Update
  architecture/status when the boundary changes.
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
- On 2026-07-15 Adi explicitly authorized a narrow successor Insight bootstrap
  while the repaired-Event routing refresh continues: delete the obsolete
  backend, define two audience prompts plus one shared schema, preserve the
  current UI shell and Feed-rank metadata, and stop before any model call. This
  is a foundation checkpoint only, not bulk generation or publication.
- Adi later authorized live Terra/high evaluation on two supplied envelope IDs,
  then approved moving the proven path into production storage and the existing
  UI. On 2026-07-15 he simplified both model boundaries: routing and Insight
  generation use only the original source post, substantive posts by that same
  author (including replies, thread continuations, and quote-post commentary),
  and accepted first-party artifacts. Independently authored reactions and
  pure reposts remain Feed activity context and scoring evidence; they cannot
  change the semantic packet, create a later-day candidate, reroute, or
  regenerate an Insight.
- Each Event is published on exactly one canonical day: the original/root
  source day. Its Feed rank is frozen on that day. Later activity appends to the
  Event's inspectable evidence and attention history, but the Event does not
  reappear on the later day.
- The date rail counts kept Insights but retains every evaluated day. UI status
  is one mutually exclusive `Kept` / `Suppressed` / `All` audit control. A
  surfaced implication is shown as `Why kept`; a suppression reason is shown as
  `Why suppressed`. Neither state introduces a model quote or another rank.
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
- Audience routing uses one stable prompt-level key. It stores no per-item key
  or sharding column, adds no padding, and requests no retention override. The
  multi-day refresh freezes packets sequentially for fast local assembly, then
  runs pending model requests in bounded parallelism without changing that
  single stable prefix contract.
- The immutable packet and evidence hash always retain the complete evidence.
  The derived model view is capped at 20,000 `o200k_base` tokens, with primary
  evidence ordered before reactions and an explicit `TRUNCATED_EVIDENCE`
  marker when the lower-priority tail is omitted. This is an inference bound,
  not source deletion.
- Artifact text readiness belongs upstream of routing. The shared extraction
  boundary rejects a body before snapshot success only when it has at least 100
  visible characters and at least 90% are exact `█` or Unicode-replacement
  placeholders. Routing contains no artifact-quality heuristic and consumes
  only successful text snapshots.
- A reply-capable envelope cannot be built from a reply-free source timeline.
  Daily collection now includes authored replies; Feed admission requires the
  conversation root to be captured. Same-author replies become first-party
  continuations, other tracked authors remain reactions, and unrelated reply
  activity remains excluded.

## Open Questions / Blockers

- GPT-5.4 mini prompt caching is proven on the current v9 route. The clean
  900-row run produced 805 cache-hit requests and read 1,442,560 of 2,760,202
  input tokens. The Terra Insight prompts are eligible and were warmed once,
  but their cold warm-up calls do not prove a read; keep model-specific evidence
  visible rather than generalizing one deployment's result to another.
- The broader artifact retrieval gaps remain upstream limitations. Do not add
  model-side web search or routing-local text-quality heuristics until the next
  Insight stage demonstrates a concrete need.
- All v8 routing cohorts are invalid historical evidence and their directories
  have been removed. Consumers must select only current source-qualified v9
  run IDs against Event run `cc76958510ddf90c14863d1c5b8de1d40881a6bf12396671dfd264a6e2df210d`.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| complete | Collect authored replies and admit only replies whose conversation root is captured. | parent | — |
| complete | Rebuild and publish Feed/events; prove Gemma and Muse include their first-party continuations. | parent | — |
| complete | Replace legacy-triage-gated artifact import with published Feed/Event discovery. | parent | `../../../references/evidence-refresh.md` |
| complete | Bound only the model-facing packet at 20,000 tokens and preserve an explicit truncation notice. | parent | — |
| invalidated | Replace all stale routes with GPT-5.4-mini/high top-100 runs for July 5–13. | parent | — |
| complete | Add one resumable publication-bound command for the next nine-day top-100 routing refresh. | parent | `../../../references/evidence-refresh.md` |
| complete | Replace unrestricted Event components with root-owned one-parent envelopes; rebuild July 5–13 and prove the Anthropic root is restored. | parent | `../../../references/signal-feed.md` |
| complete | Replace the obsolete Insight backend with the two-prompt, shared-schema, non-executing successor foundation; preserve the empty UI transport and Feed-rank metadata. | parent | — |
| complete | Run both successor prompts against envelope `9412a377…` on its latest corrected July 12 revision; inspect raw structured output, cache, and cost before designing storage. | parent | `resources/first-successor-insight-spike.md` |
| complete | Move the successor Insight path into durable SQLite-backed generation; import the first-party-only Terra result, expose kept/suppressed decisions through the API, and add Feed-style date/status audit controls to the existing UI. | parent | `resources/first-live-insight-run.md` |
| invalidated | Rerun and review the 900 v8 routes against the repaired Event publication; superseded when the semantic input boundary changed. | parent | `resources/top100-contextual-audit-v2.md` |
| complete | Replace daily continuation publication with one canonical Event day/rank while retaining later activity on the Event. | parent | — |
| complete | Reduce routing and Insight packets to first-party-authored source material plus accepted first-party artifacts and enforce one candidate per Event/audience. | parent | — |
| complete | Rebuild clean one-run Feed/Event stores and replace all routing data with nine v9 top-100 runs; prove cache telemetry and remove v8 directories. | parent | `../../../references/model-routing.md` |
| pending | Complete the clean 492-Event / 751-request Terra Insight refresh from the reset v4-only store; then reconcile and perform final Insight UI proof. | parent | `resources/first-live-insight-run.md` |

## Backlog / Remaining Work

- [x] Reject long placeholder-dominated bodies at artifact extraction without
  adding a subjective garbage-text heuristic.
- [x] Explain ready, pending, unsupported, retryable, and unavailable artifact
  content states inside expanded provenance without adding another list column.
- [ ] Add broader packet-integrity or schema-consistency validation only when a
  concrete failure justifies a deterministic rule.
- [x] Fetch authored replies for captured root conversations without adding
  unrelated reply noise to the daily Feed.
- [x] Rebuild the affected Feed/Event projections and verify Gemma and Muse
  continuations against corrected envelopes.
- [x] Decouple primary-artifact catalog import from the deleted legacy triage
  store, rebuild the reply-inclusive catalog, and add one cache-aware Evidence
  refresh command.
- [x] Audit a stratified sample of both, single-audience, and `neither`
  outcomes from the authorized top-10 cohort.
- [x] After the current boundary decision, audit a bounded sample of difficult
  low-ranked Evidence before any full-catalog expansion.
- [x] Expand the current audit surface to the top 100 envelopes for all nine
  complete days with a deterministic 20,000-token model-input ceiling.
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
- 2026-07-15: [SUPERSEDED] Initially added the narrow placeholder check inside
  the routing renderer. Adi correctly moved the responsibility upstream so
  every artifact consumer receives the same extraction result rather than
  accumulating consumer-specific cleanup.
- 2026-07-15: [VALIDATED] Shared ordinary artifact, Jina, and X Article
  extraction now rejects bodies with at least 100 visible characters and at
  least 90% exact `█`/Unicode-replacement placeholders as terminal
  `extraction_placeholder_content` before creating a text snapshot. Removed
  all routing-local quality logic. Corrected the known Claude Code fetch from
  success to terminal failure while preserving its raw response and consistent
  run counters. The remaining 880 successful snapshots have zero placeholder
  violations; focused tests keep short blocks, mixed prose, code, and progress
  bars. Repository/video behavior is unchanged, no historical routing result
  was rewritten, and no model call was made.
- 2026-07-15: [VALIDATED] Primary artifacts now keeps the collapsed list to
  Feed rank, artifact, type, and source. Expanded provenance presents a plain
  content status and the exact source timestamp. Browser QA covered a ready
  article, deferred repository support, and the preserved unusable Claude Code
  extraction; no new filter, backend state, or database field was introduced.
- 2026-07-15: [VALIDATED] Completed the reply-capable collection for all 2,561
  tracked accounts (2,558 fetched, three cached, zero failures), then rebuilt
  Feed v9 and Events v4 into 37,079 normalized posts and 7,815 envelopes. The
  Cohere Arabic ASR envelope now contains its three first-party replies; its
  leaderboard and model-weight artifacts both resolve to Feed rank 15 and have
  successful text snapshots. Replaced `import-kept` with direct published
  Feed/Event artifact discovery: 3,384 decisions produce 3,035 verified
  observations and 2,703 canonical artifacts with zero lineage violations.
  Added `fli evidence-refresh` as the cache-aware operator path. A full replay
  reused all 2,561 account page chains and made zero provider requests; Feed,
  Events, and artifact import also reused their content-addressed runs.
- 2026-07-15: [VALIDATED] Fixed exact Feed-envelope deep links that could hide
  their target behind the normal `Relevant` browsing default. A URL carrying
  `event` now opens in `All` while ordinary Feed visits still default to
  `Relevant`; invalid exact links receive an envelope-specific empty state.
  The focused frontend suite, production build, and rendered check against the
  first prompt-design envelope all pass, with the linked Satya envelope visible
  at its stable daily rank #2.
- 2026-07-15: [VALIDATED] Completed the clean primary-artifact expansion. The
  zero-violation catalog has 3,087 observations and converges to 2,735
  artifacts; 2,507 have usable text. All 221 arXiv artifacts use batch
  metadata/abstract text and all 167 X Articles are cached locally. Videos are
  the only structurally deferred kind; 65 non-video pages remain unavailable
  or retryable. `fli evidence-refresh` performs this supported pass by default
  with one artifact store and source-specific adapters hidden behind one CLI.
- 2026-07-15: [VALIDATED] Replaced every stale audience route with nine current
  GPT-5.4-mini/high top-100 runs over the corrected Evidence projection. All
  900 packets completed: 357 both, 99 Engineering-only, 147 Investment-only,
  and 297 neither. Sixteen packets exceeded the new 20,000-token variable-input
  boundary and were explicitly marked after truncating only the lower-priority
  model-facing tail; complete packet JSON and evidence hashes remain intact.
  The run produced 814 cache-hit requests, 1,463,296 cached tokens, and
  $5.506914 in proxy-reported cost. Twenty-eight repeated exact model inputs
  had zero label conflicts.
- 2026-07-15: [INVALIDATED] The broad routing run revealed an upstream Event
  bug rather than a routing-prompt failure. Anthropic's J-space thread and Ryan
  Brewer's unrelated education post landed in one 389-member component through
  a chain containing reply posts that also quote posts from another thread.
  The reply-free pipeline had hidden this transitive bridge. The current 900
  labels must not be used as evaluation evidence and will be replaced after
  the Event fix.
- 2026-07-15: [VALIDATED] Added `fli audience-routing refresh` as the resumable
  multi-day operator path. It binds all days to one published Event/Feed pair,
  uses deterministic source-qualified run IDs, executes days and items in
  bounded parallelism, aggregates cache/cost telemetry, and removes old runs
  only after the full replacement succeeds. Its dry-run freezes the exact
  nine-day top-100 plan without any model call.
- 2026-07-15: [VALIDATED] Replaced unrestricted transitive Event connectivity
  with `exact-structural-v10-root-owned-reactions`: every member has at most one
  structural parent, quote/retweet reactions attach to one source, only the
  source author's replies extend its envelope, and third-party replies remain
  preserved in the Feed ledger without rendering or grouping. Regression tests
  cover reply-plus-quote bridges, quoted replies, missing-parent first-party
  continuations, cutoff stability, weekly thin-revision replacement, Registry
  rejection, one-parent enforcement, and unique Event membership. The full
  July 5–13 publication has 7,515 grouped envelopes and zero multi-parent or
  multi-event members. Anthropic post `2074185348142280912` is restored as the
  July 7 rank-1 root with 108 cutoff-correct related posts; Ryan Brewer's post
  remains a separate 14-member Event. All 490 Python and 40 frontend tests pass.
- 2026-07-15: [VALIDATED] Bootstrapped the clean successor Insight boundary
  without executing a model. Deleted the obsolete cited/multi-stage extraction,
  review, editor, recall, audit, reconciliation, CLI, prompt, and test stack.
  Added separate naturally cache-eligible Investment and AI Engineering prompts,
  one shared strict surface-or-suppress schema, deterministic validation, and
  application-owned Event/day/Feed-rank publication metadata. The existing UI
  routes now return an honest empty successor state and never read legacy data.
  Focused tests and the full 334-test Python suite pass; the first live envelope
  remains explicitly deferred until Adi supplies its ID.
- 2026-07-15: [VALIDATED] Ran the first successor spike on the latest corrected
  July 12 revision of envelope `9412a377…`, which routes to both audiences at
  Feed rank 5. Mini-high and Terra-high each evaluated the unchanged Investment
  and AI Engineering prompts over the exact same evidence; all four validly
  suppressed the mission statement rather than manufacturing an actionable
  Insight. Terra's Investment rationale was strongest, while mini's Engineering
  rationale was more precise about the packet's existing essay artifact. The
  four calls cost $0.05248125 total. Each model/audience pair was cold, so zero
  cache reads do not test repeat-prefix behavior. Exact outputs and the next
  surfaceable-envelope comparison are recorded in
  `resources/first-successor-insight-spike.md`; no store or UI publication was
  added.
- 2026-07-15: [VALIDATED] Replaced all invalid pre-repair labels with nine
  source-qualified v8 top-100 runs over Event publication `cc76958510dd…`.
  All 900 GPT-5.4-mini/high packets completed with zero failures: 344 both,
  112 Engineering-only, 141 Investment-only, and 303 neither. The run recorded
  779 prompt-cache hits, 1,399,040 cached of 3,418,560 input tokens, and
  $5.28797975 proxy-reported cost. Thirty-eight repeated exact inputs have zero
  label conflicts. A 20-packet rank/outcome-stratified audit found 17 clear and
  three soft-but-defensible judgments; Gemma, Cohere Arabic ASR, Muse, and the
  restored Anthropic root now consume the intended first-party evidence and
  route coherently. Exact review evidence is in
  `resources/top100-contextual-audit-v2.md`.
- 2026-07-15: [VALIDATED] Removed the local audience-refresh packaging
  bottleneck. Replaced quadratic artifact/reaction comparison, stopped asking
  the Event API for 5,000 rows when only the selected cohort is needed, and
  split the operator path into sequential packet freezing followed by parallel
  model requests. A complete cached nine-day replay now reports packet time
  separately, truthfully reports `model_requests: 0`, preserves all 900 exact
  outputs, and completes in 8.267 seconds instead of roughly 8 minutes 49
  seconds. Focused routing tests pass (23), and the live Feed shows the current
  July 7 counts and repaired envelopes with no browser console errors.
- 2026-07-15: [VALIDATED] Promoted successor Insights from spike output to the
  production path. Added an immutable/resumable SQLite store, JSON-first
  `fli insights` run/import/inspect/summary commands, exact first-party-only
  request freezing, per-audience result reuse, and API projections for kept,
  suppressed, and all decisions. Imported the existing Terra/high run for
  envelope `1dc9cd72…` without another model call: AI Engineering kept one
  Feed-rank-45 harness-engineering Insight; Investment suppressed the same
  evidence. The UI reuses the Feed week rail and Status control, explains why
  each decision was kept or suppressed, and links to the exact envelope. The
  durable store contains one run/two completed items, $0.0757825 reported cost,
  and zero cached tokens. Focused Python tests, all frontend tests, lint, build,
  live API checks, and rendered kept/suppressed browser flows pass.
- 2026-07-15: [VALIDATED] Simplified Event publication to one canonical source
  day and frozen Feed rank. Later replies, quotes, and reposts append to the
  same Event activity ledger and never create a later Feed candidate, routing
  request, or Insight candidate. The production Feed/Event stores were rebuilt
  from raw evidence into fresh one-run databases. Event `1dc9cd72…` is now only
  the July 7 rank-1 Event with 35 lifetime members active on July 7/8/11/13; it
  is absent from the later three daily candidate lists.
- 2026-07-15: [VALIDATED] Promoted audience routing v9 with a shared
  first-party-only semantic boundary: root, same-author replies/thread/quote
  commentary, and accepted first-party artifacts. Independently authored
  reactions and pure reposts remain Feed activity only. A two-request probe
  proved the 1,861-token stable prefix with a 1,792-token cache read. The clean
  July 5–13 top-100 replacement completed 900/900 with zero failures: 259 both,
  100 Engineering-only, 133 Investment-only, and 408 neither. It recorded 805
  cache-hit requests, 1,442,560 cached of 2,760,202 input tokens, and
  $4.1366515 proxy-reported cost; all v8 routing directories were removed.
- 2026-07-15: [HANDOFF] The current v9 routes produce 492 unique positive
  Events and 751 audience requests (359 Engineering, 392 Investment). The
  active Terra v4 prompts are cache-eligible at 1,459 Engineering and 1,425
  Investment instruction tokens and require a title for every decision. Adi
  stopped the earlier full refresh and will execute the clean v4 run himself.
  The partial candidate database/dumps, all v3 production rows, the v3 prompt
  files, duplicate `extracted` API routes/types, stale temporary database
  aliases, and the unused Event re-anchoring helper were deleted. The live
  first clean v4 checkpoint now contains six decisions over three Events, with
  two surfaced, four suppressed, and four 1,280-token cache reads. Next:
  complete the remaining cohort, reconcile all requests, then perform final
  UI/browser proof.
