# Model Routing

Last verified: 2026-07-28

For the cross-stage cost summary and X-provider units, see
[`tokenomics.md`](tokenomics.md).

## Current Policy

Use `gpt-5.6-luna` as the default efficient model for bounded structured
classification and Registry evaluation. This is an accuracy-first default,
not a rule that the cheapest model or lowest reasoning effort always wins.
The daily brief path uses `gpt-5.6-luna` for audience routing and a persisted
`gpt-5.6-sol` Codex task for final research, consolidation, selection, and
writing. Terra per-Event outputs remain optional working annotations, not a
required authoring stage. The web-grounded Registry relevance audit was a
one-time non-mutating evaluation, not part of the daily path.

| Boundary | Default model | Reasoning effort | Rationale |
| --- | --- | --- | --- |
| Structural entity kind | `gpt-5.6-luna` | `medium` | Existing evaluated classifier contract. |
| Evidence audience routing | `gpt-5.6-luna` | `medium` | The self-contained v13 router is an upstream recall-oriented candidate gate over one complete Development packet. Current top-100 runs now cover July 19–21. The July 19–20 refresh completed all 191 routable Developments without failure: 62 both, 26 Engineering-only, 12 Investment-only, and 91 neither, for $0.856692. The July 21 pass completed all 97 routable Developments without failure: 55 both, 10 Engineering-only, 11 Investment-only, and 21 neither, for $0.588957. The historical mini/high v9 17-day Event cohort remains preserved rather than relabeled. |
| Company-aware Investment analysis | `gpt-5.6-sol` | `xhigh` | One Development is screened against the complete compact company universe, then the model opens only the full memos needed to test concrete causal paths. Top-ten passes now cover July 19–21. The current read projection surfaces 15 of 30 Developments, suppresses 15, retains 41 company assessments, and records three after-memo rejections. The July 19–20 production run completed all 20 targets without failure, reused 272,384 cached input tokens, and reported $3.693917. Sol/xhigh is the quality baseline while this new boundary is calibrated. |
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
For the live two-audience router, v13 moves the default to Luna/medium and
rewrites the stable prompt as a self-contained source, audience, and decision
contract. The first Development-lineage top-100 pass rejected vague
announcements, unsupported opinions, conference logistics, and ordinary
interface changes while retaining concrete technical, economic, policy, and
organizational leads. Its 76/97 any-audience pass rate is intentionally
recall-oriented: a positive route means the Development merits downstream
investigation, not that it is already publishable intelligence. Company
mapping and the audience Insight gate remain responsible for rejecting
speculative or immaterial leads.

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
