# Layered daily score — proposal and audit

Drafted 2026-07-26 with Adi. Supersedes the blended-candidate direction in
`candidate-comparison.md`. Production remains on `attention-v1.1`.

## The score

```text
1. How many distinct trusted Registry entities vouched for it?
2. Tie? Average network position of those voters (0–1).
3. Tie? Network position of the author.
4. Tie? Public interactions.
```

Each layer speaks only when the layer above is silent. Nothing is blended, so
no lane can silently overpower another. There is no tunable constant anywhere,
so there is nothing to overfit and nothing to justify numerically.

## Why layered rather than weighted

`attention-v1.1` blends the same four ingredients. The behaviour audit
(`v1-1-behaviour-audit.md`) showed the blend, not the ingredients, was the
defect: percentiling a zero-inflated vote count made 0→1 vote worth +40.9
points and 2→111 votes worth +2.3, and let the nominally 25% author lane
out-discriminate the nominally 55% vote lane inside the routing gate.

Layering removes the failure mode by construction rather than by retuning.

## Why no `1 + 0.5 × trust` weight

The tracker's Candidate B weighting is correct for a *summed* score, where the
`1.0` floor keeps every participant counted and the `0.5` cap stops one famous
account outweighing many ordinary ones.

In a layered score the tie-breaker is an average, and averaging is affine:

```text
mean(1 + 0.5 × p) = 1 + 0.5 × mean(p)
```

An affine transform cannot change an ordering. Verified empirically over 4,000
synthetic events: ordering by `mean(1 + 0.5 × p)` and by `mean(p)` is
identical. The constants are therefore decorative, and a decorative constant is
a liability under questioning. Use raw network position.

## Why average and not sum for layer 2

Summing voter trust re-introduces vote count into the tie-breaker: three
low-trust voters would outrank two high-trust voters, collapsing layer 2 back
into layer 1. Averaging keeps "how many" and "who" as genuinely separate
questions asked in order.

## Rejected: an organization or first-party seed vote

Considered giving org-authored or artifact-bearing first-party posts a starting
vote so cold-start lab announcements can reach the gate.

Rejected on evidence. Across the 15 briefed days there are 577 org-authored
Events with zero trusted votes. A random sample of 40 is roughly 70% vendor
marketing — conference booths, hackathon recaps, merchandise, product ads,
game trailers — and roughly 30% substantive.

More decisively, the network already performs this job for the accounts that
matter:

| Author class | 0 votes | 1 vote | 2+ votes |
| --- | ---: | ---: | ---: |
| Frontier labs | 34.2% | 34.2% | 31.6% |
| Other organizations | 69.7% | 18.3% | 11.9% |

The zero-vote organization tail is dominated by second-tier vendor marketing,
not by missed frontier-lab signal. A blanket seed would inject ~577 mostly
promotional Events into the 1-vote tier, which is already the most contested
band, and would degrade the gate boundary rather than improve it.

An artifact-conditioned seed was also rejected: promotional posts carry
resolvable links too (event pages, landing pages), so artifact presence does
not separate substance from marketing without further unproven work.

## Supporting validation already in hand

Trusted vote count predicts downstream editorial usefulness monotonically
across all 13 judged days:

| Trusted votes | Judged | Useful | Hit rate |
| --- | ---: | ---: | ---: |
| 1 | 584 | 254 | 43.5% |
| 2 | 461 | 265 | 57.5% |
| 3–4 | 248 | 161 | 64.9% |
| 5+ | 149 | 104 | 69.8% |

Author network position adds a smaller but consistent lift at every vote level
(e.g. at 2 votes: 52.4% low-standing → 61.8% high-standing), which justifies
keeping it as layer 3 rather than discarding it.

## Honest risks and limitations

1. **The tie-breakers are load-bearing at the gate, not decorative.** Under
   pure vote counting the rank-100 cut lands at 2 votes on busy days
   (2026-07-15: 118 Events at ≥2 votes, so ~18 admissions decided by layers
   2–4) but at 1 vote on quiet days (2026-07-19: 397 Events at ≥1 vote, so
   roughly 300 admissions decided by layers 2–4). Layer 2 must be presented as
   a real component of the score, not a footnote.
2. **Public engagement cannot currently be evaluated.** Only 5 of 1,442 judged
   Events (0.3%) sit below the 50th engagement percentile, because engagement
   is itself 20% of the score that selects the judged set. Demoting it to layer
   4 is defensible, but claiming it is useless is not supported.
3. **The layered score itself is not yet replayed.** The vote gradient
   validates the primary signal; it does not validate the full ordering. The
   offline replay over the 15 saved days is still required before any claim
   about rank stability or movers.
4. **Frontier-lab cold start is a real residual gap.** 34% of frontier-lab
   Events receive zero trusted votes. This proposal does not fix that; it
   declines to fix it with an unvalidated heuristic. The recall probe is the
   measurement that would size it.

## Recommended next steps

1. Replay layers 1–4 offline over the 15 saved days; report movers, gate
   churn, and the vote-count hit-rate gradient under the new ordering.
2. Run the bounded recall probe on ranks 101–200 for one day using the existing
   prompts, to size what the gate is missing. This is the single highest-value
   remaining measurement and is already named as the known gap in
   `scoring-validation.md`.
3. Do not rescore production. Reranking would invalidate the five frozen
   submission Insights and the numbers in `scoring-validation.md`. Ship this as
   a measured self-audit plus a tested, versioned successor.
