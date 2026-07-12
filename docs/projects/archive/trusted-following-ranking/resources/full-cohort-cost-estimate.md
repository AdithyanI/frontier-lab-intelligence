# Full-Cohort Following Cost Estimate

Estimate date: 2026-07-10. No API request was made for this estimate.

## Scope and Pricing

The clean graph baseline retains 2,924 X accounts: 2,607 people, 180
organizations, and 137 unsure. The existing importer also performs one
source-profile lookup per seed.

TwitterAPI.io currently documents:

- 100,000 credits = `$1.00`;
- 200 returned followings: 1 credit each;
- 100–199: 2 credits each;
- 20–99: 3 credits each;
- a 60-credit minimum per following-page call;
- one user profile: `$0.00018` / 18 credits.

Source: `https://docs.twitterapi.io/api-reference/endpoint/get_user_followings`
and `https://docs.twitterapi.io/introduction`.

## Scenarios

The totals include the 18-credit profile lookup for every account and exact
final-page tiering at the adapter's 200-item page size.

| Average accounts followed | Per seed | All 2,924 |
| ---: | ---: | ---: |
| 100 | `$0.00218` | `$6.37` |
| 250 | `$0.00368` | `$10.76` |
| 500 | `$0.00618` | `$18.07` |
| 1,000 | `$0.01018` | `$29.77` |
| 1,108 (`@karpathy` reference) | `$0.01234` | `$36.08` |
| 2,000 | `$0.02018` | `$59.01` |
| 3,000 | `$0.03018` | `$88.25` |
| 5,000 | `$0.05018` | `$146.73` |

## Planning Read

- Best rough estimate for all 2,924: about **`$36`**.
- Sensible planning range: **`$18–$59`** if the average seed follows roughly
  500–2,000 accounts.
- A full-cohort run can exceed the EUR100 project budget if the average seed
  follows roughly 3,400 or more accounts.

Cost is not the reason to avoid an all-account run. The stronger objection is
that all 2,924 accounts are candidates, not reviewed trust seeds. Treating every
candidate as equally trusted would weaken the meaning of personalized PageRank
and make the evaluation story less defensible.

## Current Checkpoint Update

The final relevance-cleanup state on 2026-07-11 contains 2,235 stored X
accounts, of which four rejected identities are excluded, leaving a 2,231
account collection cohort. Applying the same documented price model gives this
updated range:

| Average accounts followed | All 2,231 |
| ---: | ---: |
| 500 | `$13.79` |
| 1,000 | `$22.71` |
| 1,108 (`@karpathy` reference) | `$27.53` |
| 2,000 | `$45.02` |

Actual spend must be recorded from the provider run; these values remain
pre-run estimates only.

## Profile-Grounded Update

The 2026-07-11 bounded profile scan cached current follower/following counts for
2,228 of 2,231 frozen sources; nine are protected and three are missing. The
advertised following counts project the complete accessible outgoing-follow
crawl at **2,783,826 credits / `$27.83826`** before applying the protected,
missing, and zero-following exits. This replaces the rough average-based
planning estimate with a per-source projection. See
`profile-count-scan.md` for the distribution and outlier review.
