# Network source architecture decision and refresh audit

Date: 2026-07-14  
Status: accepted and implemented

## Decision

Keep Registry admission, monitoring, network support, public reach, and
candidate discovery as separate concepts.

- The Registry remains broad for recall. AI Engineer World's Fair 2026 and
  2024 are accepted external admission sources for exact-X-addressable people.
- Conference inclusion carries no score, repeat-year bonus, authority claim,
  or organization multiplier.
- Each complete active Registry entity contributes at most one follow vote,
  regardless of how many X accounts it owns.
- A target Registry entity receives support from the union of follows to any
  of its represented X accounts. Self-support is excluded.
- Registry displays `support / eligible voting entities` first and a dense,
  tie-aware ordinal second. Ranking keeps the global account ordering and calls
  it candidate discovery rather than a Registry rank.
- Authority and guaranteed treatment belong in explicit roles and source
  policy, not hidden weights. Cohort reduction or tiering requires a later,
  non-circular yield evaluation.

## Canonical data boundary

The two accepted directories contain 725 source records but only 423 unique
X-addressable people. Canonical storage therefore keeps each person once with:

- exact X identity and canonical name;
- one newest available role, bio, and listed company;
- one current affiliation only when the organization has an independently
  addressable channel;
- an explicit organization website only when supplied by the official source;
- source, observation date, and evidence URL.

Talks, schedules, LinkedIn, personal sites, conference frequency, duplicate
year claims, speculative organization X handles, and ambiguous company labels
do not become canonical organization data. Ambiguous company labels remain a
person fact only. The resolution audit pruned 195 channel-less company
identities, 233 unresolvable affiliations, six superseded conference-created
organizations, and seven stale website links; zero orphan company facts remain.

Current canonical result: 2,630 auditable identities, 2,594 active identities,
36 reason-bearing rejections, 423 conference people, 96 channel-backed
conference-sourced organizations, and 186 resolvable affiliations. The other
233 company labels remain source-bound context on people rather than false
organization identities. Of the 423 people, 410 remain active and 13 are
explicitly missing or suspended.

## Immutable network refresh

The completed child snapshot
`registry-following-2026-07-14-aie-worldsfair-v2` freezes 2,564 source accounts.
It copied immutable evidence for the retained parent cohort and collected only
the new delta:

| Measure | Parent | Refreshed | Change |
| --- | ---: | ---: | ---: |
| Complete source accounts | 2,219 | 2,558 | +339 |
| Distinct voting entities | 2,197 | 2,521 | +324 (+14.75%) |
| Entity-target votes | 2,456,084 | 2,831,995 | +375,911 |
| Discovered target accounts | 463,180 | 557,363 | +94,183 |

The snapshot has 2,832,858 raw directed edges. The 330 newly monitored
conference speakers contributed 373,503 edges, or 96.66% of the newly
collected edges. The evidence boundary is intentionally described as
incremental and mixed-time: retained sources preserve July 11 observations;
new sources preserve July 14 observations.

Profile reconciliation used 356 requests / 6,408 estimated credits
(`$0.06408`). New following collection used 430,662 estimated credits
(`$4.30662`). Combined new provider work is therefore 437,070 estimated
credits (`$4.37070`). Provider responses did not include billed spend, so
these remain estimates rather than reported cost.

## Qualitative audit

The refreshed top 100 is stable: 96 accounts remain, for 92.3% Jaccard
overlap. Shared accounts move four positions at the median and 5.44 on average;
the largest move is 20 positions. Entrants include swyx, Patrick Collison,
David Scholz, and Simon Willison. Exits are Barret Zoph, Dustin Tran, Zico
Kolter, and Ben Recht.

The conference cohort adds genuine AI-engineering breadth but is mostly
peripheral in the existing graph:

- support among 410 active conference people: p25 6, median 31, p75 124,
  mean 102;
- 35 have zero inbound support and remain visible as zero rather than being
  silently omitted;
- six are in the Registry support top 100: Thomas Wolf, Sara Hooker, Christopher
  Manning, Richard Socher, swyx, and Simon Willison;
- the 330 newly monitored speakers have median support 18, versus 279 for the
  80 speakers already covered by the parent snapshot.

Interpretation: the external curation source broadened the practitioner layer
without overturning the established center. It does **not** prove that these
speakers are the best possible voters or that equal voting is optimal.

## Residual limitations and next evaluation

- X is the only implemented monitoring channel; this creates language,
  platform, activity, and social-graph bias.
- Conference curation favors visible speakers and practitioners. It is useful
  admission evidence, not a completeness benchmark.
- The refreshed overlap result was rebuilt; personalized PageRank was not,
  because it remains diagnostic and is not product-facing.
- A smaller 500/1,000-source cohort is not justified by neatness or by the
  same support signal that selected it. Future tiering must compare unique
  primary-source events/insights, noise, redundancy, omissions, and stability
  over multiple windows.

The practical next loop is: seed externally curated identities, monitor them,
measure first-hand useful evidence and unique cited-insight yield, then change
admission or priority policy only from that non-circular evidence.

## Reproduction boundary

The tracked cohort and snapshot manifest bind membership, lineage, checksums,
cost estimates, validation, and the final `entity-overlap-v3` run. The raw
snapshot and derived analysis databases remain local ignored artifacts; no
external upload or publication occurred.
