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

## Submission North Star

Until the 2026-07-20 submission, optimize for earning the next interview with
a coherent, defensible, working case study—not a perfect platform. Prefer a
narrow end-to-end proof and 3–5 excellent cited insights over broad graph or
Registry completeness. Timebox infrastructure work, and challenge work that
does not improve rubric coverage, demo proof, or interview discussion. See
`docs/references/context.md` for the decision filter.

## Hard Rules

- No external action without explicit current-session Adi approval: submitting,
  uploading, publishing, public pushes, or contacting BIT/Lars/Marc/Vlad. Before
  asking, prepare artifacts, message text, validation evidence, limitations, and
  prompt-requirement check.
- Keep Dobby/person-memory architecture out of this product repo.
- Put scratch in `tmp/`; put durable facts, decisions, provenance, and spend in
  repo docs.

## Work Contracts

- Data first: fetch raw evidence, inspect, then model. Preserve documented
  schema invariants, but evolve unfinished pipeline stages from real evidence.
- Product principles live in `PRODUCT.md`. Treat cost as observed telemetry,
  not as a product or execution gate: record spend, but do not lower quality,
  change model choice, or block in-scope work because of cost unless Adi sets
  an explicit cap for that work.
- Build log: append one JSON object to `docs/references/build-log.jsonl` after
  meaningful chunks; `scripts/check-fast.sh` renders markdown.
- Route every LLM call through the shared LiteLLM endpoint with stable
  `metadata.tags` for app, pipeline, job, scope, prompt, and run. Capture the
  proxy-reported response cost as the operational source of truth. Use a dated
  local price snapshot only when a pre-run estimate or zero-cost proxy fallback
  is actually needed.
- For bulk LLM jobs with a repeated 1,024+ token prefix, put stable content
  first, use stable sharded `prompt_cache_key` values, and verify cache reads
  from `cached_tokens`; do not assume an eligible prompt is getting cache hits.
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
- Use the in-app Browser skill for UI inspection and screenshots, not ad-hoc
  Puppeteer scripts. Put disposable captures in `tmp/`; presentation assets
  explicitly requested for reuse belong under `docs/references/`.
- **Desktop-first for now:** design and polish the desktop view; do not spend
  effort on mobile/responsive polish unless Adi asks. (Decision 2026-07-09.)

## Skill Routing

- AGENTS/docs/harness review: `$agent-native-repo-playbook`.
- Tracker planning, refresh, or closeout: `$project`.
- UI review or frontend polish: `$impeccable`.
