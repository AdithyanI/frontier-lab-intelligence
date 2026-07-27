# Model Routing and Prompt Caching

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

## Azure/LiteLLM Prompt-Cache Adapter

All application calls still go through the shared LiteLLM endpoint. Cacheable
GPT-5.6 Responses requests must obtain provider kwargs from
`fli.llm_responses.litellm_prompt_cache_kwargs`, which currently returns:

```python
{"prompt_cache_retention": "24h"}
```

This is deliberately centralized. OpenAI's native GPT-5.6 API guidance now
prefers `prompt_cache_options.ttl`, while the Azure-backed route used by this
repository was live-verified with Azure's `prompt_cache_retention="24h"`.
Do not scatter either provider field through individual pipelines or send both.
Azure does not currently support OpenAI's explicit
`prompt_cache_options`/`prompt_cache_breakpoint` controls. Revisit the adapter
when the shared route is migrated or Azure documents and proves a different
contract.

Prompt caching is automatic and best-effort. A cache-eligible request is not
proof of a hit; only Responses
`usage.input_tokens_details.cached_tokens` is. Every model boundary records
that value, `cache_write_tokens` when supplied, input/output tokens, and
LiteLLM's response-cost header.

## Current Live Evidence

The current different-input canary ran through FLI's real LiteLLM Responses
path on 2026-07-27. It used the active roughly 1,975-token audience-routing
request shape, one fresh stable key per model, explicit 24-hour retention, and
five sequential calls. The first request is excluded from the warm-hit
criterion because Azure may already hold the same prefix:

| Model | Cached tokens by call | Warm hits |
| --- | --- | --- |
| `gpt-5.6-luna` | `1792, 1792, 1792, 0, 1792` | 3 of 4 |
| `gpt-5.6-terra` | `0, 1792, 1792, 1792, 1792` | 4 of 4 |

This proves Luna and Terra prompt caching currently works through the shared
Azure-backed route. It also proves why an individual miss cannot be interpreted
as “the model does not support caching”: Luna missed one warm request in the
same run that produced three warm hits. Earlier controls remain useful incident
history:

- an exact-repeat Luna canary read 1,792 cached tokens from a 1,990-token input
  on 2026-07-14 when `24h` was explicit;
- the historical 64-envelope Luna-medium classification run had 58 cache-hit
  requests and read 103,936 cached tokens from 168,022 input tokens (61.86%);
- a five-item Luna extraction oracle and later two-call same-key control
  recorded zero reads despite eligible prefixes.

The 2026-07-15 miss controls confirmed that the Azure route can become
intermittent even when LiteLLM forwards the key, retention, instructions, and
schema unchanged. The same request shape produced a positive GPT-5.4-mini
control and later 88 cache-hit requests out of 90 in the nine-day production
routing run. The accepted v7 prompt calibration then read 1,792 cached tokens
on each of its four warm requests.

The 2026-07-27 positive Luna run supersedes the old “budget as always uncached”
conclusion, but not the evidence that Azure availability can be intermittent.
Cost plans must use measured hit rates and retain an uncached upper bound. Do
not switch models for cache savings alone—the routing decision remains
accuracy-first.

The proxy also has a separate Redis full-response cache. An exact complete
request repeat can therefore return instantly at zero proxy spend while still
showing `cached_tokens=0`; that is not reusable-prefix caching and does not help
different catalog items. On such a full-response hit, LiteLLM 1.92.0 replays
the original `x-litellm-response-cost` header even though its persisted spend
record is zero, so use the persisted proxy record when reconciling that case.

## Cache-Lane Execution Contract

The repository follows Azure's documented request-shape guidance:

1. Put identical, cacheable instructions first and variable evidence last.
2. Keep the shared prefix at least 1,024 tokens. Do not pad a short prompt just
   to cross the boundary; improve the actual contract or accept no cache.
3. Reuse one stable `prompt_cache_key` for requests with the same exact prefix.
4. Partition only when a prefix/key approaches Azure's roughly 15-request per
   minute guidance.
5. Execute one request at a time within each cache-key lane. Different keys may
   run in parallel.

The fifth rule and the default partition count are FLI scheduling choices, not
Azure requirements. Registry jobs use eight deterministic lanes instead of the
former 64 so a normal cohort can warm each lane; each lane is serial. Audience
routing uses one prompt-level key and cache-first refresh defaults of one item
and one day at a time. Insight refreshes use one serial lane per audience prompt
and may run the two distinct audience lanes in parallel. Operators may override
worker counts when throughput matters more than cache locality, then must judge
the result from telemetry.

Azure rejects `prompt_cache_key` values longer than 64 characters. The shared
key helper preserves readable keys when they fit and compacts longer
namespace/version identities into a stable hash-backed key. All sharded callers
use that helper. `group_prompt_cache_lanes` is the shared scheduler primitive.

No output-token value enables prompt caching. In particular,
`max_tokens=16384` is not an Azure requirement. Production output budgets remain
owned by the task's quality contract. The canary's deliberately small
`max_output_tokens=64` only limits diagnostic cost; an `incomplete` response
still contains valid prompt-cache usage telemetry.

## Repeatable Canary

Run the different-input canary without prompts:

```bash
fli prompt-cache-canary --no-input
```

It tests Luna and Terra by default, uses a fresh per-execution routing key,
ignores the first request as warm evidence, changes the suffix on every request
so LiteLLM's full-response cache cannot create a false pass, and emits one JSON
document. `data.models[].calls[]` records `input_tokens`, `cached_tokens`,
`cache_write_tokens`, response status, duration, and reported cost. Exit `0`
means every selected model produced at least one post-first-request cache read;
exit `1` with `E_CACHE_NOT_OBSERVED` is a retryable no-hit result. Invalid
usage, authentication, network, and timeout/interruption use exits `2`, `3`,
`4`, and `5`. Use repeated `--model` flags to narrow or extend the probe, and
`--plain` only for human inspection.

## Source Guidance

- [OpenAI GPT-5.6 migration guidance](https://developers.openai.com/api/docs/guides/latest-model#update-api-and-model-parameters)
- [OpenAI model choice for simple agent workloads](https://developers.openai.com/tracks/building-agents#how-to-choose)
- [Azure prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)
- [Azure GPT-5.6 Responses cache incident and fix](https://learn.microsoft.com/en-in/answers/questions/5942997/gpt-5-6-implicit-prompt-caching-and-explicit-promp)
