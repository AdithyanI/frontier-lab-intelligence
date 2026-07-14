# Network Source Architecture Audit Learnings

## Summary

- This project separates a source-architecture problem from the UI symptoms
  that exposed it.
- Capture what would have made source membership, ranking scope, and role
  semantics easier to reason about before the product surface was built.

## What Helped

- The immutable following snapshot and entity-resolved Registry make every
  denominator independently auditable.
- Existing project checkpoints preserve why entity overlap was accepted only
  as candidate-generation evidence.

## What Slowed Things Down

- Registry membership, monitoring, network support, and source priority were
  discussed colloquially as “the network,” which hid distinct contracts.
- A global target-account position was projected into the Registry without a
  similarly prominent denominator or entity-level aggregation contract.

## Improvement Opportunities

### MCPs / Tools

- To be filled during the audit.

### Skills

- To be filled during the audit.

### AGENTS / Docs

- Consider a durable glossary for cohort, support, role, reach, and yield if
  the audit confirms those concepts remain separate.

### Validation / Feedback Loops

- Add a small, reusable source-yield evaluation rather than evaluating source
  selection only through graph plausibility.

### Delegation / Subagents

- Keep `tasks.md` parent-owned and ask independent reviewers to write separate,
  topic-based resources against one frozen problem statement.

## Recommended Follow-Ups

- Populate after the first independent review batch.

## Notes For Future Runs

- Do not solve an unintuitive ordinal by changing its typography before
  confirming what population it ranks and what product decision it should
  support.
