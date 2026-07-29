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

- [ ] M1 — Rotate the evidence axis. Five edits, two files, no version bump
      yet. Acceptance: the five edits in *The five edits* below are applied
      verbatim and `./scripts/check-fast.sh` prints OK. Do **not** bump
      `PROMPT_VERSION` during M1; testing runs against a scratch DB, and the
      version bump is a publication decision that belongs to M6.
- [ ] M2 — Four pre-registered single-item tests, about $0.88 total, all to a
      scratch DB so nothing published changes. Every expected outcome is
      written down *before* running. Acceptance: all four match.

      | Day | Rank | Item | Now | Expected |
      | --- | ---: | --- | --- | --- |
      | 2026-07-23 | 5 | Etched $300M at $10.3B, inference ASICs | suppress | **surface** — false negative fixed |
      | 2026-07-26 | 1 | ChatGPT travel workflow anecdote | surface | **suppress** — false positive fixed |
      | 2026-07-20 | 2 | OpenAI paused deployment, `MSFT-B5` | surface, `threshold_met: true` | **unchanged** — control |
      | 2026-07-17 | 20 | Reported Huawei SuperPoD, `NVDA-B4` | surface | **unchanged** — the evidence twin of Etched, must not move |

      If either control moves, the edit is wrong. Stop and re-diagnose rather
      than adjusting the expectations.
- [ ] M3 — Schema reorder tested separately from the prompt edits. Acceptance:
      run the same four items with only the `decision`-first schema change and
      no prompt change, so the two effects are not confounded. Records whether
      field ordering matters for a reasoning model at all. About $0.88.
- [ ] M4 — Two-day false-negative measurement. Acceptance: 2026-07-24 and
      2026-07-26 re-run to a scratch DB; every changed decision is read by a
      human and classified as correct or a false negative. Validate: diff
      decisions against the published corpus. Cost about $4.50.
- [ ] M5 — Narrow Investment-only router rule, only if M2-M4 pass. Acceptance:
      the rule sits inside `## The Investment routing boundary` and the
      Engineering judgment is provably unchanged on a sample. Validate:
      `fli audience-routing run --dry-run` then a bounded scratch run.
- [ ] M6 — Publication decision, all-or-nothing. Acceptance: an explicit go or
      no-go on bumping both version constants and re-running all 22 days at
      about $49, with the risk recorded here. There is no partial option: see
      the version-pin trap in Validation.

## The five edits

Written out in full so the work can be handed to an engineer without
re-deriving anything. Two files. Edits 1-4 are the axis rotation; edit 5 is the
independent schema change tested separately in M3.

**Edit 1 — carve-out, inserted immediately after the opening line of
`# Suppression and rejection`** (about line 409 of
`src/fli/insights/prompts/investment_company_analysis.txt`). Placed inside the
suppression block on purpose, following the escape-hatch pattern in the GPT-5
prompting guide, so it is read at the point where the conflicting rule lives.

```text
Suppression tests whether the Development establishes a real, attributable fact
that reaches a company. It never tests whether the consequence can be sized
today. If you can name the business variable that may move, publish and set
`threshold_met` to false, even when scale, price, timing, counterparty, or
supplier are undisclosed. Inability to quantify is not grounds for suppression.
That is exactly what `threshold_met: false` records.
```

**Edit 2 — split naming from sizing in the bullet that killed Etched.**

Replace:

```text
- no named operating driver can be stated;
```

with:

```text
- no operating driver can be named at all, as distinct from a driver you can
  name but cannot yet size, source, price, or date;
```

**Edit 3 — add the missing early-evidence class** to the list of "early but
potentially useful evidence" at about line 305.

```text
- a named, dated corporate action by an organization whose product, capacity,
  or capital position is the direct subject of a standing bet — financing, a
  capacity limit, a supply agreement, deal talks, or an acquisition — even when
  the terms are undisclosed;
```

**Edit 4 — add the tightening bullet to `# Suppression and rejection`.** This is
the noise half, so the change is not a one-way loosening.

```text
- the only new evidence is the author demonstrating their own product working
  well, with no measurement, no independent account, and no retrievable
  artifact.
```

**Edit 5 — schema field order** in `src/fli/insights/investment_agent.py` at
about line 276. Move `decision` to first position in both `properties` and
`required`, ahead of `headline`. Tested on its own in M3.

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

- **The bar is on the wrong axis. Rotate it, do not just tighten it.** This is
  the organizing idea for the whole project and supersedes the earlier framing
  of "two prompt edits that tighten the bar". The prompt currently filters on
  *how quantified the read-through is*. It should filter on *whether the
  underlying fact is real and attributable*. Evidence: the rejection text for
  Etched (2026-07-23 r5) reads "no ... **measurable** operating driver", but the
  prompt's own criterion 3 at line 272 says only "You can **name** the business
  variable that may move". The word "measurable" appears nowhere in that
  criterion. The model silently upgraded *name* to *measure*, which is precisely
  the judgment that `threshold_met: false` exists to absorb. Rotating the axis
  fixes both defect classes with one coherent change: the unmeasured
  self-demonstrations fail because the fact is not real or attributable, and
  Etched, Kimi capacity, and Meta/Anthropic pass because the fact is real even
  though the consequence cannot be sized. Two patches would have been a weaker
  story than one rotation.

- **The defect is a prompt contradiction, and OpenAI documents this exact
  failure mode.** The GPT-5 prompting guide, section *Instruction following*,
  states that contradictory or vague instructions are more damaging to GPT-5
  than to earlier models because the model "expends reasoning tokens searching
  for a way to reconcile the contradictions rather than picking one instruction
  at random". Our contradiction: line 294 grants permission — "The Development
  does not need to satisfy a bet's `threshold` today ... Early evidence can be
  published" — while line 407 issues an imperative — "Suppress the whole
  Development when ... no named operating driver can be stated". Permissive
  language loses to imperative language, and the later block wins. The guide's
  own remedy is to resolve the contradiction *and* add an explicit carve-out
  clause at the site of the conflicting rule (their example: "Do not do lookup
  in the emergency case, proceed immediately to providing 911 guidance"). The
  guide calls this an escape hatch. That is why edit 1 below sits inside the
  suppression list rather than in the preamble — an earlier draft of this plan
  put it in the preamble, which would have reproduced the original ordering
  problem.

  Weak corroboration, offered as consistent-with rather than proof: suppressions
  average 766 reasoning tokens (median 508), but the Kimi capacity item burned
  **2,958**, the fourth-highest of all 78 suppressions, before killing it. A
  hard case could also explain that.

- **Rejected the three-tool redesign; reordered the output schema instead.**
  Adi proposed replacing the single structured output with tools — `suppress`,
  `write_insight`, `get_company_memo` — so the agent picks a door and exits.
  The instinct identified a real flaw. The strict JSON schema currently orders
  its properties `headline`, `what_changed`, `decision`, `connections`,
  `no_match_reason`, and structured-output generation follows schema order, so
  the model writes a 6-14 word headline and the full narrative *before* emitting
  the decision token. All 78 suppression headlines follow one verdict-shaped
  template ("X lacks a concrete public-company implication"), so the visible
  commitment does precede the decision field.

  Rejected the tools for three measured reasons:
  1. **Tools do not fix the diagnosed bug.** The model meets the identical
     contradictory criteria whether it walks through a door or fills a field.
     Changing the output channel does not change the decision rule.
  2. **The branch-consistency benefit already exists.**
     `investment_agent.py:563-572` already enforces surface implies non-empty
     connections and a null reason, and suppress implies no connections and a
     non-empty reason. Branch-specific tool schemas would buy nothing new.
  3. **No cost win.** All ~20k input tokens are in the first request, and
     suppression already exits at 1.05 turns for $0.125. No tool can exit
     earlier than immediately.

  The minimal change that captures the real flaw is moving `decision` to first
  position in the schema. One line, no architecture change, testable for $0.22.
  Caveat recorded against my own argument: for a reasoning model the decision is
  settled in the reasoning trace before any output token is emitted, so the
  ordering effect may be small. Test it, do not assume it. The tool design goes
  to Future work as considered-and-deferred, which is a stronger interview
  answer than having built it.

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

- **The two Investment prompt edits.** *[SUPERSEDED 2026-07-29 by "The bar is on
  the wrong axis" above and by `## The five edits`. Kept because the diagnosis
  below is still correct and is the reason the axis rotation includes a
  tightening bullet. The framing was wrong: this draft only tightened, which
  would have deepened the false-negative problem found later the same day.]*
  The existing nine suppression bullets all
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
| done | Finding 4 — false negatives; inconsistent bar inside `NVDA-B4` | parent | Progress Log |
| done | Finding 5 — suppressed material corporate events (Meta/Anthropic, Etched, Kimi capacity) | parent | Progress Log |
| done | Diagnose root cause and write the five edits | parent | The five edits |
| todo | M1 — apply the five edits, no version bump | worker | The five edits |
| todo | M2 — run the four pre-registered tests to a scratch DB (~$0.88) | worker | Milestones |
| todo | Continue auditing for further evidence-class defects | parent | |

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

- 2026-07-29: [DONE] **Root cause found, and it is a prompt contradiction
  rather than a missing rule.** Line 294 grants permission to publish early
  evidence with `threshold_met: false`; line 407 orders suppression when no
  named operating driver can be stated. Nothing states which governs, and the
  imperative later block wins. Confirmed against the OpenAI GPT-5 prompting
  guide via the developer-docs MCP, section *Instruction following*, which
  documents this exact failure mode and prescribes resolving the contradiction
  plus an explicit carve-out clause at the site of the conflicting rule. Also
  found the drift that killed Etched: the prompt asks the model to **name** an
  operating driver, and the model applied **measurable**. Full reasoning in
  Decisions; the resulting work is written out in `## The five edits`.
- 2026-07-29: [DONE] **Evaluated and rejected a three-tool redesign**
  (`suppress`, `write_insight`, `get_company_memo` with early exit). The
  instinct behind it was correct and found a real flaw — the strict schema
  emits `headline` and `what_changed` before `decision`, so the narrative
  precedes the verdict, and all 78 suppression headlines share one
  verdict-shaped template. But tools do not resolve a contradiction, the
  branch-consistency guarantee already exists at
  `investment_agent.py:563-572`, and there is no cost win because all input
  tokens are in the first request. Captured the real flaw as a one-line schema
  reorder instead, tested separately in M3 so the two effects are not
  confounded.
- 2026-07-29: [DONE] **Finding 4 — the suppression side has false negatives, and
  the bar is inconsistent within a single standing bet.** First audit of the 78
  suppressed Investment candidates. The aggregate direction is correct and
  should be said plainly in defence of the system: suppressed candidates are
  materially thinner than surfaced ones (42.9% zero-artifact vs 29.5%, mean
  0.82 artifacts vs 1.27). The gate is not random. The problem is at the item
  level. `NVDA-B4` reads "IF frontier labs and hyperscalers optimize models for
  TPUs, custom ASICs or competing GPUs ... THEN potential revenue-share loss
  ... especially if custom silicon captures high-volume inference." Against that
  one bet:
  - **Surfaced** 2026-07-17 r20, "Reported Huawei SuperPoD sharpens NVIDIA's
    competing-accelerator risk" — one Event, **zero artifacts**, and the
    headline calls it *reported*, so it is second-hand.
  - **Suppressed** 2026-07-23 r5, Etched raising **$300M at a $10.3B
    valuation** to accelerate production of its inference clusters, plus an
    80,000 sq ft, 10 MW production facility — one Event, zero artifacts,
    first-party, specific, quantified. Suppression reason: "names no
    public-company supplier, customer, component, or measurable operating
    driver."
  Identical evidence structure, same bet, opposite decision, and the better
  specified item is the one that was killed. Etched builds transformer
  inference ASICs, which is the literal subject of `NVDA-B4`; the bet also
  already fired on a *portable inference server* (07-08 r12). This is the
  sharpest defect found so far because the yardstick is the system's own
  pre-registered bet rather than my judgement.
- 2026-07-29: [DONE] **Finding 5 — three more suppressed items look like
  material corporate events a fund would want.** All one Event, zero artifacts:
  - 2026-07-18 r16 — NYT-sourced report that **Anthropic proposed a two-year
    compute-as-a-service deal to Meta**, with Meta considering it. `META` is a
    covered company and `META-B3` covers accelerator and custom-silicon cost.
    Suppressed for lacking "deal structure, scale, and commitment" — a standard
    under which no deal-talks story could ever surface, though funds trade on
    exactly these.
  - 2026-07-19 r2 — **Moonshot paused new Kimi K3 subscriptions** with GPUs near
    capacity for 48 hours. Suppressed because no supplier was named, yet a
    China-based lab hitting a compute ceiling speaks to `NVDA-B2` inference
    demand and `NVDA-B5` export controls, both of which have fired elsewhere.
  - 2026-07-24 r7 and 2026-07-21 r13 — Midjourney/Co-Star and World
    Labs/SceniX acquisitions. Weaker, listed for completeness.
  The common shape is that a **named, dated, first-party corporate action**
  (financing, deal talks, capacity limit, acquisition) is being suppressed for
  lacking a quantified operating driver, while unquantified *capability
  commentary* surfaces. The evidence bar appears to be applied to the
  read-through rather than to the underlying fact.
- 2026-07-29: [DONE] Read all 78 suppression reasons. Prose quality is
  consistent and legible throughout; `no_match_reason` is a genuine asset and
  no instance was empty, generic, or self-contradictory. The defect is
  calibration, not explanation.
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
