# Unsure Entity Enrichment

## Goal

Add a bounded profile-to-recent-posts Responses workflow for structurally
`unsure` entities without changing canonical kinds until Adi reviews a live
calibration.

## Why / Impact

The profile-only classifier initially abstained on 145 weak identity records;
137 remain after explicit follower-floor removals and the graph-evidence reset.
Many can likely be resolved from their own recent authored posts. The first
calibration should test that evidence and the two-turn model interaction before
choosing a durable local persistence contract.

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

### Out of Scope

- Running the full unsure cohort in this implementation batch.
- Promoting enriched results into `entities.kind`.
- Adding a new database table or deciding the production persistence schema.
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
- [ ] Adi reviews a bounded calibration and accepts or changes the evidence
  policy before any full run.
- [ ] Promotion is implemented and executed, or explicitly descoped, before
  project closeout.

## Milestones

- [x] M1 — Implement the two-turn engine. Acceptance: profile `unsure` chains
  one recent-post follow-up with the same strict output contract.
- [x] M2 — Implement authored-post retrieval. Acceptance: up to 20 normalized
  authored posts are returned while replies and retweets are excluded.
- [ ] M3 — Validate and calibrate. Acceptance: `scripts/check-fast.sh` passes
  and a bounded live sample is reviewed before storage or promotion work.
- [ ] M4 — Calibrate and decide promotion. Acceptance: reviewed evidence and
  cost support an explicit go/change/stop decision before bulk execution.

## Execution Rules

- Keep the implementation bounded to this one two-stage workflow.
- Do not run the full unsure batch or promote results in this batch.
- Keep model output exactly `classification` and `reason`; runner-owned evidence
  and metadata must not leak into the output schema.
- Do not add local result persistence until the calibration clarifies which
  stage data is worth retaining.
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

## Open Questions / Blockers

- Which fields from each stage should become the durable persistence contract?
- Should a later run retain the full normalized post sample, only its hash, or
  both?
- What promotion rule should apply when the post follow-up remains `unsure`?

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Replace the hosted-web runner with one profile-to-posts Responses workflow. | parent | — |
| done | Add focused chaining and TwitterAPI.io authored-post tests. | parent | — |
| done | Run the full 137-account calibration; do not persist or promote results. | parent | — |
| pending | Decide the local persistence/resume contract from calibration evidence. | Adi + parent | — |

## Backlog / Remaining Work

- [x] Run the current 137-account recent-post calibration.
- [ ] Review labels, post evidence, cost, and false-confidence cases.
- [ ] Decide the durable local storage and resume contract.
- [ ] Implement and validate atomic promotion only after the policy is accepted.
- [ ] Run the accepted scope, verify Registry invariants, and archive the project.

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
