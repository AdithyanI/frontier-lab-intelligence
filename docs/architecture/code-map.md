# Code and Data Map

This is the cold-start map for implementation work. Read it after
[`docs/STATUS.md`](../STATUS.md), then use [`overview.md`](overview.md) for the
system boundaries relevant to the task.

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
    U --> I["Daily editorial agent<br/>ranked audience Insights"]
    I --> W["Web and CLI adapters"]
    I --> D["Manual Slack/email delivery"]
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
| Registry | `fli.registry.store`, `fli.registry.view`, and the other `fli.registry` workflows | Entity/channel mutation and curation stay in `store`; the API-facing read projection stays in `view`; admission, classification, evaluation, and seeds own their workflows. |
| Trusted network | `fli.network` | Immutable outgoing-follow snapshots, derived support/ranking analysis, and its read model. `provenance` owns the canonical JSON, file hash, checkpoint, and UTC identity shared by those frozen data products. |
| Evidence | `fli.evidence` | Deterministic Feed materialization, exact structural Events, and the end-to-end refresh client. |
| Artifacts | `fli.evidence.artifacts.store`, `.fetch`, and `.cli` | Catalog/provenance persistence, retrieval/extraction, and the machine command adapter are separate boundaries. |
| Attention | `fli.scoring` | Versioned score formulas and offline comparison. Production remains `attention-v1.1`. |
| Audience routing | `fli.routing` | Independent Engineering/Investment relevance decisions, durable runs, audit view, and active prompt. |
| Insights | `fli.insights` | Per-Event generation plus the `editorial`, `editorial_runs`, `daily_runner`, `codex_app_server`, and `editorial_cli` daily-agent boundary: strict drafts, frozen workspaces, date-keyed orchestration, persisted Codex handoff, atomic runs, the canonical read model, and `pdf_report` for deterministic cached workbooks. |
| Delivery | `fli.delivery.daily_brief` | Manual Slack all-Insight and email top-five formatting, provider adapters, a same-origin confirmation guard, and reuse of the canonical cached PDF. It does not own editorial data or scheduling. |
| Web | `fli.web.app`, `fli.web.feed`, `fli.web.events`, `fli.web.artifact_library` | HTTP composition and remaining projections only. Built SPA assets live in `fli.web.dist`; editable UI source is `frontend/`. |
| Root client | `fli.cli` | Thin subcommand router only; domain behavior belongs to the owning area. |

The root package contains only cross-domain runtime plumbing (`cli`,
`llm_responses`, and the compact product `store`). Domain behavior belongs in
the packages above; do not add compatibility modules at former flat paths.

## Frontend Ownership

The React source mirrors product domains rather than collecting unrelated
routes in a generic `pages/` directory:

| Area | Owner | What belongs there |
| --- | --- | --- |
| App composition | `frontend/src/app/` | Route composition and the shared audit-date provider only. |
| Architecture | `frontend/src/features/architecture/` | The system explanation route and its local presentation logic. |
| Evidence | `frontend/src/features/evidence/` | Feed, Artifact index, their workspace layout, and Evidence-only view state. |
| Insights | `frontend/src/features/insights/` | Audience Insight inspection, decision-state UI, selected daily brief PDF download, and the explicit Slack/email delivery confirmation. |
| Network | `frontend/src/features/network/` | Registry, Ranking, Add Profile, their workspace layout, and the shared entity detail surface. |
| Shared UI | `frontend/src/shared/` | Cross-feature API contracts, date state, text normalization, and genuinely reused components. |
| Styles | `frontend/src/styles/` | Domain styles in cascade order; `app.css` is imports only and remains the single entrypoint. |

`frontend/src/main.tsx` is the only TypeScript entrypoint at the source root.
Prefer feature-local code until two product domains genuinely share a contract;
do not recreate generic `pages/` or `components/` buckets.

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
| `data/derived/audience-routing/*/routing.db` | `fli audience-routing` | Feed, Insights, score evaluation | Immutable per-day runs. New global publications retain new target lineage while exact same-day Event/evidence/input judgments may be reused from compatible predecessors. |
| `data/derived/insights/insights.db` | `fli insights` | Insight read model/UI | Current audience Insight run store. |
| `data/derived/daily-intelligence/editorial.db` | `fli daily-intelligence import-result` / `run-day` | Daily Insight read model/UI and orchestration inspection | Complete agent-authored daily runs plus one date-keyed orchestration ledger with the effective Codex model/reasoning/tier tuple; strict v3 workspaces and the optional packet-keyed embedding cache live beside it. |
| `data/derived/daily-intelligence/pdf-cache/` | `GET /api/insights/report.pdf` | Daily Insight PDF downloads | Rebuildable content-addressed PDFs keyed by report schema, read schema, date, audience, and editorial result hash; atomic writes make concurrent first requests safe. |

Manual delivery adds no second report or outbox store. It reads the complete
editorial projection and reuses the PDF cache at confirmation time.

See [`data/README.md`](../../data/README.md) for directory lifecycle and
[`docs/references/data-lifecycle.md`](../references/data-lifecycle.md) before
removing or archiving local data.

## Commands

- Refresh current Evidence and supported artifacts: `fli evidence-refresh`
- Materialize individual boundaries: `fli signal-feed`, `fli signal-events`,
  `fli artifacts`
- Route Evidence: `fli audience-routing`
- Generate or inspect Insights: `fli insights`
- Prepare, launch, author, validate, persist, or inspect one daily brief:
  `fli daily-intelligence` (`run-day` is the end-to-end entry point)
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
- Daily agent/editorial contract: [`daily-intelligence.md`](../references/daily-intelligence.md)
- Model routing/cache contract: [`model-routing.md`](../references/model-routing.md)
