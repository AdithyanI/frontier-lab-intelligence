# Envelope Triage v2.2 — Top-1,000 Expansion

Date: 2026-07-13  
Status: complete  
Scope: top 1,000 exact attention envelopes per complete stored UTC day

## Why this run existed

The earlier seven-day validation stopped at the top 100 envelopes per day. Adi
explicitly reopened that stopping decision for one bounded learning pass while
away. The purpose was not to change the product's extraction queue. It was to
learn whether the simple envelope-level `keep | drop` gate remained useful
outside the highest-attention slice, and to prove the bulk execution path was
cache-aware, resumable, tagged, and auditable.

The run therefore froze at the smaller of 1,000 envelopes or the complete day.
It did not process the unrestricted long tail.

## Frozen contract

- Model: `gpt-5.4-mini`, reasoning effort `medium`
- Route: shared LiteLLM Responses endpoint only
- Prompt: `envelope-triage-v2.2`
- Output: exactly `decision` (`keep | drop`) and `reason`
- Input: the complete deterministic evidence envelope, without attention,
  follower, Registry-rank, or engagement values
- No web search, hosted tools, artifact-body fetch, category assignment, or new
  X-provider request
- Stable prompt first and variable envelope last; 32 deterministic
  `prompt_cache_key` lanes
- Every request tagged for app, pipeline, job, scope, prompt, and run

The v2.2 prompt clarified that provider metadata is not required when the post
itself identifies a concrete capability experiment, named primary resource,
AI-driven market claim, or specific interface/adoption thesis. The two-field
schema did not change.

## Calibration before expansion

The runner was hardened before paid expansion:

- one in-flight request per cache lane and up to 32 lanes in parallel;
- one main-thread SQLite writer;
- every completed response persisted immediately;
- reruns skip completed rows and retry only explicit failures;
- frozen cohort and prompt/cache keys recorded before calls begin;
- progress, usage, cached tokens, tags, cost, and errors remain inspectable.

The final fresh 64-envelope calibration returned 47 keep and 17 drop, with zero
failures, 36 cache-hit requests, and $0.130723 proxy-reported cost. An immediate
rerun made zero duplicate model calls. Calibration extrapolated the full
6,445-envelope pass to $13.17 before execution.

## Execution results

| UTC day | Evaluated | Keep | Drop | Cache-hit requests | Input tokens | Cached tokens | Output tokens | Proxy cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-07-05 | 569 | 214 | 355 | 566 | 1,310,645 | 1,014,272 | 85,371 | $0.682520 |
| 2026-07-06 | 904 | 424 | 480 | 898 | 2,105,981 | 1,609,728 | 137,226 | $1.129041 |
| 2026-07-07 | 1,000 | 527 | 473 | 998 | 2,332,824 | 1,788,416 | 156,073 | $1.251171 |
| 2026-07-08 | 1,000 | 577 | 423 | 997 | 2,340,128 | 1,786,624 | 157,712 | $1.258829 |
| 2026-07-09 | 1,000 | 596 | 404 | 994 | 2,354,615 | 1,781,248 | 160,312 | $1.285023 |
| 2026-07-10 | 1,000 | 559 | 441 | 981 | 2,352,476 | 1,758,464 | 165,358 | $1.328613 |
| 2026-07-11 | 972 | 442 | 530 | 922 | 2,260,712 | 1,652,224 | 152,192 | $1.271825 |
| **Total** | **6,445** | **3,339** | **3,106** | **6,356** | **15,057,381** | **11,390,976** | **1,014,244** | **$8.207020** |

Operational checks:

- 6,445/6,445 completed; zero failed and zero pending rows.
- Maximum attempt count was one on every day.
- 6,356/6,445 requests (98.62%) reported nonzero cached tokens.
- Cached tokens were 75.65% of all input tokens.
- All 32 stable cache lanes were exercised on every day.
- Every persisted request had the expected LiteLLM metadata tags.
- Actual proxy cost was 38% below the calibration estimate.
- 452 identical `(event_id, input_sha256)` inputs recurred across days; none
  received inconsistent decisions.

The live `/api/events` projection selected the newest completed v2.2 run. On
July 11 it reported 442 keep, 530 drop, and zero not-evaluated envelopes.

## Yield by attention band

| Per-day rank band | Evaluated | Keep | Drop | Keep rate |
| --- | ---: | ---: | ---: | ---: |
| 1–100 | 700 | 521 | 179 | 74.43% |
| 101–250 | 1,050 | 597 | 453 | 56.86% |
| 251–500 | 1,750 | 821 | 929 | 46.91% |
| 501–750 | 1,569 | 810 | 759 | 51.63% |
| 751–1,000 | 1,376 | 590 | 786 | 42.88% |

The middle bands are not perfectly monotonic because each aggregate combines
days with different cohort sizes and subject mixes. The useful conclusion is
stronger than any exact slope: there is no defensible attention rank at which
relevance suddenly disappears.

Manual tail review found legitimate keeps for concrete releases, benchmarks,
papers, agent demonstrations, infrastructure techniques, adoption claims, and
AI-market theses. Typical drops were sports, lifestyle, unrelated politics,
banter, vague hype, and posts whose referenced substance was not identifiable
from the supplied evidence.

## Decision and next step

The expansion succeeded as a learning and evaluation corpus. It does **not**
justify extracting insights from 1,000 envelopes per day before submission.
The keep pool is candidate evidence, not a published insight set, and attention
still provides useful ordering inside it.

The critical path returns to the five-record extraction oracle:

1. deduplicate repeated evidence by `(event_id, input_sha256)`;
2. resolve primary artifacts for a small set of high-value kept envelopes;
3. extract structured claims with verified citations;
4. prove one day yields 3–5 excellent cited insights before expanding breadth.

Do not tune the triage prompt again unless the extraction oracle exposes a
specific false-drop or false-keep failure that blocks cited yield.

## Limitations

- This is model-assisted routing, not a relevance ground truth or recall study.
- The audit sampled calibration errors and lower-ranked tails; it did not
  manually label all 6,445 decisions.
- Link bodies were not fetched, so opaque link-only posts may still drop even
  when the hidden artifact is useful.
- Cache and cost figures are the LiteLLM/Azure telemetry observed for this run;
  they are not a general price guarantee.
