# `insight-v1.1` Five-Record Oracle Evaluation — 2026-07-14

The first bounded extraction proof ran the five handwritten 2026-07-11 oracle
envelopes through `gpt-5.4-mini` at medium reasoning. The model produced five
`insight` outcomes. Application code accepted four and rejected one because its
supporting quote was not an exact substring of frozen evidence.

## Result

| Feed rank | Runtime result | Citation | Human-oracle comparison |
| ---: | --- | --- | --- |
| 4 | Published | Exact X span | Same Sol Ultra / 64-subagent proof claim. |
| 10 | Published | Exact X span | Defensible alternate: selected the product/open-source claim instead of the handwritten worldview claim. |
| 12 | Rejected | Mismatch | The claim matched the intended post-launch regression insight, but the model omitted the source's leading “And” and changed capitalization. |
| 18 | Published | Exact X span | Same attributed Grok 4.5 Pareto-frontier claim. |
| 32 | Published | Exact X span | Defensible alternate: selected the 25x cost-performance claim instead of the handwritten physician-review claim. |

Published citation validity is therefore **4/4**; frozen-oracle publish coverage
is **4/5**. Selection agreement with the handwritten preferred claim is **2/5**,
with two reasonable alternate claims and one citation-format rejection. This is
enough to prove the boundary, but not enough to claim that the prompt reliably
chooses the human-preferred proposition.

## Operational evidence

- Run: `insight-v1.1-oracle-2026-07-11`
- Repeated prompt prefix: five eligible requests, three cache-hit requests,
  3,840 cached input tokens.
- Proxy-reported cost: **$0.024084** across all five requests.
- Resumability: completed and failed rows, raw model output, usage, cost,
  response IDs, prompt hash, input hash, and error are retained in the run DB.
- Publication rule: the Insights API reads only `complete + insight` rows with
  an application-bound citation URL. The rejected row is never rendered as an
  insight.

## Decision

Ship the four verified records as the first inspectable skeleton. Do not spend
more time tuning the prompt before Adi reviews the actual output and schema.
Use the failed rank-12 item and the two alternate selections as concrete review
cases for the next prompt iteration.
