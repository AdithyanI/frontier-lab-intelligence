# Scoring validation

Computed 20 July 2026 against the served read models and the frozen Digg
baseline. This records the quantitative checks behind the scoring-rigor claim
in the submission write-up. Method scripts are inline reproducible: every
number below comes from `/api/registry`, `/api/events`, `/api/insights`, and
`data/digg/rankings.csv` on the always-on service.

## 1. Contributor ranking against downstream editorial outcomes

The strongest check uses no external reference. If the network ranking
measures anything real, Events authored by higher-ranked people should more
often survive the full judging and editorial funnel. Across all 13 briefed
days (5 to 17 July 2026), bucketing judged Events by the author's rank
quartile:

| Author rank quartile | Judged Events | Kept Insights | Hit rate |
| --- | --- | --- | --- |
| Q1 (top 25%) | 288 | 34 | 11.8% |
| Q2 | 243 | 31 | 12.8% |
| Q3 | 155 | 11 | 7.1% |
| Q4 (bottom 25%) | 51 | 4 | 7.8% |

Top half 12.2% versus bottom half 7.3%, a 1.7x gradient. The editorial stages
never see the author's rank, so the gradient is not self-fulfilling at the
judging step. One caveat: attention selection includes author support, so
higher-ranked authors get more Events judged; the hit rate conditions on
being judged, which controls most of that.

## 2. Contributor ranking against an independent external baseline

The Registry network ranking (support within the trusted follow graph) was
compared with Digg's independent tech ranking frozen on 8 July 2026
(`data/digg/rankings.csv`, 1,000 accounts, SHA recorded in
`digg-ranking-baseline.md`).

- Shared accounts: 872 of our 2,561 ranked X handles.
- Spearman rank correlation on shared accounts: **0.877**.
- Top-50 overlap: 33/50. Top-100 overlap: **72/100**. Top-250 overlap: 193/250.
- The highest-ranked accounts unique to our ranking are official lab and
  product channels (`openaidevs`, `claudeai`, `geminiapp`, `googleresearch`,
  and similar). Digg ranks people only, so these disagreements are coverage
  decisions, not errors.

Reading: two rankings built from disjoint signals (our cohort-internal follow
support versus Digg's follower-gravity method) agree strongly on who matters,
and disagree where our Registry deliberately includes organizational channels.
Per `digg-ranking-baseline.md` this comparison is diagnostic, not ground
truth, and the trusted ranking was not tuned toward it.

## 3. Attention score versus editorial outcomes

The attention score (attention-v1.1) has one consumer: it selects the top 100
Events per day for audience judging. The judges see packet content and
`feed_rank` position but never the score. Across all 13 briefed days
(5 to 17 July 2026), the primary Events behind the 138 kept Insights sit
within the judged 100 as follows:

- rank 1 to 25: 65 (47%)
- rank 26 to 50: 40 (29%)
- rank 51 to 75: 11 (8%)
- rank 76 to 100: 22 (16%)

Reading: kept Insights concentrate toward the top of the attention ordering
(76% in the top 50), but 24% come from the lower half of the judged window,
so the audience judges are not simply reproducing the attention order.

## Honest limits

- The top-100 gate makes "all kept Insights come from the top 100" true by
  construction. The unmeasured quantity is recall lost below the gate. A
  bounded probe exists but has not been run: route ranks 101 to 200 for one
  day with the same prompts and count how many would have been judged
  relevant.
- The Digg comparison validates the contributor ranking, not the daily
  attention ordering or the editorial judgments.
- Editorial quality is validated separately: verbatim citation checking
  against frozen artifact text (hallucination control), forced per-Event
  dispositions with written reasons, and the human batch audit in
  `daily-intelligence-batch-audit-2026-07-05-17.md`.
