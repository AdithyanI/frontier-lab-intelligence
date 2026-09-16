# Park and Resume

## Current state

Parked at Adi's request on 2026-09-16. Keep the project; run no web server,
collection, generation, or delivery until an explicit resume request.

- Code and compact tracked inputs: `~/GitHub/frontier-lab-intelligence`.
- Bulk research data: `/Volumes/DobbyProduction/Services/frontier-lab-intelligence/data`.
- Machine storage selection: ignored `data/storage.local.json`; see
  [data lifecycle](data-lifecycle.md) for its contents and UUID guard.
- Reserved hostname: `frontier-lab-intelligence.adithyan.io`. DNS, Cloudflare
  ingress, and Access policy are retained. Its origin is intentionally unavailable
  while parked; do not change the shared tunnel or other sites to fix that.
- Local web service: port `8797`, LaunchAgent `com.dobby.frontier-lab-intelligence`.
  The job and its plist were removed. No FLI process or listener remains.
- `~/GitHub/scripts/sync/local-production-services.json` keeps this entry disabled.
  Do not re-enable production maintenance automatically.
- `.venv`, `frontend/node_modules`, temporary files, Python/test caches, and local
  service logs are disposable and were removed. Built tracked SPA files remain.

The data move preserved 24,992 files (21.66 GiB) with full checksum verification;
all 39 nonempty SQLite databases opened read-only. The deep SQLite scan was
stopped when Adi prioritized immediate cleanup. The service subsequently started
and Registry data matched; it was then deliberately parked. Full post-move UI
verification was not completed because Adi requested shutdown. Receipts and old
logs live beside the data under `migration-20260916/`. The July recovery snapshot
on DobbyData is also retained.

## Resume when requested

1. Mount the existing `DobbyProduction` volume and inspect the storage config.
   Do not create an empty replacement corpus, restore the reviewer demo here,
   or refetch paid evidence. Recover the config from the data lifecycle document
   if needed. The configured UUID must match the actual volume.
2. Restore disposable dependencies in this checkout:

   ```bash
   cd ~/GitHub/frontier-lab-intelligence
   python3 -m venv .venv
   .venv/bin/python -m pip install -e '.[dev]'
   npm --prefix frontend ci
   .venv/bin/python -c 'from fli.paths import data_path; print(data_path("raw")); print(data_path("derived"))'
   scripts/check-fast.sh --require-runtime
   ```

3. For the existing web interface, reinstall its service:

   ```bash
   scripts/install-launchd-frontier-lab-intelligence.sh --skip-build-now
   scripts/install-launchd-frontier-lab-intelligence.sh --status
   curl --max-time 10 -fsS 'http://127.0.0.1:8797/api/registry?limit=1'
   ```

   Cold startup on the external drive took about 90 seconds during the move;
   the installer's 30-second health warning may precede readiness. Inspect
   `--logs 30` and recheck health before assuming failure. Verify Registry,
   Network, both Insight audiences, artifact text, and Development packets.
   The retained tunnel route should work once the origin is ready. Its Access
   policy currently allows public access; decide whether that still fits the
   requested resume. Restoring the web service does not authorize collection,
   model calls, Slack/email delivery, or enabling production reconciliation.

## Park again

```bash
cd ~/GitHub/frontier-lab-intelligence
scripts/install-launchd-frontier-lab-intelligence.sh --uninstall
lsof -nP -iTCP:8797 -sTCP:LISTEN
```

No listener and no loaded LaunchAgent is the desired parked state. Keep the
external data, ignored storage config, repository, and reserved hostname.
The normal commit check, `scripts/check-fast.sh`, works after dependency cleanup:
it validates repository contracts, the build log, Python syntax without writing
bytecode, and the dependency-free frontend regression tests. It explicitly skips
Python runtime tests and the live lineage audit when `.venv` is absent, and skips
frontend lint/build when `frontend/node_modules` is absent. It does not install
dependencies, open the preserved research data, or start the service in that state.
If dependency directories exist, their checks must pass; broken installed tools
are not treated as a parked checkout.

After restoring dependencies, use `scripts/check-fast.sh --require-runtime`:
it fails if either dependency directory is missing and runs all runtime checks.
Do not restart the service merely to satisfy routine parked-repo maintenance.
