# Audience Insights v2 evidence-cohort audit

Audit date: 2026-07-14  
Scope: pre-v2-adapter, read-only snapshot; no provider or model calls  
Canonical stores:

- `data/derived/cited-insights/triage/triage-v2.2-canonical-v8-2026-07-{05..13}-top1000/triage.db`
- `data/derived/artifacts/artifacts.db`
- `data/derived/signal-feed/feed.db`

## Conclusion

**Direct evidence:** the proposed top-50 start is a sound bounded baseline: it
contains 360 kept day-event rows, while top 75 contains 515 and top 100 contains
664. The hard top-100 ceiling resolves to 545 distinct event IDs because events
can recur as their envelopes mature across days. Forty-two percent of the
top-50 rows and 39% of the top-100 rows have at least one accepted canonical
artifact.

The current material evidence gap is retrieval, not catalog identity. The
top-100 cohort references 305 distinct artifacts, but only 22 have successful
body text in the pre-adapter snapshot. Of the 22 distinct X Articles in the
cohort, zero have a successful body; three were attempted by the generic
fetcher and 19 were never attempted. This is expected pre-M1 state, not evidence
that 283 artifacts failed: the existing bounded fetch deliberately attempted
only 30 artifacts.

**Recommendation/inference:** begin extraction at top 50, but run the
predeclared lower-rank and drop audit below before treating top 50 as sufficient.
Use the artifact catalog's `source_external_id` as the X Article endpoint's
publishing Post ID. Deduplicate evidence blocks by runner-owned source identity,
reject non-unique quote bindings, and deterministically section the measured
two-item long-text tail rather than summarizing it.

## Canonical-run validation

All nine databases report `envelope-triage-v2.2` /
`envelope-triage-output-v2`. In each database, `COUNT(triage_item)` and the
complete-item count equal `run_meta.expected_count`; there are zero pending or
failed items.

| Day | Expected | Complete |
| --- | ---: | ---: |
| 2026-07-05 | 560 | 560 |
| 2026-07-06 | 863 | 863 |
| 2026-07-07 | 1,000 | 1,000 |
| 2026-07-08 | 1,000 | 1,000 |
| 2026-07-09 | 1,000 | 1,000 |
| 2026-07-10 | 1,000 | 1,000 |
| 2026-07-11 | 937 | 937 |
| 2026-07-12 | 737 | 737 |
| 2026-07-13 | 1,000 | 1,000 |

## Kept cohort and artifact intersection

`Kept` means `decision = 'keep'` and `current_rank <= limit`. An artifact event
is one day-event row with at least one accepted
`artifact_import_candidate`, matched on both `envelope_day` and `event_id`.
The per-day artifact count is distinct within that day; it is not additive
across days.

| Day | Kept <=50 | Kept <=75 | Kept <=100 | <=100 artifact events | <=100 distinct artifacts | <=100 X Article edges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-07-05 | 28 | 38 | 50 | 17 | 46 | 1 |
| 2026-07-06 | 41 | 58 | 70 | 32 | 67 | 7 |
| 2026-07-07 | 45 | 66 | 84 | 35 | 53 | 3 |
| 2026-07-08 | 41 | 60 | 76 | 34 | 55 | 1 |
| 2026-07-09 | 43 | 65 | 82 | 31 | 38 | 2 |
| 2026-07-10 | 46 | 66 | 88 | 35 | 61 | 2 |
| 2026-07-11 | 39 | 54 | 71 | 24 | 42 | 2 |
| 2026-07-12 | 37 | 49 | 63 | 25 | 53 | 5 |
| 2026-07-13 | 40 | 59 | 80 | 27 | 43 | 4 |
| **Total day-event rows** | **360** | **515** | **664** | **260** | n/a | **27** |

Aggregate cross-day identity counts:

| Limit | Kept day-events | Distinct event IDs | Events with artifact | Artifact-event share | Distinct artifacts | X Article day-event edges | Distinct X Articles |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 360 | 296 | 153 | 42.5% | 201 | 16 | 12 |
| 75 | 515 | 425 | 201 | 39.0% | 247 | 19 | 15 |
| 100 | 664 | 545 | 260 | 39.2% | 305 | 27 | 22 |

The top-100 population therefore adds 304 kept rows beyond top 50: 155 at
ranks 51–75 and 149 at ranks 76–100.

## Artifact body state

Success means that at least one `artifact_fetch` row for the artifact has
`status = 'success'`. `Attempted, no success` is counted by distinct artifact,
not by retry attempt. `Never attempted` is not a fetch failure.

| Limit | Distinct artifacts | Body success | Attempted, no success | Never attempted | X Articles | X body success | X attempted, no success | X never attempted |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 201 | 22 | 6 | 173 | 12 | 0 | 3 | 9 |
| 75 | 247 | 22 | 7 | 218 | 15 | 0 | 3 | 12 |
| 100 | 305 | 22 | 8 | 275 | 22 | 0 | 3 | 19 |

All 30 artifacts ever attempted by the bounded fetch are in the top-100
cohort. Their final distinct-artifact outcome is 22 successes and eight
unresolved:

| Stratum | Attempted | Success | Unresolved |
| --- | ---: | ---: | ---: |
| HTML / other | 15 | 13 | 2 |
| Paper | 5 | 5 | 0 |
| Repository | 4 | 4 | 0 |
| Video | 3 | 0 | 3 |
| X Article | 3 | 0 | 3 |

The unresolved HTML/other items are one client-rendered Paperform shell and one
LinkedIn transport failure. Video and X failures came from the generic public
fetch path; they do not test the proposed provider Article adapter.

## X Article identity and fetch key

### Direct measurements

- The complete canonical artifact catalog contains 116 distinct X Articles,
  116 distinct `source_external_id` values, and 116 matching raw provider
  snapshots.
- All 116 matched raw snapshots have a top-level `article` object, non-empty
  title, non-empty preview, and an entity URL equal to the catalogued
  `/i/article/...` URL.
- The top-100 v2 cohort contains 27 day-event-Article edges representing 22
  distinct Articles and 22 distinct source Post IDs.
- For all 22, the numeric `/i/article/...` identity differs from the source Post
  ID. The Article identity must therefore not be passed as a Post ID.
- For every one of the 27 top-100 edges, at least one embedded metadata record
  carries the correct publishing Post ID. However, 24 edges also contain one or
  more outer/disclosure Post IDs associated with the same nested Article; one
  edge has 23 distinct metadata rows. In total, 110 distinct embedded metadata
  records collapse to the 27 actual day-event-Article edges.
- The canonical catalog resolves this ambiguity: every Article maps one-to-one
  to a unique `artifact_import_candidate.source_external_id`. For 13 of 27
  day-event edges the source and disclosure Post are the same; for 14 they are
  different.

### Recommendation/inference

The provider Article adapter should take the catalogued
`source_external_id` plus its `source_snapshot_sha256` as the durable request
key. It should not take:

1. the numeric `/i/article/...` identity;
2. the first `embedded_artifacts[].post_id`; or
3. `disclosure_external_id` unless it is identical to the source ID.

The excess embedded associations are consistent with outer posts embedding a
quoted Article payload. This likely explains the multiplicity, but the cause is
an implementation inference; the measured ambiguity itself is direct. Preserve
title and preview as metadata only. They are not Article-body evidence.

## Exact-text and token outliers

### Existing post-envelope input

The character counts below are exact `length(input_text)`. Token counts are
provider-recorded `input_tokens` from the completed triage call and include the
stable prompt, so they are not a tokenization of variable evidence alone.

| Limit | Day-event rows | Input characters | Mean chars | Min chars | Max chars | Mean provider input tokens | Min tokens | Max tokens |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 360 | 1,010,422 | 2,806.7 | 276 | 26,198 | 2,830.0 | 2,216 | 8,227 |
| 75 | 515 | 1,269,754 | 2,465.5 | 276 | 26,198 | 2,744.1 | 2,216 | 8,227 |
| 100 | 664 | 1,493,659 | 2,249.5 | 276 | 26,198 | 2,694.9 | 2,216 | 8,227 |

For top 100, exact character percentiles are p50 1,178, p90 4,954, p95
7,534, and p99 18,099. Provider input-token percentiles are p50 2,432, p90
3,323, p95 3,949, and p99 6,382. The largest post-only envelope is 26,198
characters / 8,227 provider input tokens.

### Successfully fetched artifact bodies

There are 22 successful body snapshots, none marked truncated and no duplicate
`text_sha256` values. Exact size observations:

- minimum: 1,848 characters;
- p50: 10,992 characters / 1,729 whitespace-delimited words;
- p90: 42,530 characters;
- p95: 42,607 characters;
- maximum: 470,148 characters / 69,878 words.

Two bodies exceed 100,000 characters:

| Artifact | Characters |
| --- | ---: |
| `https://arxiv.org/abs/2603.18073` | 470,148 |
| `https://gwern.net/scaling-hypothesis` | 103,253 |

No Luna-compatible local tokenizer was used during this no-call audit, so there
is deliberately no invented token estimate for artifact bodies. The existing
provider token observations exclude those bodies. V2 should record actual
request tokens after adding body evidence.

**Recommendation/inference:** use full normalized text for the measured main
body distribution, but predeclare a deterministic section/chunk path above
60,000 characters. That boundary isolates only the two measured outliers. Each
chunk must retain artifact ID, complete-text SHA-256, section/chunk ordinal,
exact character offsets, and verbatim text. Never make an LLM summary the
primary citable source.

## Duplicate source and quote-binding risk

### Direct measurements

- The 664 top-100 day-event rows contain 545 distinct event IDs. Of these, 104
  recur across days, producing 119 repeat day rows. Ninety-one event IDs occur
  on two days, 11 on three, and two on four.
- The envelopes contain 3,502 post-source occurrences and 2,472 distinct Post
  IDs. There are no duplicate Post IDs within one packet, no exact identical
  non-empty post texts from different Post IDs within one packet, and no Post
  reused by multiple events on the same day.
- Two packet/source pairs have one complete post text contained inside another
  source text. They are the same repeated event on 2026-07-08 and 2026-07-09;
  this is a concrete lower bound on future multi-block quote ambiguity.
- Across days, 822 Post IDs recur. Seven Post IDs appear under two distinct
  event IDs as envelopes evolve.
- The 305 top-100 artifacts create 472 day-event-artifact edges. A total of 109
  artifacts recur, with a maximum of eight edges, four days, and five event IDs.
- The 22 fetched body snapshots have zero duplicate text-hash groups.
- X Article embedded metadata is highly duplicated as described above, even
  though its catalog identity is one-to-one.

### Recommendation/inference

1. Build at most one evidence block per `(provider, Post ID, snapshot SHA)` and
   one per `(artifact ID, text SHA, section/chunk ordinal)`.
2. Keep event-day rows for daily provenance, but use event and artifact identity
   during editorial deduplication. Reappearance on a later day requires a
   material new fact, not merely a newer envelope.
3. Change citation acceptance from “first matching source” to exactly one
   matching source. Persist matching block ID, exact character offsets, source
   snapshot hash, and `matching_source_count = 1`; reject zero or multiple
   matches.
4. Deduplicate X title/preview records before rendering an evidence packet and
   never cite the preview as body text.

## Predeclared recall audit

The audit must be deterministic, rank-blind to the evaluator, and run for both
audiences. It tests the top-50 cutoff and upstream triage separately.

### Population

| Stratum | Population |
| --- | ---: |
| Kept ranks 51–75 | 155 |
| Kept ranks 76–100 | 149 |
| Dropped ranks 1–25 | 45 |
| Dropped ranks 26–50 | 45 |
| Dropped ranks 51–75 | 70 |
| Dropped ranks 76–100 | 76 |

### Deterministic sample

1. **Lower-kept sample:** for every day, select two kept events from ranks
   51–75 and two from ranks 76–100: 36 day-event rows total.
2. **Article census:** add every lower-kept X Article edge at ranks 51–100 not
   already selected. There are 11 such day-event edges in the current snapshot,
   representing 10 additional Article identities before overlap with the
   36-row sample.
3. **Drop sample:** for every day, select one drop from ranks 1–25, one from
   26–50, and one from 51–100: 27 day-event rows total. Every day has at least
   one candidate in each stratum.
4. Within a stratum, order by SHA-256 of
   `audience-insights-v2-recall-v1|day|band|event_id` and take the first rows.
   Store the resulting IDs before evaluation. If a repeated event was already
   selected in the same audit, take the next hash-ordered event and record the
   replacement.
5. Remove Feed rank, triage decision, engagement, and popularity features from
   evaluator input. Evaluate the same frozen packet independently under the
   Investment and AI Engineering contracts.

This is at most 74 distinct day-event rows before repeated-event replacement
(36 lower kept + up to 11 Article additions + 27 drops), or at most 148
audience evaluations. It is deliberately a recall probe, not a statistically
powered population estimate.

### Expansion and failure rules

- A lower-kept item is a **useful miss** only if it is citation-valid, passes
  that audience's usefulness and actionability rubric, is not redundant with a
  higher candidate on that day, and would enter or materially diversify the
  final 3–5.
- One useful miss in ranks 51–75 widens that day/audience to top 75. One useful
  miss in ranks 76–100 or the lower-rank Article census widens it to top 100.
  Widen only that day/audience unless the same failure pattern appears on three
  or more days.
- A dropped item is a triage false negative under the same test. Any
  high-consequence false negative, or two ordinary false negatives for one
  audience, triggers triage diagnosis and a second frozen sample. It does not
  silently override the drop or broaden every run.
- Record no-insight, redundant, citation-failed, audience-useful, actionable,
  and final-set-worthy separately. Do not collapse them into one opaque score.

## Query contract and reconciliation

The measurements were produced with read-only SQLite joins using these core
predicates:

```sql
-- Cohort row
triage_item.status = 'complete'
AND triage_item.decision = 'keep'
AND triage_item.current_rank <= :limit

-- Canonical event-to-artifact intersection
artifact_import_candidate.envelope_day = cohort.day
AND artifact_import_candidate.event_id = cohort.event_id
AND artifact_import_candidate.decision = 'accepted'

-- Usable body
EXISTS (
  SELECT 1 FROM artifact_fetch
  WHERE artifact_fetch.artifact_id = artifact.artifact_id
    AND artifact_fetch.status = 'success'
)

-- X publishing-source validation
feed_post.post_id = artifact_import_candidate.source_external_id
AND feed_post.raw_sha256 = artifact_import_candidate.source_snapshot_sha256
```

Reconciliation checks:

- per-day kept counts sum independently to 360 / 515 / 664;
- top-100 artifact event rows reconcile to 260 of 664;
- 472 day-event-artifact edges collapse to 305 artifact identities;
- 27 X day-event-Article edges collapse to 22 Article identities and 22 source
  Post IDs;
- 22 successes + 8 attempted unresolved + 275 never attempted = 305 top-100
  artifacts; and
- all 116 catalogued X Article source IDs reconcile to one matching raw source
  snapshot with Article metadata and the same entity URL.
