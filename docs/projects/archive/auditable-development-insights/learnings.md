# Project Learnings

## Summary

- This project isolates the model-heavy boundary between routed Developments
  and audience-specific Insights.
- Capture learnings whenever a prompt, schema, run-store, evaluation, or UI
  decision would otherwise need to be rediscovered by a future agent.

## What Helped

- Exact Event and Development lineage already makes the model input
  reproducible.
- The July 21 top-100 routing run supplies a fixed candidate cohort.
- All 37 Investment companies already have compact index entries and rich,
  source-bearing memos.
- Historical Investment v10 and AI Engineering v7 outputs provide examples and
  failure cases without constraining the successor schema.

## What Slowed Things Down

- The prior interview-readiness tracker mixed audit findings, rehearsal,
  implementation ideas, and obsolete pipeline assumptions in one large
  backlog.
- Prompt-cache behavior is best-effort and must remain telemetry rather than an
  architectural premise.
- The Project skill archive helper called `archive_root.mkdir()` without
  `exist_ok=True`; it failed when `docs/projects/archive/` already existed.
  The canonical tool and regression test were repaired in the agents
  control-plane repo. The old tracker used the same validated atomic
  same-filesystem directory rename and postcondition checks before that repair.

## Improvement Opportunities

### MCPs / Tools

- Add one machine-readable Insight cohort audit command that reports lineage,
  positive/negative counts, token/cache usage, cost, and missing evidence.

### Skills

- The Project archive helper repair is complete and covered by the
  `test_existing_archive_root_moves_complete_tree` regression.

### AGENTS / Docs

- Keep the distinction between routed candidate, per-Development Insight, and
  daily editorial publication explicit in `STATUS.md` and architecture docs.

### Validation / Feedback Loops

- Maintain a small fixed cohort containing clear positives, clear negatives,
  unsupported claims, product-only changes, and multi-post Developments.

### Delegation / Subagents

- Keep schemas, run identity, and promotion decisions parent-owned. Delegate
  only bounded audits or independent evidence reviews when useful.

## Recommended Follow-Ups

- Start a new project only if AI Engineering generation, full top-100
  Investment expansion, cohort-level deduplication, or a new ordering contract
  becomes a current priority.
- Keep the current application-owned Feed rank unless a reviewed cohort proves
  that a second ordering boundary improves analyst usefulness.

## Notes For Future Runs

- Do not retune routing because an Insight is weak. First decide whether the
  weakness belongs to mapping, company/build context, evidence, suppression,
  or ordering.
- Negative verdicts are part of the audit trail and must survive publication.
- A narrow Investment-only path was easier to inspect and defend than restoring
  the earlier two-audience editorial system. Deferred breadth should return as
  a new project, not as a compatibility fallback.
