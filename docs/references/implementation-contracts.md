# Implementation contract index

This is the routing index for exact implementation facts. It deliberately does
not repeat schemas, commands, counts, or historical run results. Update the
owning reference when behavior changes.

Read [`docs/STATUS.md`](../STATUS.md) first for the current proof boundary and
[`docs/architecture/overview.md`](../architecture/overview.md) for system shape.
Use the [code and data map](../architecture/code-map.md) to find the owning
module, store, command, and tests.

## Current invariants

- Raw evidence and exact structural Events remain upstream of model judgment.
- Same-day original posts form one Development only when they share the same
  accepted, release-specific canonical artifact.
- Daily Development rank is deterministic and lexicographic. It is not a
  weighted importance score.
- Audience routing returns independent Investment and AI Engineering
  relevance judgments. Each audience has one current Insight agent, store, and
  reader with no legacy fallback.
- The company-aware Investment agent is the only PDF and delivery source. The
  AI Engineering agent has its own single-call, surface-linked read path.
- Every LLM call uses the shared LiteLLM Responses boundary and records model,
  prompt, usage, cache, cost, and lineage telemetry.
- Complete Investment and AI Engineering cohorts publish atomically. Failed or
  partial batches do not become the current reader state.
- External delivery and case-study communication remain explicit human actions.

## Exact references

| Boundary | Source of truth |
| --- | --- |
| Current proof, limitations, and next boundary | [`docs/STATUS.md`](../STATUS.md) |
| System shape and dependency direction | [`docs/architecture/overview.md`](../architecture/overview.md) |
| Package, store, command, and test ownership | [`docs/architecture/code-map.md`](../architecture/code-map.md) |
| Registry identity, kind, and curation | [`registry-curation.md`](registry-curation.md) |
| Registry evaluation operations | [`registry-evaluation.md`](registry-evaluation.md) |
| Trusted-following snapshot | [`following-snapshot-storage.md`](following-snapshot-storage.md) |
| Feed, exact Events, Developments, and rank projection | [`signal-feed.md`](signal-feed.md) |
| Canonical artifact admission and retrieval | [`artifact-library.md`](artifact-library.md) |
| Evidence refresh and publication | [`evidence-refresh.md`](evidence-refresh.md) |
| Ranking validation | [`scoring-validation.md`](scoring-validation.md) |
| Audience model choice and reasoning policy | [`model-routing.md`](model-routing.md) |
| Prompt caching and provider proof | [`prompt-caching.md`](prompt-caching.md) |
| BIT's public investment and operating context | [`bit-capital-public-context.md`](bit-capital-public-context.md) |
| Investment company universe and memo packet | [`investment-company-universe.md`](investment-company-universe.md) |
| Development-to-company judgment | [`investment-company-mapping.md`](investment-company-mapping.md) |
| Audience Insight preview, run, trace, and publication | [`insight-refresh.md`](insight-refresh.md) |
| PDF, Slack, and email delivery | [`delivery.md`](delivery.md) |
| Local data preservation and restore | [`data-lifecycle.md`](data-lifecycle.md) |
| Measured provider and workflow cost | [`tokenomics.md`](tokenomics.md) |
| Reviewer snapshot and read-only boundary | [`demo-release.md`](demo-release.md) |

## Historical detail

The former 1,200-line catch-all contract is preserved at
[`archive/implementation-contracts-through-2026-07-28.md`](archive/implementation-contracts-through-2026-07-28.md).
It contains useful implementation history but also describes deleted systems.
Do not copy behavior from it without verifying the current code and scoped
reference.
