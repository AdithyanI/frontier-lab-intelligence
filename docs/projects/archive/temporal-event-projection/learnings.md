# Temporal Event Projection Learnings

## Durable Rules

- **Snapshot provider evidence before rebuilding derived stores.** Preserve immutable provider observations keyed by `(provider, post_id, raw_sha256, observed_at)`. Feed, event, and triage rebuilds must read a pinned observation rather than the latest mutable post row.
- **Normalize the complete relation closure.** Traverse quote and retweet payloads recursively, preserve reply/conversation anchors, and materialize every reachable post or opaque anchor. Direct-only normalization fragments one real event into several envelopes.
- **Separate stable event identity from temporal presentation identity.** Store a stable event cluster for the complete normalized graph, then derive the cutoff-local component and presentation root for each view. A future bridge must not rewrite what an earlier day showed.
- **Define time views explicitly.** A daily view contains only evidence visible by that UTC cutoff, with a clear daily delta and cumulative-to-date state. A weekly view merges overlapping daily components across the week instead of summing independent daily envelopes.
- **Publish atomically through explicit pointers.** Build new Feed, Event, and Triage runs off to the side; validate them; then switch one publication pointer. Readers must never infer the active run from timestamps or partially written tables.
- **Reuse triage only for identical evidence.** Reuse a result when the snapshot content hash and model-input hash match, alongside compatible prompt/schema/model settings. Event IDs alone are insufficient because an event can accumulate new evidence.
- **Use provider-qualified identifiers everywhere.** Internal keys, candidate maps, consumed sets, joins, and API references should use `(provider, post_id)` before a second source is introduced. Bare post IDs are safe only while X is the sole provider.
- **Fail closed on unresolved relations.** If a quoted or reposted payload lacks a target ID, do not invent a relation or merge it heuristically. Retain the source as independently traceable evidence and mark the relation unresolved for later repair.
- **Distinguish late discovery from history mutation.** A later provider fetch may legitimately expose an older post from an existing channel. Preserve the new immutable observation, rebuild, and then demand deterministic overlap fingerprints once the raw snapshot is frozen; do not discard valid evidence merely to preserve an older count.
- **Never use provider conversation IDs as event edges.** Conversation metadata is useful for navigation but can cover unrelated branches. Only provider-declared quote, retweet, and explicit reply-parent edges belong in deterministic exact grouping.
- **Publish data generations, not individual files.** Validate the Feed/Event pair and its exact run linkage, then move one explicit pointer. A newest-created run is an experiment until promoted.
- **Make bulk jobs replayable before making them fast.** The July 12–13 collector checkpoints every account/page and the triage runner persists each completed item. Parallelism is safe only after restart and exact-hash reuse semantics are explicit.

## Validation Heuristics

- Assert that one provider-qualified post belongs to at most one event per run.
- Assert that every normalized relation has a corresponding event link and that its endpoints are members or explicit opaque anchors.
- Fingerprint structural projections without mutable read-model annotations such as triage decisions.
- Re-run historical daily and weekly projections after every normalization change; compare counts and structural fingerprints before publication.
- Test direct and embedded copies in both ingestion orders so canonical post selection cannot depend on row order.
- Build the same frozen raw snapshot twice and compare semantic audit hashes, not only row counts.
- Extend a frozen seven-day snapshot to nine days and assert every overlapping daily fingerprint is unchanged.
- Paginate the product API and verify every displayed model decision matches the current snapshot hash.
- Manually inspect the largest exact components and a stratified keep/drop sample; machine invariants cannot judge semantic usefulness.

## Notes For Future Runs

- Raw provider JSON in the pinned Feed run is a valid immutable fallback for embedded posts that never appeared as top-level provider observations.
- Keep unresolved-quote handling and multi-provider keying visible in review checklists; both are easy to miss while X is the only active source.
- Prompt-cache eligibility is not cache proof. Record `cached_tokens` and proxy-reported cost for the completed run.
- Provider pages can change recursive relation shape across observations. Earliest-disclosure provenance is the temporal oracle; the latest payload is not.
- Final local date reads were 16–24 ms with the landed indexes. Re-measure before adding semantic clustering or a second provider rather than pre-optimizing now.
