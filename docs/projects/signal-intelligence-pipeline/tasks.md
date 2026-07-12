# Signal Intelligence Pipeline

## Goal

Turn one frozen day of existing X evidence into deduplicated events and 3–5
useful, primary-grounded insights, while measuring whether Registry network
support and trusted amplification improve signal/noise over simple baselines.

## Why / Impact

The Registry and following graph are working, but the central product thesis is
not yet proven: can this system surface something BIT would genuinely want to
know while suppressing noise? This project tests that question end to end before
building a production ingestion or scoring system.

## Scope / Non-Goals

### In Scope

- Freeze the complete 2026-07-11 evidence slice and its exact post hashes.
- Normalize stable author X IDs, embedded quote/retweet targets, post relations,
  cards/articles, and expanded URLs from existing raw JSON.
- Deduplicate related posts into versioned event candidates.
- Compare transparent candidate-ordering baselines before LLM judgment.
- Use an LLM for interest filtering, structured extraction, and clustering only
  after deterministic normalization.
- Verify surviving factual claims with first-hand X statements or primary
  artifacts.
- Blind-label candidate quality and produce 3–5 cited insights for the two
  target audiences.

### Out of Scope

- Backfilling or processing all 63,736 posts before the one-day spike succeeds.
- A permanent scalar trust/importance score or hand-tuned weighted sum.
- A learned ranking model before labeled evidence exists.
- Fetching liker, retweeter, or replier identity lists from new endpoints.
- Recursive discovered-account crawling or broad Registry admission.
- Systematic RSS/arXiv/GitHub ingestion in the first slice; reuse already stored
  primary items when they match.
- Kafka, Postgres, a warehouse migration, scheduling, or production monitoring.
- Final report/alert product implementation; this project hands verified
  insights to that delivery stage.

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

- [ ] The exact one-day input can be reconstructed from a versioned run record.
- [ ] Quote/retweet relations, embedded targets, URLs, and stable author IDs are
  queryable without mutating raw evidence or `data/fli.db`.
- [ ] At least chronological, raw-engagement, and trusted-attention baselines
  are frozen before labeling.
- [ ] Candidate events are deduplicated with inspectable supporting post IDs.
- [ ] Every delivered factual claim has a primary citation or is explicitly a
  first-hand X statement.
- [ ] Blind human evaluation reports Precision@10/@20, usefulness yield,
  grounding rate, duplicate rate, and coverage for each baseline.
- [ ] The slice produces at least three genuinely publishable insights and a
  documented keep/change/pivot decision.
- [ ] Repository checks pass and architecture/build docs match the accepted
  result.

## Milestones

- [ ] M0 — Freeze evidence. Acceptance: exact post IDs/hashes, Registry hash,
  ranking run, and selection contract are stored in one derived run.
- [ ] M1 — Normalize relationships. Acceptance: stable authors, quote/retweet
  edges, embedded targets, cards/articles, and URLs are queryable for the day.
- [ ] M2 — Rank candidates. Acceptance: transparent baselines produce
  inspectable event queues without a hand-tuned scalar score.
- [ ] M3 — Extract and ground. Acceptance: LLM-filtered event candidates retain
  exact detection posts, claims, sources, and audience-specific implications.
- [ ] M4 — Evaluate and decide. Acceptance: blind labels quantify lift over
  chronology/raw engagement and trigger keep/change/pivot.
- [ ] M5 — Deliver the proof. Acceptance: 3–5 cited insights and evaluation
  evidence are ready for the report/alert stage; tracker is archived.

## Execution Rules

- Raw posts and provider responses are immutable evidence. New relations,
  events, features, and rankings live in a derived per-run database.
- A signal run pins the exact post snapshot, Registry checksum, accepted
  following-ranking run, and algorithm/prompt versions.
- Registry changes create a new signal run. Historical scores and events never
  change in place.
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
- Spike first. Do not harden resumability, backfill history, or add systematic
  feeds until the one-day decision gate passes.

## Initial Baselines

Keep all features as inspectable columns; do not collapse them into a weighted
score.

1. **Chronological:** newest deduplicated events first.
2. **Raw engagement:** author-relative interaction percentile, not global likes.
3. **Trusted attention:** lexicographic order by:
   - distinct top-network-support Registry entities amplifying the event;
   - total distinct active Registry entities amplifying/detecting the event;
   - distinct organizations represented;
   - originator network-support percentile;
   - author-relative engagement percentile;
   - recency.
4. **Originator lane:** important first-hand posts with no amplification ordered
   by originator network support, then author-relative engagement and recency.

## Evaluation Contract

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

## Open Questions / Blockers

- None blocking. Exact implementation contracts should be decided from the
  frozen one-day evidence, not generalized before the spike.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| in_progress | Freeze the exact 2026-07-11 input and create the derived signal-run schema with checksums and selection contract. | parent | — |
| todo | Normalize stable author IDs, quote/retweet relations, embedded targets, cards/articles, and URLs for the frozen day. | parent | — |
| todo | Materialize chronological, author-relative engagement, trusted-attention, and originator candidate queues with feature explanations. | parent | — |
| todo | Blind-label the comparison sample, then run bounded LLM extraction and primary verification only on surviving events. | parent | — |

## Backlog / Remaining Work

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
