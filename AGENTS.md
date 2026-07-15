# Frontier Lab Intelligence - Agent Guide

Frontier Lab Intelligence tracks frontier AI labs and key people, turns public
output into scored/cited signal, and delivers reports + alerts. Origin: BIT
Capital AI Engineer case study.

## Start Here

1. `docs/references/case-prompt.md` - external requirements.
2. `docs/STATUS.md` - conceptual handoff: what is proven, active, missing, and
   deliberately deferred.
3. Active `docs/projects/<project>/tasks.md` - execution state; use `$project`.
4. Relevant section of `docs/architecture/overview.md` - system map.
5. `PRODUCT.md` / `DESIGN.md` when changing product or UI behavior.

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
- The build log is historical submission evidence, not current state or a
  cold-start document. Default to no entry; the active tracker is the normal
  work record. Use `scripts/build-log.py add` only when a tracker milestone
  closes, a decision changes product or architecture direction, a completed
  external run records material spend, or a learning changes future operating
  policy. Batch related work into one entry; routine UI polish, refactors,
  tests, reviews, and agent turns are not separate entries. When uncertain, do
  not log. Use bounded `recent` or `search` only when history is relevant;
  `scripts/check-fast.sh` validates and renders the reviewer artifact.
- Route every LLM call through the shared LiteLLM endpoint with stable
  `metadata.tags` for app, pipeline, job, scope, prompt, and run. Capture the
  proxy-reported response cost as the operational source of truth. Use a dated
  local price snapshot only when a pre-run estimate or zero-cost proxy fallback
  is actually needed.
- For bulk LLM jobs with a repeated 1,024+ token prefix, put stable content
  first, use stable sharded `prompt_cache_key` values, and verify cache reads
  from `cached_tokens`; do not assume an eligible prompt is getting cache hits.
- Model routing is accuracy-first: use the evaluated Luna defaults and reasoning
  efforts in `docs/references/model-routing.md`, and obtain GPT-5.6 Azure cache
  kwargs from `fli.llm_responses` rather than adding provider fields per caller.
- Update `docs/architecture/overview.md` when pipeline, schema, source classes,
  or module boundaries change.
- Update `docs/STATUS.md` only when the conceptual system status, active
  critical path, or planned/proven boundary changes; do not turn it into a
  second progress log.
- Run `scripts/check-fast.sh` before handoff, or record why validation was
  skipped in the active tracker.

## UI Preview & Visual Checks

- An always-on local server serves the built SPA at `http://127.0.0.1:8797`
  (launchd `com.dobby.frontier-lab-intelligence`). Use it. Do **not** spin up a
  throwaway `vite preview` / dev server on another port for screenshots.
- To see UI changes: `npm --prefix frontend run build` (writes into
  `src/fli/web/dist`, which the always-on server hosts), then reload
  `127.0.0.1:8797`.
- In Codex Desktop, prefer the in-app Browser for collaborative visual
  inspection when it is available. Use `$agent-browser` for repeatable or
  automation-heavy UI checks and as the fallback when the in-app Browser is
  unavailable.
  Put disposable captures in `tmp/`; presentation assets explicitly requested
  for reuse belong under `docs/references/`.
- **Desktop-first for now:** design and polish the desktop view; do not spend
  effort on mobile/responsive polish unless Adi asks. (Decision 2026-07-09.)

## Skill Routing

- AGENTS/docs/harness review: `$agent-native-repo-playbook`.
- Tracker planning, refresh, or closeout: `$project`.
- UI review or frontend polish: `$impeccable`.
