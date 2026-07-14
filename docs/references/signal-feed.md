# Signal Feed Operations

The Feed is the deterministic evidence layer between stored public output and
future LLM extraction. It currently accepts X posts, but its API contract is
source-oriented so later blog, paper, and release evidence can enter as another
provider without changing Registry identity.

## Storage Boundary

- `data/raw/x/x-content.db`: immutable provider responses, a mutable latest
  `x_post` convenience row, an append-only `x_post_observation` history, and
  exact model-evidence bundles. Historical rebuilds select observations, never
  the mutable latest row.
- `data/derived/signal-feed/feed.db`: rebuildable `signal-feed-v8` runs. Each
  content-addressed run stores its selected direct observations, recursively
  discovered embedded quote/retweet posts, immutable per-snapshot `raw_json`,
  complete declared relation closure, and opaque provider target anchors whose
  payload was not captured.
- `data/derived/signal-events/events.db`: rebuildable `signal-events-v3` runs
  under `exact-structural-v5-provider-edges`. It stores exact multi-post
  components, member/link/anchor facts, per-day membership, and the one-row
  `signal_publication` pointer that names the validated live run. Singleton
  envelopes are added by the read model without duplicating post storage.
- `data/fli.db`: current Registry identity and rejection state. It is read at
  API request time and is never copied into a Feed run.
- `data/derived/following/*/analysis.db`: accepted entity-overlap network
  support used as one score input.
- `data/derived/x-daily-collection.db`: durable collection plans, frozen
  Registry cohorts, per-account coverage state, and exact cached/provider page
  provenance for resumable UTC-day collection.

All large data files are intentionally ignored. The tracked schema, CLI, tests,
and this runbook are the reproducible contract.

## Date-Complete Collection

Freeze the current active, public Registry X cohort and inspect whether the raw
cache already proves complete coverage for an inclusive UTC range:

```bash
.venv/bin/fli x-daily-collection plan \
  --start-day 2026-07-12 --end-day 2026-07-13 \
  --no-input --json
```

The returned run ID binds the range to an ordered cohort checksum. Repeating
the same plan is idempotent. `plan` performs no provider request. Resume missing
accounts with:

```bash
.venv/bin/fli x-daily-collection execute \
  --start-day 2026-07-12 --end-day 2026-07-13 \
  --run-id <run-id> \
  --no-input --json
```

`execute` reuses fresh cached cursor chains and fetches only accounts whose
coverage is insufficient. It records each account as cached, fetched,
protected, or failed and can be rerun after interruption without repeating
completed accounts. Coverage is complete only when a response observed after
the requested end day reaches the start boundary or terminal page; merely
having some posts from the range is not enough. Inspect a durable run without
provider access:

```bash
.venv/bin/fli x-daily-collection status \
  --run-id <run-id> --no-input --json
```

Provider payloads and post observations land in `x-content.db`; the collection
manifest does not duplicate them.

## Rebuild and Publish

```bash
.venv/bin/fli signal-feed refresh --days 7 --through 2026-07-11
.venv/bin/fli signal-events refresh --publish
```

The Feed refresh selects the earliest immutable observation of every top-level
post published in the requested range, recursively materializes embedded
relations, and fingerprints the exact `(provider, post_id, raw_sha256)` input.
An unchanged range therefore reuses the same Feed run ID even after a later
provider refresh updates `x_post` engagement metrics. The default end date is
the previous UTC calendar day; pin `--through` for a reproducible demo.

The Event refresh materializes exact structural components for that Feed run.
`--publish` updates `signal_publication` only after verifying that the referenced
Feed run exists in the selected Feed database. API readers follow this explicit
pointer; they do not pick the newest row by timestamp. Build into candidate
databases and run the temporal audit before publishing when repairing or
extending a production range.

Neither rebuild command makes a provider or LLM call.

## Read Contract

- `GET /api/events/dates` lists complete materialized dates and the number of
  projected envelopes on each date. The number is not a raw post count.
- `GET /api/events?date=YYYY-MM-DD` returns one unified Registry-aware page of
  evidence envelopes at that UTC cutoff. An unrelated post is a singleton;
  provider-declared quote, retweet, and reply-parent links form a component.
  Conversation IDs alone never merge posts. Shared opaque target IDs can
  connect wrappers even when the target
  payload itself is absent.
- `GET /api/events?date=YYYY-MM-DD&projection=week` returns a deduplicated
  seven-day rollup ending on that date.
- `sort=attention|recent|engagement` changes ordering.
- `q`, `limit`, and `offset` provide server-side search and pagination.
- The lower-level `/api/feed` endpoint remains available for inspecting the
  post ledger and score inputs; it is not a separate product mode.

Each grouped response contains one `root` and a related `evidence` list. The
root never repeats in that list. Its `event_id` comes from a stable
provider-qualified canonical post or opaque target rather than the presentation
root. Related rows expose their exact relationship, target or parent post ID,
reply depth, and `is_new_on_day` flag. Posts and links must also have been
disclosed by that cutoff; a relationship embedded in a later wrapper cannot
rewrite an earlier day. The selected-day projection is cumulative through that cutoff: an event continuing from a prior
day includes its earlier context, while `day_member_count`,
`prior_context_count`, `previous_activity_day`, and `is_continuation` expose the
new daily delta. Selecting Monday cannot see Tuesday evidence; selecting
Tuesday may show both the Monday context and Tuesday additions.

The UI renders replies parent-first, labels same-account replies as thread
continuations, keeps unique quote commentary, and collapses retweets into one
traceable amplification strip. Captured parents precede descendants and
siblings are chronological. A reply whose parent was not captured appears as
an explicit unparented branch; the reader never guesses a parent from timing or
text. No URL, embedding, model, or semantic similarity is used to form these
components.

The weekly projection carries daily revisions forward by provider-qualified
visible membership. If a later exact edge merges two earlier components, the
later revision supersedes every overlapping weekly state, so the same post is
not counted twice. `active_days`, `weekly_active_day_count`, and peak daily
attention/interaction values remain available for inspection.

Registry rejection changes are dynamic. On the next request, a rejected author
is absent and a rejected amplifier no longer votes. Raw/derived evidence is not
deleted, so reversing the curation decision restores the evidence. The read
model re-componentizes the surviving structural graph: a rejected renderable
wrapper cannot bridge two otherwise separate envelopes, while an opaque
provider target remains a valid shared anchor.

## Triage Projection

Completed `keep | drop` judgments are snapshot-bound audit metadata, not event
identity and not a replacement ranking. The UI displays a judgment only when
the completed row's `event_id` and `snapshot_content_sha256` match the current
cutoff projection. The runner reuses prior work only when event ID, snapshot
hash, and exact rendered `input_sha256` all match; structural repairs therefore
retain unchanged decisions but cannot attach an old decision to newly merged or
expanded evidence. The API computes keep/drop/not-evaluated counts before
pagination.

## Read Performance

The Feed and exact-event stores already index their date, author, membership,
target, and source-link read paths. Query planning showed those indexes being
used; the expensive work was rebuilding the Registry/network joins and event
projection on every request, not scanning unindexed tables.

The web read model therefore uses state-aware in-process caches. Cache keys
include the current database and WAL file versions, so Registry curation or a
new derived run invalidates stale payloads without a compatibility layer. The
SPA prefetches the other complete days sequentially after the first page is
idle, deduplicates concurrent requests, and mounts expanded evidence trees only
when the operator opens them. A hard reload may pay one cold read; switching
among prefetched days should not repeat SQLite or large hidden-DOM work.

Registry reads remain uncached in the browser because they are already cheap
and should reflect curation promptly. Derived Ranking payloads use the same
state-aware server cache and a page-lifetime client cache; follower detail is
bounded to the 300 nodes visible in the current visualization.

## Daily Score and View Rank

The Feed presents an ordinal rank within the active sorted and filtered view.
Clicking that rank reveals the underlying daily score. The score remains
implemented by the versioned `attention-v1.1` contract; “attention” is the
internal contract name and the broad product question, not the UI label for the
number.

The daily score is an experimental, day-relative ordering aid:

- 55% tracked-amplification percentile: distinct active Registry amplifiers, one
  flat vote per canonical entity regardless of network-support rank;
- 25% author network-support percentile;
- 20% public-interaction percentile (log-scaled likes, replies, reposts, and
  quotes).

Every component is returned with the exact post that produced an envelope's
peak score. Each canonical entity votes at most once, self-amplification is
excluded, and an amplifier's network-support position remains visible without
multiplying its vote. Switching lanes or searching cannot change an item's
daily score, although the ordinal rank changes with the active view. Daily
scores from different dates are not directly comparable. The score does not
claim relevance, quality, truth, novelty, or investment importance.
