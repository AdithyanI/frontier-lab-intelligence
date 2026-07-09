# Channel Model (Entities + Channels data model)

## Goal
Introduce the entity/channel data model — `entities` (who: labs + people, rank derived here) linked to a unified `channels` table (every information tap: X, GitHub, blog, arXiv) — so entity resolution and future ingestion have a durable foundation.

## Why / Impact
The case rubric's biggest item (20%) is "Registry of labs and individuals: the right entities … entity-resolved, and kept current." Today only X accounts exist as a table; labs' other channels are strings and there is no entity concept, so people can't be tracked, rank can't be attributed to actors, and content ingestion has no attachment point. Done wrong: junk placeholder entities, or a rewrite that breaks the working graph/PageRank/API mid-case-study.

## Scope / Non-Goals
### In Scope
- `entities` table (person | lab) seeded from the 10 labs.
- Entity↔channel resolution link (nullable ownership: unresolved accounts are the default state, not an error).
- Lab channel strings (blog_feed, github_org, arxiv_query, website) become real channel rows tied to lab entities.
- Entity-level rank derived (not stored raw) from the entity's X channel PageRank.
- Update API (`/api/registry` and friends), tests, and Registry UI to read through entities.
- Docs: architecture overview + build log updated.

### Out of Scope
- Blog/GitHub/arXiv content ingestion (channels get created, not fetched).
- Multi-platform blended rank; per-signal-type weights.
- LLM auto-curation pass promoting candidate people to entities (separate project).
- People entities beyond what manual/simple promotion gives us in this batch.

## Context / Constraints
- Date started: 2026-07-09
- Current schema (data/fli.db): `accounts` (X only, ~thousands, graph + PageRank), `graph_edges`, `account_source_facts`, `labs` (channel strings + `x_account_id`), `raw_items`.
- Two independent Sonnet-5 reviews (2026-07-09, session f036cbac) converged on: entities must NOT own accounts (unresolved is the default → nullable/link-table ownership); rank stored per-channel, derived at entity level; website/arxiv are fetch config until ingested.
- PDF terminology (docs/references/case-prompt.md): "entity", "entity resolution", "channels" (official lab outlets), "accounts/handles". Table names should follow it.
- Adi's chosen mental model: ONE `channels` table; "account" is just a description of channel kinds that have followers (x, github). No separate accounts table long-term.
- Key files: `src/fli/store.py`, `src/fli/labs.py`, `src/fli/graph.py`, `src/fli/web/app.py`, `frontend/src/pages/Registry.tsx`, `tests/`.
- Validation baseline: `.venv/bin/python -m pytest -q` (16 green), `scripts/check-fast.sh`.

## Done When
- [ ] `entities` exists with the 10 labs; each linked to its X channel; lab channel strings materialized as channel rows.
- [ ] Unresolved X accounts remain first-class (graph/PageRank untouched or equivalent after rename).
- [ ] Entity rank readable via API, derived from X PageRank.
- [ ] Registry UI reads entities + channels (labs table shows channels per entity).
- [ ] All tests green; check-fast OK; architecture overview updated.

## Milestones
- [ ] M1 — Decide rename timing (Open Question 1) and write migration. Acceptance: schema migrated, row ids preserved, graph_edges intact. Validate: `pytest -q` + row-count parity checks.
- [ ] M2 — Seed entities from labs + resolution links + channel rows from lab strings. Acceptance: 10 lab entities, each with x channel linked and blog/github/arxiv channel rows where strings exist. Validate: SQL spot checks + new unit test.
- [ ] M3 — API + Registry UI read through entities; derived entity rank exposed. Acceptance: `/api/registry` returns entity-shaped data; UI renders unchanged-or-better. Validate: `pytest -q`, `npm run build && npm run lint`, screenshot review.
- [ ] M4 — Docs + closeout. Acceptance: architecture overview + build-log entry updated; tracker archived. Validate: `scripts/check-fast.sh`.

## Execution Rules
- Keep work scoped to the current milestone unless the tracker explicitly expands scope.
- Run validation after each milestone or risky batch and fix failures before advancing.
- Preserve `accounts`/`channels` row ids across any rename so `graph_edges` and `account_source_facts` FKs stay valid.
- Continue until scoped work is done or a true blocker requires Adi's input.
- When `Done When` is satisfied and validation is acceptable, archive to `docs/projects/archive/channel-model/`.
- Update this tracker whenever the plan changes materially or before ending the run.

## Decisions
- 2026-07-09: One unified `channels` table is the target model; no separate accounts table long-term. "Account" = description of follower-bearing channel kinds. (Adi + both reviewers on the unified-taps end state.)
- 2026-07-09: Entity ownership of channels is nullable/link-based — unresolved accounts are the default state (thousands of graph accounts have no known owner). Both independent Sonnet-5 reviews flagged required ownership as the killer flaw.
- 2026-07-09: Rank is stored where computed (X channel PageRank); `entity` rank is derived/rolled up, X-only for now. Honest seam for future multi-platform blend.
- 2026-07-09: `website` stays lab metadata (no feed, not a tap); blog/github/arxiv become channel rows.
- 2026-07-09: Follow PDF terminology: entities, channels, entity resolution.

## Open Questions / Blockers
- **Q1 (Adi to decide): rename `accounts`→`channels` now, or add `entities`+link now and rename when blog/GitHub ingestion lands?** Copilot's recommendation: rename later (option 2) — identical end state, zero churn mid-deadline; rename becomes step one of the ingestion project. Adi was mid-decision when tracker was created. M1 blocked on this.

## Current Batch
| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| blocked | M1: resolve Q1 (rename timing) with Adi, then write migration | parent | |
| todo | M2: seed entities + links + channel rows | parent | |

## Backlog / Remaining Work
- [ ] M1 migration (after Q1 decision).
- [ ] M2 seeding (entities, resolution links, channel rows from lab strings).
- [ ] M3 API + UI read-through, derived entity rank.
- [ ] Validation sweep: pytest, check-fast, frontend build/lint, screenshots.
- [ ] Docs: architecture overview module/data-shape update; build-log.jsonl entry + render.
- [ ] Closeout: archive tracker to `docs/projects/archive/channel-model/`.

## Validation / Test Plan
- `.venv/bin/python -m pytest -q` — all green (baseline 16).
- Row-parity check after migration: counts of channels/graph_edges/facts match pre-migration accounts-based counts.
- SQL spot checks: 10 lab entities; `openai` entity has x + blog + github + arxiv channels; unresolved account count unchanged.
- `cd frontend && npm run build && npm run lint`.
- `scripts/check-fast.sh` before handoff.

## Progress Log
- 2026-07-09: [IN-PROGRESS] Created project tracker. Prior work this session: two independent Sonnet-5 schema reviews (converged: link-based ownership, derived rank, unified taps eventually); terminology check against case PDF; registry-ui project archived to docs/projects/archive/registry-ui/.
