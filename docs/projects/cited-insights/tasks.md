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
- Sequencing decision (Adi, 2026-07-13): link-artifact resolution happens
  inside the extraction stage for top envelopes only — not as a prior Feed
  feature.

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

- 2026-07-13: Keep the frozen `attention-v1.1` candidate-generation contract:
  each active canonical Registry entity contributes one flat amplifier vote;
  the originator's entity-overlap support remains a separate component. Do not
  promote amplifier prominence into a second weight without blind evidence
  that it improves useful yield. Pass amplifier identity, relation type, and
  visible network support into the later qualitative extraction stage instead.
- 2026-07-13: Link enrichment lives inside extraction (top envelopes only);
  no second ingestion pipeline before submission.
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
| in_progress | Run a bounded `triage-v1` design spike over representative high-attention envelopes: compare the minimum dynamic input and output schema, verify prompt-cache reads and LiteLLM tags/cost telemetry, audit false drops against the July 11 labels, and recommend one-stage vs two-stage filtering. Do not run the full corpus. | worker | [top-20 audit](../archive/signal-intelligence-pipeline/resources/top-20-attention-audit-2026-07-11.md) |
| todo | Hand-build the extraction oracle after triage stabilizes: pull the five strong 2026-07-11 candidates, fetch their linked artifacts manually, and write the five `insight-v1` records they should produce. | worker | [pipeline-design.md](resources/pipeline-design.md) |
| todo | Build artifact fetch + insight extraction for one day with cost telemetry; pass the M1 oracle test. | worker | [pipeline-design.md](resources/pipeline-design.md) |

## Backlog / Remaining Work

- [ ] Relevance/substance gate with recorded reasons per envelope.
- [ ] Second-day run with the unchanged rubric.
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
