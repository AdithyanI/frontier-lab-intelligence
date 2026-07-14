# Nested Quote Split Audit — 2026-07-13

## Finding

The Greg Brockman packet is a false split caused before event clustering.
The raw provider payload contains this exact chain:

1. Ben Hylak quotes Greg Brockman (`2074709406428913753` →
   `2074707927844446527`).
2. The embedded Greg post is itself a quote of OpenAI's launch announcement
   (`2074707927844446527` → `2074704958419792299`).
3. The normalizer materializes only the first relation. It inserts Greg as an
   embedded post but does not recurse into Greg's nested quoted target.

The Event projection therefore receives two disconnected components:

- OpenAI launch event `cd607daf…`, 39 members, ranked #1 on 2026-07-08 and
  triaged `keep`.
- Greg/Ben event `1f7acd1d…`, four members, ranked #20 and triaged `drop`.

The model decisions are internally consistent with the incomplete envelopes.
The defect is the lost structural edge, not LLM judgment or UI root selection.

## Prevalence

Across the current seven-day Feed run:

- 2,228 direct provider records contain a nested quote relation.
- 750 distinct nested quote edges point to targets already present in the
  normalized Feed but are missing from `feed_relation`.
- 720 of those missing edges currently connect two different Event clusters.
- The 720 false splits involve 720 child clusters and 386 canonical target
  clusters.

This is therefore a material normalization gap, not an isolated screenshot.

## Required Contract

- Traverse provider-declared quote/retweet relationships recursively, with a
  visited set and bounded depth to prevent cycles.
- Preserve an edge when both post IDs are known even if an embedded stub lacks
  author, timestamp, or text; enrich the target from an existing direct
  snapshot when available.
- Cluster all connected provider-declared relationships before selecting a
  representative root.
- Prefer the canonical quoted/original target as the stable event root; daily
  attention remains activity-derived and must not determine root identity.
- A post absorbed as evidence in a canonical event must not also render or be
  triaged as a competing top-level envelope for the same snapshot.
- Rebuild events and invalidate/reuse triage strictly by the rebuilt snapshot
  content hash. Do not preserve the stale Greg packet decision as a separate
  decision.

## Regression Oracle

For 2026-07-08, the OpenAI launch, Greg's quote, Ben's quote, and their retweets
must resolve to one event whose root is OpenAI post `2074704958419792299`.
Greg and Ben remain independently traceable evidence inside Follow. The Feed
must show one top-level envelope and run one triage decision for the resulting
snapshot.
