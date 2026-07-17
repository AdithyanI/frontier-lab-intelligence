# Repository Housekeeping

## Goal

Make the repository easy for a cold agent to navigate, change, validate, and
operate before the next submission-critical work begins.

## Why / Impact

The product pipeline is substantially stronger than its former repository
shape suggested. Source modules were mostly flat, the long architecture
overview did double duty as a code map, local data mixed current and historical
runtime material, and the active Attention Score tracker no longer reflected
Adi's decision to pause that work. This cleanup makes ownership and lifecycle
boundaries explicit without changing the proven product contracts.

## Scope / Non-Goals

### In Scope

- Pause and archive the explicitly deferred Attention Score v2 tracker.
- Add one concise code/data ownership map and correct stale cold-start routing.
- Consolidate each cohesive domain into one package with no import aliases or
  compatibility shims.
- Remove clearly superseded prompt/root-database junk and document local data
  lifecycle, current stores, and archive rules.
- Keep fast checks deterministic and prove the cold-agent paths through tests.

### Out of Scope

- Redesigning or activating Attention Score v2.
- Deleting immutable raw evidence or current derived stores.
- Building a generalized repository governance framework.

## Context / Constraints

- Date started: 2026-07-17.
- Submission deadline: 2026-07-20.
- Adi asked to prioritize housekeeping and explicitly pause attention scoring.
- Direct clean migration is preferred; do not add old import paths or dual
  reads.
- Runtime data under `data/raw/` and `data/derived/` is ignored but contains
  current evidence and paid/cached source material; deletion requires positive
  proof that a path is obsolete.

## Done When

- [x] A cold agent can find the owner, store, command, reference, and tests for
      every current pipeline stage from one scan-page.
- [x] Domain code, prompts, and tests have coherent package boundaries without
      compatibility shims.
- [x] Active versus archived/deferred projects are unambiguous in STATUS.
- [x] Data documentation distinguishes tracked inputs, immutable raw evidence,
      rebuildable derived state, historical archives, and disposable scratch.
- [x] Clearly obsolete files are removed or archived without touching current
      evidence stores.

## Milestones

- [x] M1 — Cold-start contract corrected. Acceptance: AGENTS and STATUS route to
      this tracker and one current code map; Attention Score is archived as
      deferred. Validate: `bash scripts/check-fast.sh` tracker checks.
- [x] M2 — Domain packages consolidated. Acceptance: current Ingestion,
      Registry, Network, Evidence, Artifact, Routing, Insight, Scoring, and Web
      source/tests live under coherent paths with direct imports only.
- [x] M3 — Data lifecycle cleaned. Acceptance: current stores are documented,
      safe obsolete artifacts are archived/removed, and no current path or
      SQLite integrity check regresses. Validate: store inventory plus fast
      checks.
- [x] M4 — Handoff proven. Acceptance: architecture/code map, package docs, and
      checks agree; `scripts/check-fast.sh` succeeds.

## Execution Rules

- Keep `tasks.md` single-writer; delegated agents may own disjoint code batches
  while the parent owns shared surfaces, integration, and final validation.
- Prefer a bounded structural improvement over a wholesale source-tree move.
- Do not preserve old Python import paths or old data read paths.
- Do not delete immutable raw evidence, current routing runs, or current Insight
  results.
- Run focused tests after each move and the complete fast check before closeout.
- Archive this tracker when all scoped work is complete and validated.

## Decisions

- 2026-07-17: Pause Attention Score v2 without shipping a replacement formula;
  keep the current production score unchanged.
- 2026-07-17: Complete the package migration now, one green domain at a time,
  because Adi explicitly prioritized a clean agent-native base for the next
  work. Preserve behavior and add no compatibility shims.
- 2026-07-17: Raw provider evidence and current derived stores are durable local
  state, not housekeeping junk.

## Open Questions / Blockers

- None.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Consolidate Ingestion, Registry, Network, and tests | explorer | — |
| done | Consolidate Audience Routing and tests | explorer | — |
| done | Consolidate Evidence, Artifacts, Insights, and shared adapters | parent | — |
| done | Reconcile docs, add drift guardrails, run full validation | parent | — |

## Backlog / Remaining Work

- [x] Add and verify the concise code/data ownership map.
- [x] Move each implementation, view, prompt, and test set as green batches.
- [x] Apply the evidence-backed data cleanup and lifecycle documentation.
- [x] Reconcile STATUS and the architecture overview with implemented state.
- [x] Run `scripts/check-fast.sh`, review the final diff, write learnings, and
      archive this tracker.

## Validation / Test Plan

- Focused domain and cross-domain tests after each package move.
- `python -m compileall src tests` for import/path proof.
- SQLite integrity checks for any local database whose location changes.
- `bash scripts/check-fast.sh` before closeout.

## Progress Log

- 2026-07-17: [IN-PROGRESS] Housekeeping activated; two read-only audits were
  delegated while the parent owns all edits and validation.
- 2026-07-17: [DONE] Consolidated all runtime domains into direct-import
  packages; archived deferred score work; moved superseded local data out of
  runtime paths; added the code/data map and lifecycle contract. Focused
  cross-domain Evidence/Routing/Insight tests pass (172 tests).
- 2026-07-17: [DONE] Full fast check passed: 361 Python tests, 44 frontend
  contract tests, artifact lineage audit, frontend lint, and production build.
  Cold-import and CLI smokes resolve every moved package and canonical store.

## Learnings

- Move one domain and its tests as a green slice, then let the parent integrate
  shared CLI/web surfaces. This kept parallel work disjoint while exposing
  cross-domain import mistakes quickly.
- Repository-root calculations and package-owned prompt paths are the primary
  mechanical hazards when nesting modules. Assert canonical paths and read
  every active prompt in a cold-import smoke after a move.
- Structural cleanup becomes durable only when the code map, data lifecycle,
  and fast checks agree. The root-module allowlist now prevents the flat layout
  from silently returning.
