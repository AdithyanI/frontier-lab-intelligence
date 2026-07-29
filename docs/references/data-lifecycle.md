# Local Data Lifecycle

The local corpus contains paid/cached raw evidence, rebuildable projections,
tracked product state, and historical run evidence. File size alone is never a
reason to delete it.

## Classes

| Class | Paths | Rule |
| --- | --- | --- |
| Tracked product inputs/state | `data/fli.db`, `data/registry/`, `data/following/`, `data/digg/` | Versioned, reviewable, and retained in Git. |
| Immutable raw evidence | `data/raw/x/`, `data/raw/artifacts/`, `data/raw/following/`, `data/raw/conference-sources/` | Ignored locally; preserve successful provider responses and content-addressed bodies to avoid paid or irreproducible refetches. |
| Current derived state | `data/derived/signal-feed/`, `signal-events/`, `artifacts/`, `audience-routing/`, `insights/investment-agent.db`, current Investment traces, and current `following/` analysis | Ignored but required by the local product and audit surfaces. Rebuild only through the owning client. |
| Historical local archive | `data/archive/` | Ignored, non-runtime outputs retained for provenance or comparison. No production reader may scan this tree. |
| Disposable scratch | `tmp/`, Python/test caches, SQLite zero-byte orphans | Remove freely when no process owns the file. Scratch must never become a runtime dependency. |

## Current Runtime Set

Preserve these exact stores during interview work:

- `data/fli.db`
- `data/raw/x/x-content.db`
- `data/raw/following/registry-following-2026-07-14-aie-worldsfair-v2/snapshot.db`
- `data/raw/artifacts/`
- `data/derived/following/registry-following-2026-07-14-aie-worldsfair-v2/analysis.db`
- `data/derived/signal-feed/feed.db`
- `data/derived/signal-events/events.db`
- `data/derived/artifacts/`
- the current published `daily-development-rank-v1` routing directories under
  `data/derived/audience-routing/`
- `data/derived/insights/investment-agent.db`
- `data/derived/insights/investment-agent-traces/`
- `data/derived/x-daily-collection.db`

`data/derived/insights/pdf-cache/` is deliberately absent from the preservation
set. It is safe to delete because a complete published Investment cohort
deterministically rebuilds every file.

`data/derived/web-event-cache/` is also disposable. It retains compressed exact
Event-day projections and their compact date summary so process restarts do not
rebuild every historical day before serving a click. Cache keys bind the source
database versions and projection code; deleting it affects latency only.

Developments do not have a separate database. They are a deterministic,
in-process read projection over the current exact Event and accepted-artifact
stores. Restarting the web process or changing either source rebuilds them;
there is no Development store to preserve, restore, or clean up.

Before a destructive cleanup, trace every default path in code, inspect tracked
manifests/lineage, and run `PRAGMA quick_check` on the replacement store. Move a
historical output to `data/archive/` when its evidence remains useful but no
runtime reader should discover it.

## Current Restore Point

The complete pre-interview-work restore point created on 2026-07-26 is stored
at:

```text
/Volumes/DobbyData/Archives/project-snapshots/frontier-lab-intelligence/pre-scoring-cost-work-2026-07-26
```

It contains the complete local `data/` tree, a Git recovery bundle, and
`RESTORE.md` with the full recovery procedure. The matching local Git tag is
`local-snapshot/pre-scoring-cost-work-2026-07-26`, pointing to commit
`b4147f34db2b557751989b0a894894d8bb0a25ea`.

Never restore automatically. Restore only when Adi explicitly requests or
approves returning to this state. Before restoring, stop database writers,
inspect `git status`, and preserve the then-current `data/` directory. Follow
the external `RESTORE.md`, then run `scripts/check-fast.sh` and inspect the
application before discarding the pre-restore backup.

## Historical Retention

The corrected July 14 World's Fair v2 snapshot is self-contained and is the
only expanded following database used by the product. Its fully copied v1
parent and both superseded analyses were removed locally on 2026-07-17; the v2
manifest retains their historical checksums and copy counts as provenance.

The July 11 expanded snapshot was also removed after its evidence had been
copied forward. Its verified `snapshot.db.zst` recovery cache remains local and
has a checksum-verified durable object recorded in the tracked manifest. This
preserves paid evidence without keeping another 2+ GB expanded database.

Superseded editorial and daily-intelligence databases may remain as local
historical files, but no current reader may discover them. Current readers use
only `data/derived/insights/investment-agent.db`.
