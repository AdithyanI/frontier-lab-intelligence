# Prompt Caching

Last reviewed: 2026-07-28

Last live-verified: 2026-07-28

This is the single source of truth for prompt caching in Frontier Lab
Intelligence. Read it before changing cache keys, prompt layout, model
concurrency, Azure/LiteLLM cache parameters, or cache telemetry.

Model selection and reasoning-effort policy remain in
[`model-routing.md`](model-routing.md). Cross-stage cost evidence remains in
[`tokenomics.md`](tokenomics.md).

## Current Conclusion

Prompt caching has produced positive reads for `gpt-5.6-luna`,
`gpt-5.6-terra`, and `gpt-5.6-sol` through the repository's shared
Azure-backed LiteLLM Responses route. It is best-effort, model-specific, and
not guaranteed on every eligible request.

The latest different-input canary produced:

| Model | Cached tokens by call | Post-first-request hits |
| --- | --- | --- |
| `gpt-5.6-luna` | `0, 0, 0` | 0 of 2 |
| `gpt-5.6-terra` | `0, 1280, 1280` | 2 of 2 |

The first request is deliberately excluded from the pass criterion because
Azure may already hold the same prefix. A 27 July canary previously observed
3/4 Luna and 4/4 Terra warm hits, proving that both routes can cache. The 28
July result shows that current cache behavior can differ by model even with the
same request contract. Use measured hit rates for cost estimates and retain an
uncached upper bound.

## Production Contract

Every cacheable workflow must:

1. Put identical instructions, examples, tools, and schemas before variable
   evidence.
2. Have an exact shared prefix of at least 1,024 tokens. Do not add meaningless
   padding solely to cross the threshold.
3. Reuse one stable `prompt_cache_key` for requests with the same exact prefix.
4. Keep Azure keys at or below 64 characters by using
   `fli.llm_responses.sharded_prompt_cache_key`.
5. Partition a high-volume prefix only when traffic approaches Azure's roughly
   15-request-per-minute guidance for a prefix/key combination.
6. For a bounded cache-first batch, complete one request before parallel
   fan-out on the same stable prefix. Keep the fan-out bounded and use
   deterministic key partitions if measured traffic approaches the provider's
   per-key guidance. Workloads that do not need burst throughput may remain
   serial.
7. Record Responses `usage.input_tokens_details.cached_tokens`,
   `cache_write_tokens` when reported, total input/output tokens, and LiteLLM's
   response-cost header.

Items 1–5 reflect Azure's cache guidance and constraints. Serial execution
inside a lane and the number of default lanes are FLI scheduling choices. They
improve cache locality and make behavior easier to inspect; Azure does not
mandate a fixed lane count.

No output-token value enables prompt caching. In particular,
`max_tokens=16384` is not an Azure requirement. Production output budgets are
owned by each task's quality contract.

## Azure/LiteLLM Adapter

All application model calls go through the shared LiteLLM endpoint. GPT-5.6
Responses callers obtain the Azure-specific cache control from
`fli.llm_responses.litellm_prompt_cache_kwargs`:

```python
{"prompt_cache_retention": "24h"}
```

Do not scatter this field through individual workflows or send it alongside
OpenAI-native cache controls. OpenAI's native API now documents
`prompt_cache_options.ttl`; the current Azure route uses
`prompt_cache_retention`. Azure does not currently support OpenAI's explicit
`prompt_cache_options` or `prompt_cache_breakpoint` controls.

Revisit the adapter only when the shared route changes or a different Azure
contract is both documented and live-proven.

## Workload Design

| Workload | Stable prefix/key strategy | Execution |
| --- | --- | --- |
| Audience routing | One prompt-version key | One day per worker; item calls remain cache-first inside a day |
| Company-aware Investment analysis | One prompt-version key | Complete one warm Development, then bounded parallel fan-out; each memo continuation chains from its own response ID |
| Per-Event Insights | One key per audience prompt | One serial lane per audience; the two audience lanes may run concurrently |
| Registry evaluation | Eight deterministic entity partitions for new freezes | Serial within each partition; parallel across partitions |
| Missing-bio identity context | Eight deterministic entity partitions | Serial within each partition; parallel across partitions |
| Registry relevance audit | Eight deterministic entity partitions | Serial within each partition; parallel across partitions |

The Registry previously used up to 64 partitions. Eight is the current
amortization/throughput trade-off, not a provider constant. Existing frozen run
databases keep their historical keys and remain resumable; new freezes use the
current partition count.

Implementation ownership:

- shared adapter, key length enforcement, and lane grouping:
  [`src/fli/llm_responses.py`](../../src/fli/llm_responses.py);
- repeatable provider canary:
  [`src/fli/diagnostics/prompt_cache.py`](../../src/fli/diagnostics/prompt_cache.py);
- Registry lane runners:
  [`src/fli/registry/evaluation_runs.py`](../../src/fli/registry/evaluation_runs.py)
  and [`src/fli/registry/relevance.py`](../../src/fli/registry/relevance.py);
- audience-routing cache-first defaults:
  [`src/fli/routing/runs.py`](../../src/fli/routing/runs.py);
- company-aware Investment warm/fan-out loop:
  [`src/fli/insights/investment_agent.py`](../../src/fli/insights/investment_agent.py);
- per-audience Insight lanes:
  [`src/fli/insights/cli.py`](../../src/fli/insights/cli.py).

## Repeatable Canary

Run the real different-input probe without interaction:

```bash
fli prompt-cache-canary --no-input
```

The command tests Luna and Terra by default. It uses one fresh routing key per
model and changes the variable suffix on every request, preventing LiteLLM's
exact full-response cache from creating a false pass. The first call is retained
as telemetry but ignored when deciding whether a model produced a warm read.

The default output is one JSON document with:

- `schema_version`, `command`, `status`, `data`, `error`, and `meta`;
- per-call input, cached, cache-write, and output tokens;
- response status, latency, response model, and reported cost;
- per-model warm-request and warm-hit counts.

Exit behavior:

| Exit | Meaning |
| --- | --- |
| `0` | Every selected model produced at least one post-first-request cache read |
| `1` | `E_CACHE_NOT_OBSERVED`; retryable because caching is best-effort |
| `2` | Invalid command usage |
| `3` | Shared LiteLLM authentication failure |
| `4` | Endpoint/network failure |
| `5` | Timeout or interruption |

Use repeated `--model` flags to select specific aliases. `--plain` is available
for human inspection; JSON remains the automation contract. The canary's
`max_output_tokens=64` only bounds diagnostic cost. An `incomplete` response
still carries valid input-token cache telemetry.

## Reading Telemetry Correctly

The only proof of reusable-prefix caching is a positive
`usage.input_tokens_details.cached_tokens` value on the Responses result.

- `cached_tokens=0` means that request did not report a reusable-prefix read.
  It does not prove the model or deployment lacks cache support.
- `cache_write_tokens=0` is normal on the current Azure path because Azure does
  not separately report cache writes here.
- An exact request may return instantly from LiteLLM's separate Redis
  full-response cache while still showing `cached_tokens=0`. That is not
  reusable-prefix caching and does not help a different input.
- LiteLLM 1.92.0 may replay the original response-cost header on a
  full-response cache hit even when persisted proxy spend is zero. Use
  persisted proxy records when reconciling that special case.

## Incident History

- **2026-07-14:** Luna produced positive cache reads with explicit 24-hour
  retention. A 64-envelope Luna-medium classification run had 58 hit requests
  and read 103,936 cached tokens from 168,022 input tokens.
- **2026-07-15:** several eligible Luna and GPT-5.5 controls returned zero
  reads even though LiteLLM forwarded the key, retention, instructions, and
  schema. GPT-5.4-mini positive controls and a later 88/90-hit production run
  proved the shared Responses request shape was valid. This established the
  provider behavior as intermittent rather than an application formatting
  failure.
- **2026-07-27:** the current Luna/Terra different-input canary passed with 3/4
  and 4/4 post-first-request hits. This superseded the temporary conclusion
  that Luna should always be treated as uncached.
- **2026-07-28:** the sequential Luna/medium `audience-routing-v13` July 21
  top-10 pass reported zero cache reads across ten eligible requests despite a
  1,700-token stable prompt, one stable key, an unchanged schema, and 24-hour
  retention. A same-session different-input diagnostic then observed 0/2 Luna
  warm hits and 2/2 Terra warm hits. This is a model-specific best-effort miss,
  not a prompt-layout failure. The subsequent sequential top-100 pass also
  reported zero reads across 97 eligible requests. Retain the uncached cost
  bound and do not change model solely to chase caching.
- **2026-07-28:** the successor Luna/medium `audience-routing-v14` July 5–21
  top-100 pass completed 1,647 requests with zero failures. The Azure-backed
  route reported 1,558 cache-hit requests, 2,791,936 cached tokens from
  6,990,192 input tokens, 46,924 cache-write tokens, and $7.079129. This
  confirms that the same stable request layout can obtain substantial reuse
  in a later bounded-parallel production pass even after an earlier run
  observed no reads; cache telemetry remains the authority for each run.
- **2026-07-28:** the Sol/xhigh `investment-agent-v8` July 19–20 top-ten
  production run completed one warm request before bounded parallel fan-out.
  All 20 targets completed, with 272,384 cached tokens from 712,663 input
  tokens and $3.693917 reported cost. This is direct production proof that the
  Sol route can reuse the stable Investment prefix. The parallel Luna routing
  refresh for those dates still reported zero cache reads, reinforcing that a
  warm layout enables reuse but cannot guarantee it for every model or batch.
- **2026-07-28:** the corrected Sol/xhigh Investment cohorts for July 19–21
  completed 30 audience-routed targets with 472,576 cached tokens from
  1,386,679 input tokens and $7.740683 reported cost. One parallel request
  returned HTTP 499 before a Response ID was available; an exact single-target
  rerun succeeded. The runner now disables opaque SDK retries for this path,
  retries transient Responses failures at most three times, and records the
  failed request, status, headers, body, delay, and attempt in the durable
  trace. This retry policy is transport recovery, not prompt-cache behavior.

Historical build-log entries remain immutable evidence of what was observed at
the time. Their earlier zero-hit conclusions are incident history, not the
current operational status.

## Troubleshooting Checklist

When cache reads disappear:

1. Run `fli prompt-cache-canary --no-input` and retain its JSON output.
2. Retry once before escalating; a single warm miss is expected occasionally.
3. Confirm the request uses the same model alias, exact instructions, tools,
   schema, and prompt cache key across the compared calls.
4. Confirm variable evidence comes after the 1,024+ token shared prefix.
5. Confirm the cache key is no longer than 64 characters.
6. Confirm GPT-5.6 requests receive `prompt_cache_retention="24h"` from the
   shared adapter.
7. Inspect Responses `input_tokens_details.cached_tokens`; do not infer a hit
   from latency or LiteLLM's full-response cache.
8. Check per-key request rate before adding partitions. Add stable lanes only
   for measured routing pressure; do not create per-item keys.
9. Do not change reasoning effort, prompt quality, or production output limits
   merely to chase a cache hit.
10. If repeated different-input canaries miss while the request contract is
    unchanged, record it as an Azure/LiteLLM operational regression and retain
    the uncached cost bound.

## Provider References

- [Azure prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)
- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
