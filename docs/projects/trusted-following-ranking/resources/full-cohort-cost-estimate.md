# Full-Cohort Following Cost Estimate

Estimate date: 2026-07-10. No API request was made for this estimate.

## Scope and Pricing

The clean baseline has 586 X accounts: 473 people, 87 organizations, and 26
unsure. The existing importer also performs one source-profile lookup per seed.

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

| Average accounts followed | Per seed | All 586 |
| ---: | ---: | ---: |
| 100 | `$0.00218` | `$1.28` |
| 250 | `$0.00368` | `$2.16` |
| 500 | `$0.00618` | `$3.62` |
| 1,000 | `$0.01018` | `$5.97` |
| 1,108 (`@karpathy` reference) | `$0.01234` | `$7.23` |
| 2,000 | `$0.02018` | `$11.83` |
| 3,000 | `$0.03018` | `$17.69` |
| 5,000 | `$0.05018` | `$29.41` |

## Planning Read

- Best rough estimate for all 586: about **`$7`**.
- Sensible planning range: **`$4–$12`** if the average seed follows roughly
  500–2,000 accounts.
- A conservative hard-cap assumption is **`$20`**; exceeding it would imply an
  unusually high average following count or unexpected provider behavior.

Cost is not the reason to avoid an all-account run. The stronger objection is
that all 586 accounts are candidates, not reviewed trust seeds. Treating every
candidate as equally trusted would weaken the meaning of personalized PageRank
and make the evaluation story less defensible.
