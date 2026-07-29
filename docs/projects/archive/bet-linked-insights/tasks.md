# Bet-linked Insights

Status: complete
Owner: Adi
Started: 2026-07-29

## Goal

Make every daily Investment connection resolve to a pre-registered company bet
whose direction was fixed before the news. The daily agent should decide only
whether the Development reaches that bet and whether its explicit threshold is
already met.

## Done When

- [x] All 176 standing bets have a reproducible binary direction.
- [x] The memo corpus uses `upside | downside`; `mixed` is invalid.
- [x] The memo vocabulary is `threshold`, not `material_when`.
- [x] Agent output carries `bet_id + threshold_met` and never generates
  direction.
- [x] Validation rejects a bet that does not belong to the cited company.
- [x] Insight and BIT Lens readers resolve direction from the same memo.
- [x] Insight rows deep-link to the exact open bet.
- [x] Python, frontend, lint, typecheck, and production build pass.
- [x] A complete July 21 Sol/xhigh cohort is published on v14.
- [x] The live reader and one expanded result are visually audited.
- [x] Durable architecture, status, and refresh docs describe v14.

## Final Contract

### Company memo

```text
COMPANY
  ticker · name · summary · summary_sources · source_ledger · researched_at

BET
  id
  direction: upside | downside
  if
  exposure
  then
  threshold
  watch[]
  sources[]
```

Direction answers one fixed question: **if the bet occurs, does the named
company exposure get larger or smaller?** Execution risk does not change the
sign. A genuine second causal mechanism belongs in a separate bet.

### Daily agent result

```text
headline
what_changed
decision: surface | suppress
connections[]
  mechanism
  companies[]
    ticker
    bet_id
    threshold_met: boolean
    impact
no_match_reason
```

The daily result deliberately omits direction. The product looks it up by
`ticker + bet_id`, so the memo and Insight cannot disagree.

`threshold_met` is true only when the Development itself establishes the
memo's threshold now. A product launch, trial, anecdote, benchmark, or early
demand signal normally fires a bet without clearing its threshold.

## Architecture

The progressive-disclosure shape remains:

```text
stage 1  complete Development + compact cards for all 37 companies
         -> suppress, or request zero to eight complete memos

stage 2  requested memos are returned together
         -> validate causal connections against the full memo
         -> surface only retained ticker + bet_id connections
```

One stable prompt prefix is warmed before the remaining daily candidates fan
out with bounded workers. Exact requests, responses, response IDs, memo calls,
usage, cost, and validation results remain in per-run traces.

## Reclassification

Input: `if + exposure + then + material_when`

Model route: shared LiteLLM, `gpt-5.6-sol`, `xhigh`

Prompt: `company-bet-direction-v2`

Before:

```text
upside 59 · mixed 88 · downside 29
```

After:

```text
upside 127 · downside 49 · mixed 0
```

Eleven bets required the model's ambiguity flag because they contain real
two-sided mechanisms. The chosen sign and rationale remain inspectable in
`docs/references/company-bet-directions.json`; the complete comparison is in
`resources/direction-reclassification.md`. Future restructuring can split
those bets without changing the daily Insight contract.

The reproducible path is:

```bash
.venv/bin/python scripts/classify-company-bet-directions.py
.venv/bin/python scripts/simplify-company-memos.py
```

The simplifier refuses a missing decision, a stale source hash, or a non-binary
direction. It emits `company-memos-v3` as the only runtime corpus.

## Decisions

- Delete `mixed`. It made a bet impossible to falsify and absorbed half the
  corpus.
- Keep direction on the memo, not in daily model output.
- Keep `threshold`. It turns "interesting news" into a checkable gate for
  analyst attention.
- Replace `bet_status` with one boolean. The prior enum returned `engaged` for
  all 21 observed connections and carried no discrimination.
- Do not treat `threshold_met=false` as rejection. It means early evidence,
  while true means the analyst should review the thesis now.
- Keep shared mechanism grouping. It explains how one Development reaches
  several companies without duplicating the causal path.
- Keep all application-owned evidence and memo URLs out of model output.
- Make a clean cutover. Old prompt versions remain historical rows but cannot
  satisfy or render a v14 publication.

## Files

- `scripts/classify-company-bet-directions.py`
- `scripts/simplify-company-memos.py`
- `docs/references/company-bet-directions.json`
- `docs/references/company-memos.json`
- `src/fli/insights/company_context.py`
- `src/fli/insights/investment_agent.py`
- `src/fli/insights/investment_agent_runs.py`
- `src/fli/insights/prompts/investment_company_analysis.txt`
- `frontend/src/features/bit-lens/CompanyUniversePage.tsx`
- `frontend/src/features/insights/InsightsPage.tsx`

## Proof

- Focused post-publication Insight tests: 33 passed.
- Frontend tests: 69 passed.
- `scripts/check-fast.sh`: 460 Python tests, 69 frontend tests, lint,
  TypeScript, and production build passed.
- Live memo boundary: 37 companies and zero mixed bets.
- July 21 v14 publication: 10 candidates, seven surfaced, three suppressed,
  21 retained bet references across 20 Development-company connections, and
  zero thresholds cleared.
- Sol/xhigh run telemetry: 446,739 input tokens, 158,255 cached input tokens,
  42,009 output tokens, 34,981 reasoning tokens, and $2.781818.
- Live browser proof: the Insights reader resolved direction from the memo,
  showed the exact threshold state, and opened, scrolled to, and focused
  `PANW-B1` in BIT Lens.
- One valid output connected Alphabet through two distinct mechanisms and bet
  IDs. Validation now permits that case while continuing to reject a duplicate
  `(ticker, bet_id)` pair.

## Handoff

The binary direction and threshold-gate migration is complete. Future
Investment work should keep this schema fixed while auditing marginal company
connections, duplicate Developments, and whether the threshold language itself
is calibrated appropriately. Do not reintroduce model-authored direction or a
multi-value engagement status.
