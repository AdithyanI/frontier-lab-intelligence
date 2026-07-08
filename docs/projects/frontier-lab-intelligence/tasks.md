# Frontier Lab Intelligence — Tracker

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
data-inspection surface (FLI's own cobalt/brass identity from `DESIGN.md`,
not adi-design).

| Status | Work item | Evidence / notes |
| --- | --- | --- |
| done | **A. Graph store in SQLite:** create `accounts`, `graph_edges`, `account_source_facts` per `docs/architecture/overview.md` §Graph Storage Plan; load the full Digg pull (1,000 accounts, 361K edges). | `fli graph load`: 2,314 accounts, 6,760 facts, 361,225 edges in `data/fli.db`. Normalized (each account once); reload idempotent; `tests/test_graph.py`; 12 tests green. |
| todo | **B. Source weights:** compute PageRank over the edge graph; store alongside Digg rank as two independent attention signals. | "Important if important people follow you" = PageRank; disagreement between the two signals is itself review-worthy. |
| todo | **C. Layer curated lists:** smol.ai `prefPeople` first (then swyx / Anthropic staff lists) as `account_source_facts` rows joined on handle; triangulation across sources drives candidate confidence. | Source inventory in `docs/references/research-notes.md`. |
| todo | **D. Candidate review table:** API + UI listing one row per account with per-source evidence columns, sorted by combined confidence; the human-review gate before registry promotion. | This is the rubric's registry deliverable (20%). |
| done | **E. Frontend shell:** React + Vite + TS consuming FastAPI JSON. Jinja2 retired. | Live at `fli web` (127.0.0.1:8500): System map with live DB counts per pipeline stage, Accounts table (search/paginate over 2,314 candidates), Architecture page rendering the living doc with Mermaid. Screenshots verified vs DESIGN.md; 14 tests green; built `dist` committed so reviewers need Python only. sigma.js graph viz still todo. |
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

- Commands run:
- Results:
- Files/artifacts reviewed:
- Known limitations:
- Prompt requirements satisfied:
- Prompt requirements not satisfied / blocked:
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
