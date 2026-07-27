# Attention ranking candidate comparison

## The question

The ranking should answer one narrow question:

> Which Events received the strongest participation from the trusted AI
> network on this day?

It is a routing score. It decides what gets inspected first. It does not
measure truth, novelty, usefulness, quality, or importance.

## The scale error we are not carrying forward

The rejected proposal was:

```text
sum(1 + 0.5 × entity trust percentile)
+ 0.25 for an organization author
+ up to 0.25 for public reach
```

The participant sum is open-ended while the final two terms are fixed. With
100 median-trust participants, the first term is about 125 and either `0.25`
adjustment changes the total by only 0.2%. The formula therefore appears to
include organization status and public reach without letting either carry a
stable meaning.

The `1 + 0.5 × trust percentile` participant weight is not itself invalid.
The invalid part is adding unrelated fixed-size terms beside its unbounded
sum.

## Shared invariants

All candidates must use the same Event population and obey these rules:

1. One canonical Registry entity contributes at most once to an Event.
2. Authorship, quote-posting, retweeting, and another accepted amplification
   are different evidence roles, but repeated activity by one entity is never
   several votes.
3. The source author may contribute one trusted-participant vote when present
   in the active Registry. Independent amplifiers remain separately counted.
4. A self-retweet or self-quote cannot add another vote.
5. Every score is calculated within one frozen UTC day. Cross-day scores are
   not compared.
6. Audience judgments and editorial outcomes never enter the score.
7. Public interactions remain visible context during this comparison. They do
   not enter the three candidate scores.
8. Organization status receives no arbitrary bonus. An organization can
   contribute through its existing Registry identity and trust position, just
   as a person can.
9. Deterministic tie-breaking is:
   independent trusted amplifier count, summed participant trust percentile,
   first-party source before a wrapper, public interaction count, then stable
   Event ID.

Rule 3 deliberately makes the score about trusted **participation**, not only
independent amplification. The replay must also report independent amplifier
count separately so a direct source announcement and broad network
convergence cannot be mistaken for each other.

## Baseline

`attention-v1.1` remains the production baseline:

- 55% day-relative tracked-amplification percentile;
- 25% day-relative author network-support percentile;
- 20% day-relative public-interaction percentile.

It is coherent because all three inputs are normalized to the same 0–1 scale.
The comparison is testing whether a narrower trusted-participation score is
easier to explain and behaves better, not claiming that the baseline is
mathematically broken.

## Candidate A — Flat trusted convergence

```text
score = number of distinct trusted participants
```

Every trusted entity has one vote. The source author counts once if trusted;
every independent trusted amplifier counts once.

Within a day, dividing by the number of active trusted entities would produce
the same order, so the raw count is the clearer display.

What it tests:

- whether breadth of trusted convergence is sufficient;
- whether the existing entity ranking should stay out of Event ranking;
- whether famous accounts currently have too much influence.

Plain-language explanation:

> An Event rises when more distinct members of the trusted network participate
> in it. No person or organization can vote twice.

## Candidate B — Trust-weighted convergence

```text
entity weight = 1 + 0.5 × trust percentile
score = sum(entity weight for every distinct trusted participant)
```

Each participant contributes from 1.00 to 1.50. Breadth remains dominant, but
the existing network ranking can resolve close cases. There are no
organization or public-reach additions on another scale.

What it tests:

- whether bounded trust weighting improves the ordering over equal votes;
- whether the 1.00-to-1.50 range changes only close cases as intended;
- whether organizations already receive sufficient treatment through their
  measured trust position.

Plain-language explanation:

> Every trusted participant counts. A participant near the top of the network
> can count up to half a vote more, but never several times more.

## Candidate C — Daily attention budget

```text
entity budget = 1 + 0.5 × trust percentile
entity contribution = entity budget ÷ distinct Events touched that day
score = sum(entity contribution for all participants)
```

An entity spreads one daily attention budget across the Events it authored or
amplified. A highly prolific account therefore cannot give full-strength
support to everything it touches.

What it tests:

- whether prolific accounts currently flood the top of the day;
- whether limited attention is better represented as allocation than as one
  full vote per Event;
- whether the added complexity produces a material and defensible benefit.

Plain-language explanation:

> Each trusted entity has a limited daily attention budget. The more Events it
> touches, the more thinly its vote is spread.

This candidate requires complete enough daily activity coverage. If collection
gaps make the denominator unreliable, it is not suitable for production even
if its sample ranking looks attractive.

## Organization and public engagement

An organization is not automatically a better Event. A first-party lab
announcement is valuable evidence, but “first-party source” and “the network
paid attention” are different claims. During replay:

- organization authorship is shown as a slice and named case inspection;
- author type does not add a separate score bonus;
- a trusted organization author already contributes one participant vote and,
  in Candidates B and C, its measured trust weight;
- the final recommendation may use first-party source only as an explicit
  tie-breaker if exact score ties are common.

Public likes, reposts, replies, and quotes answer a different question:
broader popularity. They remain visible on the Event and are used to inspect
viral outliers. If removing them from rank consistently hides useful Events,
that is evidence for a separate normalized lane—not for restoring a fixed raw
bonus.

## Worked scale check

Assume all participants sit at the median trust percentile:

| Trusted participants | Candidate A | Candidate B |
| ---: | ---: | ---: |
| 1 | 1 | 1.25 |
| 4 | 4 | 5.00 |
| 100 | 100 | 125.00 |

Candidate B has one unit throughout: trusted-participant votes. There is no
`+0.25` organization term that becomes meaningless as participation grows.
Candidate C depends on how many Events each participant touched that day and
will be reported from the actual replay rather than a fabricated example.

## Replay outputs

Every candidate will run over the same frozen days and report:

- Spearman rank correlation and top-20/top-50/top-100 overlap with
  `attention-v1.1`;
- kept-Insight concentration by rank window as a diagnostic, with the
  top-100 censoring limitation stated;
- Events moving at least 25 positions in either direction;
- top-ranked Events for low-, medium-, and high-participation cases;
- organization-authored Events and direct first-party announcements;
- high-public-engagement Events with weak trusted participation;
- score ties and the tie-breaker that resolved each one;
- component distributions by day so scale failures are visible.

The comparison will recommend the simplest candidate that survives these
checks. Complexity must earn its place through a visible improvement, not just
produce a different order.

## Current expectation, before replay

Candidate A is the default to beat. It most directly measures network
convergence and is easiest to defend. Candidate B is plausible if trust
weighting improves close calls without allowing celebrity to dominate.
Candidate C is intellectually coherent but should be rejected if activity
coverage or explanation cost weakens it.

This is a hypothesis, not the production decision.
