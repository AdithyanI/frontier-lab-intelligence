# Registry X Profile Count Scan

Scan date: 2026-07-11. Provider: TwitterAPI.io. Snapshot:
`registry-following-2026-07-11-v1`.

## Result

- Frozen sources: 2,231.
- Profiles cached: 2,228.
- Missing handles: 3.
- Protected accounts: 9.
- Public profiles advertising zero outgoing follows: 12.
- Successful-profile estimate: 2,228 × 18 credits.
- Three missing responses add at most the documented 15-credit minimum each.
- Profile scan plus the complete `@karpathy` following calibration is therefore
  approximately `$0.414`; the provider response does not expose an exact cost.
- The 2,228 cached following counts project the complete accessible crawl at
  2,783,826 credits / `$27.83826` before excluding protected, missing, and
  zero-following sources. This fits inside the current Builder plan's monthly
  credit allocation.

The scan used 10 workers with request starts limited to 9 QPS. TwitterAPI.io
documents the `$99` Builder plan at 10 QPS, so the run retained one request per
second of headroom. The parallel completion took about four minutes and had no
rate-limit failure.

## Count Distribution

| Metric | P50 | P90 | P95 | P99 | P99.5 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Accounts followed | 762 | 2,264 | 3,270 | 6,844 | 8,357 | 35,605 |
| Followers | 10,297 | 101,490 | 250,831 | 1,602,997 | — | 240,789,989 |

The refreshed follower-count minimum is 1,005. No cached profile violates the
existing 1,000-follower floor.

Largest outgoing-follow counts:

| Handle | Followers | Following | Projected source cost |
| --- | ---: | ---: | ---: |
| `@nathanbenaich` | 70,666 | 35,605 | `$0.35678` |
| `@miles_brundage` | 73,089 | 13,465 | `$0.13613` |
| `@tszzl` | 395,691 | 13,114 | `$0.13246` |
| `@sarahookr` | 62,538 | 11,134 | `$0.11286` |
| `@davidsholz` | 118,838 | 10,520 | `$0.10658` |
| `@misovalko` | 8,901 | 9,655 | `$0.09783` |
| `@davidad` | 22,594 | 9,544 | `$0.09706` |
| `@jekbradbury` | 17,135 | 9,355 | `$0.09528` |
| `@ofirpress` | 18,769 | 8,695 | `$0.08903` |
| `@romainhuet` | 51,719 | 8,628 | `$0.08702` |

The top 10 projected sources account for only 4.71% of total crawl cost; the
top 25 account for 8.85%. Several are clearly high-value frontier-AI sources.
High following count is therefore an inspectable cost/outdegree feature, not a
sound automatic rejection rule. PageRank also normalizes each source's
outgoing contribution by its outdegree.

## Explicit Non-Collectable Sources

Protected: `@albertwebson`, `@alsuhr`, `@dwf`, `@gwern`, `@hengjinlp`,
`@maosbot`, `@nealkhosla`, `@nlpnoah`, and `@sindero`.

Missing: `@lxuechen`, `@mirowskipiotr`, and `@vladmnih`.

Zero following: `@bfl_ai`, `@danielgross`, `@darioamodei`, `@deepseek_ai`,
`@dralandthompson`, `@epochairesearch`, `@magicailabs`, `@midjourney`,
`@realsharonzhou`, `@sakanaailabs`, `@schmidhuberai`, and `@ssi`.

The snapshot excludes protected and missing sources from following collection
and completes zero-following sources directly from cached profile evidence.
These are graph-collection states, not silent Registry deletions.

A bounded `pageSize=20` diagnostic on protected `@alsuhr` returned provider
`success` with zero rows and no cursor even though the cached profile advertises
637 accounts followed. Protected outgoing follows are therefore inaccessible;
the empty response must not be modeled as a genuine zero-following snapshot.
Protected identities can still receive inbound edges from public sources:
Karpathy's completed list already contains `@dwf` and `@gwern`. They remain
useful as graph targets and identity anchors, but not as X collection sources.

## Decision

Do not exclude high-following or high-follower sources solely because they are
statistical outliers. The current data shows no follower-floor violations and
the cost tail is modest. Keep the count fields for later evaluation and allow
the reviewed personalization set—not a hidden numeric cutoff—to decide trust.
