# Temporal Event Projection: Adversarial Data and Performance Review

## Post-repair resolution

The review that follows remains the measured pre-repair baseline. The table
below records the replacement contract after final nine-day publication and
performance proof. Exact run evidence lives in the final rebuild audit.

| Review finding | Resolution | Status / evidence |
| --- | --- | --- |
| Future evidence leaks into earlier days | Daily projection applies an explicit UTC cutoff to member/content first disclosure and relation discovery, exposes cumulative and selected-day counts, and marks `evidence[].is_new_on_day`. An old embedded relation first exposed by a later wrapper is not visible earlier. | **Closed.** Nine-day audit has zero post/relation/link cutoff violations. |
| Root changes across days | Identity and presentation root are derived from the provider-edge component visible at the selected cutoff. A later-disclosed bridge may merge a later projection but cannot rewrite an earlier component. | **Implemented**; covered by cutoff-local component and future-wrapper regressions. |
| `event_id` hashes mutable full membership | Cutoff-local IDs derive from provider-qualified post structure. Quote, retweet, and explicit reply-parent are the only grouping edges; conversation IDs are metadata only. | **Implemented for daily/weekly projections**; a general cross-generation alias ledger remains **deferred**. |
| Latest-created run becomes active | One explicit `signal_publication` selects the validated Event/Feed pair; merely building a run does not publish it. | **Implemented**; covered by atomic-publication tests. |
| Calendar count means candidate posts | Event date payloads count projected envelopes under the same active publication/Registry boundary used by the list. | **Implemented** in the event API; API count equality is regression-covered. |
| Triage joins by event ID alone | Current snapshot content/topology hashes are persisted; web triage attaches only a matching completed hash and exact unchanged inputs may be reused across compatible runs. | **Implemented**; covered by snapshot mismatch, topology-change, and exact-reuse tests. |
| Weekly rollup missing/double-count-prone | Weekly output projects the full provider-edge envelope visible through week-end with unique posts and Registry participants. It does not concatenate daily projections. | **Closed.** Nine-day weekly projection has 6,643 unique envelopes and passes duplicate ownership checks. |
| Full-run read cost and query shape | Feed/Event schemas add day, event-member, relation, conversation, and publication-oriented indexes; read paths project only the published run and requested window. | **Closed.** Cold/warm keep-filter API reads complete locally in 16–24 ms. |
| Registry/ranking context changes historical scores | Registry rejection changes are intentionally reflected without rebuilding evidence, while attention remains day-specific. A frozen historical score-context generation is not part of this repair. | **Deferred follow-up** before future Registry expansion. |
| UI continuation semantics | A continuing card identifies its prior date and selected-day additions; earlier cumulative context stays behind the existing disclosure. | **Implemented.** API/product regressions cover two-day and seven-day continuations; direct final Browser control was unavailable and is disclosed in closeout. |
| Final proof | July 12–13 collection, final Feed v8 / Event v3 nine-day fingerprints, post-regrouping triage, full-corpus adversarial audit, live API smokes, latency observation, and `scripts/check-fast.sh`. | **Closed.** All machine-verifiable gates pass; Browser limitation is explicit. |

Date: 2026-07-14  
Scope: read-heavy review of the event store, daily Feed API, triage attachment,
attention boundaries, frontend contract, SQLite query shape, and proposed weekly
rollup. The measurements below describe the pre-projection implementation
inspected on 2026-07-14; they are regression evidence for the replacement.

## Verdict

Do not rerun triage or publish additional daily/weekly output on top of the
current event read model. The exact structural clustering is valuable, but the
daily projection is not temporally sound:

- `event_day` selects events active on a requested day, then the API expands
  each selected event with **all members and links from the full multi-day
  cluster**;
- the API ignores the stored representative and chooses a new display root
  from the requested day's ranked candidates;
- `event_id` is a hash of the full mutable member set, so adding a later member
  changes the identity of the event;
- triage is joined by that unstable `event_id`, without proving that the current
  envelope matches the model input hash.

The correct replacement is one stable canonical event plus explicit, immutable
daily projections bounded by a UTC cutoff. Weekly output should be another
projection over the canonical event, not a concatenation of daily payloads.

## Severity summary

| Severity | Finding | Consequence |
| --- | --- | --- |
| Critical | Daily API leaks future event members | Historical day can contain evidence published on later days |
| Critical | Event identity hashes mutable membership | Identity, URLs, triage joins, and citations break when an event grows |
| High | Display root is recomputed per day | The same event appears to change its subject across days |
| High | Latest-created run is implicitly active | A later backfill can silently replace the production projection |
| High | Date counts are candidate posts, not envelopes | Calendar numbers do not match the Feed rows they appear to describe |
| High | Triage joins only on `event_id` | A decision can be shown against an envelope the model never saw |
| High | Attention context is not versioned | Historical scores can change after Registry/ranking refreshes |
| High | Weekly projection is not implemented | Naive aggregation would double-count cumulative members |
| Medium | API repeatedly loads a full feed run per day | Memory and cold latency scale with run size times cached days |
| Medium | Nested relationships can be lost or over-merged | Exact quote/reply evidence can split or unrelated reply branches can merge |

## 1. Future leakage in the daily API — Critical

### Evidence

`src/fli/web/events.py:30-59` first selects clusters through `event_day`, but
then loads every `event_member` and `event_link` row for those event IDs without
a publication cutoff. `src/fli/web/events.py:282-319` turns all of those rows
into visible evidence. `member_count`, `link_count`, and `latest_evidence_at`
are then calculated from the full cluster at `src/fli/web/events.py:367-390`.

SQLite audit of the active seven-day run:

- 660 event/day rows exposed at least one later member;
- 1,386 future members leaked backward;
- 585 distinct events were affected;
- every one of the 581 multi-day events returned a later
  `latest_evidence_at` and constant full-run membership on earlier days.

Affected event/day rows by date:

| UTC day | Active events | Events with future evidence |
| --- | ---: | ---: |
| 2026-07-05 | 401 | 52 |
| 2026-07-06 | 658 | 95 |
| 2026-07-07 | 834 | 124 |
| 2026-07-08 | 940 | 120 |
| 2026-07-09 | 1,021 | 140 |
| 2026-07-10 | 954 | 129 |
| 2026-07-11 | 666 | 0 |

The final day has no leak only because there is no later day inside that run.

### Required contract

For selected day `D`, use one explicit cutoff, preferably
`D 23:59:59.999999 UTC` for a complete-day product:

- include only members with `published_at <= cutoff_at`;
- include a relationship only when both endpoints are visible by the cutoff;
- calculate cumulative counts from that visible set;
- separately calculate members first active on `D`;
- require `latest_visible_evidence_at <= cutoff_at`.

Suggested API fields:

```text
event_id                       stable canonical identity
snapshot_id                    immutable event/day projection identity
snapshot_sha256                hash of the projected model input
active_day                     selected UTC day
cutoff_at                      projection boundary
canonical_root                 stable across all projections
root_is_prior_context          root predates active_day
cumulative_member_count        all visible members through cutoff
new_member_count               members published on active_day
latest_visible_evidence_at     never later than cutoff_at
evidence[].is_new_on_day       distinguishes context from daily change
```

### Required tests

1. Monday root plus Tuesday quote: Monday excludes the quote; Tuesday contains
   root context and quote.
2. Monday API satisfies `latest_visible_evidence_at <= cutoff_at`.
3. Tuesday cumulative count is two and delta count is one.
4. A link whose target is after the cutoff is absent, even if its source is
   visible.
5. Querying days in any order returns identical projections.

## 2. Root selection changes across days — High

The materializer already persists a representative in
`event_cluster.representative_provider` and `representative_post_id`
(`src/fli/signal_events.py:43-54`, selection around
`src/fli/signal_events.py:346-355`). The API ignores it.

`src/fli/web/events.py:62-83` chooses `_root_post_id` again, constrained to the
current day's ranked candidates. The call at `src/fli/web/events.py:328-331`
therefore makes root identity a property of a view and sort boundary rather
than of the canonical event.

Live API audit found 99 of 581 multi-day event IDs with different displayed
roots across their daily views. Examples:

- `7695fe85e69d…`: root `2073834151858344016` on July 5 and
  `2073876896165544126` on July 6;
- `55ef519c3ea9…`: root `2073100352921215386` on July 5/6 and
  `2074255513353642090` on July 7.

**Recommendation:** choose and store one canonical root independently of day
ranking. A later day may show that root as muted prior context, but must not
replace it. Day-level attention and day-level representative evidence are
separate fields, not event identity.

Regression tests must prove that root ID is unchanged across days, sort orders,
Registry changes, and the addition of later members.

## 3. `event_id` is not stable — Critical

`src/fli/signal_events.py:356` derives `event_id` by hashing the sorted complete
member set. This makes the identifier change when:

- a new quote, repost, reply, or missing parent is discovered;
- a new day is appended;
- a rolling window drops an old member;
- recursive relationship normalization repairs a previously split cluster.

That breaks triage reuse, deep links, citations, cross-day continuity, and
weekly deduplication.

**Recommendation:** define a stable canonical key from an exact provider anchor,
normally `(provider, canonical_root_post_id)`. If later evidence proves a
different root, preserve redirects/merge provenance rather than silently
renaming the event. Useful fields/tables:

```text
canonical_event(event_id, provider, canonical_root_post_id,
                clustering_contract_version, created_at)
event_alias(alias_event_id, canonical_event_id, reason, recorded_at)
event_revision(event_id, revision_id, member_set_sha256, cutoff_at, created_at)
```

Regression tests must keep `event_id` stable when a day/member is added, when a
rolling window changes, and when the same input is rebuilt.

## 4. Run activation is implicit and unsafe — High

Both `src/fli/web/events.py:24-27` and `src/fli/web/feed.py:68-72` select the
run with greatest `created_at`, then lexical `run_id`. The event materializer
also chooses the newest-created Feed run (`src/fli/signal_events.py:161`).

A historical backfill or shorter diagnostic run created tonight can therefore
become the production Feed, even if yesterday's active run covers more days.
Same-second timestamps are resolved by hash ordering rather than intent.

**Recommendation:** add an explicit single-row active-run manifest (or
`activated_at` controlled by a promote command). Building a run must not
activate it; validation followed by promotion should. Test that a later-created
historical backfill does not replace the active nine-day run.

## 5. Calendar counts have the wrong meaning — High

`src/fli/web/events.py:537-552` delegates date counts to
`feed_store.dates_payload()`. That function counts Registry-gated candidate
posts, not canonical event/day projections.

Measured mismatch:

| UTC day | Calendar candidate posts | Event envelopes |
| --- | ---: | ---: |
| 2026-07-05 | 719 | 569 |
| 2026-07-06 | 1,200 | 904 |
| 2026-07-07 | 1,557 | 1,154 |
| 2026-07-08 | 1,769 | 1,243 |
| 2026-07-09 | 2,071 | 1,403 |
| 2026-07-10 | 1,865 | 1,318 |
| 2026-07-11 | 1,371 | 972 |

The frontend labels the returned value as the day's count
(`frontend/src/pages/Feed.tsx:568-579`). Return `envelope_count` from the same
daily projection used by the list. If candidate count remains useful, expose it
under the explicit name `candidate_post_count`.

Regression test: `/api/events/dates[day].envelope_count` equals
`/api/events?date=day&triage=all.total` under the same active run and Registry
state.

## 6. Triage can be attached to the wrong envelope — High

The triage run database correctly records `input_sha256`, but
`src/fli/web/triage.py:86-100` reads only `event_id`, `decision`, and `reason`.
`src/fli/web/events.py:399-400` attaches that result to the current event solely
by event ID.

Audit of seven top-1,000 runs:

- 6,445 completed rows;
- 5,846 unique event IDs;
- 5,947 unique input hashes;
- 496 repeated identical `(event_id, input_sha256)` evaluations;
- 8 event IDs changed decision across different daily inputs;
- no identical input hash changed decision.

The model behavior is stable; the join boundary is not.

**Recommendation:** triage identity is
`(prompt_version, schema_version, input_sha256)`. Store the current
`snapshot_sha256` on each event/day projection and only display a decision whose
input hash matches. Reuse a completed decision for identical hashes instead of
calling the model again.

Required tests:

- a decision for Monday is not attached to a different Tuesday snapshot;
- identical envelope hashes reuse one result;
- an event revision invalidates stale triage without deleting audit history.

## 7. Weekly rollup must be a projection — High

No weekly projection implementation exists in `src/fli` at review time. Do not
build it by concatenating daily API rows: corrected daily rows are cumulative,
so doing that would repeat the root and earlier members once for every active
day.

Weekly contract:

- one row per stable canonical event through week-end cutoff;
- unique members by `(provider, post_id)`;
- explicit `first_active_day`, `active_days`, `week_new_member_count`, and
  `member_count_through_week_end`;
- no evidence after Sunday 23:59:59.999999 UTC;
- a documented weekly score definition (recompute over weekly activity rather
  than taking an unexplained maximum is easiest to defend).

Tests: a three-day event appears once, each post appears once, next-week
evidence does not leak, and weekly membership equals the union of visible
event members—not the sum of daily counts.

## 8. Attention is not reproducible without a score context — High

Relationship rows are correctly day-bounded, but historical attention uses the
current Registry and current/latest network-support analysis. Public metrics
also represent the provider snapshot that happened to be stored, not
necessarily the value at the end of the historical day.

Choose and document one of these valid semantics:

1. **Frozen historical score:** each projection stores its Registry version,
   ranking run, metric observation time, and resulting components; or
2. **Dynamic present-day lens:** historical evidence is rescored under the
   current network, and the UI says so while exposing a `score_context_id`.

Do not imply an as-of-day score without the first contract. Add
`metrics_observed_at` because `feed_post` currently stores counts without their
observation timestamp.

Required fields: `score_context_id`, `registry_version`, `ranking_run_id`,
`metrics_observed_at`, and component values. Test either frozen invariance or
intentional context-version change after Registry/ranking refresh.

## 9. Exact-relationship boundary risks — Medium

Two structural problems deserve regression coverage alongside the temporal
repair:

- the pre-repair Feed normalizer expanded only one embedded quote/repost level,
  so nested wrappers could split from the real original;
- `signal_events.add_link` discards a relation when either endpoint is missing,
  losing provenance that could become resolvable in a later refresh;
- conversation fallback can attach replies to the first captured reply when the
  true root is absent, potentially combining independent branches.

Prefer recursive exact normalization with cycle/depth protection. Preserve
unresolved exact relations in a small table instead of dropping them. Decide
explicitly whether a whole provider conversation is one envelope; if not,
cluster parent-connected components.

Tests: nested quote depth greater than one, temporarily missing target later
captured, absent conversation root with two independent reply branches, and
cycles in malformed provider payloads.

## 10. Query and index review

### Current measurements

- warm local `/api/events` requests were approximately 20–50 ms per day on the
  seven-day dataset;
- derived stores were small (Feed about 27 MB, events about 20 MB), although the
  raw X store was about 772 MB;
- the existing `(run_id, day, event_id)` event-day index and event member/link
  primary keys are adequate for the current derived-store size.

This is not an emergency latency problem. Correct projection boundaries first.

### Current scaling risks

`src/fli/web/events.py:263-268` loads every `feed_post` in the run for each cold
day cache entry and filters in Python. With seven independently cached days,
the same full run is read and retained repeatedly. `_event_rows` also builds a
large dynamic `IN (...)` list of event IDs. Both are acceptable at current
scale but poor long-term boundaries.

Build the daily read model so the API reads only one requested projection and
its visible members. Run `ANALYZE` after materialization. Suggested indexes:

```sql
-- One immutable row per event/day projection.
PRIMARY KEY (run_id, day, event_id)
INDEX event_snapshot_rank (run_id, day, attention_score DESC, event_id)

-- If cumulative membership is queried rather than fully materialized.
INDEX event_member_cutoff
  (run_id, event_id, published_at, provider, post_id)

-- Fast calendar summaries.
PRIMARY KEY (run_id, day)  -- event_day_summary

-- Stable canonical lookup.
UNIQUE (provider, canonical_root_post_id)  -- canonical_event
```

Avoid speculative duplicate indexes. `EXPLAIN QUERY PLAN` and timings should be
captured after the new schema exists. The target is one bounded SQLite query for
the page plus one bounded evidence query, not a full-run Python hydration.

## Recommended implementation order

1. Introduce stable canonical event identity and an explicit active-run pointer.
2. Materialize cutoff-bounded daily snapshots with hashes and correct counts.
3. Switch `/api/events`, `/api/events/dates`, and the frontend to the new fields.
4. Recompute and attach triage by matching input/snapshot hash.
5. Re-run triage only for changed corrected envelopes; reuse exact hashes.
6. Add the weekly projection after daily invariants pass.
7. Run the adversarial fixture suite, `EXPLAIN QUERY PLAN`, API timing, and a
   manual Feed audit before promoting the run.

## Release invariants

The corrected project is not complete until all of these are machine-checked:

- `latest_visible_evidence_at <= cutoff_at` for every daily row;
- every visible relationship has two visible endpoints;
- a canonical event has the same root and event ID across every day;
- cumulative membership is monotonic across a growing window;
- `new_member_count` equals the set difference from the prior day;
- date `envelope_count` equals the list API total;
- triage input hash equals the current snapshot hash;
- an inactive/backfill run cannot become live without promotion;
- weekly membership is a set union and never a sum of cumulative daily counts;
- API ordering is deterministic under score ties (`event_id` final tie-breaker).
