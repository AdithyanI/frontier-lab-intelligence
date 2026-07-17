# Code and Data Map

This is the cold-start map for implementation work. Read it after
[`docs/STATUS.md`](../STATUS.md); use the longer
[`overview.md`](overview.md) only for the architecture section relevant to the
task.

## Pipeline

```mermaid
flowchart TD
    R["Registry and source identities"] --> X["X collection and raw evidence"]
    X --> F["Feed snapshots"]
    F --> E["Exact Events"]
    E --> A["Canonical artifacts"]
    E --> S["Attention score"]
    A --> U["Audience routing"]
    S --> U
    U --> I["Audience Insights"]
    I --> W["Web and CLI adapters"]
```

Dependency direction is left-to-right. Domain code must not import `fli.web`.
The current exceptions are `fli.scoring.evaluation` and parts of the artifact
and routing run code that consume the Event API read model; remove those when
the Event read model moves out of `web`, not through new aliases.

## Source Ownership

| Area | Owner | What belongs there |
| --- | --- | --- |
| Shared runtime | `fli.llm_responses`, `fli.store` | Provider response normalization and the compact product DB boundary. |
| Ingestion | `fli.ingestion` | Public-source adapters, conference imports, raw X evidence, and date-complete collection. |
| Registry | `fli.registry` | Entity/channel truth, admission, provenance, classification, evaluation, and curated seeds. |
| Trusted network | `fli.network` | Immutable outgoing-follow snapshots, derived support/ranking analysis, and its read model. |
| Evidence | `fli.evidence` | Deterministic Feed materialization, exact structural Events, and the end-to-end refresh client. |
| Artifacts | `fli.evidence.artifacts` | Canonical external-source identity, provenance, retrieval, and extracted text. |
| Attention | `fli.scoring` | Versioned score formulas and offline comparison. Production remains `attention-v1.1`. |
| Audience routing | `fli.routing` | Independent Engineering/Investment relevance decisions, durable runs, audit view, and active prompt. |
| Insights | `fli.insights` | Generation contract, durable runs, machine client, read model, and active prompts. |
| Web | `fli.web.app`, `fli.web.feed`, `fli.web.events`, `fli.web.artifact_library` | HTTP composition and remaining projections only. Built SPA assets live in `fli.web.dist`; editable UI source is `frontend/`. |
| Root client | `fli.cli` | Thin subcommand router only; domain behavior belongs to the owning area. |

The root package contains only cross-domain runtime plumbing (`cli`,
`llm_responses`, and the compact product `store`). Domain behavior belongs in
the packages above; do not add compatibility modules at former flat paths.

## Store Ownership

| Store | Writer | Main readers | Lifecycle |
| --- | --- | --- | --- |
| `data/fli.db` | Registry/source commands | Registry, network, Feed, web | Tracked compact product/demo state; never a raw crawl sink. |
| `data/raw/x/x-content.db` | X collection | Feed, Registry evaluation | Immutable provider cache plus normalized observations; preserve to avoid paid refetches. |
| `data/raw/following/<snapshot>/snapshot.db` | Following snapshot client | Following ranking | Immutable ignored crawl snapshot; manifests under `data/following/` bind checksums and lineage. |
| `data/derived/following/<snapshot>/analysis.db` | Following ranking | Feed and Network UI | Rebuildable analysis for one frozen snapshot. |
| `data/derived/signal-feed/feed.db` | `fli signal-feed` / `fli evidence-refresh` | Events, routing, Feed UI | Rebuildable current Feed projection. |
| `data/derived/signal-events/events.db` | `fli signal-events` / `fli evidence-refresh` | Artifacts, routing, Event UI | Rebuildable exact Event projection and live publication pointer. |
| `data/derived/artifacts/artifacts.db` | Artifact catalog/fetch commands | Routing and artifact UI | Durable local catalog; raw bodies and clean text are content-addressed beside it. |
| `data/derived/audience-routing/*/routing.db` | `fli audience-routing` | Feed, Insights, score evaluation | Frozen per-day current-contract runs; preserve all current v9 days. |
| `data/derived/insights/insights.db` | `fli insights` | Insight read model/UI | Current audience Insight run store. |

See [`data/README.md`](../../data/README.md) for directory lifecycle and
[`docs/references/data-lifecycle.md`](../references/data-lifecycle.md) before
removing or archiving local data.

## Commands

- Refresh current Evidence and supported artifacts: `fli evidence-refresh`
- Materialize individual boundaries: `fli signal-feed`, `fli signal-events`,
  `fli artifacts`
- Route Evidence: `fli audience-routing`
- Generate or inspect Insights: `fli insights`
- Evaluate attention formulas offline: `fli attention-score`
- Run the product: `fli web` or the always-on service at
  `http://127.0.0.1:8797`

All repeated LLM work uses the shared LiteLLM path and the exact contracts in
`AGENTS.md`; do not introduce provider-specific calls inside a domain.

## Tests and Validation

- Tests mirror stable packages under `tests/ingestion/`, `tests/registry/`,
  `tests/network/`, `tests/evidence/`, `tests/routing/`, `tests/scoring/`, and
  `tests/insights/`.
- HTTP contract tests follow the projection they exercise; the Insight read
  model currently lives with the Insight domain.
- Run focused tests while editing, then `bash scripts/check-fast.sh` before
  handoff.
- Build UI changes with `npm --prefix frontend run build`; the output under
  `src/fli/web/dist/` is intentionally tracked and served by the always-on app.

## Where Exact Details Live

- System boundaries: [`overview.md`](overview.md)
- Detailed implemented contracts: [`implementation-contracts.md`](../references/implementation-contracts.md)
- Current proof and critical path: [`docs/STATUS.md`](../STATUS.md)
- Feed/Event contract: [`signal-feed.md`](../references/signal-feed.md)
- End-to-end Evidence refresh: [`evidence-refresh.md`](../references/evidence-refresh.md)
- Artifact contract: [`artifact-library.md`](../references/artifact-library.md)
- Insight refresh/client: [`insight-refresh.md`](../references/insight-refresh.md)
- Model routing/cache contract: [`model-routing.md`](../references/model-routing.md)
