# Frontier Lab Intelligence - Agent Guide

Frontier Lab Intelligence tracks frontier AI labs and key people, turns public
output into scored/cited signal, and delivers reports + alerts. Origin: BIT
Capital AI Engineer case study.

## Start Here

1. `docs/references/case-prompt.md` - external requirements.
2. Active `docs/projects/<project>/tasks.md` - execution state; use `$project`.
3. `docs/architecture/overview.md` - system map.
4. `PRODUCT.md` / `DESIGN.md` - product and UI contracts.
5. `docs/references/research-notes.md` / `docs/references/build-log.md` -
   provenance and history.

If docs conflict with chat, note it in the active tracker and follow the
preserved prompt until Adi decides.

## Hard Rules

- No external action without explicit current-session Adi approval: submitting,
  uploading, publishing, public pushes, or contacting BIT/Lars/Marc/Vlad. Before
  asking, prepare artifacts, message text, validation evidence, limitations, and
  prompt-requirement check.
- Keep Dobby/person-memory architecture out of this product repo.
- Put scratch in `tmp/`; put durable facts, decisions, provenance, and spend in
  repo docs.

## Work Contracts

- Data first: fetch raw evidence, inspect, then model; the DB schema is not
  locked yet.
- Product principles live in `PRODUCT.md`; do not trade away quality for the
  EUR100 budget unless actual spend approaches it.
- Build log: append one JSON object to `docs/references/build-log.jsonl` after
  meaningful chunks; `scripts/check-fast.sh` renders markdown.
- Update `docs/architecture/overview.md` when pipeline, schema, source classes,
  or module boundaries change.
- Run `scripts/check-fast.sh` before handoff, or record why validation was
  skipped in the active tracker.

## UI Preview & Visual Checks

- An always-on local server serves the built SPA at `http://127.0.0.1:8797`
  (launchd `com.dobby.frontier-lab-intelligence`). Use it. Do **not** spin up a
  throwaway `vite preview` / dev server on another port for screenshots.
- To see UI changes: `npm --prefix frontend run build` (writes into
  `src/fli/web/dist`, which the always-on server hosts), then reload
  `127.0.0.1:8797`.
- Take screenshots with the **Playwright MCP** tools
  (`playwright-browser_navigate` → `_resize` → `_take_screenshot`), not
  ad-hoc puppeteer scripts. Save any images under `tmp/`.
- **Desktop-first for now:** design and polish the desktop view; do not spend
  effort on mobile/responsive polish unless Adi asks. (Decision 2026-07-09.)

## Skill Routing

- AGENTS/docs/harness review: `$agent-native-repo-playbook`.
- Tracker planning, refresh, or closeout: `$project`.
- UI review or frontend polish: `$impeccable`.
