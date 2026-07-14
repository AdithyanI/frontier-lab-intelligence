# Artifact fetch cohort audit — 2026-07-14

## Decision

Close Artifact Store v1 after the frozen 30-artifact cohort. Indexing the full
locally resolvable corpus is useful; fetching its entire 642-host long tail is
not yet justified. The bounded cohort proved HTML, PDF, repository, redirect,
and failure behavior while retaining a small enough surface for manual review.

## Reproducible result

- Import run: `9c32e0d11ff6f74fd25213534fb1e033fb10a227f0b4044d46951582962e8848`
- Fetch run: `ff2dbb60507137b6dbe2cae2d4b85e354ed5ab05c7fbaa2b506debde744f91f3`
- 30 selected artifacts: 19 success, 4 terminal, 7 retryable after 3 attempts.
- 44 total attempts: 19 success, 4 terminal, 21 retryable attempts.
- All 19 successful texts were manually inspected and were usable source text.
- A fourth identical fetch command returned `reused=true` and performed no
  additional network work.

## Cohort

| Rank | Kind | Resource | Outcome | Clean text / failure |
| ---: | --- | --- | --- | --- |
| 1 | HTML | Anthropic global workspace | success | 29,497 chars |
| 2 | HTML | OpenAI ambitious work | terminal | HTTP 403 |
| 3 | HTML | J-lens explorer | success | 2,676 chars |
| 4 | HTML | OpenAI GPT-Live | terminal | HTTP 403 |
| 5 | HTML | Thinking Machines human future | success | 12,803 chars |
| 6 | HTML | Lilian Weng harness engineering | success | 42,530 chars |
| 7 | HTML | Intelligent Internet Zenith | success | 10,992 chars |
| 8 | HTML | Thinking Machines Paperform | terminal | client-rendered error shell |
| 9 | HTML | LinkedIn post | retryable exhausted | no route to host |
| 10 | HTML | Gwern scaling hypothesis | success | 103,253 chars |
| 11 | HTML | eve.dev | success | 4,393 chars |
| 12 | HTML | OpenAI GPT-5.6 | terminal | HTTP 403 |
| 13 | paper | arXiv 2510.01123 | success | 3,353 chars |
| 14 | paper | OpenAI prompt PDF | success | 4,997 chars; no embedded title |
| 15 | paper | Berkeley synthetic-data PDF | success | 22,086 chars |
| 16 | paper | arXiv 2308.09124 | success | 2,543 chars |
| 17 | paper | Stanford dissertation PDF | success | 470,148 chars |
| 18 | repository | mem0/openmemory | success | 1,848 chars |
| 19 | repository | grok-network-monitor | success | 12,212 chars |
| 20 | repository | Meta macOS CUA cookbook | success | 7,000 chars |
| 21 | repository | Karpathy autoresearch | success | 7,181 chars |
| 22–24 | video | three YouTube URLs | retryable exhausted | no route to host |
| 25–27 | X Article | three long-form articles | retryable exhausted | local transport failure |
| 28 | redirect | Meta Muse Image/Video | success | 6,154 chars |
| 29 | redirect | Meta Muse Spark | success | 7,500 chars |
| 30 | redirect | NVIDIA Nemotron guide | success | 13,401 chars |

## Edge cases learned

1. Quoted-post URLs must bind to the quoted post, not the wrapper. Recursive
   ownership produced exactly 1,739 source observations.
2. Card-only short links are ambiguous when the provider did not preserve an
   expansion. They remain explicit exclusions rather than guessed artifacts.
3. Redirect convergence can reduce artifact count after import; aliases,
   observations, candidate rows, cohort items, and fetch attempts must move in
   one transaction.
4. A completed run may still contain retryable outcomes. It must reopen until
   those artifacts succeed, become terminal, or reach three attempts.
5. Terminal failures must never enter a future retry cohort.
6. Client-rendered error shells are not clean-text successes. The Paperform
   example became the regression fixture for this failure.
7. Attempt counts and per-artifact outcomes are different operational metrics
   and are reported separately.

## Validation

- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: zero rows
- Identical import replay: `reused=true`; logical counts unchanged
- Query plans use the observation, source-provenance, fetch, and cohort indexes
- Focused artifact tests: 10 passed before the repository-wide gate

