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

| Status | Work item | Evidence / notes |
| --- | --- | --- |
| in-progress | Build a reviewable registry-candidate table from real evidence: Digg full graph + tracked raw corpus, with smol.ai as a small high-trust supplement. | Full Digg graph summary: `data/digg/full_graph_summary.json`; raw full graph ignored under `data/raw/digg-full-2026-07-08/`; source notes in `docs/references/research-notes.md`. |
| todo | Decide the first modeled registry schema only after reviewing candidate evidence. | Current `data/fli.db` is raw evidence only. Architecture sketch is in `docs/architecture/overview.md`. |
| todo | Keep frontend work deferred until registry/extraction/scoring have real modeled output. | UI is 5% of rubric; avoid dashboard-only work. |

## Open Questions / Blockers

- **DB schema:** deliberately undecided until candidate evidence is reviewed.
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
