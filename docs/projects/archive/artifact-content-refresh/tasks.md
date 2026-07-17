# Artifact Content Refresh (completed)

## Goal

Prevent obvious extraction shells from becoming artifact evidence without
rerunning unrelated routing or any Insights.

## Completed scope

- Added shared deterministic bot/network, consent, authentication, and
  JavaScript-shell signatures while retaining short legitimate-content controls.
- Revalidated the catalog under `artifact-content-v3`: 25 prior successes were
  quarantined across 25 artifacts and 13 fetch runs; a second pass changed zero.
- Preserved raw snapshots and revoked only derived normalized text/success state.
- Created immutable July 7 and July 15 successor routing runs. They reused 195
  exact-input judgments and made five model calls: two shell removals and three
  already-approved duplicate-artifact removals.
- Did not run or modify Insights.

## Evidence

- Focused artifact/routing tests: 49 passed before data mutation.
- Both successor routing runs are complete at 100/100 with zero failures.
- Incremental GPT-5.4-mini/high cost through LiteLLM: `$0.04326975`.
- Artifact revalidation is idempotent; SQLite integrity and foreign keys pass.

## Decision

Use `fli audience-routing refresh-run` for bounded artifact-only repairs. A new
immutable full cohort is frozen, exact rendered inputs may reuse their prior
judgments with explicit provenance, and only changed packets call the model.
