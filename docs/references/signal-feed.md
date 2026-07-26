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
- `data/derived/signal-feed/feed.db`: rebuildable `signal-feed-v10` runs. Each
  content-addressed run stores its selected direct observations, recursively
  discovered embedded quote/retweet posts, immutable per-snapshot `raw_json`,
  complete declared relation closure, and opaque provider target anchors whose
  payload was not captured. Reply-inclusive timelines contribute only replies
  whose conversation root is captured in the same run.
- `data/derived/signal-events/events.db`: rebuildable `signal-events-v6` runs
  under `exact-structural-v10-root-owned-reactions`. It stores rooted
  multi-post Events, member/link/anchor facts, per-day membership, and the one-row
  `signal_publication` pointer that names the validated live run. Singleton
  Events are added by the read model without duplicating post storage.
- `data/fli.db`: current Registry identity and rejection state. It is read at
  API request time and is never copied into a Feed run.
- `data/derived/following/*/analysis.db`: accepted entity-overlap network
  support used by the daily Event rank.
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
manifest does not duplicate them. The collection contract requests authored
replies. Feed materialization preserves replies whose conversation root is
captured and excludes reply activity whose root is absent. Event materialization
admits only the source author's replies as Event continuations; third-party
replies remain inspectable in the Feed ledger but do not group or render as
product Events. When a same-author continuation survives but its immediate
parent is missing, the Event projection records an explicit conversation-root
bridge rather than rewriting provider metadata.

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

The Event refresh materializes root-owned Events for that Feed run. Every
member has at most one structural parent. Quote posts and retweets may point to
one source root, while only that source author's replies may extend its thread;
reaction replies cannot import their own branches or bridge two roots.
`--publish` updates `signal_publication` only after verifying that the referenced
Feed run exists in the selected Feed database. API readers follow this explicit
pointer; they do not pick the newest row by timestamp. Build into candidate
databases and run the temporal audit before publishing when repairing or
extending a production range.

Neither rebuild command makes a provider or LLM call.

## Read Contract

- `GET /api/events/dates` lists complete materialized dates and the number of
  projected Events on each date. The number is not a raw post count.
- `GET /api/events?date=YYYY-MM-DD` returns the Registry-aware Events whose
  canonical source day is that date. An unrelated non-reply post is a
  singleton. Provider-declared quote and retweet wrappers attach to one source,
  and same-author reply-parent links extend only that source's thread.
  Third-party replies remain in the lower-level ledger and are not projected as
  singleton cards. Conversation IDs alone never merge posts. Shared opaque
  target IDs can connect wrappers when the target payload itself is absent.
- `GET /api/events?date=YYYY-MM-DD&projection=week` returns a deduplicated
  seven-day rollup ending on that date.
- `sort=rank|recent|engagement` changes ordering.
- `q`, `limit`, and `offset` provide server-side search and pagination.
- The lower-level `/api/feed` endpoint remains available for inspecting the
  post ledger and rank inputs; it is not a separate product mode.

Each grouped response contains one `root` and a related `evidence` list. The
root never repeats in that list. Its `event_id` comes from a stable
provider-qualified canonical post or opaque target rather than the presentation
root. Related rows expose their exact relationship and target or parent post
ID. Every Event appears on exactly one canonical source date and keeps the rank
calculated on that date. Posts disclosed later append to the same Event's
activity ledger and `activity_days`; they do not create a later candidate,
rerank the Event, or change the first-party semantic snapshot unless the
original author supplied new authored material. Selecting a later activity date
therefore does not show a duplicate Event card.

The UI renders one flat expandable activity ledger. Same-author replies and
quote commentary are labeled as author updates; independent reactions remain
attributed activity; retweets collapse into one traceable amplification strip.
There is no current/prior split, continuation badge, or guessed semantic parent.
No URL, embedding, model, or semantic similarity is used to form components.

The weekly projection deduplicates canonical Event publications by stable
root-owned Event ID. Later activity contributes `active_days`,
`weekly_active_day_count`, the best inherited daily rank, and peak interaction
facts without introducing another daily row or replacing the canonical Event.

Registry rejection changes are dynamic. On the next request, a rejected author
is absent and a rejected amplifier no longer votes. Raw/derived evidence is not
deleted, so reversing the curation decision restores the evidence. The read
model re-componentizes the surviving structural graph: a rejected renderable
wrapper cannot bridge two otherwise separate Events, while an opaque
provider target remains a valid shared anchor.

## Audience Routing Projection

Completed AI Engineering and Investment judgments are snapshot-bound audit
metadata, not event identity and not a replacement ranking. The v9 semantic
snapshot contains the root, same-author authored updates, and accepted
first-party artifacts; independently authored reactions and pure reposts are
excluded. The UI displays a route only when the completed row's `event_id` and
public and stored `semantic_snapshot_sha256` match the canonical Event. Later
third-party activity does not trigger rerouting. The runner reuses work only when Event ID,
snapshot hash, and exact rendered `input_sha256` match. The API derives
kept/not-kept/not-evaluated and audience counts before pagination.

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

## Daily Event Rank

The Feed presents one stable rank for every complete canonical-day Event.
Audit filters and search hide rows without recalculating it, so the first
visible not-evaluated Event may correctly be `#1001` rather than another `#1`.
Clicking the rank reveals the ordered evidence behind `daily-rank-v2`; there is
no scalar score and no weighted blend.

Events are ordered lexicographically, descending through the first four layers
and then ascending by stable Event ID:

1. the union of distinct active Registry entities that quote or repost any
   member of the complete Event, with the source entity removed after union;
2. the mean entity-level network position of those trusted voters;
3. the source author's entity-level network position;
4. the maximum `likes + replies + reposts + quotes` on one Event member
   published on the canonical day;
5. stable Event ID as the deterministic final tiebreak.

Each canonical entity contributes at most one vote across the whole Event.
Organization and person voters use the same evidence rule; authority is
represented by the inspectable network positions, not a hidden type bonus.
Public interactions are a snapshot measure and are deliberately only the fourth
layer. Switching filters, searching, or running audience routing cannot change
the rank. The rank answers where to look first; it does not claim relevance,
quality, truth, novelty, or investment importance.
