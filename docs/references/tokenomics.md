# Workflow Economics

Last verified: 2026-07-28

This is the glanceable cost map for the current Frontier Lab Intelligence
workflow. It separates measured spend from provider estimates and from local
work that has no incremental API cost. Exact run telemetry remains
authoritative; these numbers are a dated operating snapshot, not a price
guarantee.

## Current Development-Router Pass

The July 5–21 `audience-routing-v14` top-100 pass used `gpt-5.6-luna` at
medium reasoning and saved Development evidence. It made no X or
artifact-provider requests.

| Scope | Requests | Input tokens | Cached tokens | Output tokens | Measured cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seventeen complete days | 1,647 | 6,990,192 | 2,791,936 | 432,579 | $7.079129 |

The pass completed with zero failures. The provider reported a cache read on
1,558 requests and a 39.94% aggregate token read ratio. This is measured
production telemetry, not an assumed cache discount; future refreshes can
observe different reuse even with the same request layout.

## Current 17-Day Rank Migration

The July 5–21 `daily-rank-v2` migration reused the saved X evidence. It made no
X provider request.

| Stage | Scope | Reuse | New external work | Measured incremental cost |
| --- | --- | --- | --- | ---: |
| Daily Event rank | 19,657 Events; 1,700 top-100 positions | Complete local replay | None | $0 |
| Audience routing | Final cohort: 1,674 Events | Final tie-aware correction reused 1,647 exact judgments; initial migration reused 976 | 725 GPT-5.4-mini/high calls across both migration passes; 27 in the final correction | $3.050746 total; $0.089051 in the final correction |
| Per-Event working Insights | Final cohort: 1,474 Event/audience pairs across 965 Events | Final correction reused 1,451 exact outputs; initial migration reused 524 | 981 GPT-5.6-terra/high calls across both migration passes; 23 in the final correction | $15.923542 total; $0.361769 in the final correction |
| Artifact projection | 6,298 observations; 5,378 artifacts | Existing bodies and snapshots | None | $0 |
| Semantic index | 524 stored `text-embedding-3-large` vectors | Existing packet-keyed vectors | None in this replay | Aggregate historical cost was not durably reconciled |
| Daily editorial briefs | 17 complete GPT-5.6-sol/xhigh tasks; 965 Events and 1,474 audience pairs reviewed | Existing exact evidence and current per-Event annotations | One persisted agent task per day; 199 published Insights with 353 citations | App Server does not report dollar spend for these tasks |
| PDFs and UI projections | Two audiences across all 17 days; 34 current PDFs | Deterministic local rendering and content-addressed cache | None | $0 |

The measured LiteLLM increment before the daily editorial tasks is
**$18.974288** across the initial clean migration and the final tie-aware
percentile correction. The corresponding known stored cost of the complete
current routing and per-Event Insight cohorts, including compatible reused
outputs produced in earlier runs, is **$31.797248**. One reused routing row lacks
historical cost telemetry, so this is a recorded known-cost total rather than a
complete replacement-cost estimate. It was not charged again during this
migration.

The final corrective routing pass reported 62,349 input tokens, of which
41,216 were cached, and 15,580 output tokens. The final corrective per-Event
Insight pass reported 73,725 input tokens, of which 24,064 were cached, and
15,440 output tokens. These are incremental-call counters; reused rows
correctly contribute zero new tokens.

## What a Normal Refresh Pays For

The marginal cost depends on which boundary changed:

- A rank formula or Registry-derived rank input change can replay from saved
  evidence locally. It pays only for downstream model rows whose exact input
  hashes are no longer reusable.
- A new complete day normally pays for new X timeline pages, routing for up to
  the top 100 fresh Events, routed-positive editorial work, and only the
  artifact bodies not already cached.
- Extending the Registry or refreshing the following graph is a separate,
  slower X-provider operation. It is not required for a normal daily brief.
- PDF generation and the web projections are deterministic local work.

Exact reuse is deliberately strict: the Event, audience, evidence, prompt, and
model contracts must all match. This makes the cost reduction auditable rather
than a heuristic cache claim.

## X Provider Units

TwitterAPI.io responses do not consistently expose attributable billed spend,
so X costs are recorded as requests, returned items, or documented credits
unless a command can calculate a defensible estimate.

| Operation | Current evidence |
| --- | --- |
| Profile lookup | Approximately $0.00018 per profile at the documented $0.18 per 1,000 profiles used by the repository's estimators. |
| Timeline collection | Historical complete refreshes recorded 3,147 and 4,246 provider requests. The provider did not expose attributable run spend; returned-tweet pricing and cache reuse make request count alone an unsafe dollar conversion. |
| X Article body | 100 credits per Article, or approximately $0.001 with the repository's `credits / 100,000` estimate. The live store currently records 353 requests and 35,300 estimated credits, about $0.353 cumulatively; cache hits make later replays free. |
| Outgoing-follow graph | The current incremental World's Fair expansion was estimated at $4.37070. The earlier projected full 2,231-source crawl from cold state was $27.83826. Page caches make later extensions materially cheaper than a cold rebuild. |

Provider prices can change. Recheck the live provider contract before approving
a new broad crawl; never infer exact billed spend from an endpoint count when
the provider did not return it.

## Reading the Numbers

Three figures answer different questions:

1. **Incremental replay cost** is what this exact change charged after valid
   reuse.
2. **Current-cohort known cost** adds the recorded cost of outputs reused from
   earlier compatible runs; telemetry gaps remain explicit.
3. **Fresh-day operating cost** is variable because the number of new X pages,
   routed-positive Events, cache hits, and editorial research steps changes by
   day.

Model choice and reasoning effort remain quality decisions. Cost is telemetry
used to explain and improve the workflow, not a reason to silently weaken an
in-scope brief.
