# Entity Kind Classification Learnings

## Summary

Append lessons here while building the resumable LiteLLM classifier. Finalize
this note before archiving the project.

## What Helped

- The model response contract was reduced before implementation to exactly
  `classification` and `reason`.
- The official OpenAI docs skill/MCP and existing LiteLLM runtime path were
  prepared before SDK work began.

## What Slowed Things Down

- `gpt-5-nano` followed the strict JSON shape but not the semantic abstention
  boundary: it called the lone given name `Ross` a full name twice, including
  after the prompt explicitly defined that case as `unsure`.

## Improvement Opportunities

### MCPs / Tools

- Record whether the OpenAI Developer Docs MCP answered the exact Structured
  Outputs and Responses compatibility questions needed for LiteLLM.
  It did: `text.format`, strict JSON Schema, refusal handling, and minimal
  reasoning were all resolved from current official material.

### Skills

- Record any reusable prompt/schema workflow that should be promoted out of
  this repo.

### AGENTS / Docs

- Keep implemented schema and proposed migration language visibly separate.

### Validation / Feedback Loops

- Record which calibration examples exposed prompt errors before the bulk run.
  `@rpoo` (display name `Ross`, no bio, opaque handle) exposed over-classifying
  weak personal evidence. Keep this example in every later model comparison.

### Delegation / Subagents

- None used at project creation.

## Recommended Follow-Ups

- Populate during M1–M4 and finalize at closeout.

## Notes For Future Runs

- Do not confuse `unsure` classification with a probability or a human-review
  requirement; it is the agent's explicit abstention result.
