# Combined Registry Evaluation — Two-Entity Cache Calibration

Date: 2026-07-12

## Purpose

Exercise the new one-request kind + Registry-status contract through the shared
LiteLLM endpoint using Azure-hosted `gpt-5.6-luna` at high reasoning effort.
The run was read-only: it did not change entity kind, Registry status, channels,
or rejection state.

Both requests used the exact same versioned instruction prefix, structured
output schema, optional `web_search` tool definition, and stable cache-routing
key:

```text
fli:registry-evaluation:registry-evaluation-v1:shard-55
```

Each request received one current X profile plus 20 recent authored posts.
Replies and retweets were excluded by the existing provider adapter.

## Results

| Handle | Kind | Registry status | Web actions | Input tokens | Cached tokens | Cache writes | Output tokens | LiteLLM cost |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `@openai` | organization | active | 0 | 7,993 | 0 | 0 | 159 | $0.008947 |
| `@janleike` | person | active | 0 | 7,728 | 0 | 0 | 180 | $0.008808 |

Total proxy-reported model cost: **$0.017755**.

The two profile/post provider reads were bounded to these exact identities.
Their provider-side cost was not returned by the adapter, so it is not folded
into the LiteLLM total.

### `@openai`

- Kind reason: The account speaks for OpenAI as an institutional AI research
  and product organization, using collective language and announcing
  company-wide models, products, programs, and infrastructure.
- Registry-status reason: OpenAI is a direct frontier-AI actor producing
  recurring, original, decision-useful information on frontier models, agents,
  evaluations, safety, cybersecurity, developer infrastructure, and AI chips.

### `@janleike`

- Kind reason: The account represents Jan Leike as an individual researcher,
  using personal first-person statements and describing his work history at
  Anthropic, OpenAI, and DeepMind.
- Registry-status reason: He is directly involved in frontier-AI alignment and
  safety research at Anthropic and repeatedly shares original results, model
  evaluations, interpretability findings, scalable oversight work, and
  safety-relevant technical developments.

## Cache finding

No cache hit was observable. The second request shared the same long prefix and
the same `prompt_cache_key`, but LiteLLM returned `cached_tokens=0`. The first
request also returned zero `cache_write_tokens`; Azure may not expose the newer
OpenAI cache-write counter through this route, but the second request's zero
cached-token count is sufficient to say that this calibration did not prove a
cache read.

This is not evidence that the prompt structure is ineligible. Both OpenAI and
Microsoft document the same core requirements: at least 1,024 tokens, an exact
shared prefix, and stable cache routing. The request satisfied those visible
requirements. Plausible remaining causes include LiteLLM not forwarding the
cache key on this Responses route, the proxy routing the two calls to different
Azure deployments, or provider cache population not being immediately reusable.
Do not claim cache savings until a later controlled run reports nonzero
`cached_tokens`.

Official references:

- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Azure OpenAI prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)

## Next diagnostic

Inspect the two tagged LiteLLM spend/log records for upstream deployment IDs and
forwarded request parameters. Do not run another paid calibration until that
read-only proxy inspection identifies a concrete change to test.
