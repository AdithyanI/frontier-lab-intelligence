# Full Registry Evaluation — GPT-5.4 Mini High

Date: 2026-07-12

This is a read-only review artifact. No `keep`, `remove`, or `review`
recommendation was applied to `data/fli.db`.

## Frozen contract

- Run: `active-registry-gpt-5.4-mini-high-2026-07-12`
- Cohort: all 2,207 active X-backed entities (2,114 people, 93 organizations)
- Input: public profile plus up to 20 recent authored posts
- Output: independent structural kind and Registry decision, each with a reason
- Web: optional hosted search
- Cohort SHA-256: `9fe3dee465ed264e9189dd7994e54fc8e77527adc89ae19f4c0592d8a12c2972`

## Results

| Decision | People | Organizations | Total |
| --- | ---: | ---: | ---: |
| Keep | 1,771 | 84 | 1,855 |
| Remove | 192 | 9 | 201 |
| Review | 151 | 0 | 151 |
| **Total** | **2,114** | **93** | **2,207** |

The structural result was 2,115 people and 92 organizations. The only
disagreement with current kind was `@xenovacom`, evaluated as a person rather
than an organization.

## Evidence and execution

- 2,207 exact ordered post bundles; 2,079 contained all 20 requested posts.
- 42,773 bundled posts and 63,736 normalized observed posts.
- 4,419 raw TwitterAPI.io request/response pairs; zero terminal fetch failures.
- 317 entities used web search, producing 753 search actions and 7,525 sources.
- 19,884,835 input tokens, of which 13,597,824 were cached (68.38%).
- 1,717,540 output tokens.
- Current-result proxy cost: `$13.4861493` (`$0.006111` per entity).
- Evidence collection ran from 10:27:24–10:35:47 UTC; model completions ran
  from 10:35:50–10:46:01 UTC.
- Both the run database and X-content database pass SQLite integrity and
  foreign-key checks.

LiteLLM routed `@timnitgebru` to its configured `claude-sonnet-4-6` fallback;
the other 2,206 current results used `gpt-5.4-mini`. One normalization retry
again took the same fallback, adding `$0.03039`; total operational model spend
including that retry was `$13.5165393`. No direct Azure call was made.

## Interpretation

The 201 removals are recommendations, not rejections. The people cohort
contains high-impact debatable cases, so the output is unsuitable for automatic
application. In particular, recent posts can describe current publishing
behavior while omitting durable role evidence. The Luna comparison resource
tests this failure mode on the 192 people recommended for removal.
