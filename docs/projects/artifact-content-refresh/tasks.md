# Artifact Content Refresh

## Goal
Make artifact packet eligibility depend on usable extracted content, quarantine every current non-content snapshot, and refresh the complete routing/Insight publication against the cleaned evidence.

## Why / Impact
HTTP or Reader success currently allows verification, authentication, error, video-chrome, and malformed-text shells to become artifact evidence. The audit found 116 such successes; 16 entered routing across 15 Events. The current judgments remained supported, but the packets contain irrelevant text and can reproduce the earlier Amazon Science failure class.

## Scope / Non-Goals
### In Scope
- Add one deterministic shared extracted-content validator for native, Jina Reader, and X Article text.
- Revalidate and quarantine existing derived successes without deleting immutable raw evidence.
- Retry newly eligible public HTML failures through Jina, applying the same validator to its output.
- Rebuild all July 5–15 top-100 audience-routing cohorts from cleaned packets.
- Refresh downstream Insight state required for a current coherent publication.

### Out of Scope
- Bypassing authentication, bot protection, paywalls, or region restrictions.
- Browser-rendering or video-transcript adapters.
- Semantic artifact/event alignment or cross-Event Insight consolidation.

## Context / Constraints
- Date started: 2026-07-17
- User explicitly approved refreshing the complete cohort and paid model calls.
- Preserve immutable raw X evidence and fetched response bodies.
- Preserve unrelated consolidation work already in the repository.
- Every model call must use the shared LiteLLM path and record proxy cost.

## Done When
- [ ] Native and Jina outputs cannot become successful text evidence when they match a confirmed non-content signature.
- [ ] The existing catalog contains no successful text row matching the audit signatures.
- [ ] All 1,100 July 5–15 routing items are rebuilt from the clean artifact packets with zero failures.
- [ ] Current Insights are coherent with the rebuilt routing source.
- [ ] Fast checks and live API spot checks pass; spend is recorded; tracker is archived.

## Milestones
- [ ] Milestone 1 — Shared content eligibility gate. Acceptance: confirmed shell and garbled-PDF fixtures fail closed while legitimate short/mixed content remains accepted. Validate: targeted artifact tests.
- [ ] Milestone 2 — Derived artifact state is clean. Acceptance: revalidation quarantines current bad successes, Reader retries only eligible public HTML, and a repeat audit returns zero successful shell snapshots. Validate: database audit and API inspection.
- [ ] Milestone 3 — Downstream publication is refreshed. Acceptance: 1,100/1,100 routing items complete from clean packets and current Insights expose no stale routing dependency. Validate: database/API checks and recorded telemetry.
- [ ] Milestone 4 — Repository handoff is clean. Acceptance: durable docs/build log are current and `bash scripts/check-fast.sh` passes.

## Execution Rules
- Keep work scoped to the current milestone unless the tracker explicitly expands scope.
- Run validation after each milestone or risky batch and fix failures before advancing.
- Continue until the scoped project is done or a true blocker requires human input.
- Update this tracker after meaningful batches and archive when all Done When conditions are satisfied.
- Do not weaken extraction quality to reduce cost or retain coverage.

## Decisions
- Artifact association remains preserved even when its content is unavailable; only usable text is packet-eligible.
- Apply one validator after every extractor/adapter, not a Jina-specific filter.
- Fail closed rather than attempting to bypass access controls.
- Refresh the complete routing cohort as explicitly requested; refresh only the downstream Insight work made stale by the new routing evidence.

## Open Questions / Blockers
- None.

## Current Batch
| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| in_progress | Implement shared content validation, revalidation lifecycle, and regression tests. | parent | — |
| todo | Quarantine/recover current artifacts and prove a zero-shell catalog. | parent | — |
| todo | Rebuild routing and reconcile current Insights. | parent | — |
| todo | Validate, document, record spend, and archive. | parent | — |

## Backlog / Remaining Work
- [ ] Run targeted and full fast checks.
- [ ] Update artifact/architecture/status documentation for the proven boundary.
- [ ] Record model/provider telemetry in the build log.
- [ ] Review closeout and archive this tracker.

## Validation / Test Plan
- `PYTHONPATH=src .venv/bin/pytest -q tests/evidence/artifacts/test_fetch.py tests/evidence/artifacts/test_x_articles.py`
- Artifact database integrity, success-shell audit, and lineage audit.
- Routing database completeness, evidence hashes, cost/cache totals, and live `/api/events` spot checks.
- Current Insight API/source-contract checks.
- `bash scripts/check-fast.sh`.

## Progress Log
- 2026-07-17: [IN-PROGRESS] User approved a complete clean refresh and paid routing calls; tracker created.
