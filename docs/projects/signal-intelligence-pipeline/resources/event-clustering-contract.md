# Proposed Event Clustering Contract

Status: proposed from the 2026-07-13 data audit; implement only after the
product boundary is confirmed.

## Decision

Keep the deterministic Feed as the complete post-level evidence ledger. Add a
separate, rebuildable **Event** projection that groups related Feed posts and
points back to every member. Add relevance as a later event-level decision
stage. Neither stage deletes or rewrites raw posts.

```text
Feed run (all posts + observed relations)
  -> event-cluster-v1 (mechanical grouping + why-grouped evidence)
  -> event-relevance-v1 (relevant/substantive decisions)
  -> later extraction, verification, and insight generation
```

The event layer belongs in `data/derived/signal-events/events.db`. It pins one
Feed run ID and clustering-contract hash. Registry state remains a read-time
join so a rejected account stops contributing to the current view without
changing historical clusters.

## What The Current Data Can Support

- Quote and retweet edges are explicit. Across the current seven-day run,
  5,588 referenced targets have at least one observed interaction, 1,054 have
  at least two observed handles, and 413 have at least three.
- Direct posts expose expanded URL entities. Exact shared URLs already yield
  82 anchors used by at least two different handles. Examples include the GPT
  5.6 launch page, Bun's Rust announcement, and Meta model launch pages.
- Direct timeline collection contains no authored replies. It stores only
  aggregate reply counts, which are not reply evidence.
- Embedded quote/retweet payloads do preserve a useful partial thread layer:
  539 distinct embedded reply posts across 414 conversations. Of those, 276
  have a parent already present in the Feed and 370 have the conversation root
  present. These can be normalized without a provider call, but they do not
  constitute complete reply threads.

## Clustering Stages

### 1. Normalize Evidence Anchors

Extend the rebuildable Feed representation, not the immutable raw store, with:

- `conversation_id` and `in_reply_to_post_id` when present;
- canonical expanded URLs with tracking parameters removed;
- X Article/card identifiers when present;
- the existing quote/retweet target IDs;
- stable author identity and publication time.

Generic landing pages and broken placeholders such as `t.co/`, `meta.ai`, or
site homepages are not sufficient URL anchors on their own.

### 2. Build Deterministic Seed Clusters

Create seed groups from high-precision links:

1. the same retweet/quote target;
2. the same conversation root or reply parent;
3. the same canonical substantive external URL or X Article ID.

Every membership row stores a reason such as `same_target`, `same_thread`, or
`same_canonical_url`. Avoid unconditional graph connected-components: one post
with two unrelated links could otherwise join two events into a false
mega-cluster.

### 3. Merge Semantically Equivalent Seeds

Only unresolved seeds and unanchored first-hand posts enter a bounded semantic
merge within a short time window, initially 72 hours. Candidate generation can
use normalized named entities/product names and text similarity; a structured
model decision may confirm borderline merges. The result must store the merge
reason, confidence, contract version, and exact input post IDs.

The first implementation should not generate a polished event summary. Its
representative text can come from the best first-hand/root post until event
label extraction is separately accepted.

## Proposed Schema

```text
event_run(
  run_id, feed_run_id, contract_version, contract_hash,
  input_fingerprint, created_at
)

event_cluster(
  run_id, event_id, representative_post_id,
  started_at, last_activity_at, member_count
)

event_member(
  run_id, event_id, provider, post_id,
  role, membership_reason, confidence
)

event_anchor(
  run_id, event_id, anchor_type, anchor_value
)

event_relevance(
  event_run_id, event_id, evaluation_run_id,
  frontier_relevance, substance, reason,
  evidence_post_ids_json, input_hash
)
```

`frontier_relevance` is `relevant | irrelevant | review`.
`substance` is `substantive | reaction | review`. These remain separate so a
substantive political post is not confused with an AI-relevant but empty
reaction.

## Event Ranking

Aggregate attention at the event boundary without double-counting wrappers:

- one vote per active canonical Registry entity across every member post;
- distinct first-hand originators;
- the representative/root post's public engagement, not a sum of duplicated
  retweet metrics;
- event recency and evidence breadth shown separately.

The ranking remains an ordering aid. Relevance and substance are explicit
later decisions, not hidden score weights.

## Product Surface

Keep one Feed page with an `Events | Posts` view switch. During validation,
retain **Posts** as the default audit view; make **Events** the default only
after a top-20 false-merge/split audit passes.

An Event row remains a flat editorial list item and shows:

- representative first-hand/root evidence;
- `N posts · N Registry accounts · N first-hand sources`;
- `Grouped because …` with visible anchors;
- the event attention inputs;
- an inline `Show evidence` expansion.

The expansion orders evidence as first-hand posts, quotes, partial replies,
then retweet wrappers. Replies nest under a known parent. Orphaned embedded
replies are labeled `partial conversation`; aggregate reply counts never pose
as collected replies. Each post keeps its direct X provenance link.

## Reply Collection Boundary

Do not crawl every reply thread. First normalize the partial conversation
metadata already stored. If later evaluation shows replies materially improve
high-ranked events, fetch replies only for an accepted event candidate and
preserve the raw response in `x-content.db` before rebuilding the Event run.
That provider call remains a separate, explicitly authorized collection step.

## Validation Gate

Before relevance or insight extraction:

1. inspect the top 20 event clusters from one complete day;
2. label false merge, false split, representative-post quality, and evidence
   completeness;
3. accept `event-cluster-v1` only if at least 18/20 have no material false
   merge and obvious multi-post launches are not split across the top results;
4. keep the Posts view as the fallback audit surface regardless of outcome.

