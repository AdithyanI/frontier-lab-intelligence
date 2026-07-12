# Combined Registry Evaluation — Two-Entity Cache Calibration

Date: 2026-07-12

## Purpose

Exercise the new one-request kind + Registry-status contract through the shared
LiteLLM endpoint using Azure-hosted `gpt-5.6-luna` at high reasoning effort.
The run was read-only: it did not change entity kind, Registry status, channels,
or rejection state.

This run used the initial v1 model-facing names `registry_status=active` and
`registry_status_reason`. Immediately after reviewing the terminology, the
current v2 contract renamed the recommendation to
`registry_decision=keep | remove | review` and
`registry_decision_reason`. Persisted states such as active and rejected remain
an application concern; the historical results below are preserved as emitted.

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
requirements. A subsequent read-only LiteLLM inspection established that the
proxy forwarded `prompt_cache_key` unchanged and that both calls used the same
model group, deployment ID, and Azure Responses endpoint. The remaining result
is therefore an upstream Azure cache miss, not a missing FLI request field or a
cross-deployment LiteLLM route. This matches the earlier project canary where
Azure Chat caching produced hits but Azure Responses caching did not benefit the
web-grounded relevance workload. Do not claim cache savings until a later
controlled run reports nonzero `cached_tokens`.

LiteLLM's configured Redis cache is a different mechanism: it caches complete
responses by complete request hash. The two entity inputs correctly produced
different LiteLLM response-cache hashes, so that cache cannot reuse only the
shared instruction prefix.

Official references:

- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Azure OpenAI prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)

## Next diagnostic

Keep logging `cached_tokens` and `cache_write_tokens` for every combined
evaluation. Treat Azure prefix caching as opportunistic on the Responses route;
do not add the old WIN Chat-Completions `max_tokens` workaround because current
Responses documentation does not require it and WIN never regression-tested it.
Do not run another paid calibration unless it tests one concrete provider-side
change, such as documented Azure support for GPT-5.6 explicit breakpoints.
