# Trusted-Following Ranking

## Goal

Build and evaluate a fresh, provenance-complete relevance graph from whom a
small set of trusted people and organizations follow, without reading the
questionable legacy graph.

## Why / Impact

The Registry needs a defensible way to discover the people below the obvious
names. The rejected 361K-edge graph was removed rather than treated as an
interview claim. A smaller trusted-following graph can become a clear, testable
candidate generator while demonstrating ranking and validation discipline.

## Scope / Non-Goals

### In Scope

- Freeze a versioned, human-chosen trusted seed set with short reasons.
- Fetch and persist complete outgoing-follow snapshots for those seeds.
- Isolate the new graph from every legacy edge by construction.
- Compare a simple trusted-seed overlap baseline with personalized PageRank.
- Evaluate the top results against a small recorded human judgment set.
- Produce a bounded Registry candidate shortlist and a defensible interview
  explanation of the result.

### Out of Scope

- Treating the legacy Digg/follower graph as trusted evidence.
- Reintroducing Digg data into the active Registry or graph.
- An open-ended recursive or internet-scale crawl.
- Using graph rank as the final score for documents or insights.
- Unsure-entity enrichment, which Adi owns separately.
- Polishing a graph visualization before ranking quality is proven.

## Context / Constraints

- Date started: 2026-07-10.
- Submission north star: earn the next interview by 2026-07-20 with coherent,
  defensible end-to-end proof; timebox this milestone so extraction, scoring,
  validation, and delivery still ship.
- The active graph is empty. Digg survives only as the offline 1,000-row
  comparison artifact documented in
  `docs/references/digg-ranking-baseline.md`.
- The repo has a tested X-following provider adapter. The rejected global
  PageRank implementation was removed; replacement ranking must read only the
  future isolated snapshot boundary.
- External fetches must be bounded, attributable, and cost-recorded.

## Done When

- [ ] The trusted seed set and reasons are versioned and reviewable.
- [ ] Fresh outgoing-follow snapshots persist edge direction, seed, source,
  fetch time, completeness, and stable identity.
- [ ] New ranking commands cannot read legacy edges accidentally.
- [ ] Trusted-follow count and personalized PageRank are compared on the same
  frozen snapshot.
- [ ] A labeled top-result review records precision/ranking quality and at
  least the most important failure modes.
- [ ] Adi accepts the bounded shortlist or the evaluation supports stopping;
  either outcome is documented before moving to the insight pipeline.
- [ ] Repository checks pass and architecture/build docs match reality.

## Milestones

- [x] M1 — Freeze the evidence boundary. Acceptance: existing graph/import/rank
  semantics are audited and a fresh snapshot contract cannot mix legacy edges.
- [ ] M2 — Build one bounded trusted-following snapshot. Acceptance: complete
  outgoing follows for accepted seeds are persisted with provenance and can be
  reproduced without touching legacy edges.
- [ ] M3 — Rank and compare. Acceptance: overlap baseline and personalized
  PageRank run over the same snapshot and emit inspectable explanations.
- [ ] M4 — Evaluate and decide. Acceptance: labeled top-k review supports an
  explicit keep/change/stop decision and a bounded Registry shortlist.
- [ ] M5 — Document and close. Acceptance: architecture, build log, validation,
  and interview-ready trade-offs are current; tracker is archived.

## Execution Rules

- Keep the graph small enough to understand and evaluate.
- Do not read legacy edges in the new ranking path, even as a fallback.
- Preserve raw observations and snapshot identity before modeling.
- Treat graph rank as candidate-generation evidence, not truth or a final
  intelligence score.
- Compare against the simplest credible baseline before defending PageRank.
- Stop expanding the graph when it no longer improves the accepted evaluation.
- Update this tracker after each meaningful batch and before handoff.

## Decisions

- Rebuild from trusted accounts' outgoing follows, not their followers.
- Prefer personalized PageRank seeded by the trusted set over global PageRank.
- The active database starts from two public source lists plus the 10 curated
  labs. Digg is an offline comparison only; personal following data is absent.
- The rejected Digg edge plane, derived PageRank, graph-only candidates,
  tracked edge artifacts, and reload/rank commands were removed cleanly.
- Protect the end-to-end submission: this is one timeboxed milestone, not the
  product destination.

## Open Questions / Blockers

- Which exact people and organizations form the first trusted seed set?
- What top-k size and relevance labels will Adi review for the evaluation?

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Audit existing edge/import/PageRank code and current database provenance locally. | parent | — |
| done | Verify the official X contract and one live `@karpathy` following count/cost. | parent | `../../references/research-notes.md` |
| done | Remove Digg/personal graph data and unsupported candidates; retain Digg ranking offline only. | parent | `../../references/digg-ranking-baseline.md` |
| blocked | Pause before seed selection, live following fetches, or new ranking work until Adi returns. | parent | — |

## Backlog / Remaining Work

- [ ] Freeze the first trusted seed set.
- [ ] Implement isolated snapshot storage and bounded ingestion.
- [ ] Implement overlap baseline and personalized PageRank.
- [ ] Build and review the labeled top-k evaluation.
- [ ] Update architecture and append the build log after meaningful changes.
- [ ] Run `scripts/check-fast.sh` and milestone-specific tests.
- [ ] Review project learnings and archive the tracker at closeout.

## Validation / Test Plan

- Focused unit tests for snapshot replacement, direction, provenance, and
  legacy-edge exclusion.
- Deterministic ranking tests on a small known graph for both algorithms.
- SQL reconciliation of seed, snapshot, edge, and ranked-node counts.
- Recorded top-k human review with the agreed rubric.
- `scripts/check-fast.sh` before handoff.

## Progress Log

- 2026-07-10: [IN-PROGRESS] Adi rejected the current graph as a trustworthy
  ranking basis and chose a fresh graph from trusted accounts' outgoing
  follows. Created the timeboxed ranking tracker under the submission north
  star; live fetching waits for the evidence-boundary audit and seed decision.
- 2026-07-10: [DONE] Local audit found legacy Digg and exploratory following
  edges in one table. The old PageRank read every source without a filter and
  its stored facts/observations were not a safe current signal. The audit also
  showed that deleting edges alone would leave graph-only candidates active.
- 2026-07-10: [DONE] Official X docs confirm `public_metrics.following_count`
  and `GET /2/users/{id}/following` with up to 1,000 results per page. One
  bounded TwitterAPI.io profile lookup found `@karpathy` follows 1,108 accounts
  and cost about `$0.00018`; a full existing-provider snapshot is estimated at
  `$0.01216`, versus about `$11.08` through official third-party X reads.
- 2026-07-10: [BLOCKED] Full `scripts/check-fast.sh` was not run for this
  documentation/research checkpoint because unrelated in-progress changes are
  present in `src/fli/entity_kinds.py` and `src/fli/sources.py`. Build-log JSONL
  validation, renderer regeneration, and `git diff --check` passed.
- 2026-07-10: [DONE] Adi approved a clean reset. Removed all 360,667 Digg edges,
  all exploratory personal-follow edges, their source facts/observations, the
  invalid derived PageRank, and candidates with no remaining public-list or
  curated-lab provenance. Removed 76 MB of tracked Digg edge artifacts plus
  628 MB of ignored raw graph data and retired the Digg scraper/import/ranker
  paths. The active graph is empty. The Registry now has 586 entities (473
  people, 87 organizations, 26 unsure), 618 channels, and SQLite integrity
  `ok`; `data/fli.db` shrank from 93 MB to 3.5 MB. The frozen Digg ranking CSV
  remains offline for later diagnostic comparison. No following-list API call
  was made during cleanup.
- 2026-07-10: [DONE] Final validation passed: all 36 tests, frontend lint,
  frontend production build, live `/api/status` and `/api/registry`
  reconciliation, SQLite foreign-key check, and integrity check. Execution is
  intentionally paused before seed selection or any following-list fetch.
