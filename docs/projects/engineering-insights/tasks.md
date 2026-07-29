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

## Open questions

1. **Store.** Copy the shape of `investment_agent_runs.py` or generalize it?
   Recommendation: a thin sibling store. The Engineering run has no memo
   calls and no two-stage trace, so generalizing now buys nothing and risks
   the published Investment cohort.
2. **How many decisions?** Ten is a guess. Write them first, then check how
   many of the 2026-07-21 Engineering-positive Developments hit at least one.
   From the routing reasons, expect roughly 3-5 of 10 to hit — high enough to
   demo, low enough to prove the filter works.
3. **Same page or its own?** The Insights page is already audience-parameterized
   (`?audience=ai_engineering`). Reuse it.

## Decisions

- 2026-07-29: Architecture spike only. No code until Adi approves the shape.
- 2026-07-29: Do not restore the deleted editorial generator or its schema.
  Start from the standing-decision unit instead.
- 2026-07-29: Standing decisions come from this repository's own architecture,
  cited to code and to `docs/STATUS.md`, explicitly not presented as BIT's.

## Next step

The tab is live at `/bit-lens/aion`. Once the seven surfaces read right, the
daily agent is small: one call returning a surface id and a sentence.

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
