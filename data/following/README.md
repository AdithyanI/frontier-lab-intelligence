# Following Snapshot Artifacts

Large outgoing-follow snapshots live under ignored
`data/raw/following/<snapshot-id>/snapshot.db`.

This tracked directory keeps frozen source membership under `cohorts/` and
completed snapshot manifests under `manifests/`. Cohort files contain stable X
IDs and handles selected from a byte-exact Registry checkpoint. Each completed
snapshot manifest binds a local snapshot checksum to that cohort, provider,
completeness counts, spend, collection command, ranking output, and evaluation
artifact.

Reviewed PageRank source sets live under `personalizations/`. They bind exact
X IDs and handles to one snapshot, assign explicit relative weights, and record
short selection reasons. Runtime normalization never changes the tracked
manifest.

See `docs/references/following-snapshot-storage.md` for the full contract and
future object-storage migration path.
