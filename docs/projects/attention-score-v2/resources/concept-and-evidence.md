# Attention-v2 Concept and Evidence

Written 2026-07-16 from an independent review of the `attention-v1.1` daily
score (`src/fli/web/feed.py`, `SCORE_FORMULA`). All numbers below were measured
against live data on that date; re-verify against current stores before acting,
per the STATUS rule that checkpoint counts are not present-tense claims.

## Verdict in One Paragraph

The v1.1 design intent is correct: tracked Registry amplification deserves the
dominant weight, one flat vote per curated entity is the right anti-fame
policy, and quotes/reposts should stay merged until data shows a gap. The flaw
is the *encoding*, not the weights: converting a distribution that is ~74%
zeros into a daily percentile turns the 55% amplification weight into a
near-binary "zero vs. some" bonus and throws away the range where usefulness
actually keeps rising (2 → 40 votes). The fix is a fixed saturating curve for
amplification and an early-saturating floor for author support, with weights
roughly unchanged.

## Measured Evidence (2026-07-16, run `50ae3cec…`, July 5–13 window)

### 1. Sparsity and percentile cliffs (full candidate pool, `/api/feed`)

- 2026-07-08: pool 4,851; 26.4% amplified; 82% of amplified had exactly 1 vote.
- 2026-07-12: pool 2,517; 24.4% amplified; 90% of amplified had exactly 1 vote.
- Percentile mapping observed: 1 amplifier → 0.756; 2 → 0.951–0.975;
  3 → ~0.982; everything above 2 votes compressed into 0.98–1.0.
- Consequence: a 2-vote post and a 40-vote post receive nearly identical
  amplification contribution; almost all of the 55% weight is spent on
  0 vs. 1 vs. 2.
- Degenerate-day failure mode: on a day where every candidate has ≤1 vote, the
  `bisect_left` tie handling sends the whole component to ~0 for everyone and
  the ranking silently falls back to support + engagement.

### 2. Amplifier count is the only monotonic usefulness predictor

Join of the 900 completed v9 top-100 routing decisions
(`data/derived/audience-routing/audience-routing-v9-*top100*/routing.db`,
`ai_engineering_relevant OR investment_relevant`) to daily score components
(`/api/events` `daily_score_basis.score_components`):

| Distinct Registry amplifiers | Relevant share |
| --- | --- |
| 0–1 | 44% (162/366) |
| 2 | 58% (166/288) |
| 3–4 | 63% (92/145) |
| 5+ | 71% (72/101) |

(Pool-wide bucketing on the same join: 1 → 40.2%, 2 → 54.3%, 3–4 → 63.0%,
5+ → 75.4%.) Every additional distinct vote adds usefulness far beyond the
point where the percentile encoding stops rewarding it.

### 3. Support and engagement plateau almost immediately

Same 900-label join:

- Author network support: <50 → 37.8%; 50–199 → 56.5%; 200–599 → 54.9%;
  600+ → 55.4%. Flat above a low floor. Support is a "is this author inside
  the trusted graph at all" prior, not a graded quality signal.
- Public interactions: <100 → 36.6%; 100–1k → 55.3%; 1k–10k → 57.9%;
  10k+ → 54.3%. Flat above ~100 interactions.

### 4. Single-component ranking head-to-head (precision@20, 9 days)

Rank each day's labeled cohort by one signal alone and count useful items in
the top 20 (ties randomized):

| Ranking signal | Mean P@20 |
| --- | --- |
| Current blended v1.1 rank | 62.2% |
| Amplifier count alone | 61.7% |
| Cohort base rate (random) | 54.7% |
| Public engagement alone | 54.4% |
| Author support alone | 53.3% |

Within the top-100 cohort, amplification alone matches the full blend, and the
other two components rank no better than chance. Caveat: support and
engagement helped select the top-100 cohort in the first place, so they may
still add value as coarse pre-filters below the labeled cutoff; this is
untested (see evaluation plan).

### 5. Amplification and support are anti-correlated lane markers

Pool-wide Spearman correlation between amplifier count and author support is
≈ **−0.69** (−0.68 on 2026-07-12; engagement ~uncorrelated with both).
Mechanism: the pool has two lanes — firsthand Registry-authored posts have
high support and ~zero amps (self-amplification is excluded), while
network-discovered posts by outside authors have amps and lower support
(amped-author support median 53 vs. 172 for zero-amp authors; 460 of 614
amped items on 2026-07-12 were not observed directly). The two components
partly measure lane membership, not two independent quality dimensions. Any
write-up should state this plainly rather than describe three independent
signals. Whether the two lanes should be ranked separately at all is an open
design question deliberately left out of v2 scope.

## Design Answers (the questions v2 must not re-litigate without new data)

1. **Is 55% too much for amplification?** No. It is the only signal that works
   (evidence #2, #4). If anything the data supports more. Keep ≈55%.
2. **More weight to author support?** No. It is flat above a low floor
   (evidence #3) and raising it optimizes fame. Encode it as an
   early-saturating floor instead.
3. **Weight votes by amplifier prominence (support rank / PageRank)?** No —
   fame bias and double-counted prestige; a famous repost would outweigh many
   quiet experts. Two non-fame refinements are legitimate but calibration-
   gated: (a) hyperactivity damping — down-weight votes from entities that
   amplify very frequently (per-vote information content, not prestige);
   (b) affiliation diversity — votes from same-org colleagues are less
   independent. Neither ships without measurement.
4. **Quotes vs. reposts split?** Not yet. A critical quote from a curated
   expert is still attention evidence, and quotes carry commentary that feeds
   insights. Test first (cheap: relevance rate for quote-only vs. repost-only
   amplified items in the existing 900-label set); split only if a real gap
   appears. Keep the reaction type visible in the audit trail (already done).
5. **Percentile normalization?** Wrong for amplification (three-step cliff
   over a 74%-zero distribution; degenerate-day failure). Acceptable for
   log-engagement (near-continuous). Replacing it for amplification also makes
   scores comparable across days, which v1.1 explicitly disclaims.

## Proposed Formula (v2 candidate — starting point, not a frozen contract)

```
score = 100 × ( 0.55 · A + 0.20 · S + 0.25 · E )

A = min(1, log1p(distinct_active_registry_amplifiers) / log1p(16))
S = min(1, log1p(author_network_support) / log1p(150))
E = daily percentile of log1p(likes + replies + reposts + quotes)   # unchanged
```

Resulting amplification curve: 1 vote → 0.24, 2 → 0.39, 4 → 0.57, 8 → 0.78,
16+ → 1.0. Single-vote items (40% relevant — *below* the labeled base rate)
drop below the two-vote wall instead of landing near the top; resolution is
spread across 2–16 votes where usefulness keeps rising.

**Defensible from existing data:** the saturating-log shape for A, early
saturation for S, keeping one-flat-vote-per-entity, keeping quotes+reposts
merged pending the split test, keeping E as a percentile tie-breaker.

**Requires empirical calibration before shipping:** the cap anchor (16), the
support knee (150), the exact weight split (test 0.25→0.20 support shift
toward engagement vs. keeping 0.25/0.20 as in v1.1), hyperactivity damping,
affiliation diversity, any quote/repost split, and the lane-separation
question.

## Evaluation Plan (required before any production change)

1. **Offline replay on the 900 labels.** Rescore all nine days with v2;
   compare relevant@20/@50/@100 per day against v1.1 (baseline mean P@20 =
   62.2%). Report rank churn (Kendall-τ) and manually inspect the ~10 largest
   movers in each direction per day.
2. **Below-cutoff recall probe.** The existing labels cannot see what v1.1
   buries. Route a sample of ~100 envelopes from ranks 100–200 plus a sample
   of high-support zero-amplifier firsthand posts (at v9 unit cost this is
   well under $1). This tests the real risk: an unamplified post by a key
   researcher is mathematically capped (~45 points under v1.1) and can never
   beat any two-vote item.
3. **Blind human ordering audit.** Repeat the 2026-07-11-style top-20 audit
   (`docs/projects/archive/signal-intelligence-pipeline/resources/top-20-attention-audit-2026-07-11.md`)
   on both orderings, shuffled, so model-labeled wins are sanity-checked by a
   human before adoption.
4. **Quote/repost split test.** From the existing labels, compare relevance of
   quote-only vs. repost-only amplified items; adopt differentiated treatment
   only on a clear gap.
5. Only after 1–3 agree: cut a new versioned score contract
   (`attention-v2.0`), update `docs/references/signal-feed.md` and
   `docs/architecture/overview.md`, rebuild derived surfaces, and never
   re-anchor frozen v9 routing rows or published insight decisions to the new
   rank.

## Hard Sequencing Constraint

Do **not** change the production formula before the 2026-07-20 submission is
out. The frozen 900-envelope v9 cohort, the 75-decision insight store, and the
final 3–5 selection are all anchored to the v1.1 daily rank; a rank change
days before submission invalidates them for zero rubric gain. For the
submission itself, this analysis is *stronger* as a limitations/roadmap
section ("we measured the ranker against 900 labeled decisions, found the
percentile compression, and designed a calibrated v2") than as a silent
last-minute formula swap.

## Reproduction Notes

- Pool distributions/cliffs: page `/api/feed?date=<day>&limit=200&offset=…`
  to exhaustion; read `score_components`.
- Label join: `routing_item` (status `complete`) in each
  `data/derived/audience-routing/audience-routing-v9-*top100*/routing.db`,
  keyed by `event_id` to `/api/events?date=<day>` items'
  `daily_score_basis.score_components`.
- Beware ties when ranking by a single sparse component: break ties randomly
  or the sort silently preserves the incoming (current-rank) order and all
  orderings look identical.
- Percentile logic under test: `_percentiles` / `_apply_attention_scores` in
  `src/fli/web/feed.py`; the same components feed `src/fli/web/events.py`.
