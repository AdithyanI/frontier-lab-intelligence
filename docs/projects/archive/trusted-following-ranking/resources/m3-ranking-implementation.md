# M3 Implementation Instructions — Ranking over the Frozen Snapshot

Agreed with Adi 2026-07-11 (chat). This is the engineering contract for M3
(rank and compare) and the storage boundaries it must respect.

## Storage contract (three planes)

Rows counted in millions never live next to rows curated by hand.

1. **Curated — `data/fli.db`.** The vetted Registry. No follow edges are ever
   imported here. M3 does not write graph summaries into this database; add a
   product-facing observation only when a concrete Registry feature needs it.
2. **Frozen — `data/raw/following/<snapshot-id>/snapshot.db`.** Immutable,
   checksummed in the tracked manifest. Ranking reads it read-only; nothing
   ever updates it. A new collection is a new snapshot id, never an edit.
3. **Derived — recomputable analysis outputs.** All ranking results live in a
   separate derived store (`data/derived/following/<snapshot-id>/analysis.db`,
   ignored like the snapshot), stamped with snapshot id, cohort
   sha, registry checkpoint commit, algorithm, and parameters. Delete-and-rerun
   must always be safe. Small reviewable exports (top-k CSV) go under this
   project's `resources/`.

## Known/unknown mapping (the `graph_node` question)

Do NOT add a mapping table to `fli.db` and do not duplicate identity data.
The mapping is a LEFT JOIN on stable `x_id` between `snapshot.account` and
Registry `accounts`. Materialize the join result inside the derived store only
(it is a cache of a query, stamped with the registry checkpoint it was joined
against). Preserve three explicit states: `active` for a current Registry
identity, `rejected` for a known rejected identity, and `unknown` when no
Registry identity exists. Entity-level linkage is enough; do not carry
`registry_channel_id`.

## Ranking work (in order)

1. **Overlap baseline first.** For every target account: count of distinct
   complete, active Registry **entities** following it (`cohort_follow_count`),
   restricted to the frozen snapshot. Multiple official X channels owned by
   one entity contribute at most one vote to a target. Preserve raw eligible
   X-account and edge counts separately for provenance. Emit dense score rank,
   deterministic display position, count, handle, and known/unknown flag. This is the
   explainable baseline everything else is compared against.
2. **Personalized PageRank second.** Same snapshot, edges restricted to the
   collection boundary by construction (a ranking command must be physically
   unable to read `fli.db.graph_edges` or any legacy source). Personalization
   vector = the smaller reviewed trust set, frozen and versioned with short
   reasons before the run. Treat PageRank as an experiment,
   not an assumed improvement: only collected Registry sources have outgoing
   edges, while most target accounts are dangling nodes.
3. **Comparison artifact.** One derived table + one exported CSV comparing
   both rankings on the same snapshot (rank, score, delta), split known vs
   unknown. Unknown top-k is the candidate shortlist input for M4.

## Promotion rule (unchanged)

- Known account → linked to its existing entity via `x_id`; no new rows.
- Unknown account → stays a derived-layer candidate; never auto-inserted.
- Top-ranked + human-reviewed → promoted through the normal Registry pipeline
  (profile gate → kind → relevance), the only door in.
- Rejected identities are never promoted.

## Validation

- Deterministic ranking tests on a small fixture graph for both algorithms.
- SQL reconciliation: source count, edge count, and ranked-node count match
  the frozen manifest numbers.
- Prove isolation: the ranking command path has no code path that opens
  `fli.db` for edge reads.
- `scripts/check-fast.sh` before handoff.
