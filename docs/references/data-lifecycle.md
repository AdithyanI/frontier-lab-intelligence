# Local Data Lifecycle

The local corpus contains paid/cached raw evidence, rebuildable projections,
tracked product state, and historical run evidence. File size alone is never a
reason to delete it.

## Physical storage and logical references

On the Mac mini, the ignored `data/raw/`, `data/derived/`, and `data/archive/`
trees live at `/Volumes/DobbyProduction/Services/frontier-lab-intelligence/data/`.
The code checkout, tracked `data/fli.db`, Registry inputs, and following
manifests remain under `~/GitHub/frontier-lab-intelligence`. Paths in the tables
below are logical references; they do not imply a second local copy.

`fli.paths` owns physical resolution for every runtime reader and writer.
Artifact bodies, readable text, and routing run identities keep their original
`data/raw/...` and `data/derived/...` references. Migration does not rewrite
database rows, source hashes, manifests, or historical absolute provenance.

The machine's ignored `data/storage.local.json` selects storage for both the
CLI and, after an authorized resume, the LaunchAgent. The service is currently
parked; follow [service lifecycle](service-lifecycle.md) before starting it.

```json
{
  "version": 1,
  "data_root": "/Volumes/DobbyProduction/Services/frontier-lab-intelligence/data",
  "volume_mount": "/Volumes/DobbyProduction",
  "volume_uuid": "76542850-95FF-47A2-B862-22E1C1EA90D5"
}
```

Configuration is read once per process. Restart the service after changing it.
A configured missing root, unmounted volume, or wrong UUID fails closed at startup;
the app never falls back to a new local corpus. No symlinks are required.
This is a startup guard, not a continuous volume monitor. Stop the service
before detaching or remounting the drive, then restart it to recheck identity.
Clean checkouts without this file use their own `data/`. `FLI_STORAGE_CONFIG`
can select another config file; `FLI_STORAGE_CONFIG=-` explicitly selects local
checkout storage for isolated tests. Do not use that override for production.
Normal CLI commands should use their configured defaults. Explicit `--db`,
`--source-db`, or output path overrides name physical filesystem paths; use the
external absolute path when deliberately overriding a moved store.
Run `demo.command` in a clean checkout: it refuses to restore its public
snapshot into a checkout configured for external production data.

The production volume is included in Backblaze's watched volumes; this service
directory is outside its excluded `tmp/` tree. A watched destination is not
proof that the newly moved files have finished uploading. Keep the existing
July restore point. Migration receipts and a copy of the pre-move tracked
inputs live beside the external data in `migration-20260916/`.

To inspect physical paths without fetching anything:

```bash
.venv/bin/python -c 'from fli.paths import data_path; print(data_path("raw")); print(data_path("derived"))'
scripts/install-launchd-frontier-lab-intelligence.sh --status
scripts/check-fast.sh
```

For a future move, stop the LaunchAgent and other writers; verify no open data
files; copy and checksum every file; open the copied databases read-only; then
change the config and restart the same LaunchAgent. Full-file checksum equality
proves a byte-preserving relocation. Reserve a full SQLite `PRAGMA quick_check`
for rebuilt/modified databases or suspected corruption: it can take many minutes
on the external drive and is not required to establish copy equality.
Compare Registry, Network, both Insight audiences, artifact text, and Development
analysis-packet responses before releasing the old copy. `scripts/check-fast.sh`
resolves the configured Artifact Store so relocation cannot silently skip its
live lineage audit.

Rollback requires stopping writers, copying the current external raw/derived/
archive trees back to the checkout, verifying them, and removing the local
storage config before restart. Never disable the config while the local corpus
is absent, and never restore the older July snapshot without Adi's instruction.

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
Event-day projections plus compact Event and Development date summaries so
process restarts do not rebuild every historical day before serving a click.
Cache keys bind the source database versions and owning projection code;
deleting it affects latency only.

Developments do not have a separate database. They are a deterministic,
in-process read projection over the current exact Event and accepted-artifact
stores. Full day views rebuild after a restart or source change; only their
compact date/count summary survives process restarts as disposable acceleration.
There is no Development store to preserve, restore, or clean up.

Before a destructive cleanup, trace every default path in code and inspect tracked
manifests/lineage. Run `PRAGMA quick_check` when replacement store contents have
been rebuilt or modified; use the checksum procedure above for exact relocation. Move a
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
