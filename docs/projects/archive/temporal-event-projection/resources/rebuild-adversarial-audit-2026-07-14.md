# Temporal Event Projection — Final Rebuild and Adversarial Audit

Closeout evidence for the `temporal-event-projection` project. The live local
read model is the final nine-day Feed v8 / Event v3 pair. All counts below were
read from the published candidates or the API after publication.

## Verdict

**Passed.** Recursive provider relations, cutoff-correct daily projections,
deduplicated weekly projections, hash-bound triage, and the bounded July 12–13
fresh-data collection all completed. SQLite integrity, deterministic rebuild,
historical-range invariance, structural adversarial checks, and API hash joins
have no failures.

The remaining limitations are operational follow-ups, not hidden weakening of
the exact-structure contract: collection spend is not exposed by the provider,
failed LLM-attempt cost is not yet append-ledgered, and visual verification was
limited because the in-app Browser bridge was unavailable during final proof.

## Final Publication

### Nine-day Feed v8 / Event v3

Range: **2026-07-05 through 2026-07-13 UTC**

| Fact | Final value |
| --- | --- |
| Feed schema / contract | `signal-feed-v8` / `complete-calendar-days-v7-discovery-cutoff` |
| Feed run | `adb2b4949de74a7a3120e71b62366acfcdca0656d0b49c07af10d4e5323f7f96` |
| Feed source fingerprint | `44d670a59857e29be3541970446c8049650103bc0d62a43ba1088a6e9c867302` |
| Selected source posts | 13,978 |
| Normalized renderable posts / relations | 20,159 / 11,971 |
| Opaque / shared opaque targets | 547 / 37 |
| Event schema / contract | `signal-events-v3` / `exact-structural-v5-provider-edges` |
| Event run | `f8999fcd2b674bf46557023ec8dcab2ac4a8bc115fea8158b4b713a276b588a9` |
| Event input fingerprint | `c10b72633665efabb482a6955b56cff61ec1483821590a3d8aabd1bfc8e572f9` |
| Event clusters / members / links | 5,202 / 17,347 / 12,718 |
| Weekly projection / fingerprint | 6,643 / `de8a443881d82a5c696448d5dc038af6ea4723de67ddfafd50c35146078c5627` |

Both canonical SQLite files pass `PRAGMA integrity_check` and
`PRAGMA foreign_key_check`. The explicit publication pointer references the
Event run above and its exact Feed run; readers do not infer a current run from
timestamps.

### Daily projections

| UTC day | Envelopes | Structural fingerprint |
| --- | ---: | --- |
| 2026-07-05 | 560 | `920f7ac0b18312bb80f46201686ce25fc8e049bb698ed4f6d053c928ca27d5e2` |
| 2026-07-06 | 863 | `ed2f9fb570ff4dacd8e42eb7424224e25dfb675fe2481537d85c1c89760f413a` |
| 2026-07-07 | 1,061 | `b4a1b40103bd3ca7a4588a122275710e090367d17679838acf266a7fd6f422b0` |
| 2026-07-08 | 1,143 | `c05ecfc047b9249896b3c2a3d0f77a0c5d5e8acbe593fdf9506a65f80f9d3923` |
| 2026-07-09 | 1,297 | `16787e00369fff559c02ecec054eaacb3bb89b3c74c3b44a8282a125c1e76ed0` |
| 2026-07-10 | 1,231 | `90045a63754c57cbc1af2df024becca7bbabb0c54973511b85ba3634aabbfcae` |
| 2026-07-11 | 937 | `d3a9a678d2a3e91f3416022d06a75c4ad48536f42bc5c9dff6808671ddb8ab59` |
| 2026-07-12 | 737 | `3e30b420f79af6eb0eacc6fff2202a62a505133b63ab8304dffae29e998cc0ba` |
| 2026-07-13 | 1,099 | `db29b72e254de192bdc02bf59033d4d7eb5377d8283d59d860de46116a9aedaa` |

## Fresh-data Collection

Collection run:
`x-daily-2026-07-12-2026-07-13-99f722779bef`

| Fact | Result |
| --- | ---: |
| Frozen Registry cohort | 2,234 X accounts |
| Cohort SHA-256 | `99f722779bef256f7436da9942ea7a81751d6d25776cb4c9969ee630e2a5cc10` |
| Fetched / cached accounts | 2,225 / 9 |
| Accepted coverage pages | 2,256 |
| Provider requests | 3,147 |
| Pending / failed accounts | 0 / 0 |
| Excluded rejected / protected | 23 / 12 |

Seven coverage-integrity counters are zero. No accepted page predates the
completed horizon. A second plan and execution replay made zero provider calls,
proving resumability and idempotence after the run reached `complete`.
TwitterAPI.io did not return an attributable run-cost value, so provider request
count is the honest telemetry; no synthetic spend is reported.

## Determinism and Range-extension Proof

The final seven-day candidate was rebuilt independently:

- Feed run `d4b12dd74f6958420e7462a661ffebc278dfa7215f9db0f671cac905ce3f5bd0`
- Event run `335d52a6b04c96740b9c3b714f4fef226c05f9fe888725f069365209afc401e3`
- 4,176 clusters, 14,024 members, 10,304 links
- weekly count 6,325, fingerprint
  `ad4bee6e2a9e4814ef9f3b8e1f25a6db84dbbc39abb2400dafcc23a94750f8e6`

The seven-day and nine-day builds produce byte-identical structural
fingerprints for every overlapping July 5–11 projection. Independent repeated
builds also reproduce the same run IDs and semantic audit hashes:

- seven-day semantic audit:
  `6f4d7c578401b6b1a99cbca84f0318145e1b962ff93434297dae40d820dccdd4`
- nine-day semantic audit:
  `185eb0688c615caa2f29d15205405e3f1c733137a7c8d6bb0b5f14a059fc996d`

Fresh provider pages did add legitimate immutable historical observations from
existing Registry channels, so the final July 5–11 counts are higher than the
intermediate Feed v7 / Event v2 baseline. Once raw collection was frozen, the
overlapping seven-day projection became invariant under the nine-day range
extension. This distinguishes valid late discovery from mutable-history drift.

## Structural and Temporal Adversarial Audit

`scripts/audit-temporal-events.py` checks both the seven-day and nine-day
candidates. Both return `ok=true` with an empty failure list. The audit covers:

- SQLite integrity and foreign-key checks;
- only `quote`, `retweet`, and explicit `reply_parent` grouping links;
- every normalized relation represented in Event links;
- no split renderable relation endpoints;
- no provider post owned by more than one event per projection;
- no duplicate daily or weekly event identity;
- no evidence, relation, or link discovery after the requested cutoff;
- stable canonical roots and deterministic daily/weekly fingerprints.

Conversation IDs are retained as metadata and never create grouping edges.
Rejected Registry accounts re-componentize at read time. Opaque targets fail
closed rather than receiving invented relations.

The reported regression is fixed: OpenAI post `2074704958419792299`, Greg
Brockman post `2074707927844446527`, and Ben Hylak post
`2074709406428913753` now belong to one event
`fc976363…`; the Event links preserve Greg → OpenAI and Ben → Greg quote
edges. That 69-member component has one canonical root and one triage input.

The Anthropic global-workspace event keeps one identity across seven active
days. July 6 presents only evidence visible through July 6; July 7 adds the
July 7 delta and marks the card as a continuation. A second event spans six
days, exercising the long-continuation path.

Provider snapshots themselves can change shape over time: among 40,633 posts
observed more than once, 812 had a different recursive relation signature and
36 gained a relation after their first observation. The projection therefore
uses immutable earliest-disclosure provenance rather than the latest provider
shape. This is expected evidence drift, not a projection failure.

## Snapshot-bound Triage

Final run IDs are
`triage-v2.2-canonical-v8-2026-07-DD-top1000`. Every available envelope is
triaged on days with fewer than 1,000 envelopes; otherwise the top 1,000 by
attention are triaged.

| Metric | Total |
| --- | ---: |
| Completed / failed | 8,097 / 0 |
| Keep / drop | 4,402 / 3,695 |
| Exact reuse / fresh calls | 1,516 / 6,581 |
| Fresh input / cached / output tokens | 15,785,988 / 11,651,328 / 1,049,512 |
| Fresh calls reporting cached tokens | 6,415 / 6,581 |
| Proxy-reported fresh cost | **$8.72954610** |

API pagination over all nine days found zero displayed triage hash mismatches.
Reuse required both the exact snapshot content hash and rendered input hash;
new or changed envelopes received fresh calls. July 12 completed 737/737 and
July 13 completed 1,000/1,099, as intentionally bounded.

A bounded adversarial review covered the top 40 decisions on each fresh day,
all 48 artifact-bearing drops, all 32 short/no-artifact keeps, and tail samples.
High-attention quality was strong and every artifact-bearing drop was
defensible. Across 86 events shared by July 12 and 13, 83 decisions were stable
and three changed from drop to keep after new evidence, as expected.

The review also found five useful calibration cases rather than hiding model
imperfection: four likely false keeps (X platform-integrity policy, a
Starship/Starlink item, conventional defense production, and a UBI quote whose
reason invented AI context) and one likely false drop (an attributable
GPT-5.6/Fable prompt-writing comparison). They are recorded here by event ID:
`8adf1279…`, `159fde7c…`, `d93dc579…`, `004f5d16…`, and `395a73b0…`. The
envelope/data structure is sound; the residual error is a small text-only
relevance-calibration issue. The corpus was not rerun without
a deliberate prompt-policy change. The router remains a candidate gate, not
final insight extraction.

## API, UI, and Performance Proof

- `/api/events/dates` returns all nine complete days and the counts above.
- Cold and warm keep-filter requests for each day complete locally in
  **16–24 ms** after server startup.
- Daily API rows expose stable event identity, cutoff, continuation state,
  selected-day additions, cumulative counts, and hash-matched triage.
- Weekly output is a single week-end projection with unique events and posts,
  not a concatenation of daily rows.
- Frontend production build succeeds and uses the published API for all nine
  date tabs. The agreed UI keeps prior context and triage reasons collapsed.
- Final `scripts/check-fast.sh` passed with **204 tests**, four known
  non-blocking Fast Refresh warnings, and a successful production frontend
  build. `git diff --check`, both canonical SQLite integrity checks, and the
  built-asset reference check also passed.

The in-app Browser tool bridge reported no controllable tab during final
closeout, so this report claims API/build proof rather than fabricating final
visual evidence. The existing desktop UI implementation is covered by its API
and component contracts and remained intentionally minimal.

## Residual Risks and Deferred Work

- **Multi-provider keys:** X is still the only active content provider. Before
  RSS/GitHub ingestion, promote every internal post key to `(provider, post_id)`
  at the adapter boundary.
- **Collection rejection ledger:** aggregate reconciliation is complete, but a
  row-level ledger for every malformed provider object is deferred until the
  first non-clean provider-shape incident.
- **Failed-attempt cost ledger:** successful LLM telemetry is complete; an
  append-only ledger for costs incurred by attempts that fail before
  persistence remains a later operational hardening task.
- **Triage publication pointer:** snapshot hashes fail closed and final runs are
  complete, but triage does not yet have a separate explicit publication
  pointer. Add one before concurrent production triage generations exist.
- **Registry score context:** changing the Registry cohort requires rebuilding
  attention scores and new effective-dated projections. This project correctly
  froze the cohort instead of hiding that boundary.
- **Semantic event grouping:** exact provider relationships are now reliable.
  Topic/semantic clustering remains a separate, explicitly probabilistic layer.

None of these items changes the final provider-edge grouping or cutoff
correctness claim.
