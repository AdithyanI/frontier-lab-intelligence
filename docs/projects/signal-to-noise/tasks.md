# Signal-to-noise ratio

## Goal

Raise the evidence bar of published Investment Insights so that a surfaced item
always rests on evidence a fund could act on, without suppressing the
provider-reported and shipped-fact evidence that legitimately drives investment
research.

## Why / Impact

Signal-vs-noise carries 20% of the case-study rubric and is the single question
the prompt names as most important: *"did this surface something we'd genuinely
want to know, and did it keep the noise out?"*

Three measured defect classes are recorded in the Progress Log. The clearest is
rank 1 on 2026-07-26 — the latest published day, which is what the product
opens on, so it is the first Insight a BIT reviewer sees:

> Headline: "ChatGPT's travel workflow raises the bar for Google Search"
> `what_changed`: "... This is a first-party anecdote, not a measured
> evaluation, and it does not establish repeatability, adoption, or completed
> reservations."

The model wrote the disqualifier and surfaced anyway.

The failure mode to avoid is over-correction. A blanket rule against
first-party or unquantified evidence would suppress provider-reported
benchmarks, launches, price changes, and disclosed incidents — the ordinary raw
material of investment research — and would leave the brief empty. The
suppression rate is already 35%.

## Scope / Non-Goals

### In Scope

- `src/fli/insights/prompts/investment_company_analysis.txt` — the evidence bar
  for surfacing.
- `src/fli/routing/prompts/audience_routing.txt` — a narrow rule inside the
  Investment-only section, once the Insight-stage fix is proven.
- Measuring false negatives introduced by any change before it is published.

### Out of Scope

- Ranking, `daily-development-rank-v1`, and the Digg validation. Ranking is the
  most defensible layer in the system and must not absorb evidence-quality
  judgment.
- Development grouping and same-day duplicate merging. Recorded as future work
  on the How page; see Decisions.
- The AI Engineering prompt. Its bar is deliberately different — a first-hand
  technical workflow is legitimate Engineering evidence.
- Any new suppression tool or second suppression path. See Decisions.
- Republishing the full 22-day corpus before the on-site on 2026-07-30.

## Context / Constraints

- Date started: 2026-07-29
- The BIT Capital on-site is 2026-07-30. Published data must stay coherent and
  citable until then. Prefer a measured, explainable finding over a shipped but
  unvalidated change.
- Live published state, verified 2026-07-29 against the running API:
  - Investment: 22 days, 2026-07-05 → 2026-07-26, 220 candidates,
    142 surfaced, 78 suppressed.
  - AI Engineering: 8 days, 2026-07-19 → 2026-07-26, 80 candidates,
    31 surfaced, 49 suppressed.
- Key files:
  - `src/fli/insights/prompts/investment_company_analysis.txt` —
    `# Suppression and rejection` at line 407, `## decision` at line 467.
  - `src/fli/insights/investment_agent.py` — `PROMPT_VERSION`, the
    `get_company_memo` tool at line 161, final schema at line 269.
  - `src/fli/insights/investment_agent_runs.py` — `CURRENT_PROMPT_VERSION`
    near line 19.
  - `src/fli/routing/prompts/audience_routing.txt` —
    `## The Investment routing boundary`.
- A second agent is active in this repository. It changed
  `src/fli/evidence/developments.py` at commit `ce083fe` on 2026-07-29 14:59.
  Re-read shared state before acting on it.
- Project Python is `.venv/bin/python`; bare `python` fails.

## Done When

- [ ] The unmeasured self-demonstration class no longer surfaces — the six
      instances in the Progress Log are suppressed with a stated reason.
- [ ] Provider-reported benchmarks, launches, price and availability changes,
      policy statements, and disclosed incidents still surface. This is the
      control condition and matters more than the suppression itself.
- [ ] The change is proven on at least one known-bad item and one known-good
      item before any published data changes.
- [ ] The false-negative cost is measured and recorded: how many previously
      surfaced Insights the new bar would suppress, with a human read of a
      sample to confirm they deserved it.
- [ ] Published Investment days remain internally consistent — no day serves a
      mixture of prompt versions, and no day disappears from the product.
- [ ] The decision and its measured evidence are explainable in one paragraph
      without reconstructing this tracker.

## Milestones

- [ ] M1 — Evidence bar added to the Investment prompt. Acceptance: the two
      edits in Decisions are applied and `PROMPT_VERSION` is bumped in lockstep
      with `CURRENT_PROMPT_VERSION`. Validate: `./scripts/check-fast.sh`.
- [ ] M2 — Single known-bad item flips. Acceptance: Development
      `b72d460234bd5322e8fdabc069a7cf0b1d323e0b500c6fca03d07b5f39f0c9d8`
      (2026-07-26 rank 1) returns `decision: suppress` with a reason naming the
      unevidenced first-party claim. Validate: run to a scratch DB and read the
      trace. Cost about $0.22.
- [ ] M3 — Known-good control holds. Acceptance: an item whose evidence is
      first-party but decisive still surfaces — for example 2026-07-20 rank 2
      (`MSFT-B5`), the only `threshold_met: true` connection in the corpus,
      where OpenAI paused deployment and changed requirements. Validate: same
      scratch-DB path. Cost about $0.22.
- [ ] M4 — Two-day false-negative measurement. Acceptance: 2026-07-24 and
      2026-07-26 re-run to a scratch DB; every changed decision is read by a
      human and classified as correct or a false negative. Validate: diff
      decisions against the published corpus. Cost about $4.50.
- [ ] M5 — Narrow Investment-only router rule, only if M2–M4 pass. Acceptance:
      the rule sits inside `## The Investment routing boundary` and the
      Engineering judgment is provably unchanged on a sample. Validate:
      `fli audience-routing run --dry-run` then a bounded scratch run.
- [ ] M6 — Publication decision. Acceptance: an explicit go or no-go on
      re-running all 22 days, with the cost and the risk recorded here.

## Execution Rules

- Keep work scoped to the current milestone unless this tracker expands scope.
- Never run against the published databases while testing. Use `--db` and
  `--trace-root` to write to a scratch location under `tmp/`.
- Run `./scripts/check-fast.sh` after each milestone and fix failures before
  advancing.
- Do not change ranking, grouping, or the Engineering prompt in this project.
- Every claim in the Progress Log must come from a command output or a database
  query, not from reading documentation.
- Update this tracker whenever the plan changes materially or before ending a
  run.

## Decisions

- **The Insight stage owns this fix, not the router.** The router is shared by
  both audiences and cannot make this call: deciding that a claim moves nothing
  requires the 176 pre-registered bets and their thresholds, and the router
  explicitly performs no company mapping. The same item is thin for Investment
  and legitimate for Engineering, so only a per-audience stage can hold two
  bars. The build log reached the same conclusion on 2026-07-28: *"target bare,
  weakly evidenced anecdotes rather than globally tightening the router;
  company mapping and the Insight gate remain responsible for final
  suppression."*

- **No suppression tool.** Considered giving the agent a `suppress(reason)`
  tool that exits early. Rejected on measured evidence: suppression is already
  a first-class outcome in the strict output schema
  (`decision: surface | suppress` plus `no_match_reason`), and it already exits
  early and cheaply.

  | decision | runs | avg turns | avg memos | avg cost |
  | --- | ---: | ---: | ---: | ---: |
  | suppress | 78 | 1.05 | 0.09 | $0.1253 |
  | surface | 142 | 2.04 | 2.36 | $0.2766 |

  A suppression is one turn with no memo calls. The ~20k input tokens are the
  prompt, packet, and 37 company cards, all present in the first request, so no
  tool could avoid them. A tool would add a second suppression path to store,
  validate, and render, nine days after roughly 9,000 lines were deleted to
  reach one path. The model already has the exit and used it 78 times; on the
  known-bad item it described the reason to use it and surfaced anyway. That is
  a threshold problem, and thresholds live in prompts.

- **The two Investment prompt edits.** The existing nine suppression bullets all
  test the strength of the causal chain; none tests whether the underlying claim
  is evidenced at all. The known-bad item survives every one of them.

  Add to `# Suppression and rejection`:

  ```text
  - the only evidence for the change is a first-party claim, anecdote, or
    self-run demonstration by the party that benefits from it, with no
    measurement, no independent account, and no retrievable artifact.

  Being first-party is not disqualifying by itself. Separate what a source did
  from what it says it can do. A price, a shipped capability, a stated
  commitment, an adoption figure, or a disclosed incident is decisive evidence
  even when first-party. A description of how well a product performed for its
  own maker is not, unless measured or corroborated.
  ```

  Add to `## decision`:

  ```text
  When `what_changed` would have to state that the evidence is an anecdote,
  unmeasured, unverified, or not independently confirmed, that sentence is a
  suppression finding, not a caveat to publish around.
  ```

- **The narrow router rule, deferred until M5.** If added, it belongs inside
  `## The Investment routing boundary` under "Useful distinctions include",
  where it cannot affect the Engineering judgment:

  ```text
  - A first-party demonstration, personal workflow account, or anecdote can
    qualify when the packet also contains a price, a shipped capability, a
    commitment, an adoption or usage figure, a measurement, or an independent
    account. A description of what a product did for its own maker, with none
    of those, is insufficient on its own.
  ```

  This is consistent with rules already in that list, which reject
  "availability or promotional claims alone" and "general optimism".

- **Cross-Development duplication is out of scope and already recorded.** On
  2026-07-24, ranks 4, 8, 10 and 13 are the same OpenAI agent incident. The
  cause is not a canonicalization bug: TIME, the Guardian and the Wall Street
  Journal each published a separate article, and rank 10 has no artifact at
  all, so exact-URL grouping cannot merge them by construction. The exact rule
  is deliberate — it makes an invented merge impossible. The fix is a
  cohort-level pass after a day's Insights are written, which is a new stage
  rather than a prompt change. Added to the How page under Future work on
  2026-07-29. A separate agent fixed the *cross-day* case at `ce083fe`; the
  same-day multi-publisher case remains open.

## Open Questions / Blockers

- Whether to re-run the full 22-day corpus before the on-site. Roughly $49 and
  it would bake a grouping change made on 2026-07-29 at 14:59 into every day
  presented. Current recommendation is no; decide at M6.
- Whether the 78 existing suppressions contain false negatives. Never audited,
  on either audience. This is the inverse of the current work and would make
  the calibration claim two-sided.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| done | Finding 1 — unmeasured self-demonstration class, six instances | parent | Progress Log |
| done | Finding 2 — 41 of 139 surfaced Insights rest on one Event with no artifact | parent | [zero-artifact-insights.md](resources/zero-artifact-insights.md) |
| done | Finding 3 — three Insights rest on unattributed claims | parent | Progress Log |
| todo | Continue auditing for further evidence-class defects before designing any rule | parent | |
| todo | M1 — apply the Investment prompt edits and bump both version constants in lockstep | worker | |

## Backlog / Remaining Work

- [ ] M4 — two-day false-negative measurement on 2026-07-24 and 2026-07-26.
- [ ] M5 — narrow Investment-only router rule, gated on M2–M4.
- [ ] M6 — explicit go or no-go on the full 22-day re-run, with cost and risk.
- [ ] Audit the 78 existing suppressions for false negatives.
- [ ] Update `docs/STATUS.md` if the evidence bar becomes a published contract.
      Note that STATUS.md is already stale: it describes Investment as a single
      July 21 top ten and Engineering as having no second day, while the live
      product serves 22 and 8 days respectively.
- [ ] Closeout: review and finalize `learnings.md`, then archive this project
      directory with the Project skill's archive helper.

## Validation / Test Plan

- Repo gate: `./scripts/check-fast.sh` — must print `check-fast.sh: OK`.
- Scratch-DB single item, about $0.22:

  ```bash
  .venv/bin/fli insights run-investment-agent \
    --through 2026-07-26 --days 1 --rank 1 \
    --db tmp/s2n/investment-agent.db \
    --trace-root tmp/s2n/traces --no-input
  ```

  Confirm the resolved cohort first with `--dry-run`.

- **Version-pin trap — read before running anything.**
  `investment_agent.PROMPT_VERSION` and
  `investment_agent_runs.CURRENT_PROMPT_VERSION` must be bumped together.
  `_latest_rows` filters on the store constant, so bumping the version and
  re-running only a subset makes every other published day disappear from the
  product. The Engineering agent has a guard in `run_days` that raises before
  spending when the two disagree; the Investment agent does not. Adding that
  guard is cheap and worth doing during M1.

- Consistency check after any publication, comparing published Insight
  Development IDs and ranks against the live `/api/developments` order for the
  same day. Verified clean for 2026-07-24, 2026-07-25 and 2026-07-26 on
  2026-07-29 after commit `ce083fe`.

## Progress Log

- 2026-07-29: [DONE] **Corrected an earlier overstatement.** The first pass
  reported that 29% of surfaced Insights "self-flag weak evidence", derived
  from a regex over `what_changed`. Reading all 55 matches showed the number is
  misleading. Most flags are the system behaving correctly: it labels
  provider-reported figures about a genuinely shipped product, or first-party
  statements where the statement itself is the fact (a launch, a policy
  warning, a disclosed incident). Investors act on company-reported numbers
  routinely, so labelling them is good epistemics rather than a leak. The
  regex measured honesty, not error. Do not use the 29% figure as a defect
  count.
- 2026-07-29: [DONE] **Finding 1 — unmeasured self-demonstration is the real
  leak, and it is small.** The defect class is narrower than first reported:
  an unmeasured anecdote in which the author describes their own product
  performing well. Six instances in 22 days:
  - 2026-07-26 r1 — ChatGPT travel workflow (`AMZN,GOOGL,META,PANW`),
    no artifact. Rank 1 on the latest published day, so it is the product's
    default view and the first Insight a reviewer sees.
  - 2026-07-25 r4 — AI paper-review gains (`MSFT`), no artifact.
  - 2026-07-11 r9 — AI-directed lab work (`03800.HK`), no artifact.
  - 2026-07-20 r5 — agent workloads, reported anecdotes plus company figures.
  - 2026-07-19 r30 — Claude Code longer loops, interview account.
  - 2026-07-17 r13 — autonomous coding agents, self-reported practitioner
    account.
  A rule targeting this class should not touch provider-reported benchmarks or
  shipped-fact announcements.
- 2026-07-29: [DONE] **Finding 2 — 41 of 139 surfaced Insights (29%) rest on a
  single Event with zero retrievable artifacts.** Measured structurally from
  `/api/developments` (`source_events` length and `development_artifacts`
  length), not from model prose, so it is deterministic and replayable. These
  Insights are built on one X post with no paper, blog post, model card, or
  article behind them, yet they generate company connections on `NVDA`, `MSFT`,
  `PANW`, `GOOGL`, `AMZN` and others. This is a stronger and more defensible
  measure than any regex over model output, and it is the same class of
  deterministic signal the router already uses in its evidence-readiness gate,
  which resolved 325 packets with no model call. Note that zero artifacts is
  not automatically disqualifying: a first-party price or availability change
  stated in a post is decisive without any document. It is a precondition that
  should raise the bar, not a filter on its own. Full list of the 41 recorded
  during this session.
- 2026-07-29: [DONE] **Finding 3 — three Insights rest on genuinely
  unattributed claims.** Distinct from first-party evidence, because no
  identifiable party is standing behind the claim:
  - 2026-07-18 r15 — "a non-technical user reported" (`MSFT`).
  - 2026-07-24 r2 — "early-access users reported" (`MSFT`, plus Xometry).
  - 2026-07-20 r18 — "Hugging Face reportedly ran ... after unnamed U.S." (
    `AVGO,PANW,RBRK`).
  Small in number, but this is the class most likely to embarrass the system in
  front of an investment team, because the source cannot be checked at all.
  An earlier regex reported 38 here; that was wrong, caused by matching the
  word "reportedly" in correctly attributed sentences. Verified by reading.
- 2026-07-29: [DONE] Measured concentration for completeness, not as a defect
  to fix in this project: 306 connections span 25 of 37 companies, the top
  three tickers hold 44%, `PANW` appears on 18 of 22 days, and 60 of 176
  standing bets have ever fired. Adi owns this observation separately.
- 2026-07-29: [DONE] Measured the leak against live data. 142 of 220 Investment
  candidates surfaced across 22 days (65%). Of 306 company connections, exactly
  1 has `threshold_met: true`.
- 2026-07-29: [DONE] Confirmed the threshold gate is functional rather than
  dead. The single `threshold_met: true` case is 2026-07-20 rank 2 on
  `MSFT-B5`, where OpenAI paused deployment and required new controls. The
  reasoning is sound, so the conservatism is design rather than a defect.
- 2026-07-29: [DONE] Rejected the suppression-tool design on measured grounds
  and recorded the evidence in Decisions.
- 2026-07-29: [DONE] Established that the four repeated 2026-07-24 Insights come
  from three different publishers plus one artifact-free Development, so exact
  grouping cannot merge them. Added a Future work entry to the How page
  describing the limitation and the end-of-day fix. Built, served, and verified.
- 2026-07-29: [IN-PROGRESS] Created this tracker. No prompt, ranking, or agent
  code has been changed by this project yet.
