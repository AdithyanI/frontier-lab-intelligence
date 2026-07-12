# Trusted-Following Ranking

## Goal

Build and evaluate a fresh, provenance-complete relevance graph from whom the
frozen relevance-screened Registry cohort follows, with a smaller reviewed
subset supplying personalized trust, without reading the questionable legacy
graph.

## Why / Impact

The Registry needs a defensible way to discover the people below the obvious
names. The rejected 361K-edge graph was removed rather than treated as an
interview claim. A smaller trusted-following graph can become a clear, testable
candidate generator while demonstrating ranking and validation discipline.

## Scope / Non-Goals

### In Scope

- Freeze the current Registry X-account collection cohort.
- Fetch and persist complete outgoing-follow snapshots for accessible members
  of that cohort.
- Freeze a smaller, human-chosen personalization set with short reasons.
- Isolate the new graph from every legacy edge by construction.
- Compare a simple trusted-seed overlap baseline with personalized PageRank.
- Evaluate the top results against a small recorded human judgment set.
- Produce a bounded Registry candidate shortlist and a defensible interview
  explanation of the result.

### Out of Scope

- Treating the legacy Digg/follower graph as trusted evidence.
- Reintroducing Digg data into the active Registry or graph.
- An open-ended recursive or internet-scale crawl.
- Using graph rank as the final score for documents or insights.
- Unsure-entity enrichment, which Adi owns separately.
- Polishing a graph visualization before ranking quality is proven.

## Context / Constraints

- Date started: 2026-07-10.
- Submission north star: earn the next interview by 2026-07-20 with coherent,
  defensible end-to-end proof; timebox this milestone so extraction, scoring,
  validation, and delivery still ship.
- The active graph is empty. Digg survives only as the offline 1,000-row
  comparison artifact documented in
  `docs/references/digg-ranking-baseline.md`.
- The repo has a tested X-following provider adapter. The rejected global
  PageRank implementation was removed; replacement ranking reads only the
  isolated immutable snapshot boundary.
- External fetches must be bounded, attributable, and cost-recorded.

## Done When

- [x] The cleaned Registry collection cohort has a byte-exact checkpoint with
  a documented recovery path.
- [x] The smaller personalization set and reasons are versioned and reviewable.
- [x] Fresh outgoing-follow snapshots persist edge direction, seed, source,
  fetch time, completeness, and stable identity.
- [x] New ranking commands cannot read legacy edges accidentally.
- [x] Trusted-follow count and personalized PageRank are compared on the same
  frozen snapshot.
- [ ] A labeled top-result review records precision/ranking quality and at
  least the most important failure modes.
- [ ] Adi accepts the bounded shortlist or the evaluation supports stopping;
  either outcome is documented before moving to the insight pipeline.
- [ ] Repository checks pass and architecture/build docs match reality.

## Milestones

- [x] M1 — Freeze the evidence boundary. Acceptance: existing graph/import/rank
  semantics are audited and a fresh snapshot contract cannot mix legacy edges.
- [x] M2 — Build one bounded Registry-following snapshot. Acceptance: complete
  outgoing follows for every accessible frozen cohort account are persisted
  with provenance, inaccessible accounts are explicit, and the snapshot can be
  reproduced without touching legacy edges.
- [x] M3 — Rank and compare. Acceptance: overlap baseline and personalized
  PageRank run over the same snapshot and emit inspectable explanations.
- [ ] M4 — Evaluate and decide. Acceptance: labeled top-k review supports an
  explicit keep/change/stop decision and a bounded Registry shortlist.
- [ ] M5 — Document and close. Acceptance: architecture, build log, validation,
  and interview-ready trade-offs are current; tracker is archived.

## Execution Rules

- Keep the graph small enough to understand and evaluate.
- Do not read legacy edges in the new ranking path, even as a fallback.
- Preserve raw observations and snapshot identity before modeling.
- Treat graph rank as candidate-generation evidence, not truth or a final
  intelligence score.
- Compare against the simplest credible baseline before defending PageRank.
- Stop expanding the graph when it no longer improves the accepted evaluation.
- Update this tracker after each meaningful batch and before handoff.

## Decisions

- Rebuild from trusted accounts' outgoing follows, not their followers.
- Compare personalized PageRank seeded by the reviewed set against entity
  overlap; the measured first run keeps PageRank diagnostic and advances
  entity overlap to human review.
- The active database starts from two public source lists plus the 10 curated
  labs plus the restored post-floor classified nodes. Digg rank is offline;
  only neutral bootstrap-origin markers remain active. Personal following data
  is absent.
- The rejected Digg edge plane, derived PageRank, graph-only candidates,
  tracked edge artifacts, and reload/rank commands were removed cleanly.
- Protect the end-to-end submission: this is one timeboxed milestone, not the
  product destination.
- Registry identity resolution uses one entity with many independently
  observed channels. SpaceX is the canonical organization for `@spacex` and
  `@SpaceXAI`; the stable former `@xai` account was renamed in place, not
  duplicated, and no historical alias is exposed.
- arXiv affiliation searches are document-ingestion inputs, not
  organization-owned identity channels. The eight query channels were removed;
  the 137 fetched arXiv records remain available in the raw evidence layer.
- Precision-first organization consolidation uses a reviewed manifest, not a
  fuzzy clustering step. Ten canonical organizations absorbed 20 explicit
  product/developer/subgroup accounts; ambiguous ownership remains separate.
- The All, People, and Organizations tabs sort by the visible sum of followers
  across an entity's X channels. People labels the value X followers; All and
  Organizations label it Combined X followers. This is a temporary visibility
  order only; it does not replace trusted-follow evaluation or define seed
  importance.
- Structural kind and product relevance are separate decisions. The existing
  lifecycle resolves person/organization/unsure; a future relevance gate may
  follow it, but the first full-corpus pass is an offline review artifact only
  and cannot mutate the Registry. Follower count is not a model input.
- Adi approved all 108 first-pass removal candidates. They are now a versioned
  Registry manifest applied transactionally after complete preflight; model
  output still has no direct mutation path.
- Registry cleanup now uses the versioned `registry-relevance-v1` boundary:
  frontier labs/people, evaluation research, AI-native technical builders, and
  narrowly focused specialist intelligence qualify; general technology,
  crypto, fame, and occasional AI commentary do not. Terra-high must use hosted
  web search for every identity, and a human-reviewed manifest remains the only
  deletion path.
- The read-only relevance audit now covers all 2,774 requested active entities:
  2,765 Terra-high results plus nine centrally reviewed manual web fallbacks for
  provider content-filter terminations. The composite result is 2,162 keep, 56
  review, and 556 remove recommendations; none directly mutated the Registry.
- Adi reviewed the 51 organization removal recommendations, overrode AI
  Engineer to keep as a focused technical AI publication/community, and
  approved the other 50. The approved rows were added to the protected
  manifest and removed transactionally after a clean dry run.
- Adi approved every remaining high-confidence person removal recommendation.
  The 464 exact identities were added to the protected manifest and removed
  transactionally. AI Engineer remains the sole active high-confidence model
  removal because Adi explicitly overrode it to keep; 41 medium-confidence
  removals and all 56 review cases remain untouched.
- The 41 medium-confidence removals received individual human review. Eleven
  were retained where current evidence supports technical, frontier-lab,
  safety, or specialist-intelligence value; the other 30 were approved and
  removed transactionally. Only the 56 original review cases remain unresolved.
- The final 56 review cases received a bounded human audit: 28 known frontier
  sources were retained, 16 resolved out-of-scope identities were removed,
  and 12 identity-unverified accounts were deferred and excluded from trusted
  seed consideration. Repeating the same LiteLLM audit was rejected because
  it would manufacture confidence rather than resolve missing identity evidence.
- Provider-specific Responses quirks normalize in `fli.llm_responses`, not in
  individual audit stages. Claude uses native web search with automatic tool
  choice plus a post-response search-evidence gate; translated search calls and
  cited URLs remain visibly labeled in the review artifact.
- Rejected identities are an inactive, reversible holding set. They are
  excluded from collection, ranking inputs, and candidate output; restoration
  requires an explicit `clear_rejection` decision. Nine protected-only X
  identities entered this set after the profile scan.
- Organization consolidation remains ownership-driven: NVIDIA and Meta AI each
  have one coherent entity; Moonvalley is now an official Reka channel; Papers
  with Code was removed as a dormant source; and `@shahules786` is the person
  Shahul ES. Google and Google DeepMind remain separate source actors.
- X inactivity is source evidence, not an automatic person deletion. The
  2024-07-11 cutoff found 74 inactive and 15 no-recent-post person accounts,
  including important researchers who remain in the Registry but should not be
  treated as current post sources.
- Adi explicitly approved a temporary first-PageRank breadth cutoff: remove all
  active organizations below 10,000 combined stored X followers and allow
  trusted-follow PageRank to rediscover them later. Seventeen organizations
  were removed with their original audit evidence and restoration notes saved.
- Registry cleanup ended at a byte-exact 2026-07-11 checkpoint: 2,213 entities,
  2,259 channels, 2,235 X accounts, and zero graph edges. The pushed Git object
  is the database backup; its checksum, reconciliation, and recovery procedure
  are recorded in `resources/registry-cleanup-checkpoint.md`.
- The database has 2,235 X accounts; four reason-bearing rejected identities
  are excluded, leaving a frozen 2,231-account active collection cohort. These
  are not 2,231 equal-trust seeds. Fetch their outgoing follows where
  accessible, then compare a simple screened-source overlap baseline with
  personalized PageRank from a smaller reviewed trust subset.
- Large following evidence is local-first: one ignored SQLite file per
  immutable snapshot under `data/raw/following/`. The Git-tracked `data/fli.db`
  stays small; Git keeps only the snapshot manifest, checksum, compact rankings,
  and evaluation. The storage contract preserves a later move to object
  storage + Parquet/Postgres without changing `snapshot_id` semantics.
- The immutable `registry-following-2026-07-11-v1` snapshot completed all 2,219
  accessible/empty sources and records nine protected plus three missing
  terminals. Its 13,409 raw pages normalize to 2,456,305 fresh directed edges
  over 463,180 targets at a best-available estimated provider cost of
  `$27.81218`; the tracked manifest binds the local artifact checksum.
- A verified 462 MiB Zstandard recovery archive sits beside the 2.0 GB local
  SQLite snapshot. Its decompressed SHA-256 matches the finalized database.
  The same content-addressed archive now has a full-readback-verified off-machine
  copy in WIN's existing Cloudflare R2/S3 bucket. Because that bucket has a
  public domain, it is durable but not claimed private. Adi explicitly approved
  recording its verified public recovery URL in the tracked manifest.
- No GitHub Actions workflow is needed before deployment. The managed Stop hook
  plus repo-owned `scripts/check-fast.sh` is the accepted feedback loop for the
  current local case-study phase.
- Candidate admission now has a read-only combined evaluation contract with
  independent structural kind and Registry decision. It uses one descriptive,
  versioned prompt, optional open-web research, strict four-field output, and
  the existing stable prompt-cache sharding convention. The first two-entity
  Luna-high calibration produced sensible decisions but no observable cache
  hit, so cached-token savings remain unproven.
- Cost is operational telemetry, not a product-selection or execution gate.
  Record actual spend and cache behavior, but do not lower quality or block
  in-scope work because of cost unless Adi explicitly sets a cap.
- The full GPT-5.4-mini-high run completed all 2,207 active X entities without
  terminal failures: 1,855 keep, 201 remove, and 151 review. No recommendation
  mutated the Registry. A same-evidence Luna-high comparison over the 192
  person removals kept 119, removed 60, and reviewed 13, proving that this
  removal boundary is not stable enough for automatic application.

## Open Questions / Blockers

- What top-k size and relevance labels will Adi review for the evaluation?
- Does Adi accept the experimental 30-source personalization set as a durable
  diagnostic, or want edits before any future niche-personalization use?

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Run the finalized combined evaluator read-only over all 2,207 active X entities with GPT-5.4-mini-high, cached post evidence, resumability, and measured spend. | parent | `resources/registry-evaluation-full-run.md` |
| done | Re-evaluate the 192 person-removal recommendations with Luna-high against identical stored evidence and record agreement/failure modes. | parent | `resources/registry-evaluation-luna-person-remove-comparison.md` |
| done | Audit existing edge/import/PageRank code and current database provenance locally. | parent | — |
| done | Verify the official X contract and one live `@karpathy` following count/cost. | parent | `../../references/research-notes.md` |
| done | Remove Digg/personal graph evidence while retaining the post-floor classified nodes; keep Digg ranking offline only. | parent | `../../references/digg-ranking-baseline.md` |
| done | Estimate a full 2,924-account TwitterAPI.io following run without making requests. | parent | `resources/full-cohort-cost-estimate.md` |
| done | Consolidate SpaceX and SpaceXAI into one organization with two active X channels; prove replay and invariants. | parent | — |
| done | Consolidate ten high-confidence organization groups and make all channels legible in the Registry UI. | parent | `../../references/registry-curation.md` |
| done | Run a read-only Luna-medium relevance triage and produce a conservative removal shortlist. | parent | `resources/relevance-removal-candidates.csv` |
| done | Apply the 108 Adi-approved relevance removals through a preflighted, transactional manifest. | parent | `resources/relevance-removal-candidates.csv` |
| done | Calibrate Terra-high plus required web search on 20 clear and ambiguous identities; manually review and apply three accepted removals. | parent | `resources/relevance-boundary-batch-02.csv` |
| done | Complete the read-only web-grounded relevance audit across the active Registry, including nine manual content-filter fallbacks. | parent | `resources/relevance-complete-v1.json` |
| done | Review all 51 organization removals; retain AI Engineer and transactionally remove the other 50. | parent | `resources/organization-removal-review.csv` |
| done | Apply every remaining high-confidence person removal; preserve AI Engineer and leave medium/review cases untouched. | parent | `../../../data/registry/relevance-removals.csv` |
| done | Individually audit all 41 medium-confidence removals; retain 11 and transactionally remove 30. | parent | `resources/medium-confidence-removal-audit.csv` |
| done | Resolve the final 56 review cases; retain 28, remove 16, and defer 12 identity-unverified accounts. | parent | `resources/review-case-audit.csv` |
| done | Audit organization channel ownership and consolidation candidates, focused on NVIDIA and Meta/Facebook. | external_researcher | `resources/organization-consolidation-audit.md` |
| done | Audit all organization and person X channels for activity since 2024-07-11. | parent | `resources/organization-x-activity-audit.csv`, `resources/person-x-activity-audit.csv` |
| done | Apply the temporary under-10,000-follower organization cutoff with a restorable reviewed cohort. | parent | `resources/low-follower-organization-removals.csv` |
| done | Freeze and reconcile the cleaned pre-following database boundary with an exact recovery path. | parent | `resources/registry-cleanup-checkpoint.md` |
| done | Design the local-first, isolated, resumable snapshot and tracked-manifest storage boundary. | parent | `../../references/following-snapshot-storage.md` |
| done | Implement the per-snapshot SQLite schema and freeze the 2,231-account collection manifest before any paid fetch. | parent | `../../../data/following/cohorts/registry-active-2026-07-11.json` |
| done | Add the bounded TwitterAPI.io collector over the snapshot store, then prove one small resumable calibration before the full crawl. | parent | `resources/profile-count-scan.md` |
| done | Obtain Adi's explicit go/no-go, run the full outgoing-follow crawl, validate it, and freeze its tracked proof manifest. | parent | `../../../data/following/manifests/registry-following-2026-07-11-v1.json` |
| done | Create and verify a compressed local recovery copy without modifying the immutable snapshot. | parent | `../../../data/following/manifests/registry-following-2026-07-11-v1.json` |
| done | Upload the verified archive to WIN's existing permanent R2/S3 storage and verify the complete remote object by SHA-256. | parent | `../../../data/following/manifests/registry-following-2026-07-11-v1.json` |
| done | Implement the simplest screened-source overlap baseline against the immutable snapshot before choosing personalization weights. | parent | `resources/m3-overlap-baseline.md` |
| done | Create `data/derived/following/<snapshot-id>/analysis.db` with a snapshot-stamped, recomputable active/rejected/unknown x_id join; no mapping table in fli.db. | parent | `resources/m3-overlap-baseline.md` |
| done | Audit major frontier-organization coverage and define exact parent/channel rollups before changing the Registry. | parent | `resources/major-organization-coverage-audit.md` |
| done | Apply the snapshot-pinned organization-coverage manifest, including NVIDIA/AMD/Intel compute anchors, and prove dry-run/replay safety. | parent | `../../../data/registry/organization-coverage.json` |
| done | Freeze and version the smaller reviewed PageRank personalization set with short reasons. | parent | `../../../data/following/personalizations/trusted-personalization-2026-07-11-v1.json` |
| done | Implement personalized PageRank over the isolated snapshot and emit the overlap-vs-PageRank comparison artifact. | parent | `resources/m3-pagerank-comparison.md` |
| done | Implement and calibrate the read-only combined kind + Registry-decision Responses contract with optional web research and measured prompt-cache counters. | parent | `resources/registry-evaluation-cache-calibration.md` |

## Backlog / Remaining Work

- [x] Freeze the cleaned Registry collection cohort and recovery checkpoint.
- [x] Freeze the smaller PageRank personalization set.
- [x] Complete the bounded Registry relevance cleanup and reconcile the stale
  manual top-100 artifact against the accepted web-grounded boundary.
- [x] Implement isolated, immutable snapshot storage, freeze the broad
  collection cohort, and complete bounded provider ingestion.
- [x] Implement overlap baseline and personalized PageRank.
- [ ] Build and review the labeled top-k evaluation.
- [x] Update architecture and append the build log after meaningful changes.
- [x] Run `scripts/check-fast.sh` and milestone-specific tests.
- [ ] Review project learnings and archive the tracker at closeout.

## Validation / Test Plan

- Focused unit tests for snapshot replacement, direction, provenance, and
  legacy-edge exclusion.
- Deterministic ranking tests on a small known graph for both algorithms.
- SQL reconciliation of seed, snapshot, edge, and ranked-node counts.
- Recorded top-k human review with the agreed rubric.
- `scripts/check-fast.sh` before handoff.

## Progress Log

- 2026-07-10: [IN-PROGRESS] Adi rejected the current graph as a trustworthy
  ranking basis and chose a fresh graph from trusted accounts' outgoing
  follows. Created the timeboxed ranking tracker under the submission north
  star; live fetching waits for the evidence-boundary audit and seed decision.
- 2026-07-10: [DONE] Local audit found legacy Digg and exploratory following
  edges in one table. The old PageRank read every source without a filter and
  its stored facts/observations were not a safe current signal. The audit also
  showed that deleting edges alone would leave graph-only candidates active.
- 2026-07-10: [DONE] Official X docs confirm `public_metrics.following_count`
  and `GET /2/users/{id}/following` with up to 1,000 results per page. One
  bounded TwitterAPI.io profile lookup found `@karpathy` follows 1,108 accounts
  and cost about `$0.00018`; a full existing-provider snapshot is estimated at
  `$0.01216`, versus about `$11.08` through official third-party X reads.
- 2026-07-10: [BLOCKED] Full `scripts/check-fast.sh` was not run for this
  documentation/research checkpoint because unrelated in-progress changes are
  present in `src/fli/entity_kinds.py` and `src/fli/sources.py`. Build-log JSONL
  validation, renderer regeneration, and `git diff --check` passed.
- 2026-07-10: [DONE] Adi approved a clean reset. Removed all 360,667 Digg edges,
  all exploratory personal-follow edges, their source facts/observations, the
  invalid derived PageRank, and candidates with no remaining public-list or
  curated-lab provenance. Removed 76 MB of tracked Digg edge artifacts plus
  628 MB of ignored raw graph data and retired the Digg scraper/import/ranker
  paths. The active graph is empty. The Registry now has 586 entities (473
  people, 87 organizations, 26 unsure), 618 channels, and SQLite integrity
  `ok`; `data/fli.db` shrank from 93 MB to 3.5 MB. The frozen Digg ranking CSV
  remains offline for later diagnostic comparison. No following-list API call
  was made during cleanup.
- 2026-07-10: [DONE] Final validation passed: all 36 tests, frontend lint,
  frontend production build, live `/api/status` and `/api/registry`
  reconciliation, SQLite foreign-key check, and integrity check. Execution is
  intentionally paused before seed selection or any following-list fetch.
- 2026-07-10: [DONE] Rechecked current TwitterAPI.io page pricing and modeled
  the full classified cohort without making an API request. After correcting
  the node restoration, a Karpathy-like 1,108-following average is about
  `$36.08`; a 500–2,000 average gives an `$18.07–$59.01` planning range.
- 2026-07-10: [DONE] Corrected an over-aggressive interpretation of graph
  cleanup. Restored the post-floor nodes, channels, observations, and
  classifications from Git commit `53dd026`, then removed only Digg/personal
  edges and active Digg/PageRank/personal source evidence. Current state: 2,924
  accounts/entities (2,607 people, 180 organizations, 137 unsure), 2,956
  channels, zero graph edges, zero stored follower counts below 1,000, SQLite
  integrity `ok`. All 37 tests plus frontend lint/build pass.
- 2026-07-10: [DONE] Added non-scoring provenance without restoring the noisy
  graph. All 2,924 accounts now carry `registry_bootstrap.retained_candidate`;
  2,308 accurately carry `digg_bootstrap.candidate_origin` (1,308 graph-only,
  one ranked-only, 999 both). Graph edges remain zero and no Digg rank, score,
  or PageRank is active.
- 2026-07-10: [DONE] Proved the one-entity/many-channels contract with the first
  real organization consolidation. SpaceX is now one organization owning the
  active `@spacex` and `@SpaceXAI` X channels plus x.ai and xai-org. Renamed
  the stable former `@xai` account in place, removed the
  redundant entity without deleting account/channel evidence, and made the
  two-X seed replay idempotently. Registry state is 2,923 entities, 2,956
  channels/links, and zero graph edges; SQLite foreign keys are clean,
  integrity is `ok`, and all 49 tests plus frontend lint/build pass. UI work is
  intentionally paused for Adi's database review.
- 2026-07-10: [DONE] Applied the precision-first organization batch after two
  independent audits. Anthropic, OpenAI, Mistral AI, Anysphere, Vercel,
  Hugging Face, fal, Thinking Machines, and Google now own 19 explicit
  product/developer X channels. Manus/Meta and Stable Diffusion/Stability AI
  were deliberately deferred. A rollback rehearsal exposed an implicit SQLite
  commit; the database was restored from its tracked snapshot, the command was
  hardened with full preflight, one transaction, merge audit rows, and dry-run
  regression tests, then replayed idempotently. Current state: 2,904 entities,
  2,948 channels/links, zero graph edges, clean foreign keys and integrity.
- 2026-07-10: [DONE] After a read-only audit of all 164 organization entities
  and 184 X channels, merged the only accepted subgroup decision: Stanford AI
  Lab now owns `@stanfordailab` and `@stanfordnlp`. Stanford's official NLP
  site identifies the group as part of SAIL. The manifest replay is idempotent;
  Registry state is 2,903 entities, 2,948 channels/links, 20 merge-audit rows,
  and zero graph edges. Stability product/community accounts remain deferred
  pending current account-control evidence.
- 2026-07-10: [DONE] Replaced alphabetical ordering only in the Organizations
  tab with descending combined X followers. The displayed total sums the
  latest stored count for every consolidated X channel; All and People remain
  unchanged. Live verification shows SpaceX, Google, TechCrunch, OpenAI, and
  Anthropic at the top with their exact totals visible, making the temporary
  proxy inspectable rather than presenting it as a hidden importance score.
- 2026-07-10: [DONE] Extended the same inspectable follower ordering to People
  and All. People now shows Entity + X followers; All shows Entity + Type +
  Combined X followers. Handles stay searchable and available in detail cards
  but are omitted from ranked rows, missing observations show an em dash and
  sort last, and the Rejected review view remains reason-bearing.
- 2026-07-10: [DONE] Ran a disposable, read-only Luna-medium relevance triage
  over all 2,900 active Registry entities without sending follower count or
  mutating canonical data. It produced 1,706 keep, 107 remove, and 1,051 review
  decisions; 36 incomplete JSON responses remain unclassified and are excluded
  from removal consideration. Central controls including OpenAI, Anthropic,
  Google DeepMind, DeepSeek, Sam Altman, Demis Hassabis, and Andrej Karpathy
  were kept. Added Ashton Kutcher manually from review to create a 108-row,
  follower-sorted removal candidate file for human approval. LiteLLM reported
  $2.915358 for 1,112,663 input and 300,597 output tokens. No entity was removed.
- 2026-07-11: [DONE] Adi accepted all 108 candidates. Added a CSV-backed
  relevance-removal command with complete preflight, dry-run, one transaction,
  idempotent replay, and tests. It removed exactly 101 people, seven
  organizations, 108 X channels, and 108 backing accounts; no seeded lab,
  merge canonical, rejection, multi-channel identity, or graph participant was
  in scope. Registry state is now 2,795 entities, 2,840 channels/links, and zero
  graph edges.
- 2026-07-11: [IN-PROGRESS] A stricter batched Luna audit attempted to reduce
  the 1,051 conservative reviews, but the shared LiteLLM route returned Azure
  403 before inference for all 280 batches; zero results and zero reported cost
  were produced. Continued manually with the 100 highest-reach remaining
  identities: 49 direct keeps, 47 likely removals, and four genuine reviews.
  No second-wave deletion has been applied.
- 2026-07-11: [DONE] Restored shared LiteLLM access, versioned the assignment-
  calibrated `registry-relevance-v1` prompt, and proved Terra-high with required
  hosted web search on 20 clear and ambiguous identities. The decisions matched
  the intended boundary: labs, researchers, evaluators, AI-native builders, and
  specialist sources stayed; broad tech/crypto identities did not. Manually
  accepted and transactionally removed Patrick Collison, Marc Benioff, and Om
  Malik through the existing protected manifest. Registry state is 2,792
  entities with clean foreign keys, SQLite integrity `ok`, and zero graph edges.
- 2026-07-11: [DONE] Completed the read-only full-corpus relevance audit for all
  2,774 requested active entities. Terra-high with required hosted web search
  produced 2,765 valid results; nine persistent Azure content-filter outcomes
  were researched manually against the same rubric and preserved separately.
  The composite manifest records 2,162 keep, 56 review, and 556 remove
  recommendations with zero unresolved identities and no Registry mutation.
- 2026-07-11: [DONE] Added one local Responses normalization boundary and
  proved the nine Azure-filtered identities through Claude Opus 4.6 native web
  search: 9/9 completed with recorded search queries and cited URLs. Claude
  agreed with seven central decisions but recommended removing Connor Leahy
  and Kevin Kwok; the existing human-reviewed keep/review decisions remain
  canonical, and the Claude artifact is supplementary evidence only.
- 2026-07-11: [DONE] Reviewed the 51 organization removal recommendations.
  Adi retained AI Engineer as a relevant focused technical AI publication and
  community, then approved the other 50. The canonical removal manifest now
  records 161 accepted identities. A byte-stable dry run resolved exactly 50
  live entities and 111 already-applied rows; the transaction removed 50
  organizations, X channels, and backing accounts. Registry state is 2,742
  entities, including 106 organizations, with clean foreign keys, SQLite
  integrity `ok`, and zero graph edges.
- 2026-07-11: [DONE] Adi approved clearing every remaining high-confidence
  person removal. All 464 passed the protected preflight, while AI Engineer
  stayed excluded under the explicit human keep override. The canonical
  manifest now records 625 approved identities. A byte-stable dry run resolved
  exactly 464 live rows plus 161 already-applied rows; the transaction removed
  464 people, X channels, and backing accounts. Registry state is 2,278
  entities: 2,168 people, 106 organizations, one unsure, and three rejected;
  foreign keys are clean, SQLite integrity is `ok`, and graph edges remain
  zero. The 41 medium-confidence removals and 56 review cases were untouched.
- 2026-07-11: [DONE] Individually audited the 41 medium-confidence removals
  against the repeated-original-signal boundary and preserved the full
  decision/evidence table. Retained Alfredo Canziani, Andrew McCalip, Anthony
  Goldbloom, Kyle Russell, Sankalp, Srinivas Narayanan, Sebastian Mallaby, Tim
  Scarfe, Aymeric Roucher, Oliver Habryka, and Brent Schooley. The other 30
  passed protected preflight and were removed transactionally after a
  byte-stable dry run. The canonical manifest now contains 655 identities.
  Registry state is 2,248 entities: 2,138 people, 106 organizations, one
  unsure, and three rejected; foreign keys are clean, SQLite integrity is
  `ok`, and graph edges remain zero. Only 56 review cases remain unresolved.
- 2026-07-11: [DONE] Completed the final bounded cleanup audit over all 56
  review cases. Retained 28 known frontier researchers, recent lab leaders,
  evaluators, and relevant AI organizations; approved 16 resolved out-of-scope
  identities for removal; and deferred 12 pseudonymous or identity-mismatched
  accounts rather than guessing. The 16 passed protected preflight and were
  removed transactionally after a byte-stable dry run. The canonical manifest
  now contains 671 identities. Registry state is 2,232 entities: 2,122 people,
  106 organizations, one unsure, and three rejected; foreign keys are clean,
  SQLite integrity is `ok`, and graph edges remain zero. The 12 defers are
  excluded from trusted-seed consideration and do not block ranking work.
- 2026-07-11: [DONE] Completed an independent read-only organization ownership
  audit plus direct X activity sweeps over 127 organization channels and 2,122
  person channels. Applied one reviewed merge (Moonvalley into Reka), three
  durable identity/name overrides, and one dormant-source removal (Papers with
  Code) through preflighted manifests. Two transient display-name corrections
  were dropped from replay after the later reach cutoff removed those entities.
  NVIDIA and Meta AI had no duplicate
  entities; Google and Google DeepMind remain separate. The delegated audit
  supplied an independent evidence pass and made no integration edits; parent
  work owned schema, manifests, documentation, and validation.
- 2026-07-11: [DONE] At Adi's explicit direction, applied a temporary
  organization reach boundary for the first PageRank cohort. Preserved all 17
  sub-10,000 organizations with original relevance evidence and a restoration
  note, then removed exactly their 17 entities, X channels, and accounts after
  a byte-stable dry run. Registry state is 2,213 entities: 2,123 people, 86
  organizations, one active unsure, and three rejected; no active organization
  remains below 10,000 combined X followers. Foreign keys are clean, SQLite
  integrity is `ok`, and graph edges remain zero.
- 2026-07-11: [DONE] Closed the Registry-cleanup phase before fresh graph
  ingestion. Verified that `data/fli.db` is byte-identical to the database blob
  in pushed commit `d9ffa37`, recorded its SHA-256, exact counts, integrity,
  foreign-key state, and recovery procedure, and removed disposable relevance
  canary/run scratch after confirming the durable review artifacts remain in
  project resources. The stored 2,235-account boundary is explicitly separate
  from the future active collection and smaller PageRank personalization sets.
- 2026-07-11: [DONE] Fixed the pre-ingestion repository boundary. Large raw
  pages and normalized edges will live in an ignored, immutable local SQLite
  snapshot under `data/raw/following/`; tracked `data/fli.db` remains the
  compact product/demo state. A tracked manifest binds cohort, provider,
  completeness, spend, checksum, and ranking/evaluation outputs. Future scale
  moves raw/Parquet data to object storage and run metadata to Postgres without
  changing snapshot-keyed ranking semantics. Adi explicitly declined GitHub
  Actions before deployment; local Stop-hook validation remains authoritative.
- 2026-07-11: [DONE] At Adi's direction, manually rejected the final active
  unsure identity, `@linatawfik9`, without another API or LLM call. Its
  structural kind and channel remain as provenance while the reason-bearing
  Registry state is rejected. The Registry now has zero active unsure and four
  rejected identities; excluding those four leaves 2,231 active X accounts in
  the first collection cohort.
- 2026-07-11: [DONE] Implemented the `following-snapshot-v1` local SQLite
  boundary and froze all 2,231 active, non-rejected X accounts into the tracked
  `registry-active-2026-07-11` cohort. The initialized local snapshot has 2,231
  pending sources, zero pages, zero accounts, and zero edges, and passes SQLite,
  foreign-key, checksum, cursor, and reconciliation validation. Page writes are
  transactionally raw-first, keyed by stable source X ID plus cursor,
  idempotent for identical retries, conflict-safe for changed evidence, and
  immutable after completion. No provider call or spend occurred.
- 2026-07-11: [DONE] Added the explicit-scope, JSON-first snapshot collector
  and proved page-level resume on `@karpathy`: one profile plus six following
  pages produced exactly 1,108 directed edges at an estimated `$0.01234`; the
  second run reused the cached profile and first page. Added a profile-only
  scan with a request-start limiter and ran the remaining cohort at 10 workers
  / 9 QPS under the Builder plan's documented 10-QPS cap. It cached 2,228
  profiles in total, marked nine protected and three missing sources, and
  completed 12 zero-following sources without following calls. Current profile
  counts project the full accessible crawl at `$27.83826`. No count-only
  exclusion is justified yet: all refreshed profiles pass the 1,000-follower
  floor and several high-following outliers are clearly valuable AI sources.
- 2026-07-11: [DONE] Verified the protected-account graph boundary with one
  bounded `@alsuhr` following-page probe. TwitterAPI.io returned success with
  zero rows/no cursor despite the cached profile advertising 637 follows, so
  protected sources remain explicit inaccessible terminals rather than false
  empty snapshots. They can still be graph targets: Karpathy's completed
  public list already supplies inbound edges to protected `@dwf` and `@gwern`.
- 2026-07-11: [DONE] At Adi's direction, placed all nine protected-only X
  identities in the existing Rejected view rather than hard-deleting them.
  They remain inactive and reversible with visible reasons, but cannot
  participate in normal collection, ranking inputs, or candidate output.
  Registry state is now 2,114 active people, 86 active organizations, zero
  unsure, and 13 rejected; the live UI was verified at 13 of 13 rejected rows.
- 2026-07-11: [DONE] After Adi explicitly authorized the projected `$27.84`
  spend, upgraded full collection to parallelize independent source accounts
  while preserving one sequential cursor chain per source and one shared 9-QPS
  request-start limit. The 20-worker run completed all 2,206 remaining sources
  with zero crawl errors in about 27 minutes. Together with calibration and
  zero-following exits, the finalized snapshot has 2,219 complete sources,
  nine protected, three missing, 13,409 raw pages, 463,180 target accounts,
  and 2,456,305 directed edges. Independent validation passed with no failures;
  best-available estimated spend is `$27.81218`. The 2.0 GB local database is
  immutable and its checksum/counts are frozen in the tracked manifest.
- 2026-07-11: [DONE] Paused before ranking/visualization to harden recovery.
  Created a 484,347,309-byte Zstandard archive of the finalized 2.0 GB local
  database, verified the compressed stream, and proved a streaming
  decompression reproduces the canonical database SHA-256. Recorded both
  hashes and sizes in the tracked manifest. No cloud upload occurred: the only
  visible Azure storage account belongs to an unrelated project, so a dedicated
  private destination still requires Adi's explicit approval.
- 2026-07-11: [DONE] Adi approved using WIN's existing S3-compatible storage.
  Reused its generated R2 environment in place, uploaded the content-addressed
  permanent archive, and streamed the entire remote object back through
  SHA-256. The 484,347,309 remote bytes exactly match the local archive. The
  manifest now records the durable `s3://` URI, checksum, ETag, and access
  limitation. No visualization or ranking work started.
- 2026-07-11: [DONE] At Adi's explicit direction, added the public R2 recovery
  URL to the tracked manifest. A live HEAD request returned HTTP 200 with
  `application/zstd` and the expected 484,347,309-byte content length. The
  archive is intentionally link-accessible and is not described as private.
- 2026-07-11: [DONE] Agreed the M3 storage contract with Adi and wrote the
  engineering instructions to `resources/m3-ranking-implementation.md`: three
  planes (curated fli.db, frozen snapshot.db, recomputable derived analysis
  store), active/rejected/unknown as a derived x_id LEFT JOIN rather than a new
  fli.db table, and reviewed promotion as the only door into the Registry. M3
  does not write graph summaries into fli.db without a concrete product need;
  the overlap baseline uses `cohort_follow_count`, and PageRank remains an
  experiment because most target accounts are dangling nodes.
- 2026-07-11: [DONE] Audited major model-organization coverage after the
  standalone Visual Studio Code row exposed source-list bias. Confirmed six P0
  missing anchors (Microsoft, Amazon, Apple, Ai2, ByteDance, Tencent), a
  first-party-evidenced P1 backlog, and seven existing product/team rows that
  should normalize to stable parents. No Registry rows changed. The required
  implementation is a versioned coverage manifest plus a transactional,
  snapshot-aware importer/merger and an automated P0 coverage check.
- 2026-07-11: [DONE] Implemented and applied the snapshot-pinned organization
  coverage contract. Fifteen reviewed parents now own their exact corporate,
  product, and research channels; 21 cached X accounts were imported without a
  provider call and eight product/team entities were merged. A follow-up
  compute audit fixed NVIDIA's missing main account and added AMD and Intel.
  Registry state is 2,220 entities: 2,114 active people, 93 active
  organizations, zero active unsure, and 13 rejected. Dry-run, real apply, and
  replay all completed cleanly; the replay made zero writes.
- 2026-07-11: [DONE] Implemented and ran the M3 screened-source overlap
  baseline. A new JSON-first `fli following-ranking overlap` command reads the
  immutable snapshot and only authorizer-approved Registry identity tables,
  writes a separate ignored `analysis.db`, and exports global and unknown
  top-100 review CSVs. The deterministic production run ranked 463,180 accounts
  from 2,456,305 edges and 2,219 complete active sources; 2,240 map active, 13
  rejected, and 460,927 unknown. An identical replay reused the same context
  and run without duplicate rows. At that checkpoint, personalized PageRank
  and human top-k review were the remaining steps.
- 2026-07-11: [DONE] Adversarially audited and corrected the M3 ranking
  foundation without touching the UI. Protected source databases and manifests
  from colliding outputs, transactionally snapshotted the live Registry before
  hashing, validated the complete frozen snapshot, failed closed on orphaned
  identities, included zero-score targets, reconciled reused rows, and proved
  a real legacy-graph query is denied. Corrected the vote unit from X accounts
  to real Registry entities: 2,219 complete source accounts resolve to 2,197
  voters over 2,456,305 edges and 2,456,084 deduplicated entity-target votes.
  Ties now share a dense score rank with separate deterministic position.
- 2026-07-11: [DONE] Froze a balanced experimental 30-source personalization
  manifest and completed personalized PageRank over the same immutable graph.
  The run converged after 104 iterations at L1 delta 9.83e-11 with score mass
  exactly 1.0, then replayed idempotently. Only 37.9% of its top 100 overlaps
  entity-overlap; all 30 seeds appear in the PageRank top 100 and narrow
  one-hop neighbors dominate its unknown results. PageRank remains diagnostic;
  entity-overlap advances as the default input to bounded M4 human review.
- 2026-07-11: [DONE] Completed the final M3 consolidation pass. Documented the
  immutable-evidence versus disposable-derived storage boundary, added
  symlink-alias overwrite coverage, normalized tracked CSV line endings, and
  removed temporary ranking outputs. `scripts/check-fast.sh` passed with 107
  tests plus frontend lint and production build. No Ranking UI source changed.
- 2026-07-11: [DONE] Shipped the Ranking tab: an interactive trust orbit
  (phyllotaxis layout, distance = earned rank, dot size = cohort follows,
  filled = in Registry, hollow = discovered outsider) with a synced ranked
  score column, search, All/In-Registry/Discovered filters, and click-to-see
  exactly which cohort sources follow any account (blue arcs + detail card).
  Backend adds read-only `/api/rankings` and `/api/rankings/followers/{x_id}`
  over the latest analysis.db plus the frozen snapshot; no ranking data is
  duplicated into fli.db or static JSON. Counts on the page reconcile with the
  overlap run (2,219 sources, 2,456,305 edges, 463,180 ranked, 460,927
  unknown). Validated via build, live endpoints, and browser screenshots.
- 2026-07-11: [DONE] Polished the Ranking tab. Organizations are now visually
  distinct (capital-blue squares vs ink person circles) on the orbit, in the
  list, and in the detail pill, with the filter widened to
  All/People/Orgs/Discovered so each kind is read within its own lane. Added
  hover and selection halos, Escape/background-click deselect, arc opacity
  scaling for dense selections, top-label suppression during selection, and a
  VIEW IN REGISTRY link that lands on the Registry pre-filtered (?q= support
  added). Fame-vs-trust scatter was consciously dropped as redundant with the
  orbit. Screenshot-audited each pass; check-fast OK.
- 2026-07-11: [DONE] Second Ranking-tab polish pass. Removed the permanent
  top-3 handle labels (hover/selection labels carry identification), added a
  close button on the detail card, an always-present hint line (hover to
  identify · click to trace · esc to clear), up/down-arrow stepping through the
  visible ranking, a showing-N-of-top-300 count, and an honest empty-search
  state that says deeper ranks exist beyond the loaded top 300. All
  interactions screenshot-audited via Playwright against the live server;
  check-fast OK.
- 2026-07-12: [DONE] Fixed the Ranking page regression introduced when the M3
  audit upgraded `ranking_run` and `ranking_result` to the v2 schema. The web
  adapter still queried removed `complete_source_count` and `rank` columns,
  causing `/api/rankings` to return HTTP 500. Updated it to the current account
  count and `position AS rank` contract, explicitly pinned the product endpoint
  to accepted `entity-overlap-v2` rather than the newer experimental PageRank
  run, and added endpoint fixtures covering both the ranking and follower
  queries. Live browser verification restored the orbit and detail interaction.
- 2026-07-12: [DONE] Added the read-only combined-evaluation boundary:
  one descriptive cached-prefix prompt, independent kind and Registry-decision
  fields with separate reasons, optional broad hosted web search, stable shared
  cache sharding, and cache read/write instrumentation. Ran exactly two
  sequential Luna-high evaluations through LiteLLM using the same cache shard:
  `@openai` resolved organization + active and `@janleike` person + active in
  the initial v1 calibration;
  neither needed web search. Proxy cost was $0.017755. Both responses reported
  zero cached tokens, so the implementation records but does not claim cache
  savings. Follow-up inspection proved the cache key was forwarded and both
  calls used the same Azure deployment. Renamed the model-facing v2 decision
  values to the more intuitive `keep | remove | review`; persisted Registry
  state remains a separate application mapping.
- 2026-07-12: [DONE] Completed the full GPT-5.4-mini-high read-only run over
  all 2,207 active X entities: 1,855 keep, 201 remove, 151 review, zero terminal
  failures, 68.38% cached input, and `$13.4861493` in current-result proxy cost.
  The X evidence store preserved 4,419 raw provider responses, 63,736
  normalized posts, and 2,207 exact input bundles. No Registry state changed.
- 2026-07-12: [DONE] Reused the exact evidence for all 192 person-removal
  recommendations in a Luna-high comparison. Luna kept 119, removed 60, and
  reviewed 13, with zero terminal failures and `$3.371936` reported spend.
  Jarred Sumner remained remove because the stored bio was null, the bundle was
  Bun-heavy, and neither model searched for his new Anthropic role. Alec
  Radford and other durable-but-inactive identities expose the larger boundary
  error: Registry membership and current-X-feed collection are separate
  decisions. The comparison remains read-only.
