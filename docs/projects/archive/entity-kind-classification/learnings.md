# Entity Kind Classification Learnings

Status: finalized at project archive on 2026-07-10.

## Summary

The classifier, full-corpus run, canonical projection, and Registry surface are
complete. This note captures the reusable lessons from that work.

## What Helped

- The model response contract was reduced before implementation to exactly
  `classification` and `reason`.
- The official OpenAI docs skill/MCP and existing LiteLLM runtime path were
  prepared before SDK work began.
- Separating the model decision from canonical promotion made the full run
  auditable and allowed one atomic, coverage-checked projection afterward.

## What Slowed Things Down

- `gpt-5-nano` followed the strict JSON shape but not the semantic abstention
  boundary: it called the lone given name `Ross` a full name twice, including
  after the prompt explicitly defined that case as `unsure`.
- The same prompt and inputs on `gpt-5.6-luna` with reasoning `none` correctly
  abstained on `Ross`, kept the other nine labels correct, and produced shorter,
  more evidence-grounded reasons. Model quality, not schema shape, was the gap.
- Luna with reasoning `medium` also passed a broader 15-profile smoke set,
  including two correct abstentions. Changing reasoning effort must invalidate
  the resume key; otherwise a prior `none` result can silently skip a `medium`
  evaluation.
- LiteLLM 1.83.14 accepted Responses calls but did not retain request-body tags
  and priced the new Luna alias at zero. Send the documented tag header as a
  compatibility path and keep local estimates separate from proxy-reported
  cost until the stable proxy upgrade is verified.
- Persisting results only after a whole batch was not sufficient resumability
  for a long paid run. Commit each completed entity before launching bulk work.
- LiteLLM owns provider retry and fallback for this deployment. A second
  application retry layer creates duplicate-spend ambiguity, so the durable
  classifier makes one application attempt and stores terminal failures for a
  later resumable run.
- Calibration handles, full-run projection helpers, and transitional schema
  rebuilds were useful during the bounded rollout but were not permanent
  product contracts. Remove one-time scaffolding after its evidence is captured
  in the archived tracker and regression tests.
- A hand-curated seed is not an exhaustive taxonomy. The 10-row `labs` table
  remains useful source provenance, but surfacing it as a Registry subtype
  would imply that every other organization had been evaluated for lab status.

## Improvement Opportunities

### MCPs / Tools

- Record whether the OpenAI Developer Docs MCP answered the exact Structured
  Outputs and Responses compatibility questions needed for LiteLLM.
  It did: `text.format`, strict JSON Schema, refusal handling, and minimal
  reasoning were all resolved from current official material.

### Skills

- BerriAI publishes an official `view-usage` skill for tag/job usage queries,
  but request instrumentation is a small application contract and does not
  justify installing a skill yet.

### AGENTS / Docs

- Keep implemented schema and proposed migration language visibly separate.
- When a source seed resembles a product category, document explicitly whether
  it is exhaustive before exposing it as a filter or badge.
- Treat proxy-reported spend as authoritative. A dated local model-price
  snapshot is only a fallback for pre-run projection or a temporarily unpriced
  proxy alias, not a second billing system.

### Validation / Feedback Loops

- Record which calibration examples exposed prompt errors before the bulk run.
  `@rpoo` (display name `Ross`, no bio, opaque handle) exposed over-classifying
  weak personal evidence. Keep this example in every later model comparison.

### Delegation / Subagents

- None used at project creation.

## Recommended Follow-Ups

- Add a versioned human-labeled regression fixture before changing the model,
  prompt, or reasoning effort.
- Enrich only the 145 `unsure` entities if better identity evidence becomes
  worthwhile.
- Introduce a lab-role classifier only if the product needs it, and only after
  evaluating every organization rather than reusing the incomplete seed list.

## Notes For Future Runs

- Do not confuse `unsure` classification with a probability or a human-review
  requirement; it is the agent's explicit abstention result.
