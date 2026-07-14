# Pipeline Operational Review — 2026-07-14

## Post-repair resolution

This table describes the final working tree. The original review below is
preserved as pre-repair evidence and explains why the new operational
boundaries were necessary. Final run IDs, counts, fingerprints, triage
telemetry, and product proof live in
`rebuild-adversarial-audit-2026-07-14.md`.

| Review item | Resolution | Status / evidence |
| --- | --- | --- |
| C1 — resumable date-complete collection | Added a frozen-cohort, account-checkpointed X collector with cursor-chain coverage, terminal reasons, provider-request counts, and cache-hit telemetry. | **Closed.** July 12–13 run completed 2,234 accounts with zero failures; an idempotent replay made zero provider calls. |
| C2 — stale triage on repaired envelopes | Triage freezes the projected cohort, persists snapshot/content hashes, refuses a changed cohort, reuses only compatible complete exact inputs, and the web join requires the matching snapshot hash. | **Closed.** 8,097 final decisions, zero failures, and zero API hash mismatches. |
| C3 — narrow refresh hides prior days | The derived contract builds one explicit requested window. The final publication is one nine-day July 5–13 Feed v8 / Event v3 provider-edge run after bounded two-day raw collection. | **Closed.** All nine dates are visible and independently audited. |
| C4 — no publication boundary | Event readers follow one explicit `signal_publication` pointer whose Event run is validated against its referenced Feed run before promotion. Unpublished Feed/Event runs remain invisible. | **Closed.** The final candidate pair was validated, promoted, and read back through the API. |
| H1 — mutable normalized rows rewrite history | Raw observations are append-preserved, Feed selection is pinned to immutable observations, and Feed v8 stores exact raw JSON plus first-disclosure provenance for direct/embedded content and relations. A later wrapper therefore cannot disclose an older relation into an earlier day. | **Closed.** Independent seven- and nine-day builds have identical overlap fingerprints. |
| H2 — no normalized rejection ledger | The repaired materializer exposes structural reconciliation counters, including opaque/shared targets, but does not yet persist a row-level rejection ledger for every malformed provider item. | **Partially resolved**; explicit rejection-ledger follow-up remains. |
| H3 — no run-scoped provider telemetry | Collection manifests persist per-account pages, coverage state/reason, errors, provider requests, and cache hits. | **Closed.** Final run records 3,147 provider requests and 2,256 accepted coverage pages. |
| H4 — failed LLM attempt cost can be lost | Successful/reused decision cost and cache provenance are persisted, but there is still no append-only ledger guaranteeing cost capture for every failed provider/model attempt. | **Pending follow-up**; not required to claim structural correctness. |
| H5 — triage completion/publication ordering | Items carry `completed_at`, exact-hash reuse is explicit, and stale cohorts fail closed. A separate explicitly published triage-generation pointer is not yet present. | **Partially resolved**; final runs are selected only after complete reconciliation during this project. |
| Final proof | July 12–13 terminal collection, final Feed v8 / Event v3 nine-day integrity/fingerprints, provider-edge-only adversarial audit, post-regrouping triage totals/cost/cache telemetry, API/latency proof, and repository checks. | **Closed.** See the final rebuild audit; direct Browser control was unavailable and is disclosed there. |

## Verdict

The stored seven-day corpus is healthy enough to rebuild, but the overnight
roll-forward is **not yet safe to execute as written**. The corrected temporal
projection can be built and validated locally first. Before claiming complete
2026-07-12 and 2026-07-13 coverage or reusing triage decisions, close the four
critical boundaries below.

This is an operational review only. It does not change the canonical-event or
temporal-product contracts owned by the parent task.

## Observed Baseline

Read-only inspection on 2026-07-14 found:

- `data/raw/x/x-content.db`: 772 MiB, SQLite quick check `ok`, 4,419 request
  records, 4,419 response records, 4,419 distinct response payloads, and 63,736
  normalized posts. All stored response and post JSON is valid; no normalized
  post is missing an ID or publication timestamp.
- Raw provider fetch window: `2026-07-12T10:27:24Z` through
  `2026-07-12T10:35:47Z`. The request cache is exact-URL keyed and currently has
  no duplicate `(request_sha256, fetched_at)` collisions.
- `data/derived/signal-feed/feed.db`: 27 MiB, quick check `ok`, one current run
  covering 2026-07-05 through 2026-07-11 with 11,062 selected source posts,
  15,642 normalized posts, and 8,232 relations.
- `data/derived/signal-events/events.db`: 21 MiB, quick check `ok`, one current
  run with 4,814 stored multi-post clusters, 13,436 members, and 8,898 links.
- Seven `triage-v2.2-top1000` run databases contain 6,445/6,445 complete rows,
  no currently failed rows, and `$8.207022` of proxy-reported successful-call
  cost. Failed/retried attempt cost is not represented in that total.
- Current main-file SHA-256 values (diagnostic, not a recovery artifact):
  raw `3c1a19581900f020b77c4969fa180718abea8df9f22f056dd88d73ef29b656d4`,
  Feed `81d19a4b1912dc3e6ed251bb311021eb3d3eb9ca71a5d254aa10a5da6f8482a6`,
  Events `e5860a3e67a7b21cc1d98e0c0589d642aff6109a63a5759524f85d8162c289ae`.

## Critical Gaps

### C1 — There is no resumable, date-complete X collection command

`x_content.db` safely caches exact provider pages, but it does not record a
collection run, frozen cohort hash, account-level cursor/checkpoint, requested
UTC interval, or terminal coverage reason. The existing cohort-wide caller is
`registry-evaluation run`; it fetches only enough pages to accumulate the most
recent 20 non-reply/non-retweet posts and then performs an LLM evaluation. It
cannot prove that every account was paged back through the start of July 12.

Consequences:

- a crash followed by `--refresh-x-content` can re-fetch completed accounts;
- a resume without refresh depends on the 24-hour TTL and may refetch after it
  expires;
- high-volume accounts can stop before reaching the requested day boundary;
- there is no auditable distinction between complete, protected, deleted,
  empty, rate-limited, and failed accounts;
- provider request count/spend cannot be attributed to the bounded fresh-data
  proof.

**Gate:** add a raw-only collector with a frozen Registry cohort fingerprint
and one durable account row per run. An account is terminal only when its
oldest fetched item reaches the UTC start boundary, the provider returns no
next cursor, or a documented terminal state is observed. Cursor, pages,
requests, oldest/newest timestamps, cache hits, state, and error must be
checkpointed after every page. Do not use `registry-evaluation run` as the
July 12–13 collector.

### C2 — A corrected event can silently retain and display stale triage

`freeze_run()` returns immediately when `run_meta` already exists. It does not
recompute the current event cohort or compare its stored cohort hash with the
corrected Event read model. The web projection then joins a completed decision
by `event_id` only; it does not verify that the decision's `input_sha256`
matches the envelope currently shown.

That becomes especially dangerous once event IDs are stabilized: the ID may
correctly remain the same while nested relations or as-of membership change
the envelope. The old keep/drop decision would look current even though the
model never saw the new snapshot.

**Gate:** a triage decision is reusable only by the exact pair
`(stable_event_id, input_sha256)`. The web/API layer must mark a snapshot as
unevaluated when its current input hash has no completed matching decision.
Never resume the repaired corpus in an old run database without recomputing
and validating its cohort fingerprint. Create a new repair run and copy or
reference only exact-hash matches.

### C3 — A two-day derived refresh would hide the repaired seven days

The web read models choose the latest Feed/Event run. If fresh collection is
followed by `signal-feed refresh --through 2026-07-13 --days 2`, that run
becomes latest and July 5–11 disappear from the product even though the data
still exists in an older run.

**Gate:** the post-repair roll-forward must rebuild the complete displayed
window:

```bash
.venv/bin/fli signal-feed refresh \
  --source-db data/raw/x/x-content.db \
  --feed-db <candidate-feed-db> \
  --through 2026-07-13 \
  --days 9
```

Raw collection is bounded to two new days; the derived product run is a
nine-day projection.

### C4 — Feed, Events, and triage do not have one atomic publication boundary

Each individual materialization is transactional, which protects against a
partial run inside one database. The product, however, reads three independent
SQLite stores. A clean schema replacement or file swap can expose a new Feed
with an old Event run, or a new Event envelope with an old triage decision.
This is more acute because the current Event schema has no explicit
old-version rejection/migration probe, while the project intentionally replaces
unfinished derived schemas rather than adding compatibility reads.

**Gate:** build a candidate Feed/Event pair outside the live paths, validate
the explicit `feed_run_id -> event_run.feed_run_id` relationship, reconcile
triage by snapshot hash, and publish only after all gates pass. Prefer a small
manifest/current-generation pointer or a maintenance-window swap of the whole
generation. Do not delete the previously served generation until the new one
has passed live API smokes. Use SQLite backup APIs for any database with WAL;
do not copy only the main `.db` file.

## High-Severity Gaps

### H1 — Rebuilds are based on mutable normalized post rows, not a pinned raw snapshot

Raw responses are append-preserved, but `x_post` is a latest-observation table.
A provider refresh updates text/metrics/raw hash in place. Feed run IDs are
therefore reproducible from the *current* normalized table, not necessarily
from the exact raw state used by a previous run.

Before provider collection, create a consistent SQLite backup of the raw DB
and record its SHA-256. Treat that snapshot (or a recorded raw-response cutoff)
as the source of the repaired historical rebuild. Record the post-collection
snapshot separately.

### H2 — Normalization can skip malformed records without a durable rejection ledger

Current stored rows are clean, but Feed selection/normalization contains
`continue`/`None` paths for JSON, timestamp, or identifier problems. Run counts
do not explain each rejected source row. A future provider shape change could
therefore shrink the derived corpus without an actionable failure.

Materialization should either fail closed or emit durable counts and sampled
reasons for every rejected row. Require the invariant:

```text
selected source rows = normalized direct rows + explicitly rejected rows
```

Embedded-target and relation reconciliation need equivalent counters.

### H3 — Raw failures and provider spend are not auditable at run scope

Successful response JSON is preserved, but failed HTTP/provider attempts are
not represented in `raw_response`. There is no bounded-run summary tying
requests, cache hits, retries, terminal errors, and provider spend/credits to
July 12–13. Add these to the collection manifest and append the final telemetry
to the build log. Cost is telemetry, not a gate.

### H4 — Failed LLM attempts can be missing from cost totals

Successful calls persist the LiteLLM response cost and cache token usage.
When a call incurs cost but fails parsing or persistence before completion,
the row stores the error but not necessarily the attempt's response cost.
Preserve an append-only attempt ledger (or at minimum accumulated attempt
cost/tokens/errors) so retries do not understate spend.

### H5 — Completion ordering is not a reliable triage publication clock

`run_meta.updated_at` is established at freeze time and is not advanced when
the final item completes. The web layer chooses the latest complete run using
that metadata. Concurrent or resumed runs can therefore publish in start-time,
not completion-time, order. Persist `completed_at` on the run and select only
an explicitly published complete generation.

## Safe Execution Order

1. **Quiesce and checkpoint.** Do not run provider or LLM jobs. Make a
   consistent SQLite backup of raw, Feed, Events, Registry, and completed
   triage metadata; record sizes/hashes and `PRAGMA quick_check` results.
2. **Land the deterministic repair only.** Implement recursive provider
   relations, stable canonical event identity/root, as-of projections,
   schema-version rejection, indexes, and current-envelope input hashes.
3. **Build the original seven days into candidate paths.** Pin
   `--through 2026-07-11 --days 7`; capture the emitted Feed run ID and pass it
   explicitly to Event materialization.
4. **Adversarially validate the candidate.** Run integrity/FK checks,
   reconciliation invariants, no-future-evidence assertions, nested-quote
   regressions, repeat-build fingerprints, false-split/false-merge samples,
   and API/browser checks. Do not publish or call an LLM yet.
5. **Reconcile triage without model calls.** Produce counts for exact-hash
   reuse, changed snapshots, new snapshots, and orphaned old decisions. Verify
   the web read model cannot attach a mismatched hash.
6. **Publish the corrected seven-day generation.** Keep the previous
   generation recoverable. Smoke the live API/UI and verify the Anthropic and
   OpenAI/Greg/Ben regressions.
7. **Only now collect July 12–13.** Freeze the unchanged Registry cohort and
   use the new raw-only resumable collector. Resume from account/page
   checkpoints. Validate every cohort account has a terminal coverage state.
8. **Checkpoint raw evidence again.** Record before/after request, response,
   post, and date-coverage counts plus provider telemetry.
9. **Build a nine-day candidate generation.** Use
   `--through 2026-07-13 --days 9`, then materialize Events with the explicit
   Feed run ID.
10. **Triage only new/changed hashes.** Reuse exact matches; run
    `gpt-5.4-mini` only for pending snapshot hashes. Verify LiteLLM tags,
    response cost, cached-token reads, failure/retry accounting, and completion
    manifest before publication.
11. **Publish and prove.** Atomically move the complete generation into
    service, smoke all nine dates, run repository checks, write build-log
    telemetry and limitations, then archive the project only when every Done
    When item is satisfied.

## Candidate Commands and Checks

Use repo-local `tmp/`; these paths are examples and must not be published until
validation passes.

```bash
mkdir -p tmp/temporal-event-projection/before tmp/temporal-event-projection/candidate

# Consistent backups; SQLite .backup includes committed WAL state.
sqlite3 data/raw/x/x-content.db ".backup 'tmp/temporal-event-projection/before/x-content.db'"
sqlite3 data/derived/signal-feed/feed.db ".backup 'tmp/temporal-event-projection/before/feed.db'"
sqlite3 data/derived/signal-events/events.db ".backup 'tmp/temporal-event-projection/before/events.db'"

shasum -a 256 tmp/temporal-event-projection/before/*.db
for db in tmp/temporal-event-projection/before/*.db; do
  sqlite3 "$db" 'PRAGMA quick_check; PRAGMA foreign_key_check;'
done

# Repaired historical candidate.
.venv/bin/fli signal-feed refresh \
  --source-db tmp/temporal-event-projection/before/x-content.db \
  --feed-db tmp/temporal-event-projection/candidate/feed-2026-07-11.db \
  --through 2026-07-11 --days 7

# Read FEED_RUN_ID from the JSON emitted above; never rely on "latest" here.
.venv/bin/fli signal-events refresh \
  --feed-db tmp/temporal-event-projection/candidate/feed-2026-07-11.db \
  --events-db tmp/temporal-event-projection/candidate/events-2026-07-11.db \
  --feed-run-id "$FEED_RUN_ID"

for db in tmp/temporal-event-projection/candidate/*.db; do
  sqlite3 "$db" 'PRAGMA quick_check; PRAGMA foreign_key_check;'
done

# Focused contract proof before full check.
.venv/bin/pytest \
  tests/test_x_content.py \
  tests/test_signal_feed.py \
  tests/test_signal_events.py \
  tests/test_web_events.py \
  tests/test_insight_triage.py \
  tests/test_insight_triage_runs.py

scripts/check-fast.sh
```

After the resumable collector exists and completes, repeat Feed construction
with `--through 2026-07-13 --days 9`. Triage commands must use a **new run ID
and database** for the repaired snapshot set; run `--dry-run` first and inspect
reuse/change counts before sending model calls. The current triage CLI has no
safe cross-run hash-reuse operation, so that capability is part of the gate,
not an operator workaround.

## Stop Conditions

Stop rather than publish or spend when any of the following is true:

- a cohort account lacks a terminal July 12 boundary state;
- a relation endpoint is missing without an explicit rejected-row reason;
- repeating the candidate build changes deterministic fingerprints;
- a historical day exposes evidence after its cutoff;
- an event envelope hash differs while the UI shows an old decision;
- the Event run does not name the exact Feed run being published;
- any SQLite integrity or foreign-key check fails;
- cache telemetry, provider request counts, or successful/retried LLM spend
  cannot be reconciled.
