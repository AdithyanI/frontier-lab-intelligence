# Signal-to-noise ratio

## Goal

Raise the evidence bar of published Investment Insights so that a surfaced item
always rests on evidence strong enough to act on, measured by eliminating the
29% of surfaced Insights whose own `what_changed` text disqualifies them.

## Why / Impact

Signal-vs-noise carries 20% of the case-study rubric and is the single question
the prompt names as most important: *"did this surface something we'd genuinely
want to know, and did it keep the noise out?"*

The system currently surfaces items it has itself judged to be unsupported. The
clearest example is rank 1 on 2026-07-26 — the latest published day, which is
what the product opens on, so it is the first Insight a BIT reviewer sees:

> Headline: "ChatGPT's travel workflow raises the bar for Google Search"
> `what_changed`: "... This is a first-party anecdote, not a measured
> evaluation, and it does not establish repeatability, adoption, or completed
> reservations."

The model wrote the disqualifier and surfaced anyway. If done wrong, the fix
suppresses genuinely useful early signals and the brief becomes empty; the
existing suppression rate is already 35%, so the bar must rise for unevidenced
claims only, not for early or unquantified ones.

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

- [ ] A surfaced Investment Insight never contains a sentence in `what_changed`
      that disqualifies its own evidence.
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
| todo | M1 — apply the two Investment prompt edits and bump both version constants in lockstep | worker | |
| todo | M2 — flip the known-bad item to `suppress` on a scratch DB and read the trace | worker | |
| todo | M3 — confirm the known-good control still surfaces | worker | |

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

- 2026-07-29: [DONE] Measured the leak against live data. 142 of 220 Investment
  candidates surfaced across 22 days (65%). 42 of 142 surfaced Insights (29%)
  contain a self-flagged evidence weakness in `what_changed` — 19 name a
  first-party claim, 10 note the absence of independent confirmation, 7 note
  missing benchmarks or undisclosed data, 5 note the absence of measurement,
  4 call the evidence an anecdote. Of 306 company connections, exactly 1 has
  `threshold_met: true`.
- 2026-07-29: [DONE] Identified the worst instance. Development
  `b72d460234bd…` is rank 1 on 2026-07-26, the latest published day and the
  product's default view, and its own `what_changed` calls it "a first-party
  anecdote, not a measured evaluation".
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
