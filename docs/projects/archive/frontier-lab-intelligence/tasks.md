# Frontier Lab Intelligence — Tracker (ARCHIVED)

> **Archived 2026-07-09.** This monolithic tracker grew too broad; Adi split
> the work into focused per-phase projects under `docs/projects/`. It is kept
> as the historical record of phases A–F (graph store, PageRank, labs seed,
> frontend v1/v2, docs/harness). Durable cross-project facts (deadline,
> rubric, principles, open questions) were carried into
> `docs/projects/registry-ui/tasks.md` and successor trackers; design
> decisions live in `PRODUCT.md`, `AGENTS.md`, and the build log.
> First successor project: `docs/projects/registry-ui/`.

Active execution state for the BIT Capital case-study product.

Full prompt and original materials:
- Prompt capture: `docs/references/case-prompt.md`
- Original PDF + OCR text: `docs/references/source-material/`

Build history, tools, budget, and learning notes now live in
`docs/references/build-log.md`.

## Deadline / Deliverable

- **Deadline:** 2026-07-20, from Lars's email.
- **Deliverable:** working system + code + database/schema/real data +
  architecture/model rationale + prompts + evals + tokenomics + final report.
- **Rubric:** registry 20%, signal-vs-noise 20%, scoring/validation 20%,
  actionable delivery 15%, ingestion 10%, extraction 10%, web UI 5%.
- **Budget:** €100 reimbursable API/services budget; log spend in
  `docs/references/build-log.md`.

## Current Batch

Plan agreed with Adi 2026-07-08: X/Digg graph is the connected spine; other
sources (curated lists, GitHub, blogs) layer on as evidence via shared
handles; entities/identities connect planes. UI moves to React+Vite+TS as a
data-inspection surface (BIT-anchored editorial-instrument identity from
`DESIGN.md`, not adi-design).

| Status | Work item | Evidence / notes |
| --- | --- | --- |
| done | **A. Graph store in SQLite:** create `accounts`, `graph_edges`, `account_source_facts` per `docs/architecture/overview.md` §Graph Storage Plan; load the full Digg pull (1,000 accounts, 361K edges). | `fli graph load`: 2,314 accounts, 6,760 facts, 361,225 edges in `data/fli.db`. Normalized (each account once); reload idempotent; `tests/test_graph.py`; 12 tests green. |
| done | **F. Labs as first-class entities:** `labs` table hand-seeded (~10 labs from the PDF list incl. SSI + Thinking Machines) with official channels (org X handle → `accounts` link, blog, GitHub org, arXiv affiliation). | `fli labs seed`: 10 labs, 9 org X accounts linked into the graph (only alibaba_qwen absent). `src/fli/labs.py`, `tests/test_labs.py`. Registry design agreed with Adi 2026-07-09: labs hand-curated by judgment; people graph-derived; affiliation person→lab optional (independents are valid). |
| done | **B. Source weights:** compute PageRank over the edge graph; store alongside Digg rank as two independent attention signals. | `fli graph pagerank`: 2,313 nodes, converged in 26 iterations, <1s pure Python. Stored as `account_source_facts` (source=graph, facts pagerank/pagerank_rank). Top-10 sane (elonmusk, openai, sama, karpathy…). Disagreement finding: **SSI Digg#401 vs PageRank#24** — graph sees insider attention Digg's method misses; exactly the review-worthy signal we wanted. Test added; 15 tests green. |
| todo | **G. Org/person classification + affiliation hints:** one LLM pass over accounts (974 bios) → is_org flag, lab-affiliation hints; enables graph-based lab discovery (org accounts followed by top-ranked researchers = emerging-lab candidates). | Answers PDF "new names and orgs emerge"; human review before promotion. After F + B. |
| todo | **C. Layer curated lists:** smol.ai `prefPeople` first (then swyx / Anthropic staff lists) as `account_source_facts` rows joined on handle; triangulation across sources drives candidate confidence. | Source inventory in `docs/references/research-notes.md`. |
| todo | **D. Auto-curated registry (redesigned 2026-07-09):** LLM curator reads all evidence per account (PageRank, Digg rank, bio, list membership, affiliation) and decides track/reject with cited reasons + confidence → `people` table with status (`tracked`/`rejected`) built end-to-end, no manual approval gate. Human audits the finished registry in the UI and overrides; overrides stored as top-tier evidence, survive recomputation. | Per PRODUCT.md §System Principles 2–3. Replaces the old "human review gate" design. UI: Registry page (entities) as product surface; Accounts page stays as evidence workbench. |
| done | **E. Frontend shell:** React + Vite + TS consuming FastAPI JSON. Jinja2 retired. | Live at `fli web` (127.0.0.1:8500): System map with live DB counts per pipeline stage, Accounts table (search/paginate over 2,314 candidates). Built `dist` committed so reviewers need Python only. |
| done | **E3. UI redesign (v2):** editorial-instrument direction — BIT capital-blue tokens, top-bar shell, hero-numeral home, custom visual Architecture page (hand-built SVG: graph plane, entities/identities, funnel). | `/api/architecture` + marked/mermaid removed (bundle 1MB→246KB); DESIGN.md rewritten to match; 13 tests green; all three pages screenshot-verified via Playwright MCP. |
| done | **E4. Private Mac mini preview:** host the current app through the shared Cloudflare tunnel. | `frontier-lab-intelligence.adithyan.io` → Cloudflare Access (`adithyan@wisdominanutshell.academy`) → tunnel → `127.0.0.1:8797`; launchd service `com.dobby.frontier-lab-intelligence`; local `/api/status` returns 6 stages; public unauthenticated requests 302 to Access. |
| todo | **E2. Graph visualization:** sigma.js view of the Digg graph (top ~500 nodes default, depth slider), as a drill-down from the Sources stage. | Deferred from E; Adi wants overview-first, detail later. |
| todo | Decide the first modeled registry schema (entities/identities/affiliations) only after reviewing candidates in D. | Deliberately unlocked; model from evidence. |
| later | Design requirement from BIT context: insights/scoring must carry a thesis-supporting vs thesis-breaking dimension (Devil's Advocate). | `docs/references/context.md` §BIT worldview and case lens. |

## Open Questions / Blockers

- **DB schema:** deliberately undecided until candidate evidence is reviewed.
- **Graph storage:** next DB iteration should store accounts and directed
  graph edges in SQLite, with raw observations/evidence kept separately. Do
  not keep expanding nested JSON as the primary working graph format.
- **Database artifact policy:** prompt asks for schema + real data; decide
  packaging/commit policy after modeled schema exists.
- **X API:** not needed yet. Digg is the first graph source; smol.ai can
  validate/anchor candidates. Revisit X API only if the graph has a concrete
  gap that needs paid data.
- **Private cleanup:** before external sharing, strip or rewrite private
  context from `docs/references/context.md` and the build log.

## Execution Plan

1. **Registry:** candidate review table, identity evidence, first modeled
   people/labs schema.
2. **Ingestion:** productionize scheduled public-source pulls around the
   accepted registry.
3. **Extraction:** structured, cited insights tied to people/labs/documents.
4. **Scoring/validation:** defensible dimensions, validation set, precision
   or rank-quality checks.
5. **Delivery:** persona digest, alert path, final report, tokenomics.
6. **UI:** light browse/config/report surface after real modeled output exists.
7. **Submission cleanup:** remove private context, finalize reviewer guide,
   package exact artifacts, ask Adi before any external send.

## Proof Of Work

Update before each handoff when meaningful work lands.

- Commands run: `scripts/install-launchd-frontier-lab-intelligence.sh --install-deps`; `cloudflared tunnel --config ~/.cloudflared/config.yml ingress validate`; `/Users/dobby/GitHub/scripts/setup/network/install-launchd-cloudflare-tunnel.sh`; Cloudflare DNS + Access API calls; local/public `curl` smokes; `scripts/check-fast.sh`; `~/GitHub/scripts/ops/check-fast.sh`.
- Results: local app healthy at `http://127.0.0.1:8797/`; `frontier-lab-intelligence.adithyan.io` redirects unauthenticated requests to Cloudflare Access; DNS CNAME targets the shared tunnel; app process has `cloudflare_env_count=0`; both fast checks passed.
- Files/artifacts reviewed: `~/GitHub/scripts/docs/references/mac-mini-cloudflare-tunnel.md`, `~/GitHub/scripts/sync/local-production-services.json`, `~/.cloudflared/config.yml`, app launchd logs.
- Known limitations: public browser access requires Cloudflare Access login; this is a private preview, not an externally approved submission.
- Prompt requirements satisfied: current machine hosting path is live behind the existing tunnel pattern.
- Prompt requirements not satisfied / blocked: none for private preview; no external submission performed.
- Submission package path:

## Latest Checkpoint

2026-07-08 — Consolidated docs to reduce sprawl:

- `docs/references/build-log.md` now holds build history, AI-tool usage,
  budget, and learning notes.
- `docs/references/context.md` now holds BIT/role context and private builder
  context.
- `docs/references/research-notes.md` now holds assumptions, provenance, and
  seed-source leads.
- `docs/architecture/overview.md` is the single architecture doc.
- Original PDF and OCR text remain untouched in `docs/references/source-material/`.
