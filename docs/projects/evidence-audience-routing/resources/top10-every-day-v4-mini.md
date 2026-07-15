# Audience Routing v4: Every-Day Top 10

Date: 2026-07-15

## Frozen production contract

- Model: `gpt-5.4-mini`
- Reasoning: `high`
- Prompt: `audience-routing-v4`
- Selection: top 10 ranked Evidence envelopes for every complete Feed day,
  2026-07-05 through 2026-07-13
- Execution: sequential
- Cache control: one stable prompt-level key,
  `fli:audience-routing:audience-routing-v4`
- Removed: event sharding, per-item keys, diagnostic keys, prompt padding, and
  explicit `prompt_cache_retention`

The stable key is a routing hint only. It does not identify an event, day, user,
or evidence packet. The model input remains the stable prompt and schema first,
followed by the variable Evidence packet.

## Minimal-cache proof

Two production-path GPT-5.4 mini calls without a key returned zero cached
tokens. Repeating the exact test with one constant prompt key returned 1,280
cached tokens on the second different-input request. No retention override was
present. This matches the OpenAI, Azure, and LiteLLM guidance that caching is
automatic while a stable `prompt_cache_key` can improve backend routing and hit
rates.

## Reasoning comparison

The same two July 12 packets were routed at `high` and `xhigh`.

| Setting | Decisions | Output tokens | Cost | Duration |
| --- | --- | ---: | ---: | ---: |
| high | both relevant to both audiences | 1,262 | $0.0087465 | 12.9s |
| xhigh | both relevant to both audiences | 6,873 | $0.033996 | 40.2s |

`xhigh` was about 3.9 times the cost and used 5.4 times as many hidden
reasoning/output tokens. It added a small epistemic caveat but did not change
either decision or materially improve the visible reasons. `high` already
produced grounded, audience-specific reasons near the requested length, so the
every-day run uses `high`; this avoids over-deliberation without lowering the
classification standard.

## Run results

Pending.
