# Model Routing and Prompt Caching

Last verified: 2026-07-14

## Current Policy

Use `gpt-5.6-luna` as the default efficient model for bounded structured
classification, routing, extraction, and Registry evaluation. This is an
accuracy-first default, not a rule that the cheapest model or lowest reasoning
effort always wins. Keep `gpt-5.6-terra` for the web-grounded relevance audit,
where broader research quality is the evaluated boundary.

| Boundary | Default model | Reasoning effort | Rationale |
| --- | --- | --- | --- |
| Structural entity kind | `gpt-5.6-luna` | `medium` | Existing evaluated classifier contract. |
| Feed envelope triage | `gpt-5.6-luna` | `medium` | Simple output, but false drops are costly; the 64-item migration cohort matched the accepted mini baseline 64/64. |
| Cited insight extraction | `gpt-5.6-luna` | `medium` | Requires claim synthesis plus exact quotation; the five-item migration oracle passed citation verification 5/5. |
| Missing-bio identity research | `gpt-5.6-luna` | `high` | Multi-source grounded identity resolution needs more checking. |
| Combined kind + Registry decision | `gpt-5.6-luna` | `high` | Independent structural and admission decisions with optional search. |
| Full web-grounded relevance audit | `gpt-5.6-terra` | `high` | Complex research boundary; not part of the Luna-for-efficient-work migration. |

Do not lower reasoning effort merely to reduce spend. OpenAI recommends using
the lowest effort that still meets the task, preserving the prior effort as a
migration baseline, and testing one level lower. That comparison matters here:
Luna-low agreed with the accepted mini-medium triage decisions on 63/64 current
envelopes but dropped a post that named a specific Thinking Machines Lab essay.
Luna-medium agreed 64/64, so `medium` remains the triage default.

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
Revisit the adapter when the shared route is migrated or Azure documents and
proves the newer explicit-cache contract.

The 2026-07-14 migration checks established:

- an exact-repeat Luna canary read 1,792 cached tokens from a 1,990-token input
  when `24h` was explicit;
- the 64-envelope Luna-medium triage run had 58 cache-hit requests and read
  103,936 cached tokens from 168,022 input tokens (61.86%);
- the five-item Luna extraction oracle recorded zero cache reads, so eligibility
  is never treated as proof of a hit.

Keep stable 1,024+ token content first, use deterministic sharded
`prompt_cache_key` lanes, limit each lane to one in-flight request, and record
`cached_tokens`, `cache_write_tokens`, and LiteLLM's reported response cost.
GPT-5.6 cache writes can cost more than ordinary input, so cache telemetry—not
the presence of a cache parameter—is the cost evidence.

## Source Guidance

- [OpenAI GPT-5.6 migration guidance](https://developers.openai.com/api/docs/guides/latest-model#update-api-and-model-parameters)
- [OpenAI model choice for simple agent workloads](https://developers.openai.com/tracks/building-agents#how-to-choose)
- [Azure prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)
- [Azure GPT-5.6 Responses cache incident and fix](https://learn.microsoft.com/en-in/answers/questions/5942997/gpt-5-6-implicit-prompt-caching-and-explicit-promp)
