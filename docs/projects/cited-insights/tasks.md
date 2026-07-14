# Cited Insights

## Goal

Turn accepted Feed evidence into 3–5 excellent primary-source-cited insights
per day, surfaced in the app and rendered as one delivery artifact, with
evaluation evidence and a submission write-up — before 2026-07-20.

## Why / Impact

The rubric's heavy half — structured cited extraction, insight scoring,
actionable delivery, final report with real insights — is currently empty
(see the archived Feed project's submission gap audit). The evidence
foundation is done; this project converts it into the deliverable BIT actually
reads first.

## Scope / Non-Goals

### In Scope

- A minimal versioned `insight-v1` result: `insight |
  no_extractable_insight`; an insight contains one falsifiable claim, why it
  matters, one investment implication, one AI-engineering implication, and one
  exact supporting quote. Run IDs, dates, and citation/source IDs are bound by
  application code rather than returned by the model.
- LLM extraction over the top ~20 accepted attention envelopes per day. The
  complete stored first-party X evidence is always available; fetched external
  artifacts are optional strengthening when present.
- No second general relevance/substance gate. Feed triage owns that decision;
  extraction may return `no_extractable_insight` only when the accepted
  evidence cannot safely support a concrete claim.
- An Insights surface in the app: 3–5 insights per day with citations that
  click through to the exact first-party X source or external primary artifact.
- One rendered daily briefing artifact (email-style HTML or PDF) from the
  insights API.
- Evaluation: extraction validated against the five strong candidates from
  the 2026-07-11 audit; small stratified/blind label pass for citation
  validity and worth-attention agreement. No recall claims.
- Submission write-up: architecture story, decision trail (attention-v1.1,
  one-vote rule, exact grouping), limitations, extension paths.

### Out of Scope

- A second ingestion pipeline (blogs, RSS, GitHub, arXiv) — planned channels
  stay dashed in the Architecture diagrams.
- Any real external alert send. If an alert adapter is built, it writes to a
  local inspectable outbox only; external smoke requires Adi's explicit
  current-session approval.
- Feed ranking weight tuning; the audit says banter-vs-substance belongs to
  this extraction stage, not to attention weights.
- Backfilling the full 63k-post corpus.
- Mobile/responsive polish.

## Context / Constraints

- Date started: 2026-07-13. Submission deadline: 2026-07-20.
- Predecessor: `docs/projects/archive/signal-intelligence-pipeline/` — M4
  decision KEEP; `attention-v1.1` accepted as candidate generation; extraction
  cohort = top-20 attention envelopes per day, starting with audited
  2026-07-11.
- Eval seed: archived project's
  `resources/top-20-attention-audit-2026-07-11.md` (12 worth / 8 noise labels,
  5 strong extraction candidates with post IDs).
- Gap analysis: archived project's
  `resources/submission-gap-audit-2026-07-13.md` — insights/delivery ≈75% of
  remaining rubric weight.
- All LLM calls go through the shared LiteLLM endpoint with stable
  `metadata.tags`; capture proxy-reported cost as telemetry, never as a gate.
- Reusable primitives exist from Registry work: structured outputs, hosted
  search, usage/cost capture, prompt cache, resumability.
- Feed API and envelope contract are frozen; insights read from the derived
  run, never mutate evidence.
- Sequencing amendment (Adi, 2026-07-13): the first extraction oracle remains
  bounded to links from corrected, kept X envelopes, but canonical identity,
  aliases, fetch snapshots, and source provenance live in the shared
  `canonical-artifact-library` substrate. Cited insights consumes that store;
  envelopes do not own artifacts. RSS/GitHub/blog ingestion remains deferred.

## Done When

- [ ] `insight-v1` runs end-to-end on 2026-07-11 and at least one more day,
  producing 3–5 cited insights per day with verified primary-source quotes.
- [ ] The five strong audit candidates are found (or each miss is explained).
- [ ] An Insights page ships: per-day insights, citations click through to
  the exact first-party X source or external primary artifact.
- [ ] One rendered daily briefing artifact exists and is reproducible from
  the CLI.
- [ ] Evaluation evidence recorded: citation validity, hallucination control,
  worth-attention agreement on a blind sample.
- [ ] A local inspectable alert/outbox demonstrates persona routing without
  sending anything externally.
- [ ] Workflow tokenomics summarize provider-reported usage and cost for the
  collection, triage, artifact, extraction, and delivery paths.
- [ ] `docs/final-report.md` contains the rubric-mapped write-up, 3–5 real
  insights, prompts with rationale, limitations, and extension paths.
- [ ] A public reviewer `README.md` and one package smoke path reproduce the
  local demo from a clean checkout without collection or model calls.
- [ ] `scripts/check-fast.sh` passes; architecture docs and build log updated.

## Milestones

- [x] M1 — Extraction pipeline (target Mon–Tue 07-14/15). Acceptance:
  minimal versioned `insight-v1` schema + prompt, deterministic evidence
  bundles for the five-record oracle, application-bound citation verification,
  and a resumable run store with cost/usage telemetry; the 2026-07-11 run
  finds the audit's strong candidates. Validate: pytest fixtures + manual
  audit comparison.
- [x] M2 — Insights surface (target Wed 07-16). Acceptance: Insights page
  with per-day 3–5 insights and citation click-through to the verified X or
  artifact source; desktop browser check. Validate: `scripts/check-fast.sh`
  + live check at 127.0.0.1:8797.
- [ ] M3 — Delivery artifact (target Thu 07-17). Acceptance: one rendered
  daily briefing (HTML or PDF) generated from the insights API by a CLI
  command; output visually checked. Freeze pipeline expansion after this
  milestone.
- [ ] M4 — Evaluation + write-up (target Fri–Sat 07-18/19). Acceptance:
  blind/stratified label pass recorded under `resources/`; workflow
  tokenomics summarized; `docs/final-report.md` covers the rubric map,
  prompts, hallucination control, limitations, and 3–5 real insights.
- [ ] M5 — Submission prep (target Sun 07-20). Acceptance: package reviewed
  against `docs/references/case-prompt.md`; reviewer README, clean-checkout
  smoke path, and local alert/outbox proof pass. Submission itself only with
  Adi's explicit approval.

## Execution Rules

- Narrow end-to-end proof over breadth: one day working fully beats five days
  half-extracted.
- Insights are derived views; raw evidence and envelope runs stay immutable.
- Every insight must carry at least one resolvable citation; an insight
  without a checkable source is dropped, not shipped.
- Prefer fewer, better insights; the gate may return fewer than 3 on a thin
  day — record that honestly.
- Route LLM calls through LiteLLM with tags (app, pipeline, job, scope,
  prompt, run); use sharded `prompt_cache_key` for bulk repeated prefixes and
  verify `cached_tokens`.
- Run validation at each milestone; fix failures before advancing.
- Update this tracker and `docs/references/build-log.jsonl` after meaningful
  chunks; update `docs/architecture/overview.md` when the pipeline shape
  lands.
- Archive this tracker when Done When is satisfied or descoped at deadline.

## Decisions

- 2026-07-14: **Luna becomes the accuracy-first efficient-model default.**
  OpenAI positions `gpt-5.6-luna` for efficient high-volume work and recommends
  preserving the prior reasoning effort before trying one level lower. The
  current 64-envelope comparison justified that caution: Luna-low matched the
  accepted mini-medium decisions 63/64 but made one unsafe drop; Luna-medium
  matched 64/64, completed with zero failures, read 103,936 cached of 168,022
  input tokens, and cost $0.120354. The same five-item extraction oracle passed
  exact citation verification 5/5 with Luna-medium versus 4/5 in the stored
  mini baseline. Runtime defaults therefore become Luna-medium for triage and
  extraction and Luna-high for grounded identity/Registry evaluation; the
  complex relevance audit remains Terra-high. GPT-5.6 cache retention is a
  shared Azure/LiteLLM adapter concern, currently pinned to `24h`. Preserve old
  run provenance and continue measuring cache reads rather than assuming them.
  See `docs/references/model-routing.md`.

- 2026-07-14: Open a bounded **Network Source Architecture Audit** workstream
  under this tracker rather than creating a second competing active project.
  The audit freezes the distinction between Registry membership, monitoring
  cohort, network support, source role/priority, X reach, and observed yield;
  independent reviewers write separate resources and the parent synthesizes.
  Keep all 2,197 active identities monitored and preserve Feed's flat
  one-entity/one-vote rule until Adi accepts an architecture decision. See the
  [audit brief](resources/network-source-architecture-audit/project-brief.md).

- 2026-07-14: **Audit diagnosis accepted; review program collapsed.** Direct
  inspection resolved the audit's core question without the four independent
  review lanes. Findings: the Registry `Network rank` displays a `ROW_NUMBER`
  position over the 463,180-target discovery universe whose integer-vote ties
  break alphabetically — 290,408 targets share exactly one vote (positions
  172,773–463,180), so low-support members show alphabet-noise ordinals such
  as #308,612 (Josh Bersin, 1 vote). A tie-aware `score_rank` already exists
  in the analysis store, and the Feed consumes `cohort_follow_count`, not the
  ordinal, so the defect is display-scoped. Accepted deltas: (a) show support
  count with an explicit denominator plus a tie-aware within-Registry ordinal;
  never render a tiebreak position as a rank; (b) entity-level union support —
  count distinct eligible Registry entities following any official channel,
  self excluded ("one entity, one vote on both sides of the edge"); measured
  best-account undercounts include SpaceX 491→728, Google 1,087→1,201,
  Microsoft 537→632, Anthropic 1,156→1,215. This supersedes the earlier
  best-owned-account projection decision below. The global discovery ordering
  stays in the Ranking view, labeled as candidate generation.

- 2026-07-14: **No blanket organization weight; roles carry authority.**
  Importance is never blended into descriptive scores. Explicit roles and
  affiliations (frontier lab, lab employee, first-hand researcher) provide
  guarantees, badges, and routing; network support stays a checkable count.
  Cohort-optimality work (500/1,000 cutoffs, tier taxonomy, yield-based source
  evaluation) is deferred past submission; the audit records the designed
  yield-feedback loop and interview-ready limitation language instead.

- 2026-07-14: **AI Engineer conferences become a bounded candidate source.**
  Preserve the complete supported official snapshots, but admit only the first
  20 unique X-addressable World's Fair 2026 speakers in source order for the
  initial batch. Conference curation is provenance, not a ranking boost or a
  claim that this is the optimal cohort. Match by X identity, keep canonical
  fields lean (role, bio, listed organization/affiliation, source/date/evidence;
  verified organization website only), and leave LinkedIn, talks, and personal
  sites raw-only. The network coverage query ran before insertion. New admits
  are monitored immediately but cannot vote until a future following-snapshot
  collection includes their edges (post-submission).

- 2026-07-14: Make Registry public reach rank-first without discarding its
  magnitude. **X reach** is one stable ordinal across all active Registry
  entities and renders as `#rank · compact combined followers`; search, kind
  filters, and pagination only change visibility. Network rank remains the
  separate global account ordering. The two columns therefore support quick
  relative comparison while their underlying counts and scopes stay honest.

- 2026-07-14: Merge Registry and Ranking only at the navigation layer under a
  single Network workspace, with Ranking as the default and Registry preserved
  as the assignment-aligned identity term. Registry keeps Combined X followers
  as the public-reach measure and adds a separately sortable Network rank from
  the latest immutable entity-overlap run. For multi-account entities, the
  best global owned-account position is shown. This is an ordinal projection,
  not a new score, and it does not merge the entity and account datasets.

- 2026-07-14: Keep the five-record extraction proof, first Insights surface,
  and its Architecture update inside this active `cited-insights` project.
  They are one unfinished vertical slice, not separate projects. The current
  execution goal stops after five application-verified citations render in an
  honest audit UI; day-wide extraction, briefing generation, alerts, and final
  evaluation remain later milestones. The main agent owns the shared contract
  and integration. Parallel agents are reserved for independent evaluation,
  UI polish, or test review after that contract is stable.

- 2026-07-14: Freeze the first extraction contract around the accepted
  envelope, not around external-link availability. Authored first-party X is
  valid primary evidence for the author or organization's own work, release,
  or observation; replies, quotes, and retweets are not automatically primary.
  External artifacts strengthen the evidence when available but are optional.
  Feed triage remains the only relevance/substance gate. Extraction returns
  only `insight | no_extractable_insight`; the model never returns post,
  artifact, citation, run, or source IDs. Application code binds an exact
  supporting quote back to one supplied X or artifact source and rejects any
  unmatched quote. Defer category/event type, confidence, novelty, and richer
  scoring until the five-record oracle proves a consumer for them.

- 2026-07-14: Keep direct bounded retrieval as the primary artifact path and
  add `jina-reader-v1` only as a replaceable fallback for ordinary public HTML
  failures. Reader attempts use their own immutable fetch policy, preserve the
  complete JSON response plus clean Markdown, and never run for the deferred
  X/LinkedIn/YouTube/form adapters, robots-denied pages, authentication, or
  paywalls. The optional key is repo-local runtime configuration sourced from
  the canonical Key Vault secret; no secret CLI flag exists.

- 2026-07-13: Pause cited extraction until the active
  `temporal-event-projection` project removes future evidence from historical
  day envelopes and freezes canonical event/snapshot semantics. Existing
  triage runs remain audit evidence; do not treat a stale day-specific join as
  a trustworthy extraction input.

- 2026-07-14: The temporal projection prerequisite is complete and archived.
  Resume only the narrow five-record oracle from the corrected, snapshot-bound
  kept envelopes; broad extraction remains out of scope until that proof is
  reviewed.

- 2026-07-14 (superseded by the later evidence-contract decision): A shipped
  "primary-cited insight" was initially required to have an inspectable
  external artifact. The corrected contract recognizes authored first-party X
  as primary evidence and treats external artifacts as optional strengthening.
  Artifact access failures remain recorded; the pipeline does not bypass
  publisher controls.

- 2026-07-13: Adi explicitly reopened the earlier top-100/day stopping
  decision for one bounded learning run. Evaluate at most the top 1,000 exact
  attention envelopes per complete stored day, not the unrestricted long tail:
  6,445 frozen envelopes across 2026-07-05 through 2026-07-11. Keep the v2
  `decision` + `reason` contract unchanged; this pass does not categorize,
  extract artifacts, use web research, or fetch new X data. Validate a fresh
  small cohort first, estimate the full run from its proxy-reported cost, then
  expand only if cache, tags, resumability, and decision quality hold.

- 2026-07-13: Freeze `envelope-triage-v2.2` for the bounded expansion. Two
  64-row hill-climb calibrations exposed and corrected an over-strict demand
  for provider metadata: concrete self-described capability experiments,
  identifiable linked primary resources, AI-driven market claims, and specific
  interface/adoption theses remain `keep` candidates even before artifact
  resolution. The final cohort returned 47 keep / 17 drop, zero failures, 36
  cache-hit requests, and $0.130723 proxy-reported cost. An immediate rerun of
  the prior cohort made zero duplicate calls. Estimated 6,445-row spend is
  $13.17; cost remains telemetry, not a gate.

- 2026-07-13: Treat the completed top-1,000/day expansion as a learning and
  evaluation corpus, not the default extraction queue. The 6,445-row run kept
  3,339 envelopes and dropped 3,106 with zero failures; even ranks 751–1,000
  retained 42.9%, so attention has no safe relevance cutoff. Continue to use
  attention for ordering and the triage decision for routing, then return to a
  small cited-extraction oracle instead of broadening this pass. See the
  [expansion report](resources/triage-v2.2-top1000-expansion-2026-07-13.md).

- 2026-07-13 (category clause superseded by the 2026-07-14 extraction-contract
  decision): Replace the calibration contract with one permissive
  `gpt-5.4-mini`/medium Responses call with no tools and the minimal strict
  output (`decision`, `reason`). The model routes the complete envelope; it
  does not choose post IDs or assign a topic. Category was initially assigned
  to the later extraction stage; it is now deferred until a real consumer is
  proven. The
  obsolete v1 prompt and local v1 run stores were removed rather than supported
  through a compatibility path. Calibration reports remain historical evidence
  for the keep/drop rubric. Do not add a default reviewer model.

- 2026-07-13: Stop the cross-day validation at top 100 per complete day. The
  700-row run produced 407 unique kept events and 737 unique selected posts;
  ranks 81–100 still yielded 60.7% keeps, so attention has no sharp relevance
  cutoff, but expanding to top 200 would enlarge an already sufficient
  extraction queue. Revisit only if the one-day cited-insight path cannot
  produce 3–5 excellent outputs. Deduplicate downstream by
  `(event_id, input_sha256)`. [Seven-day report](resources/triage-seven-day-validation-2026-07-13.md).

- 2026-07-13: Keep the frozen `attention-v1.1` candidate-generation contract:
  each active canonical Registry entity contributes one flat amplifier vote;
  the originator's entity-overlap support remains a separate component. Do not
  promote amplifier prominence into a second weight without blind evidence
  that it improves useful yield. Pass amplifier identity, relation type, and
  visible network support into the later qualitative extraction stage instead.
- 2026-07-13: Supersede the earlier envelope-owned link-enrichment wording.
  The bounded extraction oracle uses a shared canonical artifact catalog so
  repeated X links fetch once and later source kinds can reuse the identity.
  This does not authorize a second broad ingestion pipeline before submission:
  X remains the only implemented discovery source, and RSS/GitHub/blog
  adapters plus an artifact Feed are deferred. See
  `docs/projects/canonical-artifact-library/`.
- 2026-07-13: Blind evaluation validates insight yield here rather than feed
  ordering in the predecessor project.
- 2026-07-13: Case-prompt example check — the sheet's example intelligence
  (researcher departures, capability jumps, new techniques, open models,
  pipeline-changing papers) is event-shaped and X-first; our pipeline answers
  5/7 outright. Partials: competitive-map shifts (cross-insight synthesis —
  manual for the final report, automated is a stated next step) and
  ticker/thesis implications (LLM-drafted, flagged as hypothesis). Persona
  tailoring is two schema fields, not a second system. 7-day window vs their
  ~3-month suggestion is defended as depth-over-breadth; pipeline is
  date-parameterized.

## Open Questions / Blockers

- Delivery artifact format (email-style HTML vs PDF) — pick during M3 based
  on the shortest reproducible path. A print-ready HTML briefing is acceptable
  if it communicates the same evidence clearly.
- Persona presentation — use one insight record with investment and
  AI-engineering implications, then render two audience sections from the same
  source of truth. Do not build two pipelines.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Diagnose the Network rank anomaly, denominators, tie semantics, and multi-channel projection against code and live data. | parent | [audit brief](resources/network-source-architecture-audit/project-brief.md) |
| in_progress | Expand direct admission to every X-addressable World's Fair 2026 and 2024 speaker; reconcile people, organizations, affiliations, and exact new-cohort counts. | parent | [conference import report](resources/network-source-architecture-audit/aie-conference-import-2026-07-14.md) |
| todo | Reconcile new identities against stored X profiles, daily content, and outgoing-follow coverage; collect only missing provider data with resumable telemetry. | parent | [audit brief](resources/network-source-architecture-audit/project-brief.md) |
| todo | Materialize a new immutable Registry-following snapshot and derived analysis run; preserve old snapshot semantics and disclose the new voting denominator. | parent | [audit brief](resources/network-source-architecture-audit/project-brief.md) |
| todo | Implement and validate the accepted display delta, compare old/new rankings qualitatively, and write the coverage/miss report plus ADR. | parent | [audit ADR](resources/network-source-architecture-audit/architecture-decision.md) |

## Backlog / Remaining Work

- [x] Relevance/substance gate with recorded reasons per envelope.
- [x] Cross-day run with the unchanged rubric (seven complete days, top 100 each).
- [x] Insights API + page with citation click-through and materialized-day navigation.
- [ ] Daily briefing renderer + CLI command.
- [ ] Blind/stratified evaluation pass; record under `resources/`.
- [ ] Local alert/outbox proof with no external send.
- [ ] Workflow tokenomics summary across the final demonstrated paths.
- [ ] `docs/final-report.md`, public reviewer README, and clean-checkout package
  smoke path; check against case-prompt requirements.
- [x] Architecture page: turn the dashed "cited insights" boxes solid when
  live; update `docs/architecture/overview.md`.
- [ ] Complete the bounded Network Source Architecture Audit review, record
  Adi's decision, and implement only an accepted delta; do not let the audit
  silently displace M3–M5 delivery work.
- [ ] Closeout: review learnings, archive tracker.

## Validation / Test Plan

- Fixture tests for schema validity, deterministic evidence binding, exact
  citation resolution, and `no_extractable_insight` behavior.
- Manual comparison of the 2026-07-11 run against the audit's five strong
  candidates.
- Blind label pass for citation validity and worth-attention agreement.
- `scripts/check-fast.sh` before every handoff; live browser check for UI.

## Progress Log

- 2026-07-14: [AIE-REGISTRY-AND-NETWORK-GOAL] Adi expanded the bounded import
  into a persistent data-creation goal before stepping away: directly admit all
  X-addressable World's Fair 2026 and 2024 speakers; identify which newly
  admitted identities lack stored X profile/content/following evidence;
  collect missing data through the existing provider path; build a new
  immutable following snapshot and recompute network-derived views with an
  explicit new denominator; qualitatively audit the cohort/ranking movement;
  and finish the previously accepted Registry/Ranking display corrections.
  Europe 2026 and Summit 2023 remain snapshot-only. Admission, monitoring,
  collection completeness, and voting eligibility remain separate states so a
  Registry write cannot silently rewrite the frozen 2026-07-11 analysis.

- 2026-07-14: [AIE-CONFERENCE-COHORT-20] Added a deterministic conference
  source boundary over four official snapshots (World's Fair 2026, Europe
  2026, World's Fair 2024, Summit 2023). The pre-write audit found 945 records,
  528 unique X handles, 101 already active, 427 new, and zero rejected matches.
  Per Adi's narrowed decision, imported exactly 20 source-order World's Fair
  2026 speakers: 4 enriched existing people, 16 created people, 15 created
  organizations, and 19 dated affiliations. Only X identity, role, bio, listed
  company, affiliation, and provenance entered canonical tables; LinkedIn,
  sessions, and personal sites remain raw-only. Focused tests cover parsing,
  the stable limit, idempotency, lean facts, and rejection preservation. See
  the [import report](resources/network-source-architecture-audit/aie-conference-import-2026-07-14.md).

- 2026-07-14: [AUDIT-DECIDED] Collapsed the four-lane audit review after a
  direct diagnosis answered its core question: the Registry Network rank was
  an alphabetical tiebreak position inside huge one-vote tie blocks of the
  463k discovery ranking (290,408 targets share one vote), display-scoped
  because the Feed consumes counts, not positions. Adi accepted: entity-union
  support with explicit denominators and a tie-aware within-Registry ordinal;
  no organization weighting (explicit roles/affiliations carry authority);
  AIE World's Fair 2026 speakers as a direct-admission candidate source with
  the coverage query mandatorily run before insertion; cohort cutoffs, tiers,
  yield evaluation, and new-admit voting deferred post-submission. Handoff
  spec for the implementing engineer:
  `resources/network-source-architecture-audit/aie-worldsfair-2026-source.md`;
  full rationale in the brief's Decision Addendum.
- 2026-07-14: [NETWORK-SOURCE-ARCHITECTURE-AUDIT] Opened one bounded audit
  workstream under this canonical tracker after the repository correctly
  rejected a second active project owner. The frozen brief states the current
  evidence and separates monitored membership, network support, source role,
  source priority, reach, and yield. Four independent review lanes can now
  write topic resources without changing Feed collection, voting, ranking, or
  UI semantics before an accepted decision.

- 2026-07-14: [FIVE-RECORD-INSIGHT-SKELETON] Froze the five handwritten
  oracle envelopes and ran `insight-v1.1` through `gpt-5.4-mini`. All five
  calls returned an insight; application code published four exact-bound
  citations and rejected rank 12 after the model removed a leading source
  word and changed capitalization. Three of five eligible requests read from
  prompt cache; proxy-reported cost was $0.024084. Preserve this miss rather
  than silently repairing it. The first UI/API intentionally exposes only the
  four verified records so Adi can review the prompt and schema before any
  broader run. See the [oracle evaluation](resources/insight-oracle-evaluation-2026-07-14.md).

- 2026-07-14: [ARTIFACT-SOURCE-DATE-NAVIGATION] Added the same seven-date
  navigator used by Feed to the Artifact index, keyed strictly by the UTC
  publication date of the X source observation rather than retrieval time.
  The API exposes distinct per-day artifact counts, exact-day search and
  bounded pagination; one canonical artifact may appear on every day it was
  independently observed. Feed and Artifacts now share one navigator
  component. Live browser proof selected a prior day and loaded 60 matching
  rows; a final audit also fixed search across non-latest same-day source
  observations.

- 2026-07-14: [EXTRACTION-CONTRACT-DISTILLATION] Audited the post-artifact
  boundary before adding extraction code. The previous brief had leaked three
  premature assumptions into the plan: external artifacts were mandatory,
  extraction repeated Feed's relevance/substance gate, and the model returned
  source IDs plus unused category/confidence/novelty fields. Froze the smaller
  contract instead: accepted envelope + optional artifact text in, `insight |
  no_extractable_insight` out; authored first-party X can be primary evidence;
  application code binds and verifies the exact supporting quote. No runtime
  pipeline, Registry, Feed, ranking, or canonical artifact data changed.

- 2026-07-14: [POST-ARTIFACT-SEQUENCING] Reconciled the live catalog against
  the assignment, `docs/STATUS.md`, and the five-record oracle. Two independent
  read-only reviews agree that the next bottleneck is the cited claim → exact
  primary span → audience implication proof, not broader artifact massage.
  Corrected the Artifact index to use immutable source-observation recency:
  redirect/fetch convergence had incorrectly promoted an older NVIDIA source
  through mutable artifact metadata. Keep catalog chronology separate from a
  future extraction queue; do not imply relevance or artifact quality through
  retrieval state, observation count, or cross-day rank.

- 2026-07-14: [ARTIFACT-INDEX] Added the first read-only Artifact Library
  surface at `/artifacts`, backed directly by the canonical SQLite catalog.
  It lists one canonical artifact per row and keeps fetch state and provenance
  expandable instead of adding another analysis view. The later rank-first
  refinement orders each selected day by the best originating Feed rank and
  leaves source time as a compact secondary fact; it does not invent a new
  artifact score. The live app renders 1,566 artifacts, including 22 text
  snapshots and eight current retrieval issues; the initial API returns 60
  rows and supports bounded pagination.

- 2026-07-14: [JINA-READER-FALLBACK] Added a separate `jina-reader-v1`
  recovery run behind the native `bounded-public-v1` fetch contract. The
  fallback is JSON-only, authenticated from the repo-local Key Vault mapping,
  append-only, resumable, denylisted for deferred provider adapters, and stores
  provider provenance plus token usage without changing artifact identity.
  Twelve focused fetch tests pass. The live bounded proof recovered all three
  OpenAI HTTP-403 artifacts (GPT-5.6, GPT-Live, and ambitious work), producing
  82,476 clean-text characters with zero failures; an immediate replay made no
  duplicate calls. Next remains the five-record insight oracle, not broader
  crawling.

- 2026-07-14: [AGENT-NATIVE-HANDOFF-CONSOLIDATION] Adversarial cold-start,
  harness, and submission-strategy reviews all recovered the same critical
  path but found competing stale directions in Architecture, the historical
  case-prompt plan, the reviewer guide, and the artifact section of this
  project's implementation brief. Consolidated the durable route to
  `AGENTS.md -> docs/STATUS.md -> this tracker`, replaced obsolete future-state
  schemas and build order with implemented boundaries, added the missing
  reviewer README/demo, local alert outbox, tokenomics, final-report, and
  package-smoke acceptance proof, and froze an exact five-record oracle resume
  packet. Current artifact coverage supports Mira's primary article; the other
  four oracle records must resolve primary evidence or remain explicit misses.
  Added a fast-check invariant that prevents multiple active trackers and
  requires STATUS to name the active one. No product pipeline, Registry, graph,
  Feed, or external system was changed.
- 2026-07-14: [SYSTEM-STATUS-HANDOFF] Added `docs/STATUS.md` as the concise
  cross-project orientation for cold agents and system-level planning. It
  distinguishes proven foundations, the active cited-insight boundary,
  submission-critical missing work, and deliberate deferrals; `AGENTS.md` now
  routes to it before the active tracker. The tracker remains the execution
  source of truth and the build log remains chronological history.
- 2026-07-14: [FEED-SEVEN-DATE-NAVIGATOR] Replaced the unbounded wrapping date
  grid with a fixed seven-date navigator anchored to the newest complete days.
  Older/newer buttons page through non-overlapping available-date windows,
  preserve the selected column where possible, expose explicit disabled and
  focus states, and keep every target at least 44px. Background prefetch now
  follows only the visible window instead of every historical date. Two
  isolated layout checks agreed that the existing single-row density and
  hierarchy should remain; the post-change detector is clean and three focused
  frontend regression tests plus the production build pass. The in-app Browser
  runtime still fails during connection setup, so no new live visual proof is
  claimed for this batch.
- 2026-07-14: [FEED-AUDIT-CRITICAL-FIXES] Kept the audit remediation narrow
  after Adi challenged a broad cleanup. The Feed now clears stale rows before
  uncached view changes, keys both foreground and pagination writes to the
  active date/filter/sort/search identity, surfaces scoped load failures, and
  exposes the selected date with `aria-pressed`. Replaced the second broad
  positional selector with an explicit triage-decision class. Added a
  zero-dependency frontend regression suite for both selector leaks and the
  evidence-state guards, and wired it into `check-fast.sh`. Mobile redesign,
  broad target resizing, cache tuning, and cosmetic cleanup remain deferred.
- 2026-07-14: [FEED-MENU-TYPE-CONSISTENCY] Adi caught that Sort option labels
  rendered smaller than Audit option labels. The shared `span:last-child`
  selector intended for Audit counts also matched Sort's only span, shrinking
  every Sort label to the 9.5px count size. Replaced the positional selector
  with an explicit `feed-menu-option-count` class. Browser-computed styles now
  prove all option labels are 11.5px in both menus while only numeric counts
  remain 9.5px; browser logs are clear.
- 2026-07-14: [FEED-MENUS-COMPACTED] Adi's visual follow-up showed that the
  corrected dropdown language was right but the 210px panel and 40px rows
  were still oversized for their short option sets. Tightened both shared
  panels to the 166px trigger width and 36px rows while preserving the 44px
  trigger target. Live checks confirmed that all four Audit labels and counts
  fit, the three Sort options read cleanly, menu exclusivity still holds, and
  browser logs remain clear.
- 2026-07-14: [FEED-MENUS-ALIGNED] Adi flagged that the open Audit and Sort
  controls felt visually unrelated to the rest of the product. Reworked the
  shared Feed disclosure treatment from floating rounded cards into the
  established editorial vocabulary: square ink rules, flat hairline-separated
  rows, sand hover, and ink selection. Both menus now open from their left
  edge, keeping the Audit panel inside the narrower in-app Browser viewport;
  live verification covered both open states, selected-state semantics,
  outside-menu exclusivity, Escape dismissal, and browser logs.
- 2026-07-13: [TRIAGE-V2-EXPANSION-STARTED] Adi asked for a simple, resumable
  full learning pass while away, bounded to the top 1,000 attention envelopes
  per complete day. Measured the exact cohort at 6,445 envelopes. Official
  OpenAI prompt-caching guidance reconfirmed the existing prefix shape (stable
  1,024+ token instructions first, variable envelope last) and the need for
  stable cache-key sharding when increasing request throughput. Replanning the
  runner and validating a fresh cohort before paid expansion; no prompt/schema
  changes and no artifact extraction or new provider fetches in this pass.

- 2026-07-13: [TRIAGE-V2.2-CALIBRATED] Hardened the runner with 32
  deterministic cache lanes, one in-flight request per lane, 32-worker bounded
  concurrency, single-thread SQLite persistence, and compact progress. Ten
  focused tests pass. Two fresh 64-row calibrations corrected three obvious
  false drops and one inconsistent adoption-thesis drop without changing the
  two-field schema. Final v2.2: 47 keep / 17 drop, 36 cache-hit requests, zero
  failures, $0.130723; extrapolated bounded-run spend $13.17. Prompt frozen for
  the 6,445-row execution.

- 2026-07-13: [TRIAGE-V2.2-TOP1000-COMPLETE] Completed the bounded expansion:
  6,445/6,445 envelopes, 3,339 keep, 3,106 drop, zero failures, and no retry
  above attempt one. LiteLLM reported $8.207020 total cost, 6,356 cache-hit
  requests, and 11,390,976 cached of 15,057,381 input tokens. Every run carried
  the expected tags; 452 repeated cross-day inputs produced zero inconsistent
  decisions. Lower-attention bands still contained concrete releases, papers,
  benchmarks, agent demos, and adoption claims, confirming there is no clean
  rank cutoff. The live Feed now reads the v2.2 decisions. Next: the five-record
  cited-extraction oracle, not more triage breadth. See
  `resources/triage-v2.2-top1000-expansion-2026-07-13.md`.

- 2026-07-13: [IN-PROGRESS] Opened the project after archiving
  signal-intelligence-pipeline (M4 KEEP). Scope, milestones, and sequencing
  decisions agreed with Adi in session.
- 2026-07-13: [DESIGN] Wrote the full implementation brief
  (`resources/pipeline-design.md`): five-stage pipeline (top-20 →
  triage-v1 gate → artifact-v1 store keyed by canonical URL →
  insight-v1 extraction with programmatic citation verification →
  Insights page + daily briefing), schemas, eval plan with the audit
  oracle, timeboxed milestones, and hard constraints. Verified in raw
  data that 95% of t.co posts already carry expanded_url (21,316/22,342)
  — no new X calls needed for link resolution. Case-prompt example check
  recorded in Decisions. Handing to implementing engineer.
- 2026-07-13: [SCORE-CONTRACT] Reconfirmed the upstream `attention-v1.1`
  boundary before cited extraction. The implementation, regression test,
  durable Feed reference, system architecture, and live Architecture copy now
  agree on flat one-vote-per-entity amplification, separate originator support,
  and day-relative public engagement. Ranking behavior is unchanged.
- 2026-07-13: [TRIAGE-SPIKE] Started a bounded prompt/schema experiment before
  production extraction. Primary model is `gpt-5.4-mini` through LiteLLM;
  `gpt-5.5` is reserved for a small disagreement check. The spike will compare
  conservative one-stage filtering against an optional reviewer stage using
  real envelopes, record false drops, and verify cache/tag/cost telemetry before
  choosing the durable contract.
- 2026-07-13: [TRIAGE-FROZEN] Completed five bounded 20-envelope runs (100
  calls total; no full corpus). The final `gpt-5.4-mini`/medium contract reached
  19/20 agreement and zero false drops on the audited cohort; its one
  disagreement correctly retained a substantive child hidden below a noisy
  root. An independently audited unseen cohort improved from 18/20 to 20/20
  after adding provider article/card metadata and clarifying first-hand product
  experience. Prompt cache reads were observed and total proxy-reported spend
  was $0.304257. Adi chose mini as the single default; no Luna comparison or
  routine `gpt-5.5` reviewer is needed. Next: build the five-record extraction
  oracle. See `resources/triage-spike-2026-07-13.md`.
- 2026-07-13: [TRIAGE-SEVEN-DAY] Completed 700/700 frozen top-100 rows across
  all seven complete days with the unchanged prompt: 487 keep, 213 drop, 407
  unique kept events, and 737 unique selected signal posts. Manual review of
  the 81–100 band supported the gate; its 60.7% keep yield shows there is no
  sharp attention cutoff but also no need to expand the already large queue.
  Repeated-event decisions were 100% stable. Added one schema-constrained,
  explicitly metered repair for rare post-ID transcription errors. Next:
  extraction oracle, not more triage. See
  `resources/triage-seven-day-validation-2026-07-13.md`.
- 2026-07-13: [TRIAGE-AUDIT-UI] Joined the newest complete per-day triage run
  into the existing Feed as a read-only audit layer. Attention, recency, and
  engagement remain independent sort choices; a separate All/Kept/Dropped/Not
  evaluated filter exposes stable counts, and evaluated envelopes show their
  category, reason, candidate rank, and selected-signal count inline. The
  expensive exact-envelope projection is now cached once per day, so search,
  sort, pagination, and triage filtering reuse it instead of rebuilding it.
  No model or provider calls were added and the next critical-path work remains
  the five-record extraction oracle.
- 2026-07-13: [TRIAGE-DISTILLED] Adi challenged two premature abstractions:
  category assignment before extraction and model-selected post IDs even though
  the next stage receives the full envelope. Replaced the active contract with
  decision + reason only, removed retweet-count exposure and the post-ID repair
  retry, deleted the obsolete v1 prompt/local runtime stores, and delegated a
  matching Feed UI distillation. Category will be assigned per extracted
  insight after artifact resolution.
- 2026-07-13: [TRIAGE-DISTILLED-VALIDATED] The clean v2 boundary now has one
  strict two-field schema, one model call, one resumable fresh-run schema, and
  one compact Feed projection. The live Feed truthfully shows all 972 July 11
  envelopes as not evaluated until a v2 run is deliberately started; the old
  700-row v1 decisions remain only in historical reports, not runtime state.
- 2026-07-13: [FEED-PROVENANCE-DISTILLED] Removed the duplicate Noticed by
  disclosure from Feed cards. The attention score remains the compact summary
  of Registry support, and Follow is now the single disclosure for exact quote,
  reply, continuation, retweet, and linked-post evidence. Backend amplifier
  evidence remains unchanged for scoring and audit logic. This records the UI
  terminology at that point; the 2026-07-14 rank-first decision below supersedes
  it for the current product surface.
- 2026-07-14: [ARCHITECTURE-STORY-UPDATED] Extended the lead Architecture
  diagram without adding another competing section. It now distinguishes the
  live evidence path (Registry → X evidence → exact envelopes → Feed), the live
  keep/drop routing gate, the live canonical artifact catalog, and the planned
  cited-writing and delivery boundary. Registry intake, storage, and scoring
  diagrams remain the deeper explanations below it.
- 2026-07-14: [FEED-RANK-FIRST] Replaced the persistent composite decimal with
  ordinal position in the active sorted and filtered Feed view (`#1`, `#2`,
  ...). This initial rank scope was superseded by [FEED-DAILY-RANK-STABLE]
  below. Clicking a rank reveals an anchored daily-score disclosure with the
  exact score-producing member post, raw inputs, within-day percentiles,
  weights, contributions, and limitations. Consolidated current terminology:
  rank is the visible position; daily score is the `attention-v1.1` calculation;
  tracked amplification, author network support, and public engagement are its
  three inputs. Attention remains the broad product question, not the number's
  UI label. A future weekly rank must declare its comparison scope and must not
  average incomparable daily scores.
- 2026-07-14: [FEED-DAILY-RANK-STABLE] Froze one daily score rank over all
  projected evidence before Audit, search, or pagination. Filters now only hide
  rows, so Kept, Dropped, and Not evaluated cannot each present a conflicting
  `#1`. The API carries `daily_rank` and `daily_rank_total`; the disclosure
  names the value `Daily rank`, and a future weekly rank remains a separately
  defined comparison scope.
