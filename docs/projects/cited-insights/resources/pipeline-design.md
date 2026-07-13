# Cited-Insights Pipeline — Design & Execution Plan

Status: approved by Adi 2026-07-13 (session decision). This document is the
implementation brief for the `cited-insights` project. Read
[`../tasks.md`](../tasks.md) for milestones/tracking; this file is the *how*.

---

## 1. What we are building, in one paragraph

A daily pipeline that takes the top ~20 attention-ranked Feed envelopes,
runs a cheap LLM **triage** (keep/drop + reason),
**fetches the linked primary artifacts** (papers, repos, blog posts) into an
artifact store keyed by canonical URL, then runs a strong LLM **extraction**
that turns envelope + artifact text into 3–5 structured, cited,
persona-framed insights per day — surfaced on a new Insights page and
rendered as one daily briefing artifact. Validated against the existing
human audit labels.

Everything upstream (Registry, evidence store, envelopes, attention-v1.1)
is DONE and frozen. Do not modify it. This project only *reads* from it.

## 2. Why this order (strategic context)

- Rubric weights: signal-vs-noise 20% + scoring validation 20% + delivery
  15% + extraction 10% ≈ the heavy half is still unbuilt. UI is 5% and
  already strong. See `docs/references/case-prompt.md`.
- The single evaluation question from the case sheet: *"did this surface
  something we'd genuinely want to know, and did it keep the noise out?"*
- Decision filter for any scope question: **does it make the 3–5 final
  insights better or more credible?** If no → out (recorded in tasks.md
  Non-Goals: no RSS/GitHub ingestion, no bio-diff departure detector, no
  ranking retuning, no mobile).
- Narrow end-to-end proof beats breadth: one day working fully, then more
  days.

## 3. Existing assets the engineer must know

| Asset | Where | Notes |
| --- | --- | --- |
| Raw X evidence (immutable) | `data/raw/x/x-content.db` (`x_post`, `post_bundle`, `raw_request/response`) | 63,736 posts. `raw_json` per post. **Never mutate.** |
| Resolved URLs already in raw JSON | `x_post.raw_json` → `entities.urls[] {url (t.co), expanded_url}` | 95% of posts containing t.co links carry expanded_url (21,316/22,342 checked). No new X API calls needed. Note: `extendedEntities.media[].expanded_url` is media self-links — ignore; author-bio urls — ignore. |
| Derived envelope runs | `data/derived/` (content-addressed run dirs) | Exact-structural envelopes + attention features. |
| Feed API | `src/fli/web/feed.py`, `GET /api/events?date=…&sort=attention` | `attention-v1.1`: 100×(0.55 network + 0.25 originator + 0.20 engagement), each a within-day percentile. Envelope sort key = `peak_attention_score`. |
| Eval seed (ground truth) | `docs/projects/archive/signal-intelligence-pipeline/resources/top-20-attention-audit-2026-07-11.md` | Human labels on the 2026-07-11 top-20: 12 worth-attention / 8 noise, **5 strong extraction candidates with post IDs**. This is the acceptance oracle for M1. |
| Gap analysis | `.../resources/submission-gap-audit-2026-07-13.md` | Rubric map; why insights/delivery are the critical path. |
| LLM plumbing | existing Registry pipeline code under `src/fli/` | LiteLLM endpoint, structured outputs, usage/cost capture, prompt cache, resumability — reuse, don't rebuild. |
| Web UI | `frontend/` (React SPA, builds into `src/fli/web/dist`) | Always-on server at `http://127.0.0.1:8797` (launchd). Backend .py changes need `launchctl kickstart -k gui/$(id -u)/com.dobby.frontier-lab-intelligence`. |
| Repo gate | `scripts/check-fast.sh` | Must pass before every handoff. |

## 4. Pipeline design (five stages, one daily run)

```
(1) top-20 envelopes ──▶ (2) LLM triage ──▶ (3) artifact fetch ──▶ (4) LLM extraction ──▶ (5) surface + briefing
     exists                cheap model         HTTP + readability      strong model            UI + renderer
```

### Stage 1 — Candidate selection (exists)
Top ~20 envelopes by `peak_attention_score` for the target day, from the
existing derived run / Feed API. Start day: **2026-07-11** (audited).
Second day: 2026-07-09 or 07-10 (unaudited — good blind test).

### Stage 2 — Triage gate (implemented; `gpt-5.4-mini`)
Purpose: control *what we even extract*; produce auditable signal-vs-noise
reasons (rubric gold).

Input per envelope: root post plus every related non-retweet post with exact
relationship/authorship markers, embedded expanded URLs, provider-supplied
article/card titles and previews. Exact retweet copies are omitted entirely.
Ranking, Registry standing, follower count, amplifier identity, and
public engagement are intentionally absent: attention chose the candidate;
triage judges substance from the evidence itself.

Output (structured, one record per envelope):
```
envelope-triage-output-v2 {
  decision: keep | drop,
  reason: string               # one concise evidence-based sentence
}
```
Rules:
- Banter/memes/engagement-bait → drop, with the reason recorded. (Known
  case: Sam Altman banter ranked #1–2 on 07-11 — triage is where that gets
  caught, per the attention-v1.1 decision to NOT fix it in ranking weights.)
- A thin day may keep <20; never pad.
- A noisy root may contain a useful child; each supplied post is inspected,
  but the model routes the complete envelope rather than selecting evidence
  IDs.
- Provider article/card metadata indicates that an artifact is inspectable;
  it is not article extraction or verification.
- Versioned 1,024+ token instructions form the stable cacheable prefix;
  envelope evidence is the variable suffix. Cache reads, tags, response ID,
  exact input, usage, errors, and proxy cost live in the resumable local run
  database. OpenAI-side storage is disabled (`store=False`).
- No web tool and no routine second-model reviewer. The bounded calibration
  reached zero false drops; see
  [`triage-spike-2026-07-13.md`](triage-spike-2026-07-13.md).

### Stage 3 — Artifact resolution + fetch (new; no LLM)
For each kept envelope's embedded URLs and provider artifacts, inspect the
complete frozen envelope context:
1. Resolve: take `expanded_url` from raw JSON (already there); follow HTTP
   redirects max 3 hops for residual shorteners (goo.gle etc.).
2. Canonicalize: lowercase host, strip tracking params (`utm_*`, `ref`,
   `s`, `t`), strip fragments, arXiv: normalize `/abs/` vs `/pdf/` to
   `/abs/`, strip version suffix into its own field.
3. Fetch: HTTP GET, 15s timeout, one retry; HTML → clean text
   (readability-style extraction); PDFs: extract text (arXiv abstracts can
   come from the abs page HTML — cheaper than PDF parsing); GitHub: fetch
   the repo README via raw.githubusercontent (no API token needed).
4. Store:
```
artifact-v1 {
  canonical_url (PK), kind: paper | code | blog | news | video | other,
  title, site, fetched_at, http_status,
  text: string (clean, capped ~50k chars), text_sha256,
  fetch_error: string | null
}
post_artifact { post_id, canonical_url, envelope_id, run_id }   # many-to-many
```
Design intent (defend in write-up): canonical URL is the identity so that
(a) multiple insiders linking the same paper **merge** — convergence
signal; (b) future RSS/GitHub/arXiv pollers write rows into the *same*
table (`source` column can be added then) — this is the dashed-boxes
upgrade path on the Architecture page. X stays the only *discovery*
channel for the submission; artifacts are the multi-source *substance*.
- Fetch failures are recorded, never fatal: extraction falls back to
  tweet-only with lower confidence.
- Respect robots/timeouts; no auth-walled scraping. Paywalled/gated →
  `fetch_error`, cite the URL anyway.

### Stage 4 — Insight extraction (new; strong model)
Input per kept envelope: everything triage saw + fetched artifact texts.

Output:
```
insight-v1 {
  insight_id, run_id, day,
  claim: string                  # one falsifiable sentence, past tense
  why_it_matters: string         # ≤2 sentences
  event_type: departure | release | capability | technique | open-model
              | funding | other  # maps to case-sheet examples
  implication_investment: string # implication + possible public-equity
                                 # landing spot; ALWAYS flagged hypothesis
  implication_engineering: string# adopt / investigate / ignore + why
  citations: [
    { type: artifact, canonical_url, quote: string },   # supporting span
    { type: envelope, envelope_id, post_ids: [...] }    # who noticed
  ],
  confidence: high | medium | low,
  novelty_note: string | null    # "widely reported" vs "first signal"
}
```
Hard rules (hallucination control — evaluated deliverable):
- Every claim must carry ≥1 citation with a supporting quote that appears
  verbatim (modulo whitespace) in the artifact text or post text —
  **verified programmatically post-hoc**, failures drop the insight.
- No artifact fetched → claim may only restate what the posts themselves
  say, confidence ≤ medium.
- One envelope may yield 0 insights (substance gate) — record why.
- Per-day cap: rank kept insights, surface top 3–5, store the rest.

Prompting notes: stable prefix first (schema + rules + few-shot), envelope
last; `prompt_cache_key` sharded per day; verify `cached_tokens` on bulk
runs. Both stages: LiteLLM with `metadata.tags` (app=fli,
pipeline=insights, job=triage|extract, scope=day, prompt=vN, run=run_id);
capture proxy-reported cost per call — tokenomics is a required
deliverable.

### Stage 5 — Surface + briefing (new)
- **Insights page** (new tab, becomes the app's lead surface): per-day list
  of 3–5 insights; each shows claim, why-it-matters, both persona
  implications, event-type, confidence, and citations that click through
  to (a) the Feed envelope (existing deep-link) and (b) the artifact URL.
  Show dropped-by-triage count with reasons behind a disclosure ("what we
  filtered out and why" — signal-vs-noise evidence, great for the demo).
- **Daily briefing**: one CLI command renders a day's insights into a
  clean HTML document (print-CSS → PDF via browser print is acceptable;
  PDF lib only if cheap). Two persona framings = two sections from the
  same records, not two documents.
- Storage: insights + triage + artifacts live in the derived run world
  (rebuildable), never in raw.

## 5. Evaluation plan (rubric: scoring validation 20%)

1. **M1 oracle test:** run the pipeline on 2026-07-11. The 5 strong audit
   candidates must yield insights (or each miss explained and fixed).
   The 8 noise labels must be dropped by triage (target ≥6/8; misses
   analyzed).
2. **Citation validity (automated):** % of citations whose quote is found
   verbatim in the cited text; report the number; failures auto-dropped.
3. **Blind pass (human, ~30 min of Adi's time):** second day's insights +
   triage verdicts shuffled; Adi labels worth-knowing yes/no without
   seeing pipeline scores. Report agreement. No recall claims — precision
   and citation validity only; say so.
4. **Cost:** per-day $ for triage + extraction, from proxy telemetry, in
   the write-up.

## 6. Milestones (from tasks.md, with timeboxes)

| Milestone | Target | Definition of done |
| --- | --- | --- |
| M1 extraction pipeline | Mon–Tue 07-14/15 | Stages 2–4 run on 2026-07-11; oracle test passes; cost telemetry captured |
| M2 insights surface | Wed 07-16 | Insights tab live, citations click through; browser-checked |
| M3 briefing artifact | Thu 07-17 | CLI renders daily briefing; **pipeline expansion freezes here** |
| M4 eval + write-up | Fri–Sat 07-18/19 | Blind pass recorded; write-up draft (architecture, prompts+rationale, eval, tokenomics, limitations) |
| M5 submission prep | Sun 07-20 | Package vs case-prompt checklist; **submission only with Adi's explicit approval** |

Recommended first task (half a day, before any framework code): manually
pull the 5 strong candidates' envelopes + links, fetch their artifacts by
hand, and hand-write the 5 insight-v1 records they *should* produce. That
gives the few-shot examples, the schema sanity check, and the oracle — all
from real data. Data first, then code.

## 7. Honest limitations (state, don't hide — for the write-up)

- 7-day window vs the sheet's ~3-month suggestion: scoped-well-beats-broad
  is their own stated preference; pipeline is date-parameterized, window
  is a collection-cost decision, not an architecture limit.
- X-only discovery: things nobody posts/amplifies on X are invisible;
  fixed by the planned artifact-store pollers (RSS/GitHub/arXiv) — same
  table, new writers.
- Attention is candidate generation, not truth; substance judgment lives
  in triage/extraction (this project), validated by the blind pass.
- `implication_investment` is an LLM hypothesis, never investment advice —
  flagged as such in the UI and briefing.
- Competitive-map / trend synthesis across weeks: manual for the final
  report's 3–5 insights; automated synthesis is a stated next step.

## 8. Hard constraints for the implementing engineer

- Read `AGENTS.md` first; it routes everything.
- Raw stores are immutable; new tables live in the derived/run world.
- All LLM calls through the shared LiteLLM endpoint with the tag scheme
  above; cost is telemetry, never a quality gate (no Adi-set cap active).
- `scripts/check-fast.sh` green before every handoff; append to
  `docs/references/build-log.jsonl` (schema: title/intent/action/evidence/
  impact_next/tools_spend) after meaningful chunks.
- Update `docs/architecture/overview.md` + the Architecture page's dashed
  "cited insights" boxes when the pipeline lands.
- No external sends (email/Slack/publishing) without Adi's explicit
  current-session approval; alert delivery = local inspectable outbox only.
- Desktop-first UI; match existing design system (`frontend/src/app.css`,
  EntityCard patterns); scratch in `tmp/`.
