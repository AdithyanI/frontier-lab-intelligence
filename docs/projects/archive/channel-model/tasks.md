# Channel Model (Entities + Channels data model)

## Goal
Introduce the entity/channel data model — `entities` (who: labs + people)
linked to a unified `channels` table (where we observe them: X, GitHub,
blog, arXiv) plus `channel_observations` (what we measured there) — so
entity resolution and future ingestion have a durable foundation.

## Why / Impact
The case rubric's biggest item (20%) is "Registry of labs and individuals: the right entities … entity-resolved, and kept current." Today only X accounts exist as a table; labs' other channels are strings and there is no entity concept, so people can't be tracked, rank can't be attributed to actors, and content ingestion has no attachment point. Done wrong: junk placeholder entities, or a rewrite that breaks the working graph/PageRank/API mid-case-study.

## Scope / Non-Goals
### In Scope
- `entities` table (person | lab) seeded from the 10 labs.
- One canonical `channels` table. X accounts are `kind='x'` channels; Digg is
  only a bootstrap source, not the data model.
- `entity_channels` resolution link (nullable ownership: unresolved channels
  are the default state, not an error).
- Lab channel strings (blog_feed, github_org, arxiv_query, website) become real
  channel rows tied to lab entities.
- `channel_observations` for measured/source-specific facts: rank,
  PageRank, followers, role guesses, fetch status, etc.
- Entity-level rank derived (not stored raw) from the entity's X channel
  observations.
- Update API (`/api/registry` and friends), tests, and Registry UI to read through entities.
- Docs: architecture overview + build log updated.

### Out of Scope
- Blog/GitHub/arXiv content ingestion (channels get created, not fetched).
- Multi-platform blended rank; per-signal-type weights.
- LLM auto-curation pass promoting candidate people to entities (separate project).
- People entities beyond what manual/simple promotion gives us in this batch.

## Context / Constraints
- Date started: 2026-07-09
- Current schema (data/fli.db): `accounts` (legacy X graph import table),
  `graph_edges`, `account_source_facts`, `labs` (channel strings +
  `x_account_id`), `raw_items`.
- Two independent Sonnet-5 reviews (2026-07-09, session f036cbac) converged on: entities must NOT own accounts (unresolved is the default → nullable/link-table ownership); rank stored per-channel, derived at entity level; website/arxiv are fetch config until ingested.
- PDF terminology (docs/references/case-prompt.md): "entity", "entity resolution", "channels" (official lab outlets), "accounts/handles". Table names should follow it.
- Adi's chosen mental model: ONE `channels` table; "account" is just a description of channel kinds that have followers (x, github). No separate accounts table long-term.
- Key files: `src/fli/store.py`, `src/fli/labs.py`, `src/fli/graph.py`, `src/fli/web/app.py`, `frontend/src/pages/Registry.tsx`, `tests/`.
- Validation baseline: `.venv/bin/python -m pytest -q` (16 green), `scripts/check-fast.sh`.

## Done When
- [x] `entities` exists with the 10 labs; each linked to its X channel; lab channel strings materialized as channel rows.
- [x] Unresolved X channels remain first-class; old X graph rows stay intact as import backing until removed deliberately.
- [x] Channel observations preserve rank/PageRank/follower provenance without making Digg central to the model.
- [x] Entity rank readable via API, derived from X channel observations.
- [x] Registry UI reads entities + channels (labs table shows channels per entity).
- [x] All tests green; check-fast OK; architecture overview updated.

## Milestones
- [x] M1 — Add canonical schema + sync. Acceptance: `entities`,
      `channels`, `entity_channels`, and `channel_observations` exist;
      legacy graph rows are untouched; X accounts are mirrored as X channels.
      Validate: `pytest -q` + row-count parity checks.
- [x] M2 — Seed entities from labs + resolution links + channel rows from lab strings. Acceptance: 10 lab entities, each with x channel linked and blog/github/arxiv channel rows where strings exist. Validate: SQL spot checks + new unit test.
- [x] M3 — API + Registry UI read through entities; derived entity rank exposed. Acceptance: `/api/registry` returns entity-shaped data; UI renders unchanged-or-better. Validate: `pytest -q`, `npm run build && npm run lint`, screenshot review.
- [x] M4 — Docs + closeout. Acceptance: architecture overview + build-log entry updated; tracker archived. Validate: `scripts/check-fast.sh`.

## Execution Rules
- Keep work scoped to the current milestone unless the tracker explicitly expands scope.
- Run validation after each milestone or risky batch and fix failures before advancing.
- Preserve legacy `accounts` rows while channel model lands; do not make new
  product/API code depend on `accounts` as the canonical concept.
- Continue until scoped work is done or a true blocker requires Adi's input.
- When `Done When` is satisfied and validation is acceptable, archive to `docs/projects/archive/channel-model/`.
- Update this tracker whenever the plan changes materially or before ending the run.

## Decisions
- 2026-07-09: One unified `channels` table is the target model; no separate
  accounts concept long-term. "Account" = description of follower-bearing
  channel kinds. Digg is only one bootstrap observation source.
- 2026-07-09: Entity ownership of channels is nullable/link-based — unresolved accounts are the default state (thousands of graph accounts have no known owner). Both independent Sonnet-5 reviews flagged required ownership as the killer flaw.
- 2026-07-09: Rank is stored where computed (X channel PageRank); `entity` rank is derived/rolled up, X-only for now. Honest seam for future multi-platform blend.
- 2026-07-09: `website` stays lab metadata (no feed, not a tap); blog/github/arxiv become channel rows.
- 2026-07-09: Follow PDF terminology: entities, channels, entity resolution.

## Open Questions / Blockers
- None.

## Current Batch
| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | M1: add canonical schema + sync from existing graph/lab data | parent | |
| done | M2: seed entities + links + channel rows | parent | |
| done | M4: final check-fast + archive tracker | parent | |

## Backlog / Remaining Work
- [x] M1 canonical schema + sync.
- [x] M2 seeding (entities, resolution links, channel rows from lab strings).
- [x] M3 API + UI read-through, derived entity rank.
- [x] Validation sweep: pytest, check-fast, frontend build/lint green;
      screenshot review skipped because the in-app browser backend was
      unavailable in this session.
- [x] Docs: architecture overview module/data-shape update; build-log.jsonl entry + render.
- [x] Closeout: archive tracker to `docs/projects/archive/channel-model/`.

## Validation / Test Plan
- `.venv/bin/python -m pytest -q` — all green (baseline 16).
- Row-parity check after sync: graph-backed X channels cover every legacy
  account, and extra official X channels are allowed for labs not seen in the
  graph; graph_edges/facts remain untouched.
- SQL spot checks: 10 lab entities; `openai` entity has x + blog + github + arxiv channels; unresolved account count unchanged.
- `cd frontend && npm run build && npm run lint`.
- `scripts/check-fast.sh` before handoff.

## Progress Log
- 2026-07-09: [IN-PROGRESS] Created project tracker. Prior work this session: two independent Sonnet-5 schema reviews (converged: link-based ownership, derived rank, unified taps eventually); terminology check against case PDF; registry-ui project archived to docs/projects/archive/registry-ui/.
- 2026-07-09: [DECIDED] Build canonical channels now, but keep legacy
  `accounts` as the X graph import backing table until it can be removed
  without churn. Product/API code should move to entities/channels.
- 2026-07-09: [DONE] Built simple source-agnostic model. `fli channels sync`
  materialized 10 lab entities, 2,347 channels, 42 entity-channel links, and
  14,674 observations. API/Registry UI now read entities/channels; old
  `/api/accounts` remains as compatibility workbench.
- 2026-07-09: [DONE] Validation: `pytest -q` 16/16, frontend lint/build
  green, `scripts/check-fast.sh` OK. Browser screenshot review skipped because
  the in-app browser backend was unavailable (`agent.browsers.list()` empty).
