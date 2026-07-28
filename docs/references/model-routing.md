# Model Routing

Last verified: 2026-07-27

For the cross-stage cost summary and X-provider units, see
[`tokenomics.md`](tokenomics.md).

## Current Policy

Use `gpt-5.6-luna` as the default efficient model for bounded structured
classification and Registry evaluation. This is an accuracy-first default,
not a rule that the cheapest model or lowest reasoning effort always wins.
The daily brief path uses `gpt-5.4-mini` for audience routing and a persisted
`gpt-5.6-sol` Codex task for final research, consolidation, selection, and
writing. Terra per-Event outputs remain optional working annotations, not a
required authoring stage. The web-grounded Registry relevance audit was a
one-time non-mutating evaluation, not part of the daily path.

| Boundary | Default model | Reasoning effort | Rationale |
| --- | --- | --- | --- |
| Structural entity kind | `gpt-5.6-luna` | `medium` | Existing evaluated classifier contract. |
| Evidence audience routing | `gpt-5.4-mini` | `high` | The current v9 / `daily-rank-v2` 17-day cohort completed 1,674/1,674 with zero failures: 509 both, 183 Engineering-only, 273 Investment-only, and 709 neither. The final tie-aware correction reused 1,647 exact Event/evidence/input judgments and made 27 new calls for $0.089051 incremental proxy cost. Across the initial migration and final correction, 725 calls cost $3.050746. The v9 semantic input is first-party only. A prior same-two-packet comparison found xhigh unchanged on decisions and only marginally better on caveats while using 5.4× the hidden reasoning/output tokens. |
| Per-Event working annotations | `gpt-5.6-terra` | `high` | A completed calibration pass produced separate audience notes with stable cache keys. The daily Codex agent may inspect them but must re-evaluate the frozen evidence; they are not final brief outputs. |
| FLI daily-intelligence agent | `gpt-5.6-sol` | `xhigh` | The persisted Codex task researches the complete routed cohort, consolidates overlapping Events, selects the final set, and writes both audience briefs. |
| Missing-bio identity research | `gpt-5.6-luna` | `high` | Multi-source grounded identity resolution needs more checking. |
| Combined kind + Registry decision | `gpt-5.6-luna` | `high` | Independent structural and admission decisions with optional search. |
| Registry relevance audit | `gpt-5.6-terra` | `high` | One-time required-web-search evaluation of the initial Registry. It is non-mutating and does not run during daily brief generation. |

Do not lower reasoning effort merely to reduce spend. OpenAI recommends using
the lowest effort that still meets the task, preserving the prior effort as a
migration baseline, and testing one level lower. That comparison matters here:
Luna-low agreed with the retired mini-medium keep/drop decisions on 63/64
envelopes but dropped a post that named a specific Thinking Machines Lab essay.
That historical comparison remains relevant to the retired keep/drop boundary.
For the live two-audience router, Adi authorized a quality-first comparison on
GPT-5.4 mini. `high` produced grounded reasons near the requested length;
`xhigh` did not change either decision and mostly over-deliberated. The live
default is therefore `high`. Adi accepted the contextual audit's two narrow
boundary rules, and the final v7 five-packet rerun produced coherent labels
without changing the model, effort, or output schema.

The model string and reasoning effort are part of every run identity. Existing
run databases and historical reports remain immutable evidence of the model
that produced them; changing a runtime default never relabels old results.

## Prompt Caching

Prompt-cache provider behavior, cache-lane scheduling, telemetry
interpretation, current Luna/Terra proof, incident history, and the repeatable
canary are owned by [`prompt-caching.md`](prompt-caching.md). That page is the
single source of truth; do not duplicate its operational rules here.

## Source Guidance

- [OpenAI GPT-5.6 migration guidance](https://developers.openai.com/api/docs/guides/latest-model#update-api-and-model-parameters)
- [OpenAI model choice for simple agent workloads](https://developers.openai.com/tracks/building-agents#how-to-choose)
