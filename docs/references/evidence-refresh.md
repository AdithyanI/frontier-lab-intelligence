# Evidence Refresh Pipeline

`fli evidence-refresh` is the reusable operator path for rebuilding the Evidence
workspace. It runs the dependent stages in order and reuses valid work at each
boundary.

```text
X timelines → Feed posts/relations → publish Event envelopes
            → primary artifact links → supported artifact text
            → optimize SQLite indexes → warm every visible Feed day
```

## Normal run

```bash
fli evidence-refresh \
  --through 2026-07-15 \
  --days 11 \
  --collection-days 3 \
  --workers 32 \
  --no-input --json
```

In plain language, that command downloads only July 13–15, then rebuilds the
July 5–15 app pages from the complete local cache. The local rebuild makes no X
provider request. `--days` controls what remains visible; `--collection-days`
controls what is fetched now.

`--through` is the latest complete UTC day. `--days` defines the inclusive
published Feed/Event window. `--collection-days` can collect only the newest
overlapping slice when completed collection runs already cover the earlier
retained dates. The command proves that those completed run ranges compose
without a gap before rebuilding downstream views. This avoids repaging old
timelines merely to keep old Feed days visible. Collection uses up to
`--workers` account requests concurrently. By
default, every supported current artifact is extracted: ordinary hosts are
sharded by origin, arXiv metadata/abstracts use the official batch feed, X
Articles use their provider adapter, and eligible ordinary-page failures use
the Reader fallback. `--artifact-limit` and `--x-article-limit` are bounded
calibration overrides; a limit of `0` skips that adapter without skipping link
discovery.

Use `--skip-collection` only when raw X coverage is already known to be
complete and the operator deliberately wants to rebuild downstream views.
`--no-reader-fallback` disables the Jina retry adapter for the selected native
HTML cohort.

## Client contract

The command is machine-first and non-interactive. JSON is the default result;
`--json` makes that intent explicit and `--plain` provides a compact operator
summary. Success and failure both return one versioned object with `command`,
`status`, `data`, `error`, and execution `meta`. Validation, dependency,
interruption, and incomplete-collection failures use stable error codes and
non-zero exit codes. `--timeout-seconds` bounds provider requests, while the
same deterministic command safely resumes account-level work after an
interruption. Sparse stage progress goes to stderr and can be disabled with
`--progress off`, so stdout remains parseable.

The key is read only from `--key-file` (default:
`~/.secrets/twitterapi-io/api-key`); the client does not accept the secret
value through a flag or environment variable.

## Cache and invalidation contract

- **Collection:** the frozen Registry/date/contract run ID is deterministic.
  Cached page chains are inspected first, and only incomplete accounts call the
  provider. Account fetches are resumable and parallel; protected accounts are
  recorded rather than retried forever. Incremental collection may compose
  adjacent completed runs for the same frozen Registry cohort and collection
  contract; the retained publication is blocked if those ranges leave a gap.
- **Feed:** the run ID hashes the date window, schema contract, and immutable raw
  post snapshots. An unchanged input reuses the existing run.
- **Events:** the run ID hashes the Feed run and exact structural links. The
  validated run is published through one explicit pointer.
- **Artifact catalog:** every current envelope root and verified same-author
  reply is scanned for owned URLs. Canonical URLs deduplicate observations.
  A new import prunes observations absent from the current Feed/Event snapshot
  while retaining successful content snapshots for artifacts that still exist.
- **Artifact text:** successful and terminal fetch attempts are reused. Only
  missing or retryable items perform network work. Direct retrieval is
  sequential per origin but parallel across origins. arXiv abstracts, X
  Articles, and the public-HTML fallback keep separate fetch policies and
  caches. Videos remain explicitly deferred.
- **Read performance:** every successful refresh runs `PRAGMA optimize` on the
  Feed, Event, and artifact stores, then requests the date index and compact
  first page for every visible Feed and artifact day. This primes the server's
  state-aware projections after the database-version cache key changes. Index
  definitions are part of the schemas; they are not recreated on each browser
  visit. Use `--no-view-warmup` only for isolated diagnostics.

The pipeline does not rerun audience routing automatically. Rebuilt envelope
hashes make stale routing results disappear from the Feed; a later explicit
routing run evaluates only the intended cohort against the corrected evidence.

## Refresh audience routing

After the corrected Event run and artifact catalog are published, refresh the
top 100 envelopes for the same nine-day window with one command:

```bash
fli audience-routing refresh --through 2026-07-13 --replace
```

The defaults are GPT-5.4-mini/high, nine days, 100 envelopes per day, 24 item
workers per day, and up to nine model-running days in parallel. The command
first freezes each day's packets sequentially against one published Event/Feed
pair, then starts bounded parallel model work only after every packet is
stable. The current v9 packet contains the root, same-author authored updates,
and accepted first-party artifacts; independently authored reactions and pure
reposts remain Feed activity only. This keeps local CPU/GIL-heavy packet rendering fast while preserving
parallel network throughput. Deterministic run IDs resume complete rows in
place, and the result reports packet-packaging time plus the exact number of
model requests. `--replace` removes older routing directories only after all
requested days complete successfully. Use `--dry-run` to print the exact run
plan without packaging packets or calling the model.

LiteLLM/OpenAI prompt caching still applies to the stable instruction prefix;
the run databases provide the stronger exact-response reuse when the source
publication and frozen cohort are unchanged. A changed envelope correctly
produces a new request rather than reusing a stale judgment.

For an artifact-only correction to an already complete day, use
`fli audience-routing refresh-run` with the prior run database and a fresh run
ID/database. It freezes a new immutable full cohort, reuses a completed judgment
only when Event ID and the exact rendered `input_sha256` match, records the
source run on reused rows, and calls the model only for changed packets. This is
the bounded repair path; it does not invoke Insight generation.

## Refresh audience Insights

After every requested routing database is complete and current, inspect the
fresh all-positive Insight cohort without a model call:

```bash
fli insights refresh \
  --through 2026-07-13 \
  --days 9 \
  --all-routed \
  --audience all \
  --model gpt-5.6-terra \
  --reasoning-effort high \
  --dry-run --json --no-input
```

For a clean replacement, run the same command without `--dry-run` against a
new `--db` path under `tmp/` and a new `--dump-dir`. Validate the exact expected
request count, zero pending/failed rows, SQLite integrity, prompt/schema/source
lineage, cache telemetry, and cost before atomically replacing
`data/derived/insights/insights.db`. Do not append a new semantic contract to an
old production database. The production store accepts only the current v4
Insight prompts/output schema over current v9 routing; its first clean
checkpoint contains six completed decisions over three Events. The complete
plan is 492 unique Events and 751 audience requests.

## Output

The command emits one JSON object containing each stage result, including
whether a deterministic run was reused, collection provider-request counts,
published Feed/Event IDs, artifact counts, content-fetch outcomes, index
maintenance, and per-view warmup timings. Any incomplete collection stops the
dependent stages instead of publishing a partial workspace. A refresh is not
operationally complete until both `index_maintenance` and `view_cache` report
ready/optimized outcomes.
