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

- [ ] Registry page live at `fli web`: labs + candidate people with evidence
      columns, filterable, honest labeling.
- [ ] Registry is the first nav item / landing emphasis; Accounts reads as
      drill-down.
- [ ] Both ranks + disagreement visible; SSI-style finding spottable in UI.
- [ ] Plain-words explainer text on the page (labs curated / people derived /
      what candidate means).
- [ ] Tests green, `scripts/check-fast.sh` OK, pages screenshot-verified.

## Milestones

- [ ] M1 — `/api/registry` (labs + candidates JSON). Acceptance: labs=10 with
      channel fields; candidates carry digg_rank, pagerank_rank, role,
      followers. Validate: pytest + curl.
- [ ] M2 — Registry page (labs + candidates sections, filters, explainers).
      Acceptance: renders real data per DESIGN.md; honest candidate labeling.
      Validate: Playwright screenshots desktop + mobile.
- [ ] M3 — Nav/IA update (Registry first; Accounts demoted) + docs refresh
      (architecture overview, DESIGN.md if needed). Validate: check-fast +
      screenshots.

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

## Open Questions / Blockers

- None.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| todo | M1: `/api/registry` endpoints (labs + candidates) | parent | |
| todo | M2: Registry page in SPA | parent | |
| todo | M3: nav/IA update + docs refresh | parent | |

## Backlog / Remaining Work

- [ ] Validation pass: tests + check-fast + Playwright screenshots at 1440px
      and 390px.
- [ ] Docs review: architecture overview reflects Registry-first IA.
- [ ] Closeout: archive tracker to `docs/projects/archive/registry-ui/`.

## Validation / Test Plan

- `.venv/bin/python -m pytest -q` (API tests incl. new registry endpoints).
- `scripts/check-fast.sh`.
- `npm --prefix frontend run build` then Playwright MCP screenshots of
  Registry page (desktop + 390px).
- Manual: SSI visible in candidates with Digg#401/PR#24 disagreement.

## Progress Log

- 2026-07-09: [IN-PROGRESS] Project created from split of the monolithic
  frontier-lab-intelligence tracker (now archived).
