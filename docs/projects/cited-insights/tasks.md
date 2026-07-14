# Cited Insights

## Goal

Turn the accepted Feed evidence into 3–5 excellent primary-cited insights per
day, surfaced in the app and rendered as one delivery artifact, with evaluation
evidence and a submission write-up — before 2026-07-20.

## Why / Impact

The rubric's heavy half — structured cited extraction, insight scoring,
actionable delivery, final report with real insights — is currently empty
(see the archived Feed project's submission gap audit). The evidence
foundation is done; this project converts it into the deliverable BIT actually
reads first.

## Scope / Non-Goals

### In Scope

- A versioned `insight-v1` schema: claim · why it matters · evidence citations
  (envelope + primary artifact links) · confidence · date · event-type tag
  (departure / release / capability / technique / open-model) · two persona
  so-what fields: `implication_investment` (implication + possible
  public-equity landing spot, flagged as hypothesis) and
  `implication_engineering` (adopt / investigate / ignore).
- LLM extraction over the top ~20 attention envelopes per day, resolving links
  already embedded in the tweets as enrichment (fetch, snapshot, cite).
- A relevance/substance gate so banter and thin envelopes yield no insight
  rather than a padded one.
- An Insights surface in the app: 3–5 insights per day with citations that
  click through to the Feed envelope and the primary artifact.
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
  producing 3–5 cited insights per day with resolved primary links.
- [ ] The five strong audit candidates are found (or each miss is explained).
- [ ] An Insights page ships: per-day insights, citations click through to
  Feed envelope and primary artifact.
- [ ] One rendered daily briefing artifact exists and is reproducible from
  the CLI.
- [ ] Evaluation evidence recorded: citation validity, hallucination control,
  worth-attention agreement on a blind sample.
- [ ] Submission write-up drafted covering rubric requirements, prompts with
  rationale, limitations, and extension paths.
- [ ] `scripts/check-fast.sh` passes; architecture docs and build log updated.

## Milestones

- [ ] M1 — Extraction pipeline (target Mon–Tue 07-14/15). Acceptance:
  versioned `insight-v1` schema + prompt, link resolution for top-20
  envelopes, run store with cost/usage telemetry; 2026-07-11 run finds the
  audit's strong candidates. Validate: pytest fixtures + manual audit
  comparison.
- [ ] M2 — Insights surface (target Wed 07-16). Acceptance: Insights page
  with per-day 3–5 insights, citation click-through to Feed envelope and
  primary artifact; desktop browser check. Validate: `scripts/check-fast.sh`
  + live check at 127.0.0.1:8797.
- [ ] M3 — Delivery artifact (target Thu 07-17). Acceptance: one rendered
  daily briefing (HTML or PDF) generated from the insights API by a CLI
  command; output visually checked. Freeze pipeline expansion after this
  milestone.
- [ ] M4 — Evaluation + write-up (target Fri–Sat 07-18/19). Acceptance:
  blind/stratified label pass recorded under `resources/`; write-up draft
  covering rubric map, prompts, hallucination control, limitations.
- [ ] M5 — Submission prep (target Sun 07-20). Acceptance: package reviewed
  against `docs/references/case-prompt.md`; submission itself only with Adi's
  explicit approval.

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

- 2026-07-13: Pause cited extraction until the active
  `temporal-event-projection` project removes future evidence from historical
  day envelopes and freezes canonical event/snapshot semantics. Existing
  triage runs remain audit evidence; do not treat a stale day-specific join as
  a trustworthy extraction input.

- 2026-07-14: The temporal projection prerequisite is complete and archived.
  Resume only the narrow five-record oracle from the corrected, snapshot-bound
  kept envelopes; broad extraction remains out of scope until that proof is
  reviewed.

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

- 2026-07-13: Replace the calibration contract with one permissive
  `gpt-5.4-mini`/medium Responses call with no tools and the minimal strict
  output (`decision`, `reason`). The model routes the complete envelope; it
  does not choose post IDs or assign a topic. Category belongs to each later
  extracted insight, where the resolved claim and source are available. The
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
  on effort; PDF preferred by gap audit, HTML acceptable if PDF costs too
  much time.
- Persona split (investor vs AI-engineer views): gap audit wants two views;
  timebox — ship one excellent general briefing first, add persona framing
  only if M3 finishes early.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Harden the v2 runner for the bounded expansion: deterministic prompt-cache shards, bounded parallel model calls, single-writer resumability, compact progress, and audit telemetry. | parent | — |
| done | Run a fresh bounded v2 calibration through LiteLLM; audit decisions and verify cache reads, tags, failures, resumability, and proxy-reported cost before expansion. | parent | — |
| done | Freeze and triage the top 1,000 attention envelopes per complete day (6,445 total), resume any failures, and record the final keep/drop/cache/cost distribution. | parent | [expansion report](resources/triage-v2.2-top1000-expansion-2026-07-13.md) |
| todo | Return to the five-record extraction oracle using corrected snapshot-bound envelopes and the shared canonical-artifact catalog. | parent | [pipeline-design.md](resources/pipeline-design.md) |

## Backlog / Remaining Work

- [x] Relevance/substance gate with recorded reasons per envelope.
- [x] Cross-day run with the unchanged rubric (seven complete days, top 100 each).
- [ ] Insights API + page with citation click-through.
- [ ] Daily briefing renderer + CLI command.
- [ ] Blind/stratified evaluation pass; record under `resources/`.
- [ ] Submission write-up draft; check against case prompt requirements.
- [ ] Architecture page: turn the dashed "cited insights" boxes solid when
  live; update `docs/architecture/overview.md`.
- [ ] Closeout: review learnings, archive tracker.

## Validation / Test Plan

- Fixture tests for schema validity, citation resolution, and gate behavior.
- Manual comparison of the 2026-07-11 run against the audit's five strong
  candidates.
- Blind label pass for citation validity and worth-attention agreement.
- `scripts/check-fast.sh` before every handoff; live browser check for UI.

## Progress Log

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
  evidence remains unchanged for scoring and audit logic.
