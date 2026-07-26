# Workflow Economics

Last verified: 2026-07-26

This is the glanceable cost map for the current Frontier Lab Intelligence
workflow. It separates measured spend from provider estimates and from local
work that has no incremental API cost. Exact run telemetry remains
authoritative; these numbers are a dated operating snapshot, not a price
guarantee.

## Current 17-Day Rank Migration

The July 5–21 `daily-rank-v2` migration reused the saved X evidence. It made no
X provider request.

| Stage | Scope | Reuse | New external work | Measured incremental cost |
| --- | --- | --- | --- | ---: |
| Daily Event rank | 19,657 Events; 1,700 top-100 positions | Complete local replay | None | $0 |
| Audience routing | 1,674 Events | 976 exact judgments | 698 GPT-5.4-mini/high calls | $2.961695 |
| Per-Event working Insights | 1,482 Event/audience pairs | 524 exact outputs | 958 GPT-5.6-terra/high calls | $15.561773 |
| Artifact projection | 6,298 observations; 5,378 artifacts | Existing bodies and snapshots | None | $0 |
| Semantic index | 524 stored `text-embedding-3-large` vectors | Existing packet-keyed vectors | None in this replay | Aggregate historical cost was not durably reconciled |
| Daily editorial briefs | 17-day GPT-5.6-sol/xhigh batch launched | Existing exact evidence and prior annotations where valid | One persisted agent task per day | App Server does not report dollar spend here; replay still in progress |
| PDFs and UI projections | Target: two audiences across 17 days | Deterministic local rendering and cache | None | $0; final refresh still in progress |

The measured LiteLLM increment before the daily editorial tasks is
**$18.523467**. The corresponding known stored cost of the complete current
routing and per-Event Insight cohorts, including compatible reused outputs
produced in earlier runs, is **$31.999374**. One reused routing row lacks
historical cost telemetry, so this is a recorded known-cost total rather than a
complete replacement-cost estimate. It was not charged again during this
migration.

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
