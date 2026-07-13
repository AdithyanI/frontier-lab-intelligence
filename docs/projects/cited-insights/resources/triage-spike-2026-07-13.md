# Feed-Envelope Triage Spike — 2026-07-13

## Decision

Use one permissive, cache-efficient `gpt-5.4-mini` Responses call at medium
reasoning per frozen Feed envelope. The gate returns only `keep | drop`, one
primary category, the supplied post IDs that carry useful signal, and one
concise reason. It does not browse, score confidence, choose URLs, see
attention/ranking/popularity features, or mutate Feed or Registry state.

Do not add a routine second-model reviewer. `gpt-5.5` remains a possible
future escalation only if a blind evaluation exposes a real quality gap.
Luna was deliberately omitted from the final comparison after the session
decision to standardize on `gpt-5.4-mini`: mini met the quality bar and
produced verified cache reads through the current LiteLLM/Azure route, while
the earlier Luna deployment did not expose useful cache reads for this
workload.

## Boundary

The stable instructions ask one question: does at least one supplied post
contain a concrete frontier-AI lead, material attributed viewpoint,
inspectable primary source, or incident worth later verification and
structured extraction?

The variable input contains:

- root post ID, author, type, and text;
- every related non-retweet post with its exact relationship and whether it
  shares the root author;
- expanded URLs already present in stored provider data;
- provider-supplied article/card title, preview, and URL already present in
  stored raw JSON;
- only a count of omitted exact retweet copies.

Provider metadata is not an article fetch. It prevents a link-only post from
being treated as empty when the provider has already supplied an inspectable
title and preview. Full artifact resolution and claim extraction remain later
stages.

The strict output is:

```json
{
  "decision": "keep | drop",
  "category": "technical_development | business_or_people | strategy_or_policy | safety_or_incident | attributed_view | source_material | banter_or_meme | insufficient_substance | off_topic | other",
  "signal_post_ids": ["only IDs supplied in this envelope"],
  "reason": "one concise evidence-based sentence"
}
```

Programmatic validation requires a kept item to select at least one supplied
ID and a dropped item to select none. The full frozen envelope—not only the
selected IDs—continues to artifact resolution and extraction. This preserves
supporting links and mitigations when the model selects a conservative subset.

## Calibration Design

Two non-overlapping 20-envelope cohorts from the real 2026-07-11 derived Feed
were used:

1. **Audited cohort:** the existing human-labeled top 20, used for regression
   and false-drop measurement.
2. **Unseen cohort:** the next 20 representative high-attention envelopes,
   independently reviewed after inference to expose prompt and input gaps.

The spike was resumable in local SQLite and froze prompt/schema hashes, exact
rendered input, input hash, model response, LiteLLM tags, token usage, cache
telemetry, response ID, proxy-reported cost, and errors. Every call went
through the shared LiteLLM Responses endpoint with stable tags for app,
pipeline, job, scope, prompt, and run. No direct Azure call, web search, X API
request, external submission, or full-corpus run occurred.

The complete local audit database is preserved at
`data/derived/cited-insights/calibration/triage-spike-2026-07-13/triage-spike.db`.
It is an ignored derived artifact rather than tracked documentation; this
report is the durable review summary.

## Iterations and Results

| Run | Cohort | Result | False drops | Cached / input tokens | Proxy cost |
| --- | --- | ---: | ---: | ---: | ---: |
| v1 | audited 20 | 17/20 agreement | 1 | 0 / 36,728 | $0.069621 |
| v2 | audited 20 | 19/20 agreement | 0 | 21,760 / 39,751 (54.74%) | $0.071075 |
| v2 | unseen 20 | 18/20 independent decision audit | 2 | 25,600 / 39,844 (64.25%) | $0.046430 |
| v3 | unseen 20 | 20/20 after targeted re-adjudication | 0 | 23,040 / 45,969 (50.12%) | $0.050830 |
| v3 | audited 20 | 19/20 agreement | 0 | 24,320 / 45,674 (53.25%) | $0.066302 |

Total bounded calibration: **100 calls and $0.304257** proxy-reported spend.
The first eligible call in a sequence could be uncached, while warmed calls
reported 1,280 cached tokens. The cache was therefore measured, not assumed.

The sole final audited disagreement was intentionally permissive. The human
root label called Alexandr Wang's joke post noise, but the same audit noted
that a child contained substantive post-training analysis. The model kept only
that child. This is the desired envelope-level behavior, not a regression.

## What Changed During the Spike

- A time-bounded expert observation and a concrete first-hand product
  experience are valid `attributed_view` leads even without numerical proof.
- Named primary artifacts can be kept as `source_material` when provider
  title/preview metadata makes them inspectable; truth and value are judged
  only after resolution.
- `thin_promotion` was replaced with the clearer
  `insufficient_substance` category.
- Categories prioritize the root's material development when several kinds of
  evidence coexist.
- The selector may identify a useful child under a noisy root and may select
  multiple independently useful children, while repetitive reactions remain
  unselected.

The two unseen v2 false drops were not fixed with a larger model:

1. A link-only X Article was missing its provider-supplied title and preview
   from the compact envelope.
2. A first-hand GPT Live review described specific behavior but the prompt
   over-required numerical evidence.

Adding deterministic metadata and clarifying the epistemic role fixed both in
v3. This is evidence for improving the input contract before escalating model
size.

## Production Contract

- Module: `fli.insight_triage`
- Resumable runner: `fli.insight_triage_runs`
- CLI: `fli insight-triage run|summary|inspect-item`
- Model: `gpt-5.4-mini`
- Reasoning: `medium`
- Prompt: `envelope-triage-v1`
- Schema: `envelope-triage-output-v1`
- Tools: none
- Storage: `store=False`; local frozen run database is the audit record
- Cache: stable 1,024+ token instructions first; variable envelope last; one
  stable cache lane; verify `cached_tokens`
- Retries: no hidden application retry loop; failed rows remain explicit and
  resumable
- Output discipline: JSON stdout for operator inspection, progress on stderr,
  stable error envelope, dry-run, and exact item inspection

## Next Step

Stop prompt tuning. Hand-build the five expected `insight-v1` oracle records
from the existing strong candidates, resolve their primary artifacts, and use
those records to design and test extraction. Triage controls candidate cost and
noise; it does not replace citation verification or insight judgment.
