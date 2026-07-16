# Historical First Successor Insight Run

Date: 2026-07-15

## Frozen Candidate

- Event ID: `1dc9cd728dd09f5b4de81423c5d3757d5410b6df59e365386c8770fa7ad7e89a`
- Historical selected revision: 2026-07-13, Feed rank 45. Under the current
  canonical Event contract this source belongs only to 2026-07-07 at Feed rank
  1, with later activity appended there.
- Source routing run:
  `audience-routing-v8-gpt-5-4-mini-2026-07-13-top100-high-cc76958510dd`.
- Model: `gpt-5.6-terra`, reasoning effort `high`.
- Run ID: `insight-spike-1dc9cd72-terra-v1` (retained as immutable historical
  identity even though the public operator command is now `fli insights`).
- Historical store: deleted during the clean v4 cutover; this document retains
  the calibration evidence and spend record.
- Model view: root, same-author continuations, and linked primary artifacts;
  12 independent reactions were retained upstream but omitted from final
  Insight synthesis.

This run is retained as calibration evidence only. Its v8 source routing
directory was removed during the clean v9 replacement, so the result is not a
current publication and must not be dynamically re-anchored. The packet
contained Lilian Weng's post and the complete Lil'Log harness engineering
survey. The full variable view was 10,723 tokens before removing independent
reactions and 9,690 tokens after removal.

## Decisions

### AI Engineering — kept

**Summary:** The linked Lil'Log survey describes a self-improving coding-agent
harness pattern: mine verifier-grounded failure traces, propose bounded edits
only to explicit harness components, and accept edits only after held-in fixes
and held-out regression tests; it reports that Self-Harness and Agentic Harness
Engineering improved held-out Terminal-Bench-2 performance under such
constraints.

**Why kept:** Harness optimization can be treated as a controlled
software-change pipeline rather than unconstrained prompt iteration. Keeping
the evaluator, model configuration, traces, and permission layer read-only
would make gains more attributable and reduce benchmark gaming, while
failure-to-component mappings could make iteration more diagnosable.

**Next step:** Prototype this loop on one internal coding-agent workload:
version the editable prompt/tool/middleware/skill surfaces, retain per-run
traces and verifier results, require each proposed diff to name a failure
pattern and predicted regression risk, and promote it only if it improves a
held-in slice without degrading a frozen held-out slice.

### Investment — suppressed

This is a broad, forward-looking research review rather than a new company,
product, adoption, or commercialization development. Its cited benchmark
results support a technical thesis about harness engineering, but the packet
provides no evidence of deployment at scale or a sufficiently specific
public-equity transmission path to make the thesis actionable.

## Telemetry

| Audience | Input tokens | Cached tokens | Output tokens | Reported cost |
| --- | ---: | ---: | ---: | ---: |
| Investment | 11,057 | 0 | 844 | $0.04030250 |
| AI Engineering | 11,096 | 0 | 516 | $0.03548000 |
| **Total** | **22,153** | **0** | **1,360** | **$0.07578250** |

Both stable audience cache keys used the shared GPT-5.6 provider retention
kwargs, but neither request reported cached or cache-write tokens. Prompt
caching therefore remains unproven for Terra on this route; the application
records the zero rather than assuming eligibility produced a hit.

## Production Boundary

- The exact request JSON is frozen before any call. A reused run ID must match
  event, day, rank, source route, model, effort, audiences, prompt/schema hashes,
  cache key, and input hash.
- Each audience is completed independently and persisted immediately. Repeating
  the same run reuses completed evaluation JSON and does not construct a model
  client for those rows.
- `fli insights import-result` imported this already-paid result dump without
  another call. `summary` and `inspect` expose the stored state as stable JSON.
- The current API requires the source routing prompt version, prompt hash,
  schema, and completed packet to match v9. This historical row therefore
  fails closed. A new Terra run must consume the clean v9 routes rather than
  reuse or re-anchor this result.
