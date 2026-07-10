# Unsure Entity Enrichment

## Goal

Add a bounded, resumable Responses API web-enrichment runner for structurally
`unsure` entities without changing canonical kinds until Adi reviews the
calibration evidence.

## Why / Impact

The profile-only classifier initially abstained on 145 weak identity records;
137 remain after explicit corpus removals.
Many can likely be resolved with current public evidence, but the next pass
must preserve its searches, sources, cost, and exact input identity rather than
turning ad-hoc browsing into an unrepeatable correction.

## Scope / Non-Goals

### In Scope

- Read only current `unsure` X-backed entities.
- Use Luna through shared LiteLLM with hosted Responses `web_search`.
- Return only `classification` and `reason` from the model.
- Persist search actions, consulted/cited sources, usage, cost, errors, and
  resumability identity separately from the model output.
- Provide a bounded CLI action and focused fake-client tests.

### Out of Scope

- Running all 145 entities in this implementation batch.
- Promoting enriched results into `entities.kind`.
- Fetching recent X posts through another provider.
- Relevance curation, channel merging, roles, affiliations, or new sources.
- Agents SDK, Codex subagents, or a generalized agent framework.

## Context / Constraints

- Date started: 2026-07-10.
- The first profile-only pass and canonical promotion are complete.
- Azure-hosted Luna web search was proven through LiteLLM with required search,
  source inclusion, Structured Outputs, and three hosted tool actions.
- All LLM calls must use the shared LiteLLM endpoint and stable request tags.
- One application attempt; LiteLLM owns provider retry/fallback.
- Existing person and organization entities must remain untouched.

## Done When

- [x] `fli entity-kinds enrich` reads only current unsure entities and supports
  `--limit` without modifying canonical kinds.
- [x] Completed results skip exact matching input/model/effort/prompt contracts.
- [x] Search actions and source URLs/titles/citation state are stored with each
  result, along with usage and proxy-reported cost.
- [x] Contract, refusal/error, resumability, and scope tests pass.
- [x] Durable docs describe the implemented boundary and deferred decisions.
- [ ] Adi reviews a bounded calibration and accepts or changes the evidence
  policy before any full run.
- [ ] Promotion is implemented and executed, or explicitly descoped, before
  project closeout.

## Milestones

- [x] M1 — Implement schema and runner. Acceptance: one fake hosted-search
  response persists the strict decision plus inspectable evidence.
- [x] M2 — Implement CLI/resume/error coverage. Acceptance: exact repeats make
  no second model call and non-unsure entities never enter the runner.
- [x] M3 — Validate and document. Acceptance: `scripts/check-fast.sh` passes;
  full execution and promotion remain explicitly deferred.
- [ ] M4 — Calibrate and decide promotion. Acceptance: reviewed evidence and
  cost support an explicit go/change/stop decision before bulk execution.

## Execution Rules

- Keep the implementation bounded to this one enrichment stage.
- Do not run the 145-entity batch or promote results in this batch.
- Keep model output exactly `classification` and `reason`; runner-owned evidence
  and metadata must not leak into the output schema.
- Persist each completed entity immediately for interruption-safe resume.
- Update this tracker before handoff and leave it active while calibration and
  promotion decisions remain open.

## Decisions

- Direct Responses API through LiteLLM, not Agents SDK: one responsibility and
  existing SQLite orchestration do not justify a general agent framework.
- Enrichment results remain staged separately from canonical kinds.
- JSON stores the bounded hosted-tool trace and sources in this first pass;
  normalize later only if downstream query/UI requirements justify it.

## Open Questions / Blockers

- Which representative calibration entities and evidence-quality rubric should
  gate a full run?
- Should recent posts be fetched deterministically before open-web escalation?
- What promotion rule should apply when web enrichment still returns `unsure`?
- The discarded `@philschmid` result stored all 17 consulted URLs but no
  final-message citation annotations. A replacement calibration still needs
  to decide whether the internal contract must bind its reason to source IDs.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Implement the bounded web-enrichment runner and evidence schema. | parent | — |
| done | Add focused tests and run repository validation. | parent | — |
| done | Update curation/architecture references and checkpoint this tracker. | parent | — |
| done | Run, document, and then discard the `@philschmid` calibration and entity at Adi's direction. | parent | `resources/philschmid-calibration.md` |
| blocked | Select a replacement calibration and agree the source-binding rubric with Adi; do not run more entities yet. | parent | `resources/philschmid-calibration.md` |

## Backlog / Remaining Work

- [ ] Select and run a bounded representative calibration after discussion.
- [ ] Review labels, sources, search depth, cost, and false-confidence cases.
- [ ] Decide whether to add deterministic recent-post evidence.
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
  was transferred. Removed only the accidental `@adithyan_ai` unknown Registry
  row while preserving its internal account and 638 graph edges. All 137 unsure
  entities remain, all have follower counts of at least 1,000, and the Registry
  has zero unknowns.
