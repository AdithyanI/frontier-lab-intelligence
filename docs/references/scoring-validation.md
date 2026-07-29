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

## 3. Daily Event rank versus independent routing outcomes

Recomputed 26 July 2026 after the clean `daily-rank-v2` migration. The replay
covers all 17 saved days from 5 to 21 July: 19,657 Events and 1,700 top-100
positions. Current v9 routing provides 1,674 labels for those positions; 26
Events were omitted by the router's separate first-party freshness boundary.
The routing model sees the frozen semantic evidence, not the rank or rank-layer
values.

The primary rank layer—distinct trusted entities that quote or repost the
complete Event—shows a monotonic relationship with later independent routing:

| Trusted Event voters | Top-100 Events | Labeled Events | Routing-relevant | Hit rate |
| --- | ---: | ---: | ---: | ---: |
| 1 | 213 | 204 | 70 | 34.3% |
| 2 | 703 | 692 | 373 | 53.9% |
| 3–4 | 499 | 495 | 318 | 64.2% |
| 5+ | 285 | 283 | 204 | 72.1% |

There are no zero-vote Events in the selected top 100 on these days. The
gradient is useful evidence that independent convergence carries signal; it is
not a precision estimate for the full corpus because the labels exist only
inside the selected and freshness-eligible window.

For adjacent positions within the 17 daily top-100 lists, the first differing
layer was:

- trusted-voter count: 182 comparisons (10.7%);
- mean voter network position: 1,362 (80.1%);
- source-author network position: 22 (1.3%);
- maximum same-day one-post public interactions: 99 (5.8%);
- stable Event ID: 35 (2.1%).

This is behavior attribution, not a quality score. It makes the system's
trade-off explicit: convergence chooses broad bands; voter-network position
does most ordering within those bands; source authority and public response are
late tiebreaks. Network position is the six-decimal, tie-aware percentile of
entity-union support: entities with equal support receive equal position, and
raw support magnitude never enters the Event rank. The exact replay is
`fli daily-rank evaluate --json --no-input`.

### Historical submission baseline

Before the migration, `attention-v1.1` selected the submitted cohort with a
55/25/20 weighted percentile score. Across 13 briefed days, 76% of the 138
ultimately kept Insights originated in ranks 1–50 and 24% in ranks 51–100.
Those dated numbers explain the submitted proof set; they do not describe the
current production ranking.

## Honest limits

- The top-100 gate makes "all routed and authored Insights come from the top
  100" true by construction. The unmeasured quantity is recall lost below the gate. A
  bounded probe exists but has not been run: route ranks 101 to 200 for one
  day with the same prompts and count how many would have been judged
  relevant.
- The Digg comparison validates the contributor ranking, not the daily Event
  rank or the editorial judgments.
- The rank counts reactions from the Event's canonical UTC day. A post
  published late therefore gets less time to collect trusted reactions. A
  future version may wait for the same fixed period after every post before
  freezing the rank. A shorter wait favors faster briefs; a longer wait gives
  the network more time. This remains deferred until the effect is measured.
- Editorial quality is validated separately: verbatim citation checking
  against frozen artifact text (hallucination control), forced per-Event
  dispositions with written reasons, and the human batch audit in
  [`archive/daily-intelligence-batch-audit-2026-07-05-17.md`](archive/daily-intelligence-batch-audit-2026-07-05-17.md).
