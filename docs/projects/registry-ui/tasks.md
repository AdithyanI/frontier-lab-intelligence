# Registry UI

## Goal

Ship the Registry page as the product's front door: labs (real, seeded) and
people candidates (evidence-ranked, honestly labeled) browsable in the web UI.

## Why / Impact

The registry is the rubric's top deliverable (20%) and the surface BIT would
actually use. Today the UI leads with raw Accounts — a workbench, not a
product. Adi wants to *see* the registry first, then build curation/scoring
on top of it. Nav story after this project: Registry (who we track) →
Accounts (evidence workbench) → Architecture (how it works).

## Scope / Non-Goals

### In Scope

- `/api/registry` endpoints serving labs (from `labs`) and top people
  candidates (from `accounts` + `account_source_facts`: Digg rank, PageRank,
  disagreement, role, followers).
- Registry page in the SPA: labs section (10 entities, status, channels,
  graph link) + people section (top candidates, clearly labeled "candidates —
  curation pass not yet run"), with filters (type lab/person, role) and rank
  columns (Digg vs PageRank, disagreement highlighted).
- Nav update: Registry becomes first; Accounts demoted to evidence drill-down.
- Plain-words explainers on the page per the teach-Adi contract.

### Out of Scope

- LLM auto-curation pass (own project; will fill `people.status`).
- Org/person classification + affiliation extraction (own project).
- Sigma.js graph visualization (deferred E2).
- Insights/reports/alerts surfaces.

## Context / Constraints

- Date started: 2026-07-09
- Deadline (case study): 2026-07-20. Rubric: registry 20% — this is the
  visible half of it.
- Data ready: `labs` (10 rows, 9 linked to graph accounts), 2,314 accounts,
  361K edges, Digg rank + PageRank facts (`account_source_facts`).
  Notable: SSI Digg#401 vs PageRank#24 — show disagreement, it's the story.
- Stack: FastAPI JSON API (`src/fli/web/app.py`) + React/Vite/TS SPA
  (`frontend/`, builds into `src/fli/web/dist`). Design: `DESIGN.md`
  (editorial instrument), `PRODUCT.md` §System/Design Principles.
- People entities don't exist yet — the page must be honest: candidates are
  candidates, not tracked people. No fake "tracked" status.
- Global contracts (deadline, rubric, principles, submission guardrail) live
  in `AGENTS.md` + `docs/references/case-prompt.md`; archived history in
  `docs/projects/archive/frontier-lab-intelligence/`.

## Done When

- [x] Registry page live at `fli web`: labs + candidate people with evidence
      columns, filterable, honest labeling.
- [x] Registry is the first nav item / landing emphasis; Accounts reads as
      drill-down.
- [x] Both ranks + disagreement visible; disagreement finding spottable in UI
      (used @jack #246 Digg / #52 PageRank in the on-page example — SSI
      itself is a lab and excluded from the people table by design, so it's
      no longer the right in-UI example; still true and citable in writing).
- [x] Plain-words explainer text on the page (labs curated / people derived /
      what candidate means).
- [x] Tests green, `scripts/check-fast.sh` OK, pages screenshot-verified.

## Milestones

- [x] M1 — `/api/registry` (labs + candidates JSON). Acceptance: labs=10 with
      channel fields; candidates carry digg_rank, pagerank_rank, role,
      followers. Validate: pytest + curl. Done 2026-07-09.
- [x] M2 — Registry page (labs + candidates sections, filters, explainers).
      Acceptance: renders real data per DESIGN.md; honest candidate labeling.
      Validate: Playwright screenshots desktop + mobile. Done 2026-07-09.
- [x] M3 — Nav/IA update (Registry first; Accounts demoted) + docs refresh
      (architecture overview, DESIGN.md if needed). Validate: check-fast +
      screenshots. Done 2026-07-09.

## Execution Rules

- Keep work scoped to the current milestone unless the tracker explicitly
  expands scope.
- Run validation after each milestone and fix failures before advancing.
- Update this tracker whenever the plan changes materially or before ending
  the run.
- Append a build-log entry (`docs/references/build-log.jsonl`) per meaningful
  chunk.
- Archive to `docs/projects/archive/registry-ui/` when Done When is
  satisfied.

## Decisions

- 2026-07-09: UI-first sequencing (option A) — Adi wants to see the registry
  before building the curation pass on top of it.
- 2026-07-09: Registry shows entities; Accounts stays as the evidence
  workbench underneath (provenance in one click).
- 2026-07-09: Candidates exclude any account already linked as a lab's
  `x_account_id` (orgs like @openai shouldn't double-count as person
  candidates). Consequence: SSI (a lab) never appears in the people table,
  so the on-page disagreement example uses @jack instead.

## Open Questions / Blockers

- None.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | M1: `/api/registry` endpoints (labs + candidates) | parent | `src/fli/web/app.py`, `tests/test_web.py` |
| done | M2: Registry page in SPA | parent | `frontend/src/pages/Registry.tsx`, `frontend/src/app.css` |
| done | M3: nav/IA update + docs refresh | parent | `frontend/src/App.tsx`, `docs/architecture/overview.md` |

## Backlog / Remaining Work

- [x] Validation pass: tests + check-fast + Playwright screenshots at 1440px
      and 390px.
- [x] Docs review: architecture overview reflects Registry-first IA.
- [ ] Closeout: archive tracker to `docs/projects/archive/registry-ui/`.

## Validation / Test Plan

- `.venv/bin/python -m pytest -q` (API tests incl. new registry endpoints).
- `scripts/check-fast.sh`.
- `npm --prefix frontend run build` then Playwright MCP screenshots of
  Registry page (desktop + 390px).
- Manual: disagreement column populated and correctly signed (verified via
  @jack #246 Digg / #52 PageRank → "graph +194").

## Progress Log

- 2026-07-09: [IN-PROGRESS] Project created from split of the monolithic
  frontier-lab-intelligence tracker (now archived).
- 2026-07-09: [DONE] M1-M3 shipped in one session. `/api/registry` added
  (labs query + candidates query with lab-exclusion + disagreement field +
  pool total); `Registry.tsx` built (labs table, candidates table, search +
  role filter, plain-words explainers, honest "0 tracked" banner); nav
  restructured (Registry "/" landing, System moved to "/system", Accounts
  "/accounts", Architecture unchanged); mobile nav overflow bug (topbar
  didn't wrap with 4 links) found and fixed in the same pass. Also fixed a
  copy bug: initial draft cited SSI's Digg#401/PageRank#24 disagreement as
  the in-UI example, but SSI is a lab and is excluded from the candidates
  table by design — swapped to @jack (visible in the actual table).
  Evidence: 16/16 pytest green, `scripts/check-fast.sh` OK, Playwright
  screenshots at 1440px and 390px reviewed (labs table, candidates table,
  mobile nav wrap). `npm run lint` clean, `npm run build` clean.
