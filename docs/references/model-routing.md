# Model Routing and Prompt Caching

Last verified: 2026-07-15

## Current Policy

Use `gpt-5.6-luna` as the default efficient model for bounded structured
classification, routing, and Registry evaluation. This is an
accuracy-first default, not a rule that the cheapest model or lowest reasoning
effort always wins. Keep `gpt-5.6-terra` for the web-grounded relevance audit
and the current audience Insight calibration, where broader synthesis quality
is the active boundary.

| Boundary | Default model | Reasoning effort | Rationale |
| --- | --- | --- | --- |
| Structural entity kind | `gpt-5.6-luna` | `medium` | Existing evaluated classifier contract. |
| Evidence audience routing | `gpt-5.4-mini` | `high` | The current v9 nine-day top-100 run completed 900/900 with zero failures: 259 both, 100 Engineering-only, 133 Investment-only, and 408 neither. All requests were cache-eligible; 805 reported cache reads totaling 1,442,560 tokens. The v9 semantic input is first-party only. A prior same-two-packet comparison found xhigh unchanged on decisions and only marginally better on caveats while using 5.4× the hidden reasoning/output tokens. |
| Audience Insight generation | `gpt-5.6-terra` | `high` | Quality-first default confirmed by Adi. The Investment and Engineering v4 prompts contain roughly 1.43k and 1.46k stable instruction tokens and use separate stable cache keys. In the current six-request sample, the first request for each audience warmed its prefix and all four later requests reported 1,280 cached tokens each (5,120 total). A Luna/high control produced coherent decisions but zero cache reads across six calls and one less-polished title, so it is not the active default. |
| Missing-bio identity research | `gpt-5.6-luna` | `high` | Multi-source grounded identity resolution needs more checking. |
| Combined kind + Registry decision | `gpt-5.6-luna` | `high` | Independent structural and admission decisions with optional search. |
| Full web-grounded relevance audit | `gpt-5.6-terra` | `high` | Complex research boundary; not part of the Luna-for-efficient-work migration. |

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
Revisit the adapter when the shared route is migrated or Azure documents and
proves the newer explicit-cache contract.

The 2026-07-14 migration checks established:

- an exact-repeat Luna canary read 1,792 cached tokens from a 1,990-token input
  when `24h` was explicit;
- the historical 64-envelope Luna-medium classification run had 58 cache-hit
  requests and read
  103,936 cached tokens from 168,022 input tokens (61.86%);
- the five-item Luna extraction oracle recorded zero cache reads, so eligibility
  is never treated as proof of a hit.

A 2026-07-15 control found that the same Azure Responses deployment had
regressed or become intermittent again. A cache-eligible audience-routing
prefix returned zero reads for different evidence, and two fresh variable
inputs through the previously successful 1,670-word Feed-triage prefix also
returned zero reads. LiteLLM's request transform forwarded the key, `24h`
retention, instructions, and structured schema unchanged to one deployment.
Treat this as an upstream operational limitation, not a reason to pad prompts
or change classification quality. The exact diagnostic is recorded in
`docs/projects/evidence-audience-routing/resources/audience-routing-v3-cache-diagnostic.md`.
The same v3 different-input control also returned zero reads on the available
GPT-5.5 Azure Responses deployment despite an explicit shared key and `24h`
retention, so the live failure is not isolated to the Luna model alias.

A same-day positive control localized the failure further. The exact current
v4 request shape sent through `gpt-5.4-mini` returned 1,280 cached tokens on the
second different-input call. The shared LiteLLM Responses path, v4 prompt,
schema, and explicit cache key are therefore valid; the observed miss belongs
to the current GPT-5.5/GPT-5.6 routes or their backing Azure deployments, not
the application contract or shared proxy in general.

The production follow-up removed event sharding, per-item keys, padding, and
the retention override. GPT-5.4 mini received one stable prompt-level key and
ran sequentially. An implicit-only two-call test missed twice; the single-key
test read 1,280 tokens on call two. The nine-day top-10 run then returned 88
cache-hit requests out of 90 and read 152,576 of 305,600 input tokens from the
provider cache. This is the current proven audience-routing contract.

The accepted v7 prompt revision was calibrated on exactly five disputed or
borderline packets. Its cold request missed, while the next four requests each
read 1,792 cached tokens. The run read 7,168 of 12,482 input tokens (57.43%)
from the provider cache and cost $0.0256731. The result confirms that the same
one-key sequential contract remains effective after a prompt version change.

A final Luna-specific control removed the remaining sharding ambiguity: two
different v4 evidence packets ran sequentially with the exact same forced
cache key and an 8,284-character / 1,516-token stable prefix. The 3,289-token cold request
and 1,953-token follow-up both returned zero cached tokens. Catalog jobs must
therefore be budgeted as uncached when using the GPT-5.6 Luna route; keep
telemetry and treat any future reads as measured upside rather than a
prerequisite. Do not switch models for cache savings alone—the routing model
decision remains accuracy-first.

The proxy also has a separate Redis full-response cache. An exact complete
request repeat can therefore return instantly at zero proxy spend while still
showing `cached_tokens=0`; that is not reusable-prefix caching and does not help
different catalog items. On such a full-response hit, LiteLLM 1.92.0 replays
the original `x-litellm-response-cost` header even though its persisted spend
record is zero, so use the persisted proxy record when reconciling that case.

Keep stable 1,024+ token content first, reuse one stable `prompt_cache_key` for
requests sharing that prefix, and record `cached_tokens`, `cache_write_tokens`,
and LiteLLM's reported response cost. Partition traffic only when one key
approaches the documented roughly 15-request-per-minute routing threshold;
do not introduce shards for low-rate sequential work.
GPT-5.6 cache writes can cost more than ordinary input, so cache telemetry—not
the presence of a cache parameter—is the cost evidence.

Azure rejects `prompt_cache_key` values longer than 64 characters. The shared
key helper preserves readable keys when they fit and compacts longer
namespace/version identities into a stable hash-backed key. All callers must
use that helper rather than constructing cache keys directly.

## Source Guidance

- [OpenAI GPT-5.6 migration guidance](https://developers.openai.com/api/docs/guides/latest-model#update-api-and-model-parameters)
- [OpenAI model choice for simple agent workloads](https://developers.openai.com/tracks/building-agents#how-to-choose)
- [Azure prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)
- [Azure GPT-5.6 Responses cache incident and fix](https://learn.microsoft.com/en-in/answers/questions/5942997/gpt-5-6-implicit-prompt-caching-and-explicit-promp)
