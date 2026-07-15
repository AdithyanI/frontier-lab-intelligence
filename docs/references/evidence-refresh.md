# Evidence Refresh Pipeline

`fli evidence-refresh` is the reusable operator path for rebuilding the Evidence
workspace. It runs the dependent stages in order and reuses valid work at each
boundary.

```text
X timelines → Feed posts/relations → Event envelopes → Primary artifact links
            → supported artifact text → publish
```

## Normal run

```bash
fli evidence-refresh \
  --through 2026-07-13 \
  --days 9 \
  --workers 32 \
  --artifact-limit 30 \
  --x-article-limit 20 \
  --json
```

`--through` is the latest complete UTC day. `--days` defines the inclusive
window. Collection uses up to `--workers` account requests concurrently. The
artifact limits choose bounded, rank-stratified content-extraction cohorts;
all primary links are catalogued regardless of those limits. A limit of `0`
skips that content-fetch adapter without skipping link discovery.

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
  missing or retryable items in the selected bounded cohort perform network
  work. X Articles and the public-HTML fallback keep separate fetch policies.

The pipeline does not rerun audience routing automatically. Rebuilt envelope
hashes make stale routing results disappear from the Feed; a later explicit
routing run evaluates only the intended cohort against the corrected evidence.

## Output

The command emits one JSON object containing each stage result, including
whether a deterministic run was reused, collection provider-request counts,
published Feed/Event IDs, artifact counts, and content-fetch outcomes. Any
incomplete collection stops the dependent stages instead of publishing a
partial workspace.
