# Corrected Top-100 Contextual Audit

Date: 2026-07-15  
Run family: `audience-routing-v8-gpt-5-4-mini-<day>-top100-high-cc76958510dd`

## Production Result

- 900/900 packets completed across 2026-07-05 through 2026-07-13.
- Outcomes: 344 both, 112 Engineering-only, 141 Investment-only, 303 neither.
- 858 unique model inputs; 38 repeated inputs have zero label conflicts.
- Reasons remain close to the prompt guidance: median 45 words, p95 52, range
  31–59. The schema applies no length rejection.
- Provider telemetry: 779 cache-hit requests, 1,399,040 cached of 3,418,560
  input tokens, 813,650 output tokens, and $5.28797975 reported cost.

## Review Method

Twenty distinct packets were selected deterministically across all four
outcomes and approximate ranks 5, 25, 50, 75, and 98. The review compared each
root, supplied first-party artifact/continuation evidence, and both stored
reasons. This is a bounded contextual audit, not a scored human-label oracle.

| Outcome | Day / rank | Event | Short description | Review |
| --- | --- | --- | --- | --- |
| both | Jul 6 / 5 | `80362915e9f4…` | GPT-style memorization capacity | clear |
| both | Jul 7 / 25 | `0b1a203ceaaf…` | Meta Muse launch and artifacts | clear |
| both | Jul 9 / 50 | `31287257fc2f…` | desktop multi-model agent wish | soft but defensible |
| both | Jul 11 / 75 | `9507bd6d9387…` | SFT/RL compositional reasoning | clear |
| both | Jul 12 / 98 | `332dfc6c430d…` | GPT-5.6 Design Arena result | clear with benchmark caveat |
| Engineering | Jul 5 / 4 | `3ed836b8bf66…` | AI education/user-data thesis | clear from primary text |
| Engineering | Jul 9 / 25 | `3f118e531e45…` | removable dual-use capability modules | clear |
| Engineering | Jul 7 / 51 | `c70e07a094c6…` | ARC-AGI-3 winners and workflow constraints | clear |
| Engineering | Jul 6 / 76 | `288ef528f1c6…` | Ideogram serving latency and price | clear |
| Engineering | Jul 13 / 98 | `9c88898bd437…` | Lean Minecraft-clone claim | soft; worth investigation only |
| Investment | Jul 6 / 6 | `098d431672a1…` | software-only capability-growth thesis | clear as attributed forecast |
| Investment | Jul 12 / 25 | `24f4afabd7b4…` | OpenAI pressure on Anthropic bundling | clear but speculative |
| Investment | Jul 7 / 50 | `117f2a53f0b4…` | possible Chinese frontier-model controls | clear with reporting caveat |
| Investment | Jul 8 / 75 | `959a461642cc…` | Tesla/Boom turnaround anecdote | soft and unverified |
| Investment | Jul 9 / 98 | `0ccced49d1f2…` | OpenAI product roadmap | clear |
| neither | Jul 5 / 5 | `0379a97d7e00…` | conference/networking praise | clear |
| neither | Jul 6 / 25 | `a42d79ccd4b7…` | Starfield Library recommendation | clear |
| neither | Jul 8 / 50 | `8cbed89c0f20…` | normative globally beneficial AI paper | clear |
| neither | Jul 12 / 75 | `176094570383…` | San Francisco rental vacancy | clear under public-equity standard |
| neither | Jul 10 / 98 | `91e1bef70a55…` | satirical AI-governance thread | clear |

Seventeen decisions are clear. Three are softer but remain consistent with the
approved assignment because the router may preserve an attributable lead for
later investigation; none justifies another prompt change by itself.

## Repaired-Envelope Checks

- Anthropic post `2074185348142280912` is July 7 rank 1 with 108 related posts
  and routes to both audiences.
- Gemma event `3074d73120d30cf24136bed082b8b25f752362002a23843ff08a379a7bb73750`
  is rank 12, contains the technical report evidence, and routes to both.
- Cohere event `4840b35270a75d3612ad8c625c2837c8b7ce04736fbe45e8241e3b466f4d06b4`
  is rank 15, contains three first-party continuations plus the model card and
  leaderboard evidence, and routes to both.
- Muse event `28b76f97598a10db0ece6d39b0e022e7ac63f3cb5d284318fa7a0dd128b971da`
  contains its first-party launch thread and routes to both.

The important correction is upstream evidence completeness, not a more
permissive routing prompt. The earlier false negatives should not be used as
prompt-quality evidence.
