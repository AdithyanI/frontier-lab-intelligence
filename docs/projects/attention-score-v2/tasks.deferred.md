# Attention Score v2

> **Deferred tracker.** The repo allows one active tracker at a time
> (`scripts/check-fast.sh`), and the submission critical path owns it. To
> activate this project after the current active tracker is archived, rename
> this file to `tasks.md` and update the STATUS active-tracker pointer.

## Goal

Replace the percentile encoding of the daily attention score's amplification
and support components with fixed saturating curves, validated against labeled
routing decisions, without changing the design's core policies (amplification-
dominant weights, one flat vote per Registry entity, merged quotes/reposts).

## Why / Impact

The v1.1 percentile encoding wastes the score's dominant 55% amplification
weight: with ~74% of daily candidates at zero amplifiers, one vote reaches the
~75th percentile and two votes the ~97th, so 2-vote and 40-vote posts score
nearly the same while measured usefulness keeps rising monotonically
(1 vote → ~40% relevant, 5+ → ~75%). Single-vote items (relevance *below* the
top-100 base rate) currently land near the top of the component. Fixing the
encoding spreads ranking resolution across the range that carries information,
makes scores comparable across days, and removes a degenerate-day failure mode
where the component silently zeroes out. Full analysis, measured evidence, and
design rationale: [resources/concept-and-evidence.md](resources/concept-and-evidence.md)
— read it first; it answers the "why not X" questions so they are not
re-litigated without new data.

## Scope / Non-Goals

### In Scope

- Offline evaluation harness replaying candidate formulas over the existing
  900-label v9 routing cohort (P@k, rank churn, mover inspection).
- Below-cutoff recall probe (ranks 100–200 + high-support zero-amp firsthand
  sample) to measure what the current formula buries.
- Quote-only vs. repost-only relevance split test from existing labels.
- Calibrating the v2 candidate anchors (amplification cap, support knee,
  weight split) against those measurements.
- Blind human top-20 ordering audit of v1.1 vs. the calibrated v2.
- If adopted: new versioned score contract, `feed.py`/`events.py` update, doc
  updates (`docs/references/signal-feed.md`, `docs/architecture/overview.md`),
  UI explanation text.

### Out of Scope

- Any production formula change before the 2026-07-20 submission is delivered
  (hard constraint — see Execution Rules).
- Prominence-weighted votes (PageRank/support-weighted amplifiers) — rejected
  in the concept doc as fame bias; do not reopen without new evidence.
- Increasing the author-support weight — measured flat above a low floor.
- Learned ranking models, semantic clustering, lane-separation redesign
  (firsthand vs. network-discovered as separate rankings) — the last is a real
  open question but a separate project.
- Re-anchoring frozen v9 routing rows or published insight decisions to a new
  rank.

## Context / Constraints

- Date started: 2026-07-16 (concept only; implementation deliberately deferred).
- Current formula: `attention-v1.1` in `src/fli/web/feed.py` (`SCORE_FORMULA`,
  `_percentiles`, `_apply_attention_scores`); same components consumed by
  `src/fli/web/events.py`. Documented in `docs/references/signal-feed.md`.
- Labels: 900 completed decisions in
  `data/derived/audience-routing/audience-routing-v9-*top100*/routing.db`
  (`routing_item`, status `complete`), joinable by `event_id` to
  `/api/events?date=<day>` → `daily_score_basis.score_components`.
- Baseline to beat: mean P@20 = 62.2% over the nine July 5–13 days (v1.1 blend;
  amplifier-count-alone already achieves 61.7%).
- Labels are model judgments (GPT-5.4-mini v9), not human truth, and are
  censored at the current top-100 — hence the human audit and below-cutoff
  probe milestones.
- STATUS lists "a learned ranking model or renewed daily-score weight tuning"
  as deliberately deferred; this project is the successor to that deferral and
  must not start implementation while the submission critical path
  (`docs/projects/evidence-audience-routing/tasks.md`) is active.
- All numbers in the concept doc are 2026-07-16 checkpoint evidence; re-verify
  against live stores before building on them.

## Done When

- [ ] An offline evaluation harness can replay any candidate formula over the
      900-label cohort and report P@20/P@50/P@100 per day plus rank churn.
- [ ] The v2 candidate's anchors and weights are chosen from measured results,
      with the comparison recorded in this project's resources.
- [ ] Below-cutoff probe and quote/repost split test are run and their
      outcomes recorded as decisions (adopt / reject / defer).
- [ ] A blind human top-20 audit confirms (or refutes) the model-label wins.
- [ ] Either: v2 ships as a new versioned contract with code + docs + UI
      explanation updated and frozen artifacts left un-re-anchored; or: the
      change is explicitly rejected with the evidence recorded.

## Milestones

- [ ] M1 — Evaluation harness. Replays v1.1 exactly (sanity: reproduces the
      62.2% baseline) and any candidate formula over the 900 labels.
      Acceptance: per-day P@k table + Kendall-τ churn output. Validate:
      harness reproduces published v1.1 ranks for two spot-checked days.
- [ ] M2 — Candidate calibration. Grid over amplification cap {8, 16, 32},
      support knee {100, 150, 300}, weight splits {55/25/20, 55/20/25}.
      Acceptance: chosen candidate ≥ v1.1 baseline on P@20 without degrading
      P@100; movers manually inspected. Validate: comparison table in
      resources.
- [ ] M3 — Below-cutoff recall probe. ~100 envelopes from ranks 100–200 plus
      high-support zero-amp firsthand sample routed with the current audience
      contract. Acceptance: measured relevance rate below the cutoff and its
      effect on the v2-vs-v1.1 verdict recorded. (Requires a routing run; keep
      to the current frozen prompt contract or its successor.)
- [ ] M4 — Quote/repost split test from existing labels. Acceptance: decision
      recorded (split or keep merged) with the measured gap.
- [ ] M5 — Blind human top-20 ordering audit, v1.1 vs. calibrated v2,
      shuffled. Acceptance: human verdict recorded per day.
- [ ] M6 — Ship or reject. If shipping: `attention-v2.0` contract in code,
      `signal-feed.md` + `architecture/overview.md` + UI score explanation
      updated, `scripts/check-fast.sh` green, frozen v9/insight artifacts
      untouched. If rejecting: evidence and decision recorded, project
      archived.

## Execution Rules

- **Hard gate: no production formula change before the 2026-07-20 submission
  is delivered and Adi confirms the freeze is lifted.** M1–M2 and M4 are
  offline/read-only and may proceed earlier if they do not touch production
  code paths; M3 spends (trivially) on routing calls and needs the usual
  spend norms; M5–M6 wait for the gate.
- Keep work scoped to the current milestone unless the tracker explicitly
  expands scope.
- Read `resources/concept-and-evidence.md` before proposing design changes;
  do not re-open the settled questions (prominence-weighted votes, higher
  support weight) without new measurements.
- Run validation after each milestone and fix failures before advancing;
  `scripts/check-fast.sh` before any handoff that touches code.
- Route any LLM calls through the shared LiteLLM endpoint with stable
  `metadata.tags`; record proxy-reported cost.
- Update this tracker whenever the plan changes materially or before ending a
  run; use `Current Batch` as the live board.
- When `Done When` is satisfied, archive to
  `docs/projects/archive/attention-score-v2/`.

## Decisions

- 2026-07-16: Keep amplification-dominant weighting (~55%); it is the only
  monotonic usefulness predictor (concept doc §2, §4). Encoding, not weight,
  is the problem.
- 2026-07-16: Keep one flat vote per Registry entity; reject prominence-
  weighted votes as fame bias / double-counted prestige. Hyperactivity damping
  and affiliation diversity are the only sanctioned vote refinements, both
  calibration-gated.
- 2026-07-16: Keep quotes and reposts merged until M4 shows a measured gap.
- 2026-07-16: Replace percentile encoding with fixed saturating curves for
  amplification and support; keep percentile for log-engagement. Starting
  candidate: `A = log1p(n)/log1p(16)`, `S = log1p(s)/log1p(150)`, weights
  0.55/0.20/0.25 (support/engagement split to be settled in M2).
- 2026-07-16: Implementation deferred until after the submission; this project
  exists so the analysis is not lost and someone else can pick it up cold.

## Open Questions / Blockers

- Blocked (M5–M6 and any production change): submission freeze until
  2026-07-20 delivery and explicit go-ahead from Adi.
- Should firsthand (Registry-authored) and network-discovered lanes be ranked
  separately instead of blended? Deliberately out of scope here; if M2/M3
  results make the blend look unsalvageable, raise it as a new project rather
  than expanding this one.
- M3 dependency: which audience prompt contract is current when the probe
  runs (v9 or a successor) — use whatever is then-frozen, never a mixture.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| todo | M1: build offline evaluation harness reproducing the v1.1 baseline | parent | [resources/concept-and-evidence.md](resources/concept-and-evidence.md) |

## Backlog / Remaining Work

- [ ] M1 evaluation harness (promotable now; offline-only).
- [ ] M2 candidate calibration grid + mover inspection.
- [ ] M4 quote/repost split test (offline; can run alongside M2).
- [ ] M3 below-cutoff recall probe (needs routing calls + current contract).
- [ ] M5 blind human top-20 audit (post-submission gate).
- [ ] M6 ship-or-reject: code, docs (`signal-feed.md`,
      `architecture/overview.md`), UI explanation, `scripts/check-fast.sh`,
      build-log entry for the decision.
- [ ] Closeout: verify Done When, record final decision, archive tracker.

## Validation / Test Plan

- M1 sanity: harness-reproduced v1.1 ranks match `/api/feed` published ranks
  for ≥2 spot-checked days; baseline P@20 reproduces 62.2% ± tie noise.
- M2: comparison table (per-day P@20/P@50/P@100, Kendall-τ) committed under
  `resources/`; top movers eyeballed with verdicts noted.
- Code changes (M6 only): `scripts/check-fast.sh`; focused tests for the new
  score function including the degenerate all-zero and all-ones days.
- Ranking-by-single-component checks must randomize ties, or sorts silently
  preserve incoming order and all orderings look identical (see concept doc
  Reproduction Notes).

## Progress Log

- 2026-07-16: [DONE] Independent review of attention-v1.1 completed; all core
  claims verified against live data (pool distributions, percentile cliffs,
  900-label join, single-component P@20 head-to-head, amplification–support
  anti-correlation). Findings, proposed formula, and evaluation plan written
  to [resources/concept-and-evidence.md](resources/concept-and-evidence.md).
- 2026-07-16: [IN-PROGRESS] Tracker created. Implementation intentionally not
  started: submission freeze active; next agent starts at M1 (offline
  harness), which is safe to begin before the freeze lifts.
