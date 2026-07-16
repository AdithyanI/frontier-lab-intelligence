# July 12 Top-8 Audience Routing v3

## Frozen Run

- Run: `audience-routing-v3-2026-07-12-review8`
- Database: `data/derived/audience-routing/audience-routing-v3-2026-07-12-review8/routing.db`
- Cohort: an eight-envelope review cohort on `2026-07-12`. These exact records
  were originally chosen from the former positive gate, then migrated without
  changing model output into the direct Evidence routing schema.
- Source event run: `f8999fcd2b674bf46557023ec8dcab2ac4a8bc115fea8158b4b713a276b588a9`
- Source feed run: `adb2b4949de74a7a3120e71b62366acfcdca0656d0b49c07af10d4e5323f7f96`
- Selection: `review_cohort`, limit 8; no source-triage reference or column
- Model: `gpt-5.6-luna`, medium reasoning
- Prompt/schema: `audience-routing-v3` / `audience-routing-output-v1`
- Prompt hash: `0fb63b9f2106a3dba3412ae4380f359c8ccd36010422e879bd75d2286caf0fd0`
- Execution: sequential (`--workers 1`), 8 complete, 0 failed, SQLite
  integrity `ok`

## Telemetry

| Measure | Result |
| --- | ---: |
| Input tokens | 21,365 |
| Output tokens | 2,646 |
| Cached input tokens | 0 |
| Cache-write tokens | 0 |
| Cache-hit requests | 0 / 8 |
| Proxy-reported cost | $0.037241 |
| Runner duration | 71.576 seconds |

All eight requests were cache-eligible but used eight deterministic lanes, so
this small run did not reuse a lane. More importantly, Azure reported no cache
read or write telemetry. Do not claim provider prefix-cache savings from this
run; retain the stable prefix and instrumentation for a larger catalog run.

## Outcomes And Qualitative Pass

| Frozen rank | Evidence | AI Engineering | Investment | Initial assessment |
| ---: | --- | --- | --- | --- |
| 1 | Alexander Yue model/browser evaluation | yes | yes | Specific comparative capability, speed, and cost evidence; useful to both audiences, with the informal evaluation caveat visible in the reasons. |
| 2 | Satya Nadella enterprise AI architecture article | yes | yes | Strong result. The reasons distinguish a concrete architecture/operating thesis from its strategic and competitive implications. |
| 4 | Sam Altman AI and jobs thesis | no | yes | Appropriate split: broad labor-market thesis with no concrete engineering practice, but clear investment relevance. |
| 6 | Anthropic access and rate-limit extension | yes | yes | Investment is clear. AI Engineering is plausible operational evidence, but is a borderline positive because it is product-capacity policy rather than a technical method or research result. |
| 7 | Tibo product limits and six-million-user update | yes | yes | Investment is strong. AI Engineering is again a borderline operational positive based on usage limits and efficiency rather than implementation detail. |
| 8 | Uber autonomous-vehicle policy claim | no | yes | Appropriate audience split, but the reason correctly treats the material claim as unverified because the packet contains no linked supporting source. |
| 9 | Thinking Machines product and technical direction | yes | yes | Strong differentiated technical direction and company strategy for both audiences. |
| 10 | Riley Goodside binary-noise model behavior | yes | no | Strong concrete model-behavior failure for Engineering and no supplied commercial signal for Investment. |

Distribution: five `both`, one `AI Engineering only`, two `Investment only`,
and zero `neither`. The absence of `neither` is not threshold evidence: the
review cohort was originally biased toward strong evidence. A later bounded
calibration sample should include hard negatives before the routing contract
is treated as broadly proven.

## Product Projection

The read-only Feed projection selects a fully completed, schema-compatible run
for the exact UTC day. It attaches a judgment only when the current envelope
snapshot hash matches the frozen routing record; display rank is not identity.

The July 12 Feed shows neutral hairline `ENG` and `INV` marks and exposes the
two audience decisions and reasons in one disclosure. One derived Status
control selects the mutually exclusive Relevant, Not relevant, or Not
evaluated state. No third model judgment or Insight prose is
introduced.

Live proof after rebuilding and restarting the always-on service:

- API selected the exact migrated run above and returned 8 / 8 routing records.
- Before routing-derived filters, the day contained 737 matching envelopes: 8
  relevant, 0 not relevant, and 729 not evaluated.
- Current displayed Feed ranks were `1, 2, 4, 5, 6, 8, 9, 10`; these may differ
  from the run's frozen source ranks as the Registry-backed projection changes.
  Snapshot-hash matching, not display rank, binds each route.
- Future calls use `audience-routing-v4`, which adds soft 40–50-word reason
  guidance without truncation or schema rejection. These stored v3 results
  retain their true prompt provenance.
