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

- **Why 17 days rather than the suggested ~3 months, with 68% of the €100
  budget unspent?** (finding 15) The inferred answer is X's first-party
  retrieval window, not budget or effort — but this audit did not confirm it
  from provider docs or ingestion code. Adi needs this as one sentence.
- **Does Adi want B3 (cross-day novelty) built before Thursday?** It is the
  highest-value pipeline improvement and the only build that can break the
  demo. Decision not yet made.
- Confirm the budget for B2 (~$2) and B4 (~$10). Adi has said cost is not the
  constraint if the result is good.
- Unclear who Carlos is. Vlad Gheorghe appears in the original interview
  thread subject. Marc handles welcome. Worth a public check before Thursday.
- Is the "Aion" reference in Investment rejection reasons intended
  cross-audience reasoning or prompt bleed? (finding 6)

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Audit Investment lane against prompt + BIT context | parent | `resources/findings.md` |
| done | Ship funnel yield line and merge/role labels | parent | — |
| done | Audit AI Engineering lane to the same depth | parent | findings 7–8 |
| done | Diagnose the concentration finding with a free measurement | parent | finding 1 |
| done | Anchor editorial rank against deterministic rank | parent | finding 9 |
| done | Second sweep: citations, deliverables, rubric coverage | parent | findings 13–15 |
| todo | **B0 — The 3–5 most interesting insights showcase** | handoff | finding 14 |
| todo | **B1 — Surface evidence rank on each Insight** | handoff | finding 9 |
| todo | **B2 — Run the ranks 101–200 recall probe** | handoff | finding 4 |
| todo | **B3 — Cross-day novelty delta** | handoff | finding 10 |
| todo | **B4 — Stability re-run** | handoff | finding 11 |
| todo | **B5 — Extend verification to `web` citations** (post-Thursday) | handoff | finding 13 |
| todo | Build quant-session defense pack | parent | — |
| todo | Rank the improvement list for Carlos/Vlad | parent | — |

## Recommended Work Order

Adi asked for a prioritized implementation list to hand to another engineer.
Ordered by (value × visibility) ÷ risk. **B0 first — it is the cheapest item
here and it touches the highest-weighted criterion in the rubric.** Then B1 and
B2, both safe. B3 last, because it is the only one that can break the demo.

### B0 — The 3–5 most interesting insights showcase

**One to two hours. Zero risk. No code, no model calls.**

An explicit required deliverable that does not exist anywhere in the repo or the
app (finding 14). The prompt calls it "proof that it works", and it answers the
question the prompt names as most important: *did this surface something we'd
genuinely want to know?*

Pick 5, write a paragraph each: what the system saw, what a human would have
missed, and the citation trail. Both audiences represented.

**Select from measured strength, not taste.** Finding 9 gives the rule: the
largest evidence-rank → Insight-rank promotions are where the system saw what
the crowd did not. Starting candidates, all Investment:

| Evidence rank | Insight |
| ---: | --- |
| 86 / 1360 | Oracle's OpenAI backlog now carries an investment-grade warning |
| 73 / 1360 | NVIDIA's Diffusers integration strengthens its software moat |
| 53 / 1360 | CXMT's HBM lag keeps Micron's AI-memory advantage intact |

The rank-12 evidence example is the best single demo of the ingestion layer: a
post whose entire text is three `t.co` links and zero words, behind which the
system resolved a 65,708-character Dwarkesh interview and a 114,642-character
Forecasting Research Institute report.

Engineering candidates should come from the merge cases — 15 of 84 Insights
merge multiple Events, and 4 carry an explicit `counterevidence` role.

### B1 — Surface evidence rank on each Insight

**Half a day. Zero risk. No model calls, no pipeline re-run.**

The number already exists. Every Insight carries `events[].feed_rank`, the
position of its source Event in that day's deterministic `daily-rank-v2`
ordering, out of `daily_rank_total` (1,360 on 21 July). It is never displayed.

Show it per Insight — for example "evidence ranked #39 of 1,360 that day" — and
ideally the delta against the Insight's own rank, since finding 9 proves the two
disagree in a meaningful and audience-appropriate direction.

This is the honest answer to "you never scored the Insights." It does not invent
a score, which the prompt calls a red flag. It exposes a measured, replayable,
hash-pinned quantity the system already computes. It also makes B0's selection
rule visible in the product rather than only in a script.

**Do not** derive a composite or weighted number from it.

### B2 — Ranks 101–200 recall probe

**Half a day. ~$1–2. Read-only; does not modify the product.**

Named in `scoring-validation.md` under "Honest limits" and never run. Route one
day's Events at ranks 101–200 through the same routing prompts and count how
many would have been marked relevant. This is the most likely Quant Research
question and currently has no answer.

There is already a known miss: on 5 July, Anthropic research sat at rank 111,
below a football rumour at 109. The question is not whether the gate is lossy,
it is how lossy.

### B3 — Cross-day novelty delta

**One day. The real build. Carries the only real risk.**

Already designed and explicitly deferred as follow-up item 2 in
`docs/references/daily-intelligence-batch-audit-2026-07-05-17.md`. Read that
section before starting — the design decision is already made and reasoned:

> expose compact recent-development fingerprints — canonical source URLs,
> accepted Insight IDs, company/mechanism keys, and the prior core claim — and
> require the editor to state what is new. It should **not** inject prior
> Insight prose wholesale because that would anchor the next editor.

That constraint is the important part. Fingerprints, never prose.

Guardrails for whoever builds it:

- **Freeze a fallback first.** The existing 17 days are the demo. Keep the
  current runs intact and readable no matter what happens.
- **Re-run narrow.** Two or three recent days, not all seventeen. Enough to
  prove it works, not enough to risk the corpus.
- Before/after on the same day is the better demo anyway.

### B4 — Stability re-run

**Half a day. ~$10.**

Re-run one day's editorial three times and count how many published Insights
recur. Converts "you are trusting the model to behave" from an opinion into a
number. Nondeterministic is not the same as unstable, and there is currently no
evidence either way.

### B5 — Extend citation verification to the `web` tier

**Not before Thursday. Recorded because it is the right next fix.**

Finding 13: the enforced excerpt check covers artifact citations only — 45% of
398 citations. The 62 `web` citations (16%) have a model-asserted URL, a
model-asserted excerpt and a model-asserted retrieval time, with nothing stored
to check against.

Same fix as batch-audit follow-up 4: capture and freeze fetched page text, then
drop the `kind != "artifact"` guard at `editorial_runs.py:1613`. That extends
enforced verification from 45% to 61% of citations.

Until then, **disclose the tiers rather than claiming blanket verification.**

## Backlog / Remaining Work

- [ ] Prepare the answer for mega-cap concentration (finding 1 — now diagnosed,
      needs rehearsing rather than fixing).
- [ ] Prepare the answer for insight scoring absence (findings 3 and 9).
- [ ] Prepare the answer for cross-platform entity resolution (finding 2).
- [ ] Consider aligning the Insights page subtitle to BIT's own wording
      (finding 5).
- [ ] Check whether "Aion" leaks into Investment rejection reasons by design
      (finding 6).
- [ ] Run finding 9's Spearman measurement on the AI Engineering lane too.
- [ ] Consider follow-up 4 from the batch audit — exact source-text windows and
      historical-availability metadata. This is the missing half of the
      entailment gap (finding 12) and is a stronger fix than a prompt change.
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
- 2026-07-27: [DONE] Free measurement on concentration. Kept Insights reach
  outside the mega-caps 16x more often than declined candidates (16% vs 1%).
  Selection is the corrective, not the cause; the constraint is registry
  coverage. Finding 1 re-diagnosed, severity high → medium.
- 2026-07-27: [DONE] Anchored the editorial layer against the deterministic
  rank. Spearman(insight rank, evidence rank) mean **0.179** across 16 days.
  The override direction is legible: demotes loud-but-financially-empty,
  promotes quiet-but-mechanical. Finding 9 recorded — best answer available to
  "how do you know the model isn't just deciding?"
- 2026-07-27: [NOTE] Read `daily-intelligence-batch-audit-2026-07-05-17.md`.
  The pipeline agents independently found cross-day novelty (deferred item 2)
  and the excerpt-vs-entailment gap, with five named citation-selection
  defects. Their design constraint — fingerprints, never prior prose, because
  prose anchors the next editor — is better than the one proposed in session.
- 2026-07-27: [DONE] AI Engineering lane audited across all 17 days / 124
  Insights. Every one carries a `decision_rule` (0 missing). Recurring house
  style: refuses adoption on benchmarks alone (8+ instances), prices work by
  accepted-task cost rather than tokens (5+). Aion confirmed as BIT's real
  public platform, not invented. Findings 7–8 recorded. **Recommendation: lead
  Thursday's walkthrough with this lane, not Investment.**
- 2026-07-27: [DONE] Second sweep — citations, deliverables, and rubric
  coverage. Three new findings. **13:** the enforced excerpt check covers
  artifact citations only; measured tiers are 45% excerpt-verified / 39%
  provenance-verified / 16% (`web`) unchecked. **14:** the explicit "3–5 most
  interesting insights" deliverable exists nowhere in the repo or app — now B0,
  the cheapest and highest-weighted item on the list. **15:** 17 days against a
  suggested ~3-month window with 68% of the €100 budget unspent; needs a
  one-sentence answer. Also confirmed alerts (Slack + email) and PDF export are
  real, zero Event double-counting across 199 Insights, and AI Engineering
  rho=0.42 vs Investment rho=0.18 on the finding-9 measurement.
