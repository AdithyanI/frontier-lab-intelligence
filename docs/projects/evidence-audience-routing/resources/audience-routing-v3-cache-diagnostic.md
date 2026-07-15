# Audience Routing v3 Cache Diagnostic

Date: 2026-07-15

## Contract change

- Runtime prompt: `src/fli/prompts/audience_routing_v3.txt`
- Prompt SHA-256: `0fb63b9f2106a3dba3412ae4380f359c8ccd36010422e879bd75d2286caf0fd0`
- Stable prompt size: 8,188 characters; 1,180 whitespace-delimited words; rough
  characters/4 estimate of 2,047 tokens.
- Audience reasons: usually three to four sentences; no schema maximum length.
- Reaction input: no minimum or maximum character count. The rank-1 packet now
  includes “Grok 4.5 is Opus class for browser use.”
- Catalog routing: 32 deterministic cache lanes, with only one in-flight request
  per lane.

## Controlled v3 results

All calls used `gpt-5.6-luna`, medium reasoning, the same prompt hash, and the
same diagnostic run tags.

| Request | Input tokens | Azure cached tokens | LiteLLM response-cache hit | Proxy spend | Duration |
| --- | ---: | ---: | --- | ---: | ---: |
| Rank 1, cold | 1,920 | 0 | no | $0.003330 | 3.470s |
| Rank 1, exact complete repeat | 1,920 | 0 | yes | $0.000000 | 0.145s |
| Satya, same stable prefix but different evidence | 3,256 | 0 | no | $0.005290 | 3.758s |

The exact repeat was served by LiteLLM's Redis response cache. Its spend record
has `cache_hit=True`, zero duration, and zero spend. The response still carries
the original `x-litellm-response-cost` header, so the application-level header
value is not authoritative for a full-response cache hit; the persisted
LiteLLM spend record is the actual operational evidence.

The Satya request is the cache behavior the catalog needs: different variable
evidence after the same stable prompt and schema. It received no Azure prefix
cache read.

## Known-working-path control

To distinguish a v3 prompt problem from an upstream problem, two fresh variable
inputs were sent through the repository's previously successful
`envelope-triage-v2.2` request path. That stable prompt is 1,670 words and had
read 103,936 cached tokens across the July 14 64-envelope Luna-medium run.

| Request | Total input tokens | Azure cached tokens | Proxy spend | Provider duration |
| --- | ---: | ---: | ---: | ---: |
| Known path, new input 1 | 3,203 | 0 | $0.003875 | 3.556s |
| Known path, new input 2 | 3,065 | 0 | $0.003713 | 27.996s |

Both requests reached the same single Azure deployment. LiteLLM's transform
inspection showed that `prompt_cache_key`, `prompt_cache_retention="24h"`, the
complete instructions, and the structured-output schema were forwarded
unchanged, with no retry or fallback.

## Conclusion

The miss is not caused by the 1,024-token threshold, v3 prompt length, cache-key
instability, multiple deployments, parallel calls within one lane, or a dropped
adapter field. Azure's GPT-5.6 Responses prompt-prefix cache is currently
intermittent or regressed on this deployment. Microsoft documented the same
Responses-specific failure in July and reported it resolved on July 13; this
live control shows that the behavior is not reliable again on July 15.

Keep the proven request shape, 32 stable lanes, sequential per-lane scheduling,
and cache telemetry. Do not pad the prompt or claim prefix-cache savings. Exact
reruns still benefit from LiteLLM's full-response cache, while different catalog
items must be costed as uncached until `cached_tokens` becomes nonzero again.

References:

- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Azure prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)
- [Azure GPT-5.6 Responses cache incident](https://learn.microsoft.com/en-in/answers/questions/5942997/gpt-5-6-implicit-prompt-caching-and-explicit-promp)
