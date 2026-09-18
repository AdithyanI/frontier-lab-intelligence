# Code and Data Map

Use this map to locate ownership when the package layout is not enough.
[`overview.md`](overview.md) explains boundaries; [`docs/STATUS.md`](../STATUS.md)
tracks conceptual proof. The runtime is parked; command examples below require
the authorization and setup in [`service-lifecycle.md`](../references/service-lifecycle.md).

## Pipeline

```mermaid
flowchart TD
    R["Registry and source identities"] --> X["X collection and raw evidence"]
    X --> F["Feed snapshots"]
    F --> E["Exact Events"]
    E --> A["Canonical artifacts"]
    E --> V["Developments<br/>artifact-anchored Event groups"]
    A --> V
    V --> S["Daily Development rank"]
    A --> U["Audience routing"]
    V --> U
    S --> U
    U --> I["Company-aware Investment agent<br/>bet-linked Insights"]
    U --> G["AI Engineering agent<br/>surface-linked Insights"]
    I --> W["Web and CLI adapters"]
    G --> W
    I --> D["Manual Slack/email delivery"]
```

Dependency direction is left-to-right. Domain code must not import `fli.web`.
The current exceptions are `fli.scoring.evaluation` and parts of the artifact
and routing run code that consume the Event API read model; remove those when
the Event read model moves out of `web`, not through new aliases.

## Source Ownership

| Area | Owner | What belongs there |
| --- | --- | --- |
| Shared runtime | `fli.llm_responses`, `fli.store`, `fli.paths` | Provider response normalization, deterministic cache-key lane grouping, the compact product DB boundary, and logical data references with guarded external storage. |
| Provider diagnostics | `fli.diagnostics.prompt_cache` | Non-mutating Luna/Terra reusable-prefix canary with stable JSON, typed errors, and cache/cost telemetry. |
| Ingestion | `fli.ingestion` | Public-source adapters, conference imports, raw X evidence, and date-complete collection. |
| Registry | `fli.registry.store`, `fli.registry.view`, and the other `fli.registry` workflows | Entity/channel mutation and curation stay in `store`; the API-facing read projection stays in `view`; admission, classification, evaluation, and seeds own their workflows. |
| Trusted network | `fli.network` | Immutable outgoing-follow snapshots, derived support/ranking analysis, and its read model. `provenance` owns the canonical JSON, file hash, checkpoint, and UTC identity shared by those frozen data products. |
| Evidence | `fli.evidence` | Deterministic Feed materialization, exact structural Events, artifact-anchored Development projection, and the end-to-end refresh client. Exact Events remain the immutable provenance unit. An artifact-based Development belongs to the artifact's earliest accepted Event day, so later disclosures cannot republish the same Development ID. |
| Artifacts | `fli.evidence.artifacts.store`, `.fetch`, and `.cli` | Catalog/provenance persistence, retrieval/extraction, and the machine command adapter are separate boundaries. |
| Daily Development rank | `fli.scoring.development_attention` | Versioned lexicographic Development ordering. Production uses `daily-development-rank-v1`; the earlier exact-Event `daily-rank-v2` remains historical lineage only. |
| Audience routing | `fli.routing` | Independent Engineering/Investment relevance decisions, durable runs, audit view, and active prompt. |
| Insights | `fli.insights` | Audience-specific generators, result validation, exact traces, cohort publication, and read projections. `company_context` owns Investment memo/bet interpretation; `pdf_report` and `pdf_report_engineering` render the canonical audience projections. See the Insight refresh contract for execution. |
| Delivery | `fli.delivery.daily_brief` | Explicit Slack/email delivery of canonical audience briefs and derived PDFs. It owns formatting/provider adapters, not Insight data or scheduling. |
| Web | `fli.web.app`, `fli.web.feed`, `fli.web.events`, `fli.web.developments`, `fli.web.artifact_library` | HTTP composition and read projections only. `/api/events` preserves exact Event inspection; `/api/developments` is the ranked Feed read model; `/api/developments/analysis-packet` renders the exact read-only routing input without a model call. Built SPA assets live in `fli.web.dist`; editable UI source is `frontend/`. |
| Root client | `fli.cli` | Thin subcommand router only; domain behavior belongs to the owning area. |
| Demo release | `demo.command`, `scripts/demo.py`, `scripts/build-demo-release.py` | Verified snapshot restore, read-only launch, and operator-only release construction. The release contract is `data/demo-release.json`. |

The root package contains only cross-domain runtime plumbing (`cli`,
`llm_responses`, the compact product `store`, and storage `paths`). Operational provider probes
live in `fli.diagnostics`; domain behavior belongs in the packages above. Do
not add compatibility modules at former flat paths.

## Frontend Ownership

The React source mirrors product domains rather than collecting unrelated
routes in a generic `pages/` directory:

| Area | Owner | What belongs there |
| --- | --- | --- |
| App composition | `frontend/src/app/` | Route composition and the shared audit-date provider only. |
| System guide | `frontend/src/features/system/` | The `/how` shell composes the interactive story, long-form narrative, page index, reviewer map, and closed technical appendix. There is no separate public System or Status workspace. |
| Architecture figures | `frontend/src/features/architecture/` | Reusable technical figures embedded by `/how`; these do not own a public route. |
| Evidence | `frontend/src/features/evidence/` | Feed, Artifact index, their workspace layout, and Evidence-only view state. |
| Insights | `fli.insights` | Audience-specific generators, result validation, exact traces, cohort publication, and read projections. `company_context` owns Investment memo/bet interpretation; `pdf_report` and `pdf_report_engineering` render the canonical audience projections. See the Insight refresh contract for execution. |
| BIT Lens | `frontend/src/features/bit-lens/` | Public BIT research brief plus the auditable company-context ledger. The index comes from the canonical Investment packet; the single generated `docs/references/company-memos.json` packet supplies 37 source-bearing company memos and their binary standing bets. |
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
| `data/derived/signal-events/events.db` | `fli signal-events` / `fli evidence-refresh` | Artifacts, routing, Event UI | Rebuildable exact Event projection with an explicit date-to-run publication map. |
| `data/derived/artifacts/artifacts.db` | Artifact catalog/fetch commands | Routing and artifact UI | Durable local catalog; daily imports append dated lineage, while raw bodies and clean text are content-addressed beside it. |
| Development read model | No independent writer | Feed, routing, artifact UI | Deterministic projection over exact Events plus accepted canonical artifacts. Full day views are cached in process; the compact date/count summary is also persisted as a disposable exact-view cache so restarts do not rebuild every day before rendering navigation. There is deliberately no separate Development database. |
| `data/derived/audience-routing/*/routing.db` | `fli audience-routing` | Feed, Insights, rank evaluation | Immutable per-day runs. Current-compatible runs bind their source Feed/Event publication and full-day Development rank-input SHA. |
| `data/derived/insights/investment-agent-traces/<day>/*.json` | `fli insights run-investment-agent` | Investment import, operator audit | Durable exact request/response envelopes for every model turn, plus response IDs, retryable and terminal request failures, memo calls and packets, usage, cost, and the validated final result. |
| `data/derived/insights/investment-agent.db` | Investment runner/import | Investment API/UI/PDF | Durable validated runs and complete current-version cohort publication; exact evidence, memo, prompt, model and cost lineage stays attached. |
| `data/derived/insights/engineering-agent-traces/<day>/*.json` | `fli insights run-engineering-agent` | Engineering import, operator audit | Durable exact request/response envelope for the single model call, plus response ID, retryable and terminal request failures, the surface map hash, usage, cost, and the validated final result. |
| `data/derived/insights/engineering-agent.db` | `fli insights run-engineering-agent` / `import-engineering-trace` | AI Engineering Insights API/UI | Durable surface-linked runs. Each row binds the Development, prompt/model identity, surface-map and evidence hashes, token/cache/cost telemetry, and validated result. A per-day publication records the complete current AI Engineering-routed cohort under the same all-or-nothing and cross-day uniqueness contracts as Investment. |
| `data/derived/insights/pdf-cache/` | `GET /api/insights/report.pdf` | Daily Insight PDF downloads | Rebuildable content-addressed PDFs keyed by report schema, read schema, date, audience, and published-cohort result hash; atomic writes make concurrent first requests safe. |
| `data/derived/web-event-cache/` | Event and Development API read models | Evidence API and Feed UI | Optional compressed exact Event-day views plus Event and Development date summaries, automatically invalidated by source database versions and projection code. Safe to delete; source stores remain authoritative. |

Manual delivery adds no second report or outbox store. It reads the complete
published Investment projection and reuses the PDF cache at confirmation time.

See [`data/README.md`](../../data/README.md) for directory lifecycle and
[`docs/references/data-lifecycle.md`](../references/data-lifecycle.md) before
removing or archiving local data.

## Commands

- Refresh one new UTC day without moving older publications:
  `fli evidence-refresh --day YYYY-MM-DD`
- Rebuild an intentional historical Evidence window:
  `fli evidence-refresh --through YYYY-MM-DD --days N`
- Materialize individual boundaries: `fli signal-feed`, `fli signal-events`,
  `fli artifacts`
- Route Evidence: `fli audience-routing`
- Generate or inspect Insights: `fli insights`. Run the company-aware
  Investment loop with `fli insights run-investment-agent`; add `--dry-run` to
  resolve and validate the exact cohort without model calls, traces, database
  writes, or publication. Import one already completed trace with `fli insights
  import-investment-trace`, read the live contract with `fli insights
  contract`, and inspect the company packet with `fli insights
  company-context` or `fli insights company-universe`.
- Inspect the daily Development rank: `/api/developments` or the Feed. The
  historical `fli daily-rank evaluate` command still evaluates exact-Event
  `daily-rank-v2` lineage.
- Inspect one exact future routing input without running the model:
  `/api/developments/analysis-packet?date=YYYY-MM-DD&development_id=...` or
  `Preview what audience analysis reads` inside the expanded Feed Development.
- After resume, run the product with `fli web` or its service at
  `http://127.0.0.1:8797` (only after resume)
- Open the hosted product:
  `https://frontier-lab-intelligence.adithyan.io/`
- Restore and run the frozen reviewer release: `./demo.command`

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
  `src/fli/web/dist/` is intentionally tracked and served by the app when resumed.

## Where Exact Details Live

- System boundaries: [`overview.md`](overview.md)
- Scoped implementation contract index: [`implementation-contracts.md`](../references/implementation-contracts.md)
- Current proof and critical path: [`docs/STATUS.md`](../STATUS.md)
- Feed/Event contract: [`signal-feed.md`](../references/signal-feed.md)
- End-to-end Evidence refresh: [`evidence-refresh.md`](../references/evidence-refresh.md)
- Artifact contract: [`artifact-library.md`](../references/artifact-library.md)
- Insight refresh/client: [`insight-refresh.md`](../references/insight-refresh.md)
- Model routing contract: [`model-routing.md`](../references/model-routing.md)
- Prompt-cache contract and live proof: [`prompt-caching.md`](../references/prompt-caching.md)
- Measured workflow and provider economics: [`tokenomics.md`](../references/tokenomics.md)
