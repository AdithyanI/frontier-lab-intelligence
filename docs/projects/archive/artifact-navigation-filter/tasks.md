# Artifact Navigation Filter

## Goal
Exclude deterministic navigation endpoints from canonical artifact packets and rebuild the affected July 14 evidence so envelope #92 cannot route on unrelated dynamic search-page content.

## Why / Impact
The artifact catalog accepted `https://www.amazon.science/search` as a durable artifact. Its changing search-page snapshot supplied unrelated Amazon Ads content to routing, producing audience reasons that did not describe the root AWS departure post.

## Scope / Non-Goals
### In Scope
- Add a conservative deterministic URL exclusion for generic search/navigation endpoints.
- Preserve the observed link and reason-bearing exclusion provenance.
- Rebuild affected artifact/routing data and verify July 14 envelope #92.

### Out of Scope
- Semantic model-based artifact alignment.
- General artifact-role classification.
- Audience-routing prompt changes.
- Filtering specific job postings or other durable documents.

## Context / Constraints
- Date started: 2026-07-17
- Preserve existing canonical-artifact and lineage invariants.
- Keep the rule structural and host-agnostic; do not special-case Amazon or this envelope ID.
- Run all LLM calls through the shared LiteLLM endpoint if a routing rerun is required.

## Done When
- [x] Generic `/search` navigation URLs are excluded with a stable reason code and regression coverage.
- [x] The Amazon Science search page is absent from envelope #92's routing packet after rebuild.
- [x] The affected route no longer cites unrelated Amazon Ads evidence.
- [x] Fast checks pass and the completed tracker is archived.

## Milestones
- [x] Milestone 1 — Navigation URLs are excluded during artifact import. Acceptance: structural test covers generic search endpoints without excluding specific documents. Validate: 29 targeted artifact tests pass.
- [x] Milestone 2 — July 14 derived evidence is clean. Acceptance: #92 packet excludes the search artifact and its route is refreshed or invalidated. Validate: local API and both SQLite stores.
- [x] Milestone 3 — Repository handoff is clean. Acceptance: relevant architecture/status guidance is accurate and fast checks pass. Validate: `bash scripts/check-fast.sh`.

## Execution Rules
- Keep work scoped to the current milestone unless the tracker explicitly expands scope.
- Run validation after each milestone or risky batch and fix failures before advancing.
- Continue until the scoped project is done or a true blocker requires human input.
- Archive the tracker when all Done When conditions are satisfied.

## Decisions
- Filter generic navigation endpoints before they can become packet-eligible artifacts; preserve their import-candidate exclusion record.
- Use URL structure only in this spike. Semantic alignment remains out of scope.
- Revalidate the final URL after redirects and fail terminally before writing a body snapshot when the destination is ineligible.
- Rebuild the affected routing day explicitly. Making route publication automatically artifact-sensitive is a separate harness improvement, not part of this bounded gate.

## Open Questions / Blockers
- None.

## Current Batch
| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Locate artifact URL admission and derived-data refresh boundaries; implement the smallest structural exclusion. | parent | — |
| done | Rebuild and inspect July 14 #92 packet/route. | parent | — |
| done | Run repository checks, record the completed reroute, and archive. | parent | — |

## Backlog / Remaining Work
- [x] Run targeted tests and full fast checks.
- [x] Review architecture/status docs for any durable contract update.
- [x] Close and archive this tracker.

## Validation / Test Plan
- Targeted artifact URL/import tests.
- Inspect artifact candidate decision and routing packet for event `28de30d40da6c2824b51ca28d9cf3315aa87d14a70e6213beb0bc0c19b0ae46e`.
- `bash scripts/check-fast.sh`.

## Progress Log
- 2026-07-17: [IN-PROGRESS] Created tracker for the bounded navigation-filter cleanup.
- 2026-07-17: [DONE] Bumped the candidate contract to `artifact-url-v2`, excluded exact `/search` paths, and added final-redirect eligibility validation. Targeted URL/fetch tests pass 29/29.
- 2026-07-17: [DONE] Removed the derived Amazon search artifact, re-imported the immutable Feed/Event evidence, and persisted the author URL as `failed_terminal` with `final_url_search_navigation` and no snapshots.
- 2026-07-17: [DONE] Rebuilt the July 14 top-100 routing cohort for $0.508 proxy-reported cost. The live API exposes #92 with zero artifacts and both audiences correctly mark the unspecified career/project teaser irrelevant.
- 2026-07-17: [DONE] `scripts/check-fast.sh` passes 362 backend tests, 47 frontend tests, lint, and the production build; tracker closed for archive.
