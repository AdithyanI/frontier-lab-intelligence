# What `attention-v1.1` actually does

Measured 2026-07-26 against the published Event run
(`9d5a1212…d27ac1`) via `fli.web.events.events_payload`, seven briefed days.
This is a behaviour audit of the live production score, not a candidate.

## Why this matters more than the rejected `+0.25` proposal

The project opened because a *proposed* formula mixed an open-ended sum with
fixed adjustments. That rejection was correct, but the same class of defect is
already present in production, at larger magnitude. The audit below is the
strongest available argument for the redesign, and it is checkable.

## Finding 1 — the amplification lane is a step function, not a scale

`network_attention_percentile` applies a day-relative percentile to
`registry_amplifiers`, a zero-inflated low-cardinality count. Roughly half of
each day sits at exactly 0, so the percentile transform spends almost its whole
range on the 0→1 step.

| Day | Events | 0 amplifiers | percentile @1 | percentile @2 |
| --- | ---: | ---: | ---: | ---: |
| 2026-07-06 | 1,095 | 48.7% | 0.726 | 0.966 |
| 2026-07-08 | 1,358 | 43.9% | 0.736 | 0.951 |
| 2026-07-10 | 1,276 | 45.6% | 0.728 | 0.955 |
| 2026-07-13 | 1,111 | 44.6% | 0.741 | 0.961 |
| 2026-07-15 | 1,319 | 47.4% | 0.743 | 0.958 |
| 2026-07-17 | 1,289 | 47.2% | 0.740 | 0.961 |
| 2026-07-19 | 829 | 52.1% | 0.775 | 0.970 |

At the 55% lane weight, on 2026-07-15:

- 0 → 1 amplifier is worth **+40.9 points**;
- 1 → 2 amplifiers is worth +11.8 points;
- 2 → 111 amplifiers is worth **+2.3 points**.

The 111-amplifier Thinking Machines "Inkling" release — the clearest example of
broad trusted convergence in the whole cohort — is separated from a single
retweet by 14 points on the lane that is supposed to measure exactly that.
The score saturates precisely where the product claim lives.

## Finding 2 — the stated weights do not match the realized behaviour

Inside the top 100 (the only window that matters, because it is the routing
gate), per-lane contribution spread in score points:

| Day | network (55%) | author support (25%) | public (20%) |
| --- | ---: | ---: | ---: |
| 2026-07-06 | 6.90 | 6.15 | 2.33 |
| 2026-07-08 | 5.58 | **6.33** | 1.61 |
| 2026-07-10 | 6.08 | **6.57** | 1.73 |
| 2026-07-13 | 8.06 | 7.43 | 1.74 |
| 2026-07-15 | 6.19 | **6.92** | 1.72 |
| 2026-07-17 | 6.40 | **6.71** | 1.84 |
| 2026-07-19 | 5.57 | **7.20** | 1.74 |

On five of seven days the nominally 25% author-support lane out-discriminates
the nominally 55% amplification lane. The network lane has already saturated
near its 55-point ceiling for every top-100 Event (2026-07-15 mean 48.9 of 55),
so it mostly stops separating them. Ordering inside the gate is therefore
driven substantially by *who posted* rather than *how much the network
converged* — the opposite of the documented intent.

Public engagement, nominally 20%, has a spread of ~1.7 points inside the gate.
It is close to decorative for ordering, yet it still moves marginal Events
across the rank-100 admission boundary, which is the least defensible place for
raw popularity to have influence.

## Finding 3 — the gate admits and rejects against the stated claim

2026-07-15, exactly:

- 37 of the top 100 Events have ≤1 trusted amplifier;
- 11 Events with ≥3 trusted amplifiers rank *below* 100 and are never judged,
  including one with 5 amplifiers at score 77.1 against a rank-100 cutoff
  of 77.9 held by a 1-amplifier Event.

Across the seven days, 23–60 of each top 100 have ≤1 amplifier, and up to 14
Events per day with ≥3 amplifiers miss the gate. This is a concrete, named
recall loss caused by the transform rather than by the top-100 budget.

## Finding 4 — one cosmetic redundancy

`apply_attention_scores` computes `percentiles(math.log1p(engagement))`.
Percentiles are rank-based, so the `log1p` is provably a no-op (verified
directly). It is harmless, but `signal-feed.md` describes the lane as
"log-scaled likes, replies, reposts, and quotes", which reads as deliberate
compression that the code does not actually perform. Either drop the transform
or drop the claim.

## Reading

`attention-v1.1` is not arbitrary — its three inputs are real and share a 0–1
scale, which is why it survived earlier review. The defect is narrower and
harder to see: **a percentile transform is the wrong tool for a zero-inflated
count with a long thin tail.** It is the right tool for public engagement,
which is continuous and heavy-tailed. Applying it uniformly to all three lanes
is what silently converted the primary signal into a near-binary
"was this amplified at all?" flag and handed effective control to the
secondary lane.

This supports the project's existing hypothesis that a direct
trusted-participant count (Candidate A) or a bounded trust-weighted count
(Candidate B) is both simpler *and* strictly better behaved. It does not need
a percentile at all, because a count is already on a meaningful scale.

## Consequence for the submitted proof

The five submitted Insights were selected under `attention-v1.1`. Rescoring
production would rerank the judged cohort and invalidate both the frozen
submission proof and the measured numbers in `scoring-validation.md`. This
audit is therefore an interview artefact first and an implementation trigger
second. Production stays on `attention-v1.1` until Adi decides otherwise.
