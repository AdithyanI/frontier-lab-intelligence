# Signal Intelligence Pipeline

## Goal

Build a polished, auditable Feed that turns the latest seven complete days of
stored X evidence into deduplicated, date-filterable posts ordered by a
transparent attention score. The first milestone is the evidence surface and
its reusable data contract—not generated insights.

## Why / Impact

The Registry and following graph are working, but their stored public output is
not yet inspectable as a coherent product surface. A durable Feed makes the
evidence auditable, tests whether network-supported ordering suppresses noise,
and creates the reusable input boundary for later extraction and insights.

## Scope / Non-Goals

### In Scope

- Materialize the latest seven complete days, initially 2026-07-05 through
  2026-07-11, from locally stored X evidence without provider calls.
- Normalize stable author X IDs, embedded quote/retweet targets, post relations,
  direct X provenance, and public engagement from existing raw JSON.
- Deduplicate related posts into versioned event candidates.
- Compute a transparent, explicitly experimental attention score from Registry
  amplification, originator network support, and public engagement.
- Serve a Registry-aware API and a polished Feed page with date, lane, sort,
  and text filters plus inspectable score inputs.
- Keep current Registry rejections dynamic: rejected authors disappear and
  rejected amplifiers stop contributing on the next API read/page refresh.
- Provide an idempotent refresh command for newly stored X evidence.

### Out of Scope

- Backfilling or processing all 63,736 posts before the seven-day Feed is audited.
- A permanent scalar trust/importance score or hand-tuned weighted sum.
- A learned ranking model before labeled evidence exists.
- Fetching liker, retweeter, or replier identity lists from new endpoints.
- Recursive discovered-account crawling or broad Registry admission.
- Systematic RSS/arXiv/GitHub ingestion in the first slice; reuse already stored
  primary items when they match.
- Queryable card/article payloads and expanded external URLs; the immutable raw
  JSON retains them for the later extraction/verification stage.
- Kafka, Postgres, a warehouse migration, scheduling, or production monitoring.
- LLM relevance filtering, summarization, categorization, insight generation,
  or primary-source verification in this milestone.
- Final report/alert product implementation.

## Context / Constraints

- Date started: 2026-07-12.
- Submission deadline: 2026-07-20. Make the first keep/change/pivot decision by
  2026-07-13 EOD Europe/Berlin and freeze pipeline expansion by 2026-07-17 so
  delivery has protected time.
- The accepted network-support input is `entity-overlap-v2` run
  `181d539ebc7ec1adee8c28adbec0c0a578f151eb116f9bba021094d915dab0f9`.
- Current canonical Registry SHA-256:
  `6f247beba19813c40616c2f4be685870b2055e332281f10c4b61780ba0074bb0`.
- Current ranking analysis SHA-256:
  `9344706f11e4910617d39f664dbfa35e5aae9eb0fc98461fd00981c3402766e0`.
- Current X-content SHA-256:
  `3c1a19581900f020b77c4969fa180718abea8df9f22f056dd88d73ef29b656d4`.
- Current evidence already contains 27,588 originals, 30,526 quote tweets,
  5,622 retweets, public engagement counts, and nested referenced-post context.
  Replies were not collected.
- The 2026-07-11 active-Registry slice contains 375 originals, 356 quotes, and
  588 retweets. Its quote/retweet relations reference 751 distinct target posts;
  97 targets were amplified by at least two active Registry accounts.

## Done When

- [x] The exact seven-day input can be reconstructed from a versioned run record.
- [x] Quote/retweet relations, embedded targets, URLs, and stable author IDs are
  queryable without mutating raw evidence or `data/fli.db`.
- [x] Chronological, public-engagement, and network-attention orderings are
  available from one deterministic API.
- [x] Candidate evidence items collapse pure retweets and retain inspectable
  supporting post IDs; quotes remain authored evidence plus a relation.
- [x] The Feed supports seven dates and exposes the exact reasons for each
  item's rank without generated interpretation.
- [x] Registry rejection changes affect the next response without mutating raw
  or historical derived evidence.
- [x] The live desktop UI is visually checked and useful for evidence audit.
- [x] Repository checks pass and architecture/build docs match the accepted
  result.

## Milestones

- [x] M0 — Freeze evidence. Acceptance: exact post IDs/hashes, source metadata,
  and selection contract are stored in one derived run.
- [x] M1 — Normalize relationships. Acceptance: stable authors, quote/retweet
  edges, embedded targets, X provenance, and public metrics are queryable.
- [x] M2 — Rank candidates. Acceptance: transparent orderings and an inspectable
  experimental score are recomputed from current Registry state.
- [x] M3 — Ship the Feed. Acceptance: backend API, refresh tool, and polished
  date-filterable UI work together for the seven-day slice.
- [ ] M4 — Evaluate and decide. Acceptance: the evidence surface is audited and
  the next extraction/insight milestone is explicitly accepted or changed.

## Execution Rules

- Raw posts and provider responses are immutable evidence. New relations,
  events, features, and rankings live in a derived per-run database.
- A signal run pins the exact post snapshot and normalization contract. Each
  run owns immutable normalized post rows and relations.
- Registry and accepted-ranking state are joined at API read time and returned
  with the response. They may change the current score/view without mutating a
  historical evidence run; frozen score snapshots can be added when evaluation
  begins.
- Call the graph feature `network support` or `cohort attention`, not proven
  trust or importance.
- Count each canonical Registry entity at most once per event. Multiple channels
  from one organization never create multiple votes.
- Discovered accounts cannot endorse themselves into relevance in this slice;
  only active Registry entities contribute amplification evidence.
- Rank events, not tweets. A retweet wrapper deduplicates to its target; a quote
  remains authored content plus a relation.
- External URLs are verification evidence, not an eligibility gate. A
  first-hand statement by the originating person/lab can itself be primary.
- Public likes, views, replies, and repost counts are diagnostics/tie-breakers,
  not global importance. Aggregate likes do not reveal trusted liker identity.
- Freeze baselines before labeling and blind reviewers to ranking features.
- Spike first. Do not backfill the complete corpus or add systematic feeds until
  the seven-day evidence surface is audited.

## Initial Baselines

Keep all score features inspectable. The UI may expose a provisional weighted
attention score for ordering, but it is not a claim of quality or importance.

1. **Chronological:** newest deduplicated events first.
2. **Public engagement:** day-relative log interaction percentile; public
   counts remain a diagnostic, not importance.
3. **Network attention:** provisional score = 55% active Registry amplification
   percentile + 25% originator network-support percentile + 20% public
   engagement percentile. High-network-support amplifiers are visible and add
   one extra unit before the network percentile is computed.
4. **First-hand lane:** direct posts remain separately filterable, whether or
   not another Registry entity amplified them.

## Future Evaluation Contract

Reviewers do not see ranking features. Label a stratified sample containing the
top 20 trusted-attention events, top 20 raw-engagement events, and 20
chronological/random events.

Per event:

- frontier-AI relevant?
- substantive rather than reaction/noise?
- useful enough to show BIT?
- groundable with a primary source or first-hand statement?
- duplicate of another event?
- useful to investment, AI engineering, or both?

Report Precision@10/@20, useful events per 20 reviews, primary-grounding rate,
duplicate rate, and unique-author/organization coverage. Do not claim recall
without labeling the complete day.

Decision gate by 2026-07-13 EOD:

- at least 3 publishable/useful grounded insights;
- all delivered factual claims primary-cited or explicitly first-hand;
- at least 12 of the trusted-attention top 20 judged worth attention.

If the gate fails, pivot to the 1,599 already stored blog/arXiv/GitHub items
instead of expanding the graph or processing the complete X history.

## Decisions

- Archive trusted-following ranking with entity overlap accepted only as a
  network-support feature; downstream utility evaluation belongs here.
- Start from the latest complete day, 2026-07-11, rather than partial today or
  all history.
- Normalize observed retweet/quote relations already present in raw JSON; do
  not fetch engagement-actor lists.
- Use two signal lanes: multi-source consensus events and important
  single-originator posts.
- Keep first-slice X detection and primary verification complementary. Direct
  primary feeds remain a later option, not a competing implementation now.
- Name the deterministic product surface **Feed**, not Insights. It shows
  evidence and ranking inputs without claiming interpretation.
- Freeze normalized posts and relations per content-addressed run, but join
  Registry state and the accepted network ranking at read time so curation
  changes are visible on refresh without rewriting evidence.
- Use `attention-v1` only as a transparent experimental ordering aid. Search
  and lane changes never recalibrate scores; self-amplification is excluded.

## Open Questions / Blockers

- None blocking. Exact implementation contracts should be decided from the
  frozen one-day evidence, not generalized before the spike.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| todo | Audit the top Feed results for signal/noise and record the keep/change decision for `attention-v1`. | parent | — |
| todo | Design the next deterministic event-clustering and relevance-filter boundary from that audit; do not add LLM extraction before the contract is accepted. | parent | — |
| todo | Normalize expanded external URLs/cards only for the accepted candidate set, then resolve primary citations in the later extraction milestone. | parent | — |

## Backlog / Remaining Work

- [ ] Add LLM relevance filtering, structured extraction, clustering, and
  primary verification only after the Feed evidence surface is accepted.
- [ ] Produce 3–5 cited insights and the keep/change/pivot decision.
- [ ] Test the accepted rubric unchanged on a second complete day if the first
  day passes.
- [ ] Compare 20 highly ranked discovered sources against 20 active sources
  only after the base extraction path proves useful.
- [ ] Hand verified insights and evaluation evidence to the report/alert stage.
- [ ] Review project learnings and archive at closeout.

## Validation / Test Plan

- Fixture tests for stable author identity, retweet dedupe, quote preservation,
  canonical URL extraction, and one-vote-per-entity behavior.
- Deterministic baseline ordering on a small known event graph.
- SQL reconciliation of post types, relations, targets, voters, and event
  membership against the frozen input.
- Blind human labels stored separately from ranking features.
- `scripts/check-fast.sh` before handoff.

## Progress Log

- 2026-07-12: [IN-PROGRESS] Opened the project after closing trusted-following
  ranking. A read-only audit of the current X store confirmed the first day can
  run without provider calls: 1,319 current-active timeline observations (375
  originals, 356 quotes, 588 retweets), 751 referenced targets, and 97 targets
  with at least two active Registry amplifiers. Independent data-model,
  scoring, and project-boundary reviews converged on event-level ranking,
  derived versioned runs, transparent features, and no scalar trust score.
- 2026-07-12: [CHECKPOINT] Shipped the complete deterministic Feed vertical
  slice. Content-addressed run `89b7562e...0742949` materializes seven complete
  days (11,062 direct posts, 15,642 normalized posts, 8,232 relations) without
  provider or LLM calls. The current Registry view exposes 1,371 items on
  2026-07-11, including 699 amplified and 806 first-hand. Registry rejections,
  one-vote-per-entity, self-amplification exclusion, stable scores across
  filters, pagination, date navigation, search, sort, and long-post expansion
  are fixture- and browser-tested. `scripts/check-fast.sh` passes 134 tests,
  frontend lint, and production build. The next product decision is whether
  the visible top results justify keeping or changing `attention-v1` before
  relevance filtering and event clustering.
