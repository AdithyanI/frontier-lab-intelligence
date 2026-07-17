# Local Data Lifecycle

The local corpus contains paid/cached raw evidence, rebuildable projections,
tracked product state, and historical run evidence. File size alone is never a
reason to delete it.

## Classes

| Class | Paths | Rule |
| --- | --- | --- |
| Tracked product inputs/state | `data/fli.db`, `data/registry/`, `data/following/`, `data/digg/` | Versioned, reviewable, and retained in Git. |
| Immutable raw evidence | `data/raw/x/`, `data/raw/artifacts/`, `data/raw/following/`, `data/raw/conference-sources/` | Ignored locally; preserve successful provider responses and content-addressed bodies to avoid paid or irreproducible refetches. |
| Current derived state | `data/derived/signal-feed/`, `signal-events/`, `artifacts/`, `audience-routing/`, `insights/`, current `following/` analysis | Ignored but required by the local product and audit surfaces. Rebuild only through the owning client. |
| Historical local archive | `data/archive/` | Ignored, non-runtime outputs retained for provenance or comparison. No production reader may scan this tree. |
| Disposable scratch | `tmp/`, Python/test caches, SQLite zero-byte orphans | Remove freely when no process owns the file. Scratch must never become a runtime dependency. |

## Current Runtime Set

Preserve these exact stores during the submission sprint:

- `data/fli.db`
- `data/raw/x/x-content.db`
- `data/raw/following/registry-following-2026-07-14-aie-worldsfair-v2/snapshot.db`
- `data/raw/artifacts/`
- `data/derived/following/registry-following-2026-07-14-aie-worldsfair-v2/analysis.db`
- `data/derived/signal-feed/feed.db`
- `data/derived/signal-events/events.db`
- `data/derived/artifacts/`
- all eleven current v9 top-100 directories under `data/derived/audience-routing/`
- `data/derived/insights/insights.db`
- `data/derived/x-daily-collection.db`

Before a destructive cleanup, trace every default path in code, inspect tracked
manifests/lineage, and run `PRAGMA quick_check` on the replacement store. Move a
historical output to `data/archive/` when its evidence remains useful but no
runtime reader should discover it.

## Known Retained History

The July 14 World's Fair v1 raw snapshot and analysis are superseded by the
corrected self-contained v2 stores. They live under `data/archive/`; the
tracked v2 manifest retains the archived parent path and its checksum as
lineage. Runtime discovery sees only v2.

The archived Insight v9/v6 database lives under
`data/archive/derived/insights/`; current readers use only
`data/derived/insights/insights.db`.
