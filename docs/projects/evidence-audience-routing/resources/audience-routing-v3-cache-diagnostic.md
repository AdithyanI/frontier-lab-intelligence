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

## GPT-5.5 control

At Adi's request, the same v3 different-input test was repeated through the
available `gpt-5.5` Azure Responses deployment. Both requests explicitly used
the same prompt cache key and `prompt_cache_retention="24h"`.

| Request | Total input tokens | Azure cached tokens | Proxy spend | Duration |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.5 rank 1, cold | 1,920 | 0 | $0.026820 | 10.419s |
| GPT-5.5 Satya, same prefix | 3,256 | 0 | $0.031250 | 8.814s |

GPT-5.5 also failed to reuse the different-input prefix. This broadens the
diagnosis from a Luna-specific regression to the Azure Responses caching path
or its current interaction through the shared proxy.

## LiteLLM version audit

The shared proxy is running LiteLLM 1.92.0. The automatic stable-version
workflow committed that image on July 12, and Azure changed the live container
to the 1.92.0 image at 19:57 UTC that day. The successful July 14 Feed-triage
run therefore already used 1.92.0; the version upgrade cannot by itself explain
why the same route stopped returning cache reads on July 15.

The 1.91.2-to-1.92.0 source diff does not change Azure Responses handling for
`prompt_cache_key` or `prompt_cache_retention`. Both fields remain declared
Responses parameters and are passed through the Azure Responses transform. The
only 1.92 release item labelled as a caching fix repairs replay of LiteLLM's own
Redis full-response cache for a streamed Responses-to-Chat bridge; it does not
alter provider-side prompt-prefix caching. A newly reported LiteLLM issue about
silently dropped `prompt_cache_key` values applies to the Chat Completions
client path, not this Responses path, and the live transform inspection already
proves that this request retained both fields.

The sibling LiteLLM repository does have a daily workflow that automatically
selects the newest stable release, commits the Docker image bump, and triggers
Azure deployment. No rollback or workflow change was made during this audit.
The current newest stable release remains 1.92.0; 1.93 and 1.94 are prerelease
channels.

## Conclusion

The miss is not caused by the 1,024-token threshold, v3 prompt length, cache-key
instability, parallel calls within one lane, a dropped adapter field, or the
1.92.0 image upgrade alone. Both
GPT-5.5 and GPT-5.6 failed the different-input test, so the Azure Responses
prompt-prefix cache or its current proxy interaction is not functioning
reliably. Microsoft documented a GPT-5.6 Responses-specific failure in July and
reported it resolved on July 13; these live controls show that reliable caching
is still not observable on July 15.

Keep the proven request shape, 32 stable lanes, sequential per-lane scheduling,
and cache telemetry. Do not pad the prompt or claim prefix-cache savings. Exact
reruns still benefit from LiteLLM's full-response cache, while different catalog
items must be costed as uncached until `cached_tokens` becomes nonzero again.

References:

- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Azure prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)
- [Azure GPT-5.6 Responses cache incident](https://learn.microsoft.com/en-in/answers/questions/5942997/gpt-5-6-implicit-prompt-caching-and-explicit-promp)
- [LiteLLM 1.92.0 release](https://github.com/BerriAI/litellm/releases/tag/v1.92.0)
- [LiteLLM 1.92 Redis replay fix](https://github.com/BerriAI/litellm/pull/28158)
- [LiteLLM Chat Completions parameter issue](https://github.com/BerriAI/litellm/issues/33184)
