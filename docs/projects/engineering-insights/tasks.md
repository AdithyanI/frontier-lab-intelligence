# Engineering insights

Status: architecture spike — no implementation
Owner: Adi
Started: 2026-07-29

This project is independent of `docs/projects/bet-linked-insights/`. That
tracker owns the Investment path. Do not edit it from here.

## Goal

Give the AI Engineering audience the same shape the Investment audience just
got: today's Development is matched against something **pre-registered**, so
the agent's only job is to say which one it hit and whether it is actionable
yet.

## Where AI Engineering actually stands today

Verified, not assumed:

- Routing works. `audience-routing-v15` runs both audiences independently.
  On 2026-07-20: 49 Engineering-positive of 93 complete. On 2026-07-21 the
  Engineering reasons are specific and usable (agent sandbox escape, Poolside
  weights + evals, Gemini 3.6 Flash token claims, Cognition split execution).
- Everything after routing is gone. `/api/insights` returns an explicit
  unavailable payload for `ai_engineering` (`src/fli/web/app.py:638`). The old
  editorial generator was deleted; its context survives only as history at
  `docs/references/archive/ai-engineering-editorial-context.md`.
- So the input is proven and the last mile is empty. That is the cheapest
  possible starting position.

## The trap to avoid

The deleted editorial system asked the model for `interpretation`, `next_step`,
`decision_rule` and answers to seven reader questions. Every field was
generated prose, so every field could be wrong, and none could be checked.
That is the same failure the Investment side just spent a day undoing
(`horizon`, `mixed`, `bet_status` all collapsed to one value).

Rule for this project: **the model gets one judgment and one sentence.
Everything else is a lookup.**

## The architecture

BIT Lens holds client context. Investment side: 37 companies, each with
standing bets. Engineering side: the **assumed Aion stack** — seven surfaces
of the research platform BIT's AI team operates, inferred from its public AI
Engineer and Data Platform roles.

```text
DATA   Data platform     RETR  Retrieval      EXTR  Extraction
AGENT  Agents            MODEL Models and cost
EVAL   Evaluation        OPS   Operations
```

One line each. It is a list of buckets, not a specification, and its only job
is to give a daily Insight one thing to point at.

Honesty constraint: inferred from public material, never presented as
knowledge of BIT's private architecture.

### What the daily agent returns

```text
surface_id · useful (bool) · why (one sentence)
```

The Insight links to `/bit-lens/aion?surface=RETR`, which highlights that row —
the same deep-link contract the Investment side uses for `?company=X&bet=X-B1`.

Suppressed when it lands nowhere. No generated enums, no invented experiment,
no prose framework: that is what killed the deleted editorial generator and
three Investment fields.

## Why this is cheaper than the Investment path

- Ten decisions fit in one prompt. No memo-retrieval tool loop, no second
  turn, no `MAX_UNIQUE_MEMOS`. Single call per Development.
- Routing packets average 5,053 input tokens. Expect roughly 8k in / 1k out
  per Development, so under $1 for a ten-item day against $3.16 for
  Investment.
- No 176-row ledger. Ten decisions, written once, reviewed by hand.

## Scope

In scope: the standing-decision set, the output contract, the two-state gate,
one prompt, one thin run store, reuse of the existing Insights page.

Out of scope: a new UI page, a new database engine, PDF and Slack delivery
(add only if the day allows), regenerating anything on the Investment side,
restoring any deleted editorial code.

## Resolved questions

1. **Store.** Answered: a thin sibling store. `engineering_agent_runs.py`
   mirrors the Investment run/publication contract without memo calls or a
   two-stage trace, so the published Investment cohort was never at risk.
2. **How many land?** Answered on real data: 4 of 10 on 2026-07-21, with 6
   surface landings. The estimate was 3-5. High enough to demo, low enough to
   prove the filter works.
3. **Same page or its own?** Answered: reuse. `/insights?audience=ai_engineering`
   dispatches on `content_kind`.

## Open questions

1. **Sol/high versus Luna.** Untested. The Investment boundary uses Sol/xhigh;
   Engineering uses Sol/high on the argument that it is taste plus one sentence
   of technical writing, not retrieval or a multi-hop causal chain. Running the
   same day on Luna/medium would settle it for about $0.10.
2. **One day only.** 2026-07-21 is the only cohort. The surface distribution
   (OPS, MODEL, AGENT used; DATA, RETR, EXTR, EVAL unused) is a one-day sample
   and may simply reflect what frontier labs published that day.
3. **Suppression calibration.** 6 of 10 suppressed. Every suppression reads
   correct on inspection, but nobody has checked the inverse: whether anything
   suppressed should have surfaced.

## Decisions

- 2026-07-29: Architecture spike only. No code until Adi approves the shape.
- 2026-07-29: Do not restore the deleted editorial generator or its schema.
  Start from the standing-decision unit instead.
- 2026-07-29: Standing decisions come from this repository's own architecture,
  cited to code and to `docs/STATUS.md`, explicitly not presented as BIT's.

## Next step

The path is live end to end. The remaining work is calibration, not
construction: run a second day, and run one day on Luna to test the model
choice.

## Progress log

- 2026-07-29: [IN-PROGRESS] Architecture spike. Verified Engineering state
  against `routing.db` for 2026-07-20 and 2026-07-21 and the unavailable
  payload in `src/fli/web/app.py`.
- 2026-07-29: [DISCARDED] First attempt catalogued *this repository's* own
  architecture choices as "Build decisions". Wrong subject — BIT Lens holds
  client context, so the Engineering side must describe BIT's system, not ours
  — and far too much structure. Deleted.
- 2026-07-29: [DONE] BIT Lens `Aion stack` tab: seven surfaces, one line each,
  with `?surface=ID` deep-link highlighting so an Insight can point at one.
  `aionStack.ts`, `AionStackPage.tsx`, tab and route wiring, `bit-lens.css`.
  Build clean; BIT Lens routes 200. No backend, no agent, no change to the
  Investment path.
- 2026-07-29: [DONE] Backend spine and full wiring, built independently of the
  in-flight Investment work.
  - `docs/references/aion-surfaces.json` is the canonical surface map, read by
    the Python prompt builder and the store. It carries the public sources it
    was inferred from and an explicit boundary line stating it is not knowledge
    of BIT's private architecture.
  - `prompts/engineering_surface_analysis.txt`: long stable context (who BIT
    is, what Aion is, who the reader is, the seven surfaces, where evidence
    comes from, what to surface, what to suppress, transfer discipline), tiny
    output. Direct instructions and delimiters, zero-shot, no chain-of-thought
    scaffolding, per OpenAI reasoning-model guidance.
  - `engineering_agent.py`: one Responses call, no tool loop. Rejects any
    `surface_id` outside the map, more than two landings, a repeated surface, a
    surfaced result with no landing, and a suppression with no reason.
  - `engineering_agent_runs.py`: sibling store, atomic day publication, read
    projection that resolves `surface_name` from the map so the model never
    restates it.
  - `cli.py`: `run-engineering-agent`, `import-engineering-trace`,
    `engineering-summary`, `aion-surfaces`; `contract` now reports both
    boundaries.
  - `app.py`: `/api/insights` and `/api/insights/dates` dispatch on audience.
    PDF and delivery stay Investment-only and say so.
  - `EngineeringAgentInsight.tsx` (new file, to stay clear of the other
    agent's `InsightsPage.tsx` edits) plus three surgical edits to
    `InsightsPage.tsx`, the union type in `shared/api/insights.ts`, and a
    scoped `.engineering-agent-*` block in `insights.css`.
- 2026-07-29: [MEASURED] 2026-07-21 top ten. 4 surfaced, 6 suppressed, 6
  landings, 0 failures, $0.531415 — about a sixth of the Investment cohort's
  $2.78. The field does not collapse, which is the failure this project was
  designed to avoid. The strongest evidence is ranks 3 and 14: both are Gemini
  3.6 Flash, the documented release surfaced on MODEL and AGENT, and the bare
  announcement was suppressed for carrying no measured price-performance data.
  Same subject, opposite decisions, both correct.
- 2026-07-29: [FIXED] The first cohort lost 3 of 10 runs to a 22-word headline
  cap invented without measurement. The rejected headlines were 23 words and
  good. A technical headline naming a lab, a model, and a measured change needs
  more words than an investment one. The prompt now states a 28-word budget and
  the validator rejects at 30. This is the same mistake as the collapsed
  enums — a number chosen before looking at the data.
- 2026-07-29: [MEASURED] Cross-run prompt caching does not happen at this
  endpoint. Engineering reports 0 cached tokens, but so does turn 1 of every
  Investment run; Investment's 28% is entirely within-run reuse via
  `previous_response_id`. A single-turn design therefore cannot cache here, and
  0% is expected rather than a defect. The serial warm-up call was kept for
  fail-fast, not for cache.
