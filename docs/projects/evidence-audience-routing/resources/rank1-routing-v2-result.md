# Feed rank 1 audience-routing v2 result

Status: completed one authorized Luna-medium call on 2026-07-15. This was the
second v2 request and the first intended prompt-cache reuse test.

## Source

- Root author: `@alezander907`
- Root URL: `https://x.com/Alezander907/status/2076110148695966172`
- Feed rank: 1
- Event ID:
  `8ca5173faeb4207e358c8a619bc2788bf4791a330b41f54e7375817f4faa22e1`

## Exact model input

```yaml
evidence_packet:
  primary_source:
    author: "@alezander907"
    post:
      kind: x_post
      text: |
        Some new model release and my eval scores: gpt-5.6-sol is a small improvement on browser tasks, but seems to consume many more tokens Muse spark 1.1 outperforms gemini 3.5 flash at a cheaper price, but is not overall very good Claude sonnet 5 is 5th best performance at higher cost than opus. I am not very impressed with new models browser-use abilities. Maybe I will train my own instead
    continuations:
      - kind: x_post
        text: |
          I take it all back. We just got access to eval Grok 4.5 and it has landed above GPT-5.6-Sol and just shy of Opus for browser use. Because cache input is expensive, the overall cost is only 10% cheaper than opus. Its overall a bit faster. We have another opus-class model in the competition
  independent_reactions:
    - kind: reply_post
      author: "@elonmusk"
      text: |
        @Alezander907 Sounds like we should lower our cached price
    - kind: reply_post
      author: "@mamagnus00"
      text: |
        @elonmusk We should collab to beat them next time
    - kind: quote_post
      author: "@gregpr07"
      text: |
        We should collab to beat them on the next one 👀 @elonmusk
```

## Result

```json
{
  "ai_engineering": {
    "relevant": true,
    "reason": "The author reports comparative browser-use evaluation results, token consumption, latency, and cache-input cost across named models, providing concrete hypotheses for engineers to reproduce and investigate."
  },
  "investment": {
    "relevant": true,
    "reason": "The reported near-Opus browser performance, approximately 10% lower overall cost, faster execution, and an apparent pricing response from Musk provide specific evidence relevant to model competition, inference economics, and competitive positioning, though the results are an individual evaluation rather than established fact."
  }
}
```

## Telemetry and cache test

| Field | Value |
| --- | ---: |
| Model | `gpt-5.6-luna` |
| Reasoning effort | `medium` |
| Input tokens | 1,860 |
| Output tokens | 121 |
| Cached tokens | 0 |
| Cache-write tokens | 0 |
| LiteLLM-reported cost | $0.002586 |
| Duration | 3.412 seconds |
| Prompt SHA-256 | `b3fec75f322ce5654a74423f9cfec3d060ee7acdfded935680ee5d5f7fd81ed3` |
| Prompt cache key | `fli:audience-routing:audience-routing-v2:shard-00` |

This request reused the exact prompt hash and cache key from the immediately
preceding Satya request and exceeded the 1,024-token eligibility threshold. It
still reported zero cached tokens and zero cache-write tokens. Therefore the
current Azure/LiteLLM request configuration has not produced observable prompt
cache reuse across these two calls.

## Input-contract finding

The frozen source packet also contained this independently authored quote-post:

> `@elonmusk`: Grok 4.5 is Opus class for browser use

It was not present in the model input because the first cleanup contract
excluded every reaction shorter than 40 characters. This is a real
counterexample to that rule: short text can contain a specific material claim.
The model still received the primary evaluator's more detailed Grok comparison,
so this result did not depend on the omitted quote. However, the length-only
filter should be removed before any third envelope is routed.

## Provenance

- Run database:
  `data/derived/audience-routing/audience-routing-v2-2026-07-12-rank1/routing.db`
- Evidence SHA-256:
  `4d1e37c6805ea2607772fb71247af2a1359bf31ae14314f57eca7d980044737e`
- Input SHA-256:
  `27dd7d1b33d1c595f534f355ed18871a08f9066674cc0d62dc73f42de49a106f`
- SQLite integrity check: `ok`
