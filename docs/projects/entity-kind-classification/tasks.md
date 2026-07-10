# Entity Kind Classification

## Goal

Build and evaluate an agent-native first pass that classifies every currently
unknown X-backed entity as `person`, `organization`, or `unsure`, stores a short
reason, and makes the result safely resumable before any channel merging or
track/reject curation.

## Why / Impact

The Registry currently contains 2,956 unknown provisional clusters. Earlier UI
versions implicitly presented most accounts as people even though the corpus
contains organizations, products, publications, communities, and projects.
This pass establishes the simplest truthful structural label so later agents
can merge organizational channels and separately decide what is worth tracking.

## Scope / Non-Goals

### In Scope

- Classify each existing unknown X-backed entity independently as
  `person`, `organization`, or `unsure`.
- Use only identity-bearing profile fields for the first attempt: handle,
  display name, bio, and profile URL.
- Use OpenAI Structured Outputs through the existing LiteLLM proxy.
- Return only `classification` and `reason` from the model.
- Persist classifications, short reasons, and deterministic run metadata so a
  failed or interrupted run can resume without repeating completed work.
- Run a varied bounded calibration batch before the complete corpus.
- Keep the Registry/API truthful as classifications land.

### Out of Scope

- Merging multiple X accounts into one organization.
- Inferring employment or lab affiliation for people.
- Track/reject relevance curation.
- PageRank recomputation or source weighting.
- Adding more discovery sources.
- Fetching recent posts for every account. Recent posts may later enrich only
  accounts classified `unsure`.
- Direct Azure OpenAI integration.

## Context / Constraints

- Date started: 2026-07-10.
- Deadline: 2026-07-20, Europe/Berlin working assumption.
- Read first: `AGENTS.md`, this tracker,
  `docs/references/registry-curation.md`, and
  `docs/architecture/overview.md`.
- Archived predecessor:
  `docs/projects/archive/entity-spine-bootstrap/tasks.md`.
- Current database snapshot:
  - 2,967 graph accounts; 1,746 have a non-empty bio.
  - 2,966 visible entities: 10 seeded labs and 2,956 unknowns.
  - 2,998 channels and exactly 2,998 entity-channel links.
  - 12,664 source facts, 361,863 graph edges, and 21,133 observations.
  - SQLite integrity is `ok`.
- Source invariants: Digg ranks 1,000; AI High Signal members 609; smol.ai
  members 31; retained Adi follows 638.
- Runtime LLM path: LiteLLM only. Read `LLM_API_ENDPOINT` and `LLM_API_KEY`
  from the existing shared machine-secret setup at `~/.secrets/litellm/env`.
  Do not add or consume direct Azure OpenAI credentials in this repo.
- The existing `openai-docs` skill and `openaiDeveloperDocs` MCP are routed to
  this repository. A fresh Codex task is required to load them.
- Playwright MCP is intentionally disabled for this data phase. Re-enable it
  through `/Users/dobby/GitHub/agents/codex/config/repo-bootstrap.json` only
  when frontend visual work resumes.
- The current database still implements `lab | person | unknown`. Do not
  pretend the target taxonomy is already migrated.

## Accepted Classifier Contract

The runner already knows the entity/account being processed. The model must not
repeat the handle, ID, model name, prompt version, timestamp, or probability.

Input assembled by deterministic code:

```json
{
  "handle": "example",
  "display_name": "Example Name",
  "bio": "Observed profile biography or null",
  "profile_url": "https://x.com/example"
}
```

Only valid model output:

```json
{
  "classification": "person",
  "reason": "The name and biography describe an individual researcher."
}
```

Rules:

- `person`: the account represents an individual human.
- `organization`: the account represents a company, lab, nonprofit, team,
  product, publication, community, or project rather than one individual.
- `unsure`: identity-bearing evidence is missing, contradictory, or too weak.
- No probability or confidence score.
- Digg rank, PageRank, follower count, Digg role, and list membership are not
  classifier inputs.
- Classification is independent per current cluster. Do not merge channels in
  this pass.
- A person usually has one primary X account; an organization may have many.
  The underlying channel model continues to allow multiple channels for both.
- Seeded labs are organizations with a lab role in the target model. Preserve
  current lab UI behavior until the migration is explicitly implemented.

## Done When

- [x] The prompt and Structured Outputs schema enforce exactly
      `classification` plus `reason`.
- [x] A resumable CLI/agent runner processes deterministic account batches
      through LiteLLM with bounded concurrency and structured errors.
- [x] A varied calibration batch is stored and inspected before the full run;
      obvious people, organizations, missing bios, brands, and ambiguous
      handles are represented.
- [ ] Every one of the 2,956 initial unknown entities has either a stored valid
      classification result or a clearly recorded terminal error requiring
      action; `unsure` is a valid result.
- [ ] Result counts reconcile to the input universe and no channel ownership,
      source evidence, or graph edges are changed by classification.
- [ ] The Registry/API exposes the truthful person/organization/unsure result
      without presenting a probability.
- [x] Prompt/model version, token use, cost, and validation evidence are logged
      outside the model response.
- [ ] Repo checks pass and architecture/curation docs match implemented reality.

## Milestones

- [x] M1 — Classifier foundation. Acceptance: official docs checked; OpenAI SDK
      talks to LiteLLM; minimal structured schema, prompt, persistence, CLI, and
      tests exist. Validate: focused tests plus `scripts/check-fast.sh`.
- [x] M2 — Calibration. Acceptance: a deterministic varied sample is processed,
      outputs and abstentions are inspected, prompt errors are corrected, and
      estimated full-run cost is recorded. Validate: sample reconciliation and
      qualitative audit notes.
- [ ] M3 — Full corpus. Acceptance: the complete initial unknown set is
      processed resumably with bounded concurrency and exact reconciliation.
      Validate: database invariants, token/cost totals, and SQLite integrity.
- [ ] M4 — Product surface and closeout. Acceptance: API/Registry shows the new
      structural labels truthfully, docs are current, checks pass, and this
      tracker is archived. Re-enable Playwright through the control plane before
      any required screenshot validation.

## Execution Rules

- Use `$openai-docs` and the official Developer Docs MCP before implementing
  Responses API or Structured Outputs code.
- Keep the model schema minimal; application code owns identifiers and run
  metadata.
- Treat `unsure` as correct abstention, not a request to invent an answer.
- Do not use attention metrics as structural identity evidence.
- Make writes idempotent and resumable before running paid bulk inference.
- Estimate and record spend before the full-corpus run.
- Keep classification, merging, affiliation, and relevance as separate stages.
- Update this tracker and `docs/references/build-log.jsonl` after each milestone.
- Run `scripts/check-fast.sh` before handoff.
- Archive this tracker when all Done When conditions are satisfied.

## Decisions

- 2026-07-10: First pass labels are exactly `person`, `organization`, and
  `unsure`; no probability is wanted.
- 2026-07-10: Model output is exactly `classification` and `reason`. Repeating
  the handle or operational metadata in the LLM output is unnecessary.
- 2026-07-10: Run through the shared LiteLLM proxy, not direct Azure OpenAI.
- 2026-07-10: Use identity-bearing profile data first. Consider recent posts
  only for `unsure` cases after the initial pass.
- 2026-07-10: Kind classification comes before channel merging. Track/reject is
  a later independent decision.
- 2026-07-10: Organization is intentionally broad for this first pass and
  includes non-person brands, products, publications, communities, and
  projects. Later merging determines the parent organization when appropriate.
- 2026-07-10: The Responses request uses `text.format` with strict JSON Schema,
  `additionalProperties: false`, and required `classification` / `reason`.
  LiteLLM advertises response-schema support for `gpt-5-nano` and
  `gpt-5-mini`; calibration started with nano at minimal reasoning effort.
- 2026-07-10: The accepted runtime default is `gpt-5.6-luna` with
  `reasoning.effort=medium`. Reasoning effort is part of the resumability key,
  so evaluation results from `none` and `medium` remain independently auditable.
- 2026-07-10: Every classifier request carries stable LiteLLM tags for app,
  pipeline, job, scope, prompt, and run through both `metadata.tags` and the
  compatibility `x-litellm-tags` header. Store proxy-reported cost separately
  from the local official-price estimate.

## Open Questions / Blockers

- The one-time 2,000-follower cleanup is not replayable policy. Do not rerun
  `import-x-following` or `channels sync` during classification without first
  handling the documented rematerialization risk.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Freeze `gpt-5.6-luna` + prompt v2 + reasoning `medium` as the application default after the 15-profile result passed qualitative review. | parent | `src/fli/entity_kinds.py` |
| done | Verify the stable LiteLLM deployment with one tagged Luna-medium call and reconcile request tags, token counts, proxy spend, and local estimated cost. | parent | `data/fli.db` |
| in_progress | Run all 2,956 initial unknown entities with resumable Luna-medium inference, then reconcile classifications, spend, errors, and data invariants. | parent | `data/fli.db` |

## Backlog / Remaining Work

- [ ] Add a versioned human-labeled evaluation fixture for regression testing; Adi explicitly authorized the full run after reviewing the 15-profile calibration.
- [ ] Reconcile classification counts and verify graph/channel invariants.
- [ ] Migrate or project accepted results into the Registry API and UI.
- [ ] Re-enable Playwright through the control plane for final UI screenshots.
- [ ] Update architecture, curation contract, and build log to implemented state.
- [ ] Review project learnings and archive this tracker at completion.

## Validation / Test Plan

- `scripts/check-fast.sh`
- Focused classifier/CLI tests with a fake LiteLLM client; no network required.
- Structured-output schema rejects extra keys and invalid labels.
- Rerunning a completed batch performs no duplicate paid calls or duplicate
  decision writes.
- Calibration and full-run counts reconcile to the snapshotted input IDs.
- SQLite `PRAGMA integrity_check` returns `ok`.
- Entity/channel ownership, source fact counts, and graph edge counts remain
  unchanged by pure classification.
- Live `/api/registry` counts and labels match stored classification results
  once M4 lands.

## Fresh-Session Resume Prompt

Copy this into a fresh Codex task after restarting the app:

> Use `$project` and `$openai-docs`. Resume the active project at
> `docs/projects/entity-kind-classification/tasks.md`. Read `AGENTS.md`, that
> tracker, `docs/references/registry-curation.md`, and
> `docs/architecture/overview.md` first. Confirm that the OpenAI Developer Docs
> MCP is available and Playwright MCP is absent. Then execute the Current Batch
> autonomously: verify the current Responses API Structured Outputs contract,
> inspect the local LiteLLM routing contract, and implement the minimal
> `person | organization | unsure` classifier whose model output contains only
> `classification` and `reason`. Use only the LiteLLM endpoint/key already
> provided by the shared machine-secret setup; do not use direct Azure OpenAI.
> You are authorized to run one bounded calibration batch through LiteLLM after
> implementing tests and resumability. Estimate and report the full-run cost
> before processing all 2,956 unknown entities. Do not add sources, merge
> channels, classify relevance, rerun the X following import, or submit anything
> externally. Keep the tracker and build log current and run
> `scripts/check-fast.sh` before handoff.

## Progress Log

- 2026-07-10: [IN-PROGRESS] Archived the evidence/entity-spine phase and
  created this tracker from Adi's accepted minimal classifier contract.
- 2026-07-10: [DONE] Verified the handoff snapshot against SQLite and the live
  Registry API; JSONL build history parsed, all 28 tests passed, and
  `scripts/check-fast.sh` completed successfully. No inference call was made.
- 2026-07-10: [DONE] Verified the current official Responses Structured Outputs
  contract through the OpenAI Developer Docs MCP and OpenAPI spec. The local
  LiteLLM `/models` and `/model/info` routes advertise `gpt-5-nano` and
  `gpt-5-mini`, response-schema support, and respective prices of
  $0.05/$0.40 and $0.25/$2.00 per million input/output tokens. Playwright MCP
  remains absent.
- 2026-07-10: [DONE] Implemented `fli entity-kinds`: strict two-field schema,
  identity-only inputs, versioned prompt/input hashes, separate run/result/error
  tables, bounded concurrency, retries, resumable skips, refusal/incomplete
  handling, token/cost accounting, and fake-client tests. The canonical
  `entities.kind` field remains unchanged.
- 2026-07-10: [IN-PROGRESS] Calibration run 1 processed 12 varied profiles with
  nano prompt v1: 12 valid outputs, zero retries/errors, 6 person / 6
  organization / 0 unsure, 2,626 input + 623 output tokens, and $0.0003805.
  Audit found `@rpoo` should abstain and outside-knowledge phrasing should be
  forbidden, producing prompt v2. Adi then authorized only 10 more: run 2
  produced 10 valid outputs, zero errors, 5 person / 5 organization / 0 unsure,
  2,434 input + 538 output tokens, and $0.0003369. Nano still mislabeled
  `@rpoo`; M2 remains open. The measured v2 full-run estimate is 719,490 input
  + 159,033 output tokens and $0.09959 for 2,956 entities. No bulk run started.
- 2026-07-10: [DONE] Adi proposed the newly available `gpt-5.6-luna` alias.
  Official docs identify Luna as the efficient/high-volume GPT-5.6 option and
  require `none`/`low` rather than the older `minimal` effort. The same 10
  prompt-v2 inputs ran with `reasoning.effort=none`: 10 valid outputs, zero
  errors, 4 person / 5 organization / 1 unsure, 2,434 input + 392 output
  tokens, and $0.004786 at official standard prices. Luna correctly abstained
  on `@rpoo` and all nine obvious labels/reasons passed qualitative review.
  The base full-run projection is 719,490 input + 115,875 output tokens and
  $1.41474; budget $1.56 if the documented 10% regional-processing uplift
  applies. No full run started.
- 2026-07-10: [IN-PROGRESS] Made Luna-medium the default and expanded the
  deterministic smoke set to 15 profiles. Run 4 completed 15/15 with zero
  errors: 5 person / 8 organization / 2 unsure, 3,698 input + 612 output
  tokens, and $0.00737 by official pricing; the full-run projection is
  $1.45238 before any regional uplift. All labels and reasons passed
  qualitative review, including abstentions for `@rpoo` and the anonymous
  `@vibagor44145276`. Added reasoning-aware resume identity, six stable
  LiteLLM request tags, compatibility tag headers, and proxy response-cost
  capture. The old proxy stored tokens but zero spend and only User-Agent tags;
  wait for Adi's stable LiteLLM deployment, then verify with one call.
- 2026-07-10: [DONE] LiteLLM 1.91.1 and the explicit GPT-5.6 standard rate
  cards deployed successfully. One post-deploy Luna-medium request classified
  `@jeffdean` as `person` with a grounded reason. App run 5, the response cost
  header, and the persisted LiteLLM spend log all reconcile at 261 input + 36
  output tokens and `$0.000477`; all six app/pipeline/job/scope/prompt/run tags
  are present in both the request log and tag aggregation. The database now
  holds 5 runs, 48 classifications, and zero classification errors. No bulk
  run was started.
