# Local reviewer release

The repository stays small while a clean checkout remains reproducible. Git
owns the code, documentation, compact manifests, and `data/fli.db`. An
immutable object-storage release owns the larger read models needed for local
reproduction. The primary reviewer experience is the public hosted application
at [frontier-lab-intelligence.adithyan.io](https://frontier-lab-intelligence.adithyan.io/).

## One-command contract

Run:

```bash
./demo.command
```

The command:

1. reads `data/demo-release.json`;
2. downloads the content-addressed ZIP into ignored `tmp/demo-release/`;
3. verifies its byte count and SHA-256 before extraction;
4. rejects paths outside the manifest's exact install roots;
5. restores the ignored runtime stores;
6. creates `.venv`, installs the local package, and starts the web app; and
7. sets `FLI_READ_ONLY=1` before opening `http://127.0.0.1:8797`.

If a healthy local Frontier Lab Intelligence process is already serving that
port, the launcher opens it and does not download, replace data, or start a
second process.

The installer refuses to replace unmarked local runtime data. A developer can
use `--force` to replace only the exact paths declared in the manifest. Use
`--prepare-only` for unattended setup or validation without starting a server.

## Frozen release

| Field | Value |
| --- | --- |
| Release | `fli-demo-2026-07-19` |
| Source checkpoint | `fee2dfe3e153cb37e3290415ebf38fe67b3f977d` |
| Archive bytes | `357367846` |
| Uncompressed bytes | `1604137889` |
| Files | `4225` |
| SHA-256 | `45b846acec1829f384cdceafb4d4313a868e2ff83b369589d811cecc07defedd` |
| Public object | [Download the frozen snapshot](https://storage.aipodcast.ing/permanent/frontier-lab-intelligence/demo/by-hash/45b846acec1829f384cdceafb4d4313a868e2ff83b369589d811cecc07defedd/fli-demo-2026-07-19.zip) |

The public object was read back in full after upload. Its byte count and
SHA-256 matched the local archive.

## Included and excluded data

The release includes consistent SQLite backups for the current Feed and Event
publication, the complete derived network ranking, the normalized follower
edges used by the UI, cited artifact text, referenced audience-routing runs,
candidate Insights, and the published submission-era daily runs.

It excludes:

- `.env`, delivery credentials, API keys, and private inputs;
- raw X provider response bodies and following-page payloads;
- paid-request caches and unrelated historical projections;
- daily-agent workspaces, orchestration state, and feedback; and
- rebuildable PDF cache files.

The release Feed keeps normalized post text, metrics, URLs, hashes, and
discovery provenance while replacing duplicate `raw_json` bodies with an empty
object. The full raw evidence remains in ignored local storage and is not
required by any reviewer read path.

## Read-only boundary

`FLI_READ_ONLY=1` disables Registry intake and Daily Brief delivery at the API
boundary. Delivery status also ignores local credentials, so a reviewer cannot
accidentally expose a destination or send a message. Read endpoints and local
PDF generation remain available.

This read-only boundary belongs to the frozen local reproduction path. The
hosted application is a separate deployment of this repository's normal
operator runtime.

## Rebuilding the release

The operator-only builder is:

```bash
python3 scripts/build-demo-release.py --force
```

It uses SQLite's backup API before pruning historical projections, removes raw
provider bodies, builds a deterministic ZIP, and writes an untracked draft
manifest under `tmp/demo-release/`. Upload the archive through the shared
machine-local uploader, verify a full public readback, then update
`data/demo-release.json`. Storage credentials remain owned by the generated
machine-local secret lane and never enter this repository.
