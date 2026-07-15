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

One limitation was identified during the clean-routing review: the v3 Rank 1
and Satya requests followed their normal event-derived 32-shard keys, so that
pair alone did not prove reuse within one cache lane. The later GPT-5.5 control
did force one shared key, but the Luna conclusion needed the same exact test.

## Same-lane v4 follow-up

A minimal follow-up used `audience-routing-v4` with two different July 12
evidence packets and the exact same forced cache key:
`fli:audience-routing:audience-routing-v4:diagnostic-00`. The calls were fully
sequential. The stable prompt was 8,284 characters / 1,201 words and measured
1,516 tokens with `o200k_base`, comfortably above the 1,024-token eligibility
threshold before the stable structured-output schema is counted. Request input
hashes were different, so the
second response could not be a LiteLLM exact-response replay.

| Request | Input tokens | Azure cached tokens | Proxy spend | Duration |
| --- | ---: | ---: | ---: | ---: |
| Same lane, evidence 1 | 3,289 | 0 | $0.005065 | 4.617s |
| Same lane, evidence 2 | 1,953 | 0 | $0.003561 | 2.995s |

Both requests reached `gpt-5.6-luna` and reported no cache-write telemetry.
This closes the sharding ambiguity: even within one explicit key, after the
cold request completed, Azure did not report a prefix read for the different
input.

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

### Fresh GPT-5.5 v4 retry

Adi asked for a live retry because GPT-5.5 prompt caching is otherwise known to
work. Two fresh July 12 packets used the current `audience-routing-v4` prompt,
the same structured-output schema, and one new forced key,
`fli:audience-routing:v4:gpt55-retry-00`. The calls were fully sequential and
their variable-input hashes differed.

| Request | Total input tokens | Azure cached tokens | Proxy spend | Duration |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.5 v4, cold | 3,289 | 0 | $0.027905 | 7.407s |
| GPT-5.5 v4, same prefix and key | 1,953 | 0 | $0.021825 | 12.364s |

The fresh retry also produced no provider cache read or cache-write telemetry.
This reproduces the miss on GPT-5.5 with the exact current prompt and removes
the remaining concern that the earlier result was specific to v3.

## GPT-5.4 mini positive control

The exact v4 canary was then repeated through `gpt-5.4-mini`, again with two
different packets, fully sequential calls, and one fresh forced key,
`fli:audience-routing:v4:gpt54mini-canary-00`.

| Request | Total input tokens | Azure cached tokens | Proxy spend | Duration |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.4 mini v4, cold | 3,289 | 0 | $0.00390225 | 4.873s |
| GPT-5.4 mini v4, same prefix and key | 1,953 | 1,280 | $0.00202725 | 3.334s |

This is a successful provider prefix-cache read. It proves that the current v4
prompt, structured schema, explicit cache key, sequential request shape, and
shared LiteLLM Responses path are cacheable. Neither call reported explicit
cache-write tokens, so that field's absence is not evidence that no cache entry
was created. The remaining failure is localized to the current GPT-5.5 and
GPT-5.6 routes or their backing Azure deployments rather than the application
request contract or shared proxy in general.

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

The miss is not caused by the 1,024-token threshold, prompt length, cache-key
instability, sharding, parallel calls within one lane, a dropped adapter field,
or the application request shape. GPT-5.4 mini returned 1,280 cached tokens for
the identical v4 control through the same proxy, while GPT-5.5 and GPT-5.6
returned zero. The remaining failure is therefore specific to those model
routes or their backing Azure deployments. Microsoft documented a GPT-5.6
Responses-specific failure in July and reported it resolved on July 13; these
live controls show that reliable caching is still not observable on the current
5.5/5.6 routes on July 15.

The production follow-up chose GPT-5.4 mini with one prompt-level key, no
sharding, no padding, and no retention override. An implicit-only two-call
control returned no read; the same production path with the single stable key
read 1,280 tokens on call two. The nine-day top-10 run then produced 88 cache
hits across 90 sequential requests and read 152,576 of 305,600 input tokens
from cache. Keep that minimal contract and telemetry. Partition a key only if
future throughput approaches the documented routing threshold; do not add
shards speculatively.

References:

- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Azure prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)
- [Azure GPT-5.6 Responses cache incident](https://learn.microsoft.com/en-in/answers/questions/5942997/gpt-5-6-implicit-prompt-caching-and-explicit-promp)
- [LiteLLM 1.92.0 release](https://github.com/BerriAI/litellm/releases/tag/v1.92.0)
- [LiteLLM 1.92 Redis replay fix](https://github.com/BerriAI/litellm/pull/28158)
- [LiteLLM Chat Completions parameter issue](https://github.com/BerriAI/litellm/issues/33184)
