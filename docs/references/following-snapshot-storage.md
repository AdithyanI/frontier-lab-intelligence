# Outgoing-Follow Snapshot Storage

## Decision

The first broad following crawl stays local and filesystem-backed. Large raw
pages and normalized edges do **not** go into the Git-tracked `data/fli.db`.

```text
data/
  fli.db                                      # tracked product/demo state
  raw/following/<snapshot-id>/snapshot.db     # ignored local crawl database
  following/manifests/<snapshot-id>.json      # tracked small manifest

docs/projects/trusted-following-ranking/resources/
  <snapshot-id>-ranking.csv                   # tracked compact result
  <snapshot-id>-evaluation.csv                # tracked human labels
```

This keeps the current Registry checkpoint cheap to clone and review while the
local snapshot database can grow to millions of edges.

## Local Snapshot Contract

Use one SQLite file per immutable snapshot. It should contain:

- `snapshot_run`: snapshot ID, frozen cohort checksum, provider, schema
  version, start/end time, status, and reported/estimated spend;
- `source_fetch`: one row per source X account with advertised following count,
  page cursor, fetched count, completion state, attempts, and error;
- `raw_page`: exact provider response per source/cursor plus retrieval time and
  checksum;
- `account`: normalized followed-account identity keyed primarily by stable X
  ID and secondarily by normalized handle;
- `edge`: directed `source follows target` rows attributed to the source fetch.

Requirements:

- write raw page evidence before deriving normalized edges;
- commit each successful page so the job resumes after interruption;
- distinguish complete, unavailable, protected, missing, and failed sources;
- never interpret an unavailable source as an empty following list;
- freeze source cohort and schema versions in the snapshot row;
- do not mutate a completed snapshot; create a new snapshot ID for a refresh;
- ranking commands accept an explicit snapshot path and never fall back to
  `data/fli.db` graph edges.

## What Git Keeps

The tracked manifest is the portable proof of the local snapshot. It records:

- snapshot ID and schema version;
- cohort/checkpoint commit and checksum;
- provider and endpoint contract;
- start/end timestamps;
- expected, completed, unavailable, and failed source counts;
- raw pages, unique accounts, edges, and duplicates;
- snapshot database SHA-256 and byte size;
- actual or best-available spend;
- commands used to collect and rank;
- paths to the compact ranking and evaluation outputs.

The manifest does not claim the ignored SQLite file is recoverable from Git.
It proves exactly what local artifact produced the tracked result. The database
can be copied to durable object storage later without changing the manifest or
ranking contract.

## Future Production Shape

Do not adopt a graph database merely because the data contains edges. The
expected workload is snapshot ingestion plus batch ranking, not low-latency
arbitrary graph traversal.

When local storage stops being sufficient:

1. Put immutable provider pages and partitioned edge files in object storage.
2. Store run/source status, checksums, and spend in Postgres.
3. Write normalized edges as Parquet partitioned by snapshot/source and query
   them with DuckDB or a batch job for ranking and evaluation.
4. Keep the ranking interface keyed by `snapshot_id`, so storage can move
   without changing product semantics.
5. Consider a graph database only if interactive multi-hop traversal becomes a
   measured product requirement.

The first implementation should optimize for one resumable local job and a
defensible interview artifact, while preserving this migration seam.

