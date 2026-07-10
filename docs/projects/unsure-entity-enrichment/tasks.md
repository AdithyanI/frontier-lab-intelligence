# Unsure Entity Enrichment

## Goal

Resolve structurally `unsure` entities with a bounded profile-to-recent-posts
Responses workflow, persist accepted results, and reject accounts whose posts
are explicitly protected before any model call.

## Why / Impact

The profile-only classifier initially abstained on 145 weak identity records;
The 137-account cohort has now been classified and persisted. Three of the five
remaining abstentions expose an explicit protected-account flag and cannot
supply public output, so they belong in an auditable rejected state rather than
being deleted or sent to the model again.

## Scope / Non-Goals

### In Scope

- Read only current `unsure` X-backed entities.
- Use one shared entity-kind instruction prompt with Luna through LiteLLM.
- Classify the profile first; only after `unsure`, fetch up to 20 recent
  authored posts through TwitterAPI.io and continue with
  `previous_response_id`.
- Exclude replies and retweets; retain only the account's top-level commentary
  for quote posts.
- Return only `classification` and `reason` from the model.
- Return inspectable stage outputs, Response IDs, normalized evidence, usage,
  cost, and errors from the bounded calibration runner.
- Check the provider's explicit protected flag before inference; persist a
  reason-bearing Registry rejection and make it visible in the UI.

### Out of Scope

- Hosted web search or open-web fallback.
- Relevance curation, channel merging, roles, affiliations, or new sources.
- Agents SDK, Codex subagents, or a generalized agent framework.

## Context / Constraints

- Date started: 2026-07-10.
- The first profile-only pass and canonical promotion are complete.
- Azure Responses chaining with `previous_response_id`, Structured Outputs,
  and 30-day stored-response retention is documented for this route.
- All LLM calls must use the shared LiteLLM endpoint and stable request tags.
- One application attempt; LiteLLM owns provider retry/fallback.
- Existing person and organization entities must remain untouched.

## Done When

- [x] `fli entity-kinds enrich` reads only current unsure entities and supports
  `--limit` without modifying canonical kinds or adding persistence tables.
- [x] One developer prompt governs both stages; the second call contains only
  the authored-post follow-up and `previous_response_id`.
- [x] Retweets and replies are excluded, including across pagination.
- [x] Contract, chaining, error, scope, and bounded CLI tests pass.
- [x] The full cohort is persisted and promoted with per-entity resumability.
- [x] Protected accounts are rejected before inference and shown with reasons.
- [x] One idempotent X-handle command owns profile persistence, eligibility
  gates, profile/posts/web classification, promotion, and Registry visibility.
- [ ] A paid live calibration proves the final web-search escalation through
  the shared LiteLLM route before project closeout.

## Milestones

- [x] M1 — Implement the two-turn engine. Acceptance: profile `unsure` chains
  one recent-post follow-up with the same strict output contract.
- [x] M2 — Implement authored-post retrieval. Acceptance: up to 20 normalized
  authored posts are returned while replies and retweets are excluded.
- [x] M3 — Validate and calibrate. Acceptance: `scripts/check-fast.sh` passes
  and a bounded live sample is reviewed before storage or promotion work.
- [x] M4 — Calibrate and decide promotion. Acceptance: reviewed evidence and
  cost support an explicit go/change/stop decision before bulk execution.
- [x] M5 — Reject unusable protected accounts. Acceptance: rejection occurs
  before model inference, retains the entity kind, and exposes a reason in the
  Registry.
- [x] M6 — Consolidate one X-account lifecycle. Acceptance: one command applies
  the follower floor, protected gate, profile turn, 20-post turn, final bounded
  web search, persistence, and promotion with exact resume behavior.
- [ ] M7 — Live proof and closeout. Acceptance: one explicitly authorized paid
  calibration resolves or safely abstains, sources/cost are persisted, and
  `scripts/check-fast.sh` passes before archive.

## Execution Rules

- Keep the classifier sequential and bounded: profile, then at most 20 authored
  posts, then one Responses request with at most four hosted web tool calls.
- Keep model output exactly `classification` and `reason`; runner-owned evidence
  and metadata must not leak into the output schema.
- Do not run a paid hosted-web calibration without explicit current-session
  approval.
- Update this tracker before handoff and leave it active while calibration and
  promotion decisions remain open.

## Decisions

- Direct Responses API through LiteLLM, not Agents SDK: one responsibility and
  existing SQLite orchestration do not justify a general agent framework.
- One `ENTITY_KIND_INSTRUCTIONS` developer prompt replaces the three historical
  classifier/web/post instruction variants in the active code.
- Responses use `store=True` only to support chaining and rely on Azure's normal
  30-day retention; no explicit remote deletion is required.
- The first calibration returns JSON but does not write model results locally.
- A Registry rejection is curation state, not a fourth structural kind. The
  add-only `entity_registry_rejections` table owns its code, reason, source,
  evidence URL, and timestamp.
- Twenty authored posts remain the deterministic evidence cap. If they still
  abstain, missing evidence is usually external identity linkage rather than
  more account voice, so one required hosted-web turn is the final escalation.
- Hosted-web actions and complete consulted sources remain runner-owned in the
  existing `entity_kind_web_enrichments` table; the model still returns only
  `classification` and `reason`.

## Open Questions / Blockers

- Paid live proof is awaiting Adi's explicit approval. Recommended first target:
  only `@jack`; expected incremental cost is small but includes hosted-search
  spend that is not fully represented by the LiteLLM model-cost header.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Implement and locally validate the canonical single-handle X lifecycle with a final bounded web-search escalation. | parent | — |
| blocked | Run one paid `@jack` calibration and inspect the exact sources, cost, and persisted Registry result. | parent | `resources/philschmid-calibration.md` (historical tool smoke only) |
| todo | Review the live result, run final validation, and archive the tracker if the accepted scope is complete. | parent | — |

## Backlog / Remaining Work

- [x] Run the current 137-account recent-post calibration.
- [ ] Review labels, post evidence, cost, and false-confidence cases.
- [ ] Decide the durable local storage and resume contract.
- [ ] Implement and validate atomic promotion only after the policy is accepted.
- [ ] Run the accepted scope, verify Registry invariants, and archive the project.
- [x] Route the canonical single-handle onboarding lifecycle through the same
  protected-account gate and rejection store.
- [x] Add a final required hosted-web turn only after profile and posts abstain.
- [ ] Run the explicitly approved live calibration, verify Registry/API state,
  and decide whether to run the same final step for `@linatawfik9`.

## Validation / Test Plan

- `.venv/bin/python -m pytest -q tests/test_entity_kinds.py`
- `scripts/check-fast.sh`
- Confirm `entities.kind` counts and SQLite integrity are unchanged.

## Progress Log

- 2026-07-10: [IN-PROGRESS] Azure/LiteLLM capability smoke succeeded; scoped
  implementation to a staged runner only, with full execution and promotion
  deferred for discussion.
- 2026-07-10: [DONE] Implemented `fli entity-kinds enrich` with required hosted
  search, strict two-field output, staged SQLite evidence, one-attempt errors,
  per-entity commits, exact resume identity, and bounded CLI limits. Added four
  focused tests; all 42 repository tests plus frontend lint/build pass. Applied
  the new empty table to `data/fli.db`; canonical kinds remain 2,639 person,
  182 organization, and 145 unsure, with zero stored enrichments.
- 2026-07-10: [DONE] Ran one live `@philschmid` enrichment through LiteLLM.
  Stage one had only handle/name/null bio/X URL and correctly abstained. Stage
  two performed one hosted search, consulted 17 URLs, and staged `person` with
  a grounded personal-site/Hugging Face reason. It used 8,698 input and 160
  output tokens and cost `$0.009658`. Canonical kind remains `unsure`. The
  exact trace is in `resources/philschmid-calibration.md`; broader execution is
  paused because the structured message did not identify a minimal cited
  subset within the full consulted-source list.
- 2026-07-10: [DONE] At Adi's explicit direction, permanently removed the stray
  `@philschmid` candidate and its local account, channel, source fact,
  classification, and staged enrichment. Then audited every remaining
  Registry X channel and removed all 38 entities with a stored follower count
  below 1,000: 32 people, two organizations, and four unsure, plus 558 attached
  graph edges. Six entities with missing counts remain. Current Registry:
  2,607 people, 180 organizations, 140 unsure; zero below-threshold entities;
  SQLite integrity `ok`.
- 2026-07-10: [DONE] Filled five of six missing smol.ai profile snapshots
  through TwitterAPI.io. Removed `@akhaliq` at 40 followers and `@lucidrains`
  at 395; retained `@rohanpaul_ai`, `@thebloke`, and `@tom_doerr` above the
  floor. The stale `@danhendrycks` handle resolved to the existing canonical
  `@hendrycks` entity, refreshed at 44,775 followers, and its smol.ai provenance
  was transferred. At that checkpoint all 137 unsure entities had follower
  counts of at least 1,000 and the Registry had zero unknowns; the later clean
  source reset supersedes this historical cohort size.
- 2026-07-10: [BLOCKED] Adi took ownership of the remaining unsure-enrichment
  calibration and promotion decision. Agent execution moves to the separate
  trusted-following ranking project and must not resume this batch unless Adi
  asks.
- 2026-07-10: [IN-PROGRESS] Adi explicitly resumed this project and selected a
  simpler profile-to-posts workflow. Consolidated the active prompt to one
  developer instruction set, added a plain-language profile turn and optional
  `previous_response_id` follow-up with up to 20 authored posts, and excluded
  replies and retweets. The calibration path adds no result table and does not
  modify canonical kinds; local persistence will be designed after review.
- 2026-07-10: [DONE] Corrected an over-aggressive graph cleanup by restoring all
  post-floor classified nodes from the Git-tracked database snapshot while
  keeping rejected graph evidence absent. The active unsure cohort remains 137.
- 2026-07-10: [DONE] Ran all 137 current unsure accounts through the unified
  Luna-medium profile-to-posts workflow without writing results or changing
  canonical kinds. The full pass plus the single `@jack` incomplete-response
  retry produced 129 person, four organization, and four unsure decisions with
  zero remaining failures. The accepted full-run calls cost `$0.388090` by
  LiteLLM; an earlier 10-account calibration cost `$0.018285`. Removed an
  arbitrary local 240-character reason limit and raised the Responses output
  ceiling after the calibration exposed both harness issues.
- 2026-07-10: [DONE] At Adi's direction, reran the current 137-account set and
  committed every completion immediately into the existing
  `entity_kind_classifications` table, then updated `entities.kind` without a
  schema change. The Registry now shows 2,735 people, 184 organizations, five
  unsure, and zero unknown; the live API/UI and SQLite integrity check confirm
  the persisted state. This persistence run cost `$0.382921` through LiteLLM.
- 2026-07-10: [DONE] Added an explicit protected-account precondition before
  model inference and a separate reason-bearing Registry rejection state.
  Marked `@_michi_y`, `@andrwpng`, and `@samsamoa` rejected from provider flags
  without deleting them. The Registry now presents 2,735 people, 184
  organizations, two active unsure, three rejected, and zero unknown.
- 2026-07-10: [IN-PROGRESS] Consolidated the full lifecycle behind
  `fli entity-kinds onboard --handle @…`: fetch/persist the provider profile,
  enforce the 1,000-follower and protected-account gates before inference,
  classify the profile, add up to 20 authored posts after abstention, and use
  one required hosted-web Responses turn after a second abstention. The web
  turn continues with `previous_response_id`, caps hosted tool calls at four,
  and persists actions/sources outside the unchanged two-field model schema.
  Focused fake-provider tests pass; live paid proof is awaiting approval.
