# Following Snapshot Artifacts

Large outgoing-follow snapshots live under ignored
`data/raw/following/<snapshot-id>/snapshot.db`.

This tracked directory keeps only small snapshot manifests under `manifests/`.
Each manifest binds a local snapshot checksum to its frozen source cohort,
provider, completeness counts, spend, collection command, ranking output, and
evaluation artifact.

See `docs/references/following-snapshot-storage.md` for the full contract and
future object-storage migration path.

