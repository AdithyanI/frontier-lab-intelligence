# Model Routing

Last verified: 2026-07-28

For the cross-stage cost summary and X-provider units, see
[`tokenomics.md`](tokenomics.md).

## Current Policy

Use `gpt-5.6-luna` as the default efficient model for bounded structured
classification and Registry evaluation. This is an accuracy-first default,
not a rule that the cheapest model or lowest reasoning effort always wins.
The current daily path uses `gpt-5.6-luna` for audience routing,
`gpt-5.6-sol` for company-aware Investment analysis, and `gpt-5.6-sol` for
surface-linked AI Engineering analysis. Historical
Terra annotations and persisted Codex editorial tasks are retired. The
web-grounded Registry relevance audit was a one-time non-mutating evaluation,
not part of the daily path.

| Boundary | Default model | Reasoning effort | Rationale |
| --- | --- | --- | --- |
| Structural entity kind | `gpt-5.6-luna` | `medium` | Existing evaluated classifier contract. |
| Evidence audience routing | deterministic evidence gate, then `gpt-5.6-luna` | none, then `medium` | A narrow evidence-completeness gate suppresses only short unsupported packets and stores the exact reason without spending model tokens. All other packets reach the self-contained, recall-oriented router. Current checkpoint counts and spend live in [`docs/STATUS.md`](../STATUS.md) and [`tokenomics.md`](tokenomics.md). |
| Company-aware Investment analysis | `gpt-5.6-sol` | `xhigh` | One Development is screened against the compact company universe, then the model opens only the full memos needed to test concrete causal paths. Sol/xhigh is the quality baseline while this boundary is calibrated. Exact run proof and spend belong in [`docs/STATUS.md`](../STATUS.md) and [`insight-refresh.md`](insight-refresh.md). |
| Surface-linked AI Engineering analysis | `gpt-5.6-sol` | `high` | One Development is judged in a single call against the seven assumed Aion surfaces in [`aion-surfaces.json`](aion-surfaces.json). There is no tool loop: the surface map is small enough to send in full, so progressive disclosure buys nothing. The work is taste plus one sentence of technical writing, not retrieval or a multi-hop causal chain, so `high` is the calibration baseline rather than `xhigh`. Luna at this boundary is untested. |
| Missing-bio identity research | `gpt-5.6-luna` | `high` | Multi-source grounded identity resolution needs more checking. |
| Combined kind + Registry decision | `gpt-5.6-luna` | `high` | Independent structural and admission decisions with optional search. |
| Registry relevance audit | `gpt-5.6-terra` | `high` | One-time required-web-search evaluation of the initial Registry. It is non-mutating and does not run during daily evidence or Insight generation. |

Do not lower reasoning effort merely to reduce spend. OpenAI recommends using
the lowest effort that still meets the task, preserving the prior effort as a
migration baseline, and testing one level lower. That comparison matters here:
Luna-low agreed with the retired mini-medium keep/drop decisions on 63/64
envelopes but dropped a post that named a specific Thinking Machines Lab essay.
That historical comparison remains relevant to the retired keep/drop boundary.
For model-eligible packets, v15 keeps Luna/medium and the stable self-contained
source, audience, and decision contract. It also requires the Investment hook
to arise from the central Development rather than an attractive incidental
fact. The pre-model rule is deliberately narrow: it applies only when the
complete packet is one short root post and no supporting source survived packet
construction. A remaining link is recorded as unavailable linked or media
evidence; the rule does not claim to have understood that missing material.
The current router is intentionally recall-oriented: a positive route means a
Development merits downstream investigation, not that it is already
publishable intelligence. Company mapping and the Investment Insight gate
remain responsible for rejecting speculative or immaterial leads.

The model string and reasoning effort are part of every run identity. Existing
run databases and historical reports remain immutable evidence of the model
that produced them; changing a runtime default never relabels old results.

## Prompt Caching

Prompt-cache provider behavior, cache-lane scheduling, telemetry
interpretation, current Luna/Terra proof, incident history, and the repeatable
canary are owned by [`prompt-caching.md`](prompt-caching.md). That page is the
single source of truth; do not duplicate its operational rules here.

## Long-running Responses calls

Use OpenAI Responses background mode for a web-grounded or high-reasoning call
that may outlive one HTTP request through the LiteLLM proxy:

```python
response = client.responses.create(..., background=True)
while response.status in {"queued", "in_progress"}:
    time.sleep(30)
    response = client.responses.retrieve(response.id)
```

This is the official OpenAI polling contract. Always poll the ID on the latest
returned response object. LiteLLM's default response-ID security hook may
return a different encrypted wrapper on each retrieval; that wrapper remains
valid and does not mean that a second provider job was created. Do not disable
the security hook or bypass the shared proxy merely to make the visible ID
stable.

OpenAI's example uses a two-second interval. FLI's research pilot uses
30 seconds because completion latency is unimportant for multi-minute Sol
research and the slower interval avoids needless proxy traffic and log noise.

The deployed LiteLLM v1.93.0 path was verified on 2026-07-28 with the exact
loop above: a Luna background request moved from `queued` to `completed` and
returned the expected output while its visible encrypted ID changed. The
v1.93.0 response-ID fix concerns nested hosted-MCP double encoding, not visual
ID stability between polling responses.

Background calls may set `store=False`; OpenAI temporarily retains enough
state to execute and poll them. Persist the returned result and provenance in
the owning workflow once the response reaches a terminal state.

- [OpenAI background-mode guide](https://developers.openai.com/api/docs/guides/background)
- [LiteLLM v1.93.0 MCP response-ID fix](https://github.com/BerriAI/litellm/pull/32034)
- [LiteLLM response-ID security hook](https://github.com/BerriAI/litellm/blob/v1.93.0/litellm/proxy/hooks/responses_id_security.py)

## Source Guidance

- [OpenAI GPT-5.6 migration guidance](https://developers.openai.com/api/docs/guides/latest-model#update-api-and-model-parameters)
- [OpenAI model choice for simple agent workloads](https://developers.openai.com/tracks/building-agents#how-to-choose)
