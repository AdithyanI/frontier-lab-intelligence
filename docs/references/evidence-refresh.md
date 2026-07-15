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
  --through 2026-07-13 \
  --days 9 \
  --workers 32 \
  --json
```

`--through` is the latest complete UTC day. `--days` defines the inclusive
window. Collection uses up to `--workers` account requests concurrently. By
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

## Cache and invalidation contract

- **Collection:** the frozen Registry/date/contract run ID is deterministic.
  Cached page chains are inspected first, and only incomplete accounts call the
  provider. Account fetches are resumable and parallel; protected accounts are
  recorded rather than retried forever.
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
workers per day, and nine days in parallel. The command binds every daily run
to the same published Event/Feed pair, uses deterministic run IDs so an
interrupted invocation resumes in place, and checks that publication did not
change while it ran. `--replace` removes older routing directories only after
all requested days complete successfully. Use `--dry-run` to print the exact
run plan without calling the model.

LiteLLM/OpenAI prompt caching still applies to the stable instruction prefix;
the run databases provide the stronger exact-response reuse when the source
publication and frozen cohort are unchanged. A changed envelope correctly
produces a new request rather than reusing a stale judgment.

## Output

The command emits one JSON object containing each stage result, including
whether a deterministic run was reused, collection provider-request counts,
published Feed/Event IDs, artifact counts, content-fetch outcomes, index
maintenance, and per-view warmup timings. Any incomplete collection stops the
dependent stages instead of publishing a partial workspace. A refresh is not
operationally complete until both `index_maintenance` and `view_cache` report
ready/optimized outcomes.
