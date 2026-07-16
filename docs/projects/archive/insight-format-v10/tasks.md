# Insight Format v10

## Goal

Ship the reviewed Insight format upgrade in one version bump and one full
regeneration: Investment v9→v10, AI Engineering v6→v7, schema
`audience-insight-output-v3`→`v4`. Field renames (`implication`→
`why_it_matters`; `next_step`→`watchpoint` for Investment / `experiment` for
Engineering), a temporal standard backed by `posted:` dates in the evidence
packet, named public-company mapping for Investment, and shorter
trigger-shaped action fields.

## Why / Impact

Review on 2026-07-16 found four gaps between the v9/v6 output and the case
prompt: no tickers/public companies despite the rubric asking for them;
"why kept" gate-justification leaking into reader prose; laundry-list next
steps nobody can act on; and a stale-source failure (2022 ChatGPT launch
surfaced as current news on 2026-07-15 r44) because only 9/173 packets carry
any date. All four are fixed by the two new prompts plus dates in the packet.

## Decisions

- 2026-07-16: Keep the action field (it is the rubric's "what to do" and the
  third suppression gate) but rename and shrink it: Investment `watchpoint`
  = one "If ⟨observable⟩ → revisit ⟨assumption⟩" sentence, max two
  observables; Engineering `experiment` = workload + baseline + metric +
  fail condition, max two sentences.
- 2026-07-16: No web search in the insight editor. The closed-world frozen
  packet is the hallucination-control and replayability story. Optional
  later: a separate human-reviewed enrichment pass over the final 3–5 only.
- 2026-07-16: Investment may name publicly traded companies from
  well-established general knowledge, labeled as analyst mapping; sector
  fallback when unsure; never guess listings or ownership.
- 2026-07-16: Stale sources are suppressed ("resurfaced historical content",
  naming the source date) unless the packet shows a new dated development
  about the old material.
- 2026-07-16: Do not change `audience_routing.render_input` default output —
  the frozen v9 routing store hashes must stay valid. Dates enter only the
  insight-specific render via an opt-in flag.

## Current Batch

Complete. Full v10/v7 regeneration covers every routed-positive audience from
the current July 5–15 top-100 routing cohort; both reader views, temporal
handling, action quality, cache invalidation, and the full fast check are
verified. Resume downstream work at cross-Event consolidation and final 3–5
submission selection, not in this per-Event generation contract.

## Tasks

Prompts (done):

- [x] `src/fli/prompts/investment_insight_v10.txt` written.
- [x] `src/fli/prompts/ai_engineering_insight_v7.txt` written.

Code — `src/fli/insight_generation.py`:

- [x] Bump `SCHEMA_VERSION` to `audience-insight-output-v4`.
- [x] Rename output fields: `_OUTPUT_FIELDS`, `OUTPUT_FORMAT` (name
      `audience_insight_v4`; properties `why_it_matters`, plus ONE
      audience-specific action field — see note below), `InsightResult`,
      `PublishedInsight`, `validate_output`, `publish`.
- [x] Note: the action field differs per audience (`watchpoint` vs
      `experiment`). Either make `OUTPUT_FORMAT` a per-audience dict keyed
      like `PROMPT_CONTRACTS`, or keep one schema with both fields where
      exactly one must be non-null. Per-audience schemas are cleaner and
      match the per-audience prompt contract; `insight_runs._request_contract`
      compares `request["text"]["format"]`, so it must look up the
      audience's schema, not one global constant.
- [x] Update `PROMPT_CONTRACTS`: versions `investment-insight-v10` /
      `ai-engineering-insight-v7`, new paths, cache keys
      `fli:insights:investment:v10` / `fli:insights:ai-engineering:v7`.
- [x] `render_input`: emit `evaluation_day:` header and per-post `posted:`
      dates. Add an opt-in `include_dates=True` path (flag on
      `audience_routing._render_full_input`/`render_input`, default False)
      so routing render output is unchanged.

Code — packet dates:

- [x] Add optional `posted: str | None = None` to
      `audience_routing.EvidenceSource`. Exclude it from `evidence_sha256`
      payload so frozen routing hashes stay stable.
- [x] In the insight CLI candidate build (where routing `packet_json` is
      loaded), enrich root and continuation sources with post dates from the
      events/feed store by `source_id` before rendering. Missing date = omit
      the `posted:` line (prompt handles that case).

Code — `src/fli/insight_runs.py`:

- [x] Rename `implication`/`next_step` columns in `SCHEMA`, INSERT/UPDATE
      statements, and `run_payload` to `why_it_matters`/`action`
      (or per-audience name stored in one `action` column — simplest:
      one `why_it_matters` column + one `action` column, since audience is
      already a key).
- [x] Old `insights.db` rows are all invalidated by the version bump and the
      old columns will not match: move
      `data/derived/insights/insights.db` aside (e.g. `insights-v9-v6.db`,
      keep as historical audit evidence) and let the new schema create
      fresh. No dual-read, no migration.

Code — API/UI:

- [x] `src/fli/web/insights.py` `_item_payload`: emit `why_it_matters` and
      `watchpoint`/`experiment` (or a generic `action` + `action_label`);
      `decision_reason` for kept items now reads `why_it_matters`.
- [x] `frontend/src/api.ts` types + `frontend/src/pages/Insights.tsx`
      labels: "Why it matters", "Watchpoint" (investment), "Experiment"
      (engineering). Then `npm --prefix frontend run build`.

Validation:

- [x] Update/extend existing insight tests for new field names and
      per-audience schema; `scripts/check-fast.sh`.
- [x] One-envelope dry run per audience (`fli insights` freeze + inspect
      request JSON: dates present, prompt v10/v7, cache key new) BEFORE any
      model call.
- [x] Verify the 2026-07-15 r44 ChatGPT envelope now renders with its 2022
      `posted:` date in the frozen request.

Run (Adi approved 2026-07-16):

- [x] Regenerate all routed-positive envelopes under v10/v7.
- [x] Spot-audit: stale-source suppression fired on r44; tickers named where
      defensible; watchpoints/experiments are short; no gate-talk in
      `why_it_matters`.

## Progress Log

- 2026-07-16: Implemented the v4 per-audience output contract, temporal
  packet enrichment, v10/v7 prompts, fresh SQLite store, API projection, and
  flat four-part reader UI. The prior 173-decision store remains preserved as
  `data/derived/insights/insights-v9-v6.db`; no compatibility read was added.
- 2026-07-16: Targeted Insight tests pass (22 tests). Frozen-request proof
  shows `evaluation_day: 2026-07-15` and `posted: 2022-11-30` for the stale
  ChatGPT candidate, while the current Sutton candidate shows both dates as
  2026-07-13. Three canaries correctly suppressed the stale item and produced
  bounded Engineering and Investment outputs; the second Investment call
  reported 2,304 cached input tokens.
- 2026-07-16: Refreshed all eleven current top-100 audience-routing days
  before Insight generation: 1,100/1,100 complete, zero failures, 967
  cache-hit requests, 1,732,864 cached tokens, and $5.372287 proxy-reported
  cost.
- 2026-07-16: Completed 947/947 unique Event/audience decisions: 404
  surfaced and 543 suppressed, with 847 cache-hit requests, 1,755,904 cached
  tokens, and $15.512238 proxy-reported cost. Five transient timeouts were
  resumed without repeating the other 942 calls. All 189 surfaced Investment
  actions follow trigger→assumption form; no surfaced rationale contains
  editorial gate-talk; the stale ChatGPT candidate is suppressed with its
  2022 source date. Live verification covered both reader views and exposed a
  stale in-process routing-source cache after database replacement; the cache
  now keys on main/WAL version tokens and has a regression test.
- 2026-07-16: `scripts/check-fast.sh` passes: 354 backend tests, 43 frontend
  tests, frontend lint (four pre-existing Fast Refresh warnings), and the
  production build.

## Done When

- New store contains complete v10/v7 decisions for all eleven days; UI shows
  the four-part reader format; the stale ChatGPT item is suppressed with a
  dated reason; at least a handful of investment insights name real public
  companies; `scripts/check-fast.sh` passes; STATUS.md Insight rows updated.
