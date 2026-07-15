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

All nine runs completed without a model failure.

| Day | ENG only | INV only | Both | Neither | Cache hits | Cached/input tokens | Reported cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-07-05 | 2 | 0 | 2 | 6 | 9/10 | 11,520 / 18,549 | $0.02601675 |
| 2026-07-06 | 1 | 1 | 3 | 5 | 10/10 | 12,800 / 29,693 | $0.05894925 |
| 2026-07-07 | 1 | 0 | 7 | 2 | 10/10 | 22,528 / 46,805 | $0.06141885 |
| 2026-07-08 | 0 | 0 | 8 | 2 | 10/10 | 32,256 / 50,058 | $0.06176520 |
| 2026-07-09 | 0 | 0 | 7 | 3 | 10/10 | 14,336 / 46,830 | $0.06923070 |
| 2026-07-10 | 0 | 1 | 6 | 3 | 10/10 | 12,800 / 38,379 | $0.05666175 |
| 2026-07-11 | 0 | 2 | 4 | 4 | 10/10 | 18,432 / 28,453 | $0.04183365 |
| 2026-07-12 | 1 | 1 | 4 | 4 | 9/10 | 15,104 / 25,031 | $0.04958655 |
| 2026-07-13 | 1 | 3 | 3 | 3 | 10/10 | 12,800 / 21,802 | $0.03750300* |
| **Total** | **6** | **8** | **44** | **32** | **88/90** | **152,576 / 305,600** | **$0.46296570*** |

`*` One July 13 response omitted the LiteLLM response-cost header, so the
reported total covers 89 of 90 completed calls and is a lower bound. All token
and classification telemetry is complete.

The aggregate cache-read ratio was 49.93%. The first July 5 request was the
expected cold miss; one July 12 request also missed. Some cross-day repeats
read more than the 1,280-token base prompt prefix because overlapping packet
content also matched.

Every database passed `PRAGMA integrity_check`, recorded the exact
`gpt-5.4-mini` / `high` run identity, and contains no per-item cache key or
sharding column. The Feed API selected the matching 10-record run for all nine
days. July 12 rendered six Relevant rows, ten total `ENG`/`INV` marks, twelve
audience-reason labels, and no horizontal overflow in the in-app browser.

## Audit interpretation

The cohort is no longer positive-only: 32 of 90 top-ranked envelopes were
relevant to neither audience, while 14 routed to exactly one audience. This is
enough variation for Adi to audit the threshold in the existing Feed before
any full-catalog expansion or Insight generation.
