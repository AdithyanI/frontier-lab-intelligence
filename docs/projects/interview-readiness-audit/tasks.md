# Interview Readiness Audit

## Goal

Give Adi a defensible, evidence-backed account of what the system does well,
where it is genuinely weak, and what he would improve — ready to use in the
30 July 2026 on-site at BIT Capital.

## Why / Impact

Adi wants this job. The case study is already submitted and frozen; the
remaining variable is whether he can explain and defend it, and whether he
walks in with a credible improvement list.

BIT asked for exactly that. Lars, 23 July:

> Followed by a session with Carlos and Vlad also regarding your case.
> **If you can think upfront about things you would want to improve in it
> that would be a good preparation.**

So this audit is not optional polish. It is the requested preparation.

## Scope / Non-Goals

### In Scope

- Audit both audience lanes (Investment, AI Engineering) against the case
  prompt, the BIT research context, and live data.
- Verify every claim against the running service or the databases, not docs.
- Record findings with the exact numbers behind them.
- Small, low-risk UI changes that surface judgment the system already records.
- Identify the highest-value measurement that can still be run before Thursday.

### Out of Scope

- Rebuilding ranking, routing, clustering, or the editorial layer.
- New ingestion sources, registry expansion, or model changes.
- Any external send, publish, or contact with BIT. Blocked without Adi's
  explicit approval in-session.
- Changing production behavior merely to look more complete.

## Context / Constraints

- Date started: 2026-07-27
- On-site: **Thursday 30 July 2026, 12:00–16:00**, Dircksenstraße 4, Berlin.
- Agenda per Lars (23 July):
  1. Marc — welcome and tour.
  2. **Carlos and Vlad — the case.** Explicitly asked: bring improvements.
  3. **Data Science session with the Quant Research Team.**
- Adi brings his laptop and drives the demo himself.
- Three working days: 27, 28, 29 July.
- The Quant session is the highest-risk technical room. Scoring rigor,
  validation, selection bias, and recall are quant-native questions.
- Case prompt: `docs/references/case-prompt.md` and the source PDF/text under
  `docs/references/source-material/`.
- BIT research: `docs/references/bit-capital-editorial-context.md`, plus the
  `/bit-lens` product page.
- Scoring evidence already written: `docs/references/scoring-validation.md`.
- Live service: `http://127.0.0.1:8797`.

## Done When

- [ ] Both lanes audited against the prompt with numbers, not impressions.
- [ ] Findings recorded here with the evidence behind each one.
- [ ] A ranked improvement list Adi can speak from in the Carlos/Vlad session.
- [ ] Quant-session defenses prepared for scoring, validation, and recall.
- [ ] Any shipped change verified in the browser and `scripts/check-fast.sh`.

## Milestones

- [x] Milestone 1 — Investment lane audited against the prompt and BIT context.
      Acceptance: concentration, rejection quality, and merge behavior measured
      from live API. Validate: numbers reproduced from `/api/insights`.
- [x] Milestone 2 — Surface recorded judgment already in the data.
      Acceptance: funnel yield line and merge/role labels render on both
      audiences. Validate: `npm --prefix frontend run build`, browser check,
      `scripts/check-fast.sh`.
- [x] Milestone 3 — AI Engineering lane audited to the same depth.
      Acceptance: candidate quality, action shape, and suppression reasons
      measured across all 17 days. **Result: the stronger lane. 124/124
      Insights carry a falsifiable `decision_rule`; house style visible in
      the titles. Findings 7–8 recorded.**
- [ ] Milestone 4 — Quant-session defense pack.
      Acceptance: written answers for selection bias, recall below the gate,
      the layer-attribution table, and the Digg comparison's limits.
- [ ] Milestone 5 — Ranked improvement list for the Carlos/Vlad session.
      Acceptance: each item states the gap, the evidence, and the fix.

## Execution Rules

- Verify before asserting. Every finding needs a number pulled from the live
  service or a database, and the command that produced it.
- Audit first, implement almost never. Ship only changes that expose judgment
  the system already records, and only when the risk is near zero.
- Do not touch ranking, routing, prompts, or editorial logic before Thursday.
- Talk to Adi like a person: one idea at a time, no information dumps.
- Record findings here as they land, while the numbers are fresh.
- Run `scripts/check-fast.sh` before handoff after any code change.

## Decisions

- **No Kept/Suppressed toggle on the Insights page.** The two views are
  different pipeline stages, not two halves of one list: `kept` is the
  editorial layer (66 reviewed → 6 published, 58 declined) while `suppressed`
  is the insight-editor gate (66 candidates → 30 surfaced, 36 suppressed).
  Placing them one click apart would show two different rejection counts for
  the same day with nothing explaining the gap. Reachable by URL if wanted.
- **Reject the organization/frontier-lab boost for thin days.** Tested against
  weekend data: only 13 lab-authored weekend Events exist, and the five with
  zero votes were Cohere marketing, two Google AI Studio "what are you vibe
  coding this weekend?" posts, and a football congratulation. The boost would
  have made the ranking worse.
- **Do not widen the investment prompt to admit thesis-only signals.** BIT's
  own wording is "connect private-lab developments to public-equity landing
  spots." The narrow bar is on-spec. The page subtitle is what is off-spec.

## Open Questions / Blockers

- Does Adi want the ranks 101–200 recall probe actually run before Thursday?
  It is the one named, designed, unrun measurement in `scoring-validation.md`,
  and it is the most likely quant question. Bounded to one day, ~$1–2.
- Unclear who Carlos is. Vlad Gheorghe appears in the original interview
  thread subject. Marc handles welcome. Worth a public check before Thursday.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Audit Investment lane against prompt + BIT context | parent | `resources/findings.md` |
| done | Ship funnel yield line and merge/role labels | parent | — |
| in_progress | Audit AI Engineering lane to the same depth | parent | `resources/findings.md` |
| todo | Build quant-session defense pack | parent | — |
| todo | Rank the improvement list for Carlos/Vlad | parent | — |

## Backlog / Remaining Work

- [ ] Audit the AI Engineering lane: candidate quality, experiment shape,
      suppression reasons, and whether it serves "what should we adopt".
- [ ] Decide with Adi whether to run the ranks 101–200 recall probe.
- [ ] Prepare the answer for mega-cap concentration (see finding 1).
- [ ] Prepare the answer for insight scoring absence (see finding 3).
- [ ] Prepare the answer for cross-platform entity resolution (see finding 2).
- [ ] Consider aligning the Insights page subtitle to BIT's own wording.
- [ ] Check whether "Aion" leaks into Investment rejection reasons by design.
- [ ] Validation pass: `scripts/check-fast.sh` plus browser verification.
- [ ] Closeout: finalize `learnings.md`, then archive the project directory.

## Validation / Test Plan

- `scripts/check-fast.sh` — repo fast checks, run after any code change.
- `npm --prefix frontend run build` — SPA build before browser verification.
- `fli daily-rank evaluate --json --no-input` — reproduces the ranking replay.
- Browser verification through `$agent-browser` against `127.0.0.1:8797`,
  captures under `tmp/` only.

## Progress Log

- 2026-07-27: [DONE] Verified the `daily-rank-v2` migration independently.
  `daily-rank evaluate` reproduced `replay-validation.md` exactly.
- 2026-07-27: [DONE] Fixed the How-page collect figure: added the tracked
  network box (2,431 people / 160 organizations) and corrected the relation
  stack to Post / Retweet / Quote / Reply.
- 2026-07-27: [DONE] Investment lane audited. Findings 1–11 recorded in
  `resources/findings.md`.
- 2026-07-27: [DONE] Shipped the funnel yield line on the Insights page
  (`6 published · 66 candidates reviewed · 58 declined in writing`, the last
  part reveals and scrolls to the declined log) and the merge/role labels in
  the Sources block (`3 EVENTS MERGED`, `PRIMARY` / `SUPPORTING` /
  `COUNTEREVIDENCE`). Verified in browser on both audiences; check-fast OK.
- 2026-07-27: [DONE] AI Engineering lane audited across all 17 days / 124
  Insights. Every one carries a `decision_rule` (0 missing). Recurring house
  style: refuses adoption on benchmarks alone (8+ instances), prices work by
  accepted-task cost rather than tokens (5+). Aion confirmed as BIT's real
  public platform, not invented. Findings 7–8 recorded. **Recommendation: lead
  Thursday's walkthrough with this lane, not Investment.**
