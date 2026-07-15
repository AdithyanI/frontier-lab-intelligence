# Audience Insights v2 Learnings

## Summary

- Long-running product/pipeline project separating two editorial audiences over
  one evidence and citation substrate.
- Append concrete tooling, prompt, evaluation, and execution lessons throughout
  the run so future work does not repeat v1's blended-contract mistake.

## What Helped

- Freezing one shared evidence/citation core before splitting audience prompts
  kept factual provenance identical while allowing genuinely different claims,
  analytical fields, and editorial choices.
- Application-owned exact quote binding removed a large class of persuasive but
  unverifiable model output before editorial review.
- Separating the pre-editor item filter, ID-only daily editor, day-set padding/
  duplicate review, and adjacent rank-blind publication audit exposed different
  failure modes without letting one model certify itself.
- Immutable failed/superseded runs made prompt and reviewer calibration
  inspectable. Corrected history could be rebuilt without pretending the first
  chronology never existed.
- A frozen lower-rank/X-Article/drop recall cohort turned rank-window arguments
  into exact per-day widening decisions. It found two real AI Engineering misses
  while rejecting a global widening rule.
- The explicit production reconciliation manifest replaced fragile
  newest-directory selection with one deterministic, adversarially testable
  publication object.
- `agent-browser` against the always-on local build caught diagram collisions
  and proved rendered structure, console state, and interaction instead of
  treating source inspection as UI validation.

## What Slowed Things Down

- Editorial history was initially inferred from the newest audited earlier-day
  directory. A later recall widening changed Jul 5, forcing a corrected suffix
  rebuild and making the need for an explicit history manifest obvious.
- The first production reconciler existed only after several runs had already
  accumulated. Earlier manifest-first execution would have made the exact
  required cells and contracts visible from the start.
- Provider schema/citation failures were sometimes discovered after expensive
  audience runs. Deterministic source-shape and quote-bind canaries should run
  before broad extraction.
- Investment's low yield prompted repeated editorial scrutiny before the corpus
  audit showed the core issue: social-first packets lacked filings, IR,
  contracts, earnings, pricing, adoption, and regulatory evidence.
- Mechanical audit dimensions were necessary but not sufficient for the
  senior-reader bar. The Muse Spark item passed its frozen checks yet a later
  qualitative audit found its analysis upgraded a partner testimonial into a
  stronger adoption/demand signal.
- Prompt-cache eligibility did not guarantee cache reads. The observed Luna
  runs often reported zero cached tokens, so repeated prefixes must be measured,
  not assumed to save time or cost.
- Parallel agents accelerated audits and frontend work, but shared-worktree
  edits and automated commits made ownership boundaries important. Small,
  non-overlapping file scopes worked; concurrent changes to one source surface
  required parent reinspection.

## Improvement Opportunities

### MCPs / Tools

- Keep browser captures under `tmp/` and make live URLs, viewport, interactions,
  accessibility checks, and console checks part of the browser QA command log.
- Add a single top-level status command for recall, production runs, adjacent
  audits/finalizations, and reconciliation readiness. Inspecting many SQLite
  stores manually is accurate but slow and easy to misread.
- Provider adapters should expose a cheap identity/schema canary and a dry-run
  evidence preview before consuming a bounded cohort.

### Skills

- The project skill's small `Current Batch`, progress checkpoints, and mandatory
  archive rule are valuable for an overnight run; update the tracker after each
  immutable data milestone rather than reconstructing state from chat.
- Use `agent-browser` throughout UI implementation, not only at final polish.
  Its first rendered pass should happen as soon as representative fixture data
  exists.
- Pair UI polish guidance with this repo's BIT-specific `DESIGN.md`; a generic
  personal-app theme would have changed the established product identity.

### AGENTS / Docs

- Keep `docs/STATUS.md` conceptual and put exact run IDs, adjudications, and
  production totals in this project's evaluation/tracker resources.
- Document the canonical manifest/report publication boundary in architecture
  and enforce it in fast checks whenever either file exists. Future agents
  should never restore recency-based production discovery for convenience.
- Make the audience-specific extraction efforts and prompt/schema versions
  application-owned defaults shared by runner and reconciler; duplicated CLI
  assumptions drift.

### Validation / Feedback Loops

- Use three gates: mechanical citation/schema validity, independent rubric
  audit, and senior-reader qualitative review. Passing the first two does not
  guarantee a portfolio manager or engineering lead would be glad to read it.
- Treat honest zero days as evaluated results. Never weaken the rubric or pad a
  day to make a UI count look healthy.
- When a lower-ranked item enters, rebuild that audience's later chronological
  history; duplicate and diversity decisions are history-dependent.
- Require the stored production report to equal a fresh canonical evaluation,
  and adversarially test source/audit/finalization replacement, path escape,
  contract/telemetry drift, and artifact snapshot drift.

### Delegation / Subagents

- Independent exact-item reviewers were most useful when they received opaque,
  immutable evidence and a binary `would_enter` question. Broad “review the
  pipeline” delegations produced less actionable output.
- Keep one parent responsible for history order, canonical manifest assembly,
  tracker state, and final product judgment. Delegate isolated qualitative
  audits, browser QA, adversarial reconciliation review, and harness checks.
- Require delegated reviewers to return exact candidate IDs, evidence paths,
  decision, and rationale so their result can become a hash-bound sidecar or a
  durable tracker decision.

## Recommended Follow-Ups

- Add an explicit, frozen prior-history manifest to run initialization so the
  runner fails before model calls if its chronological input is not exactly the
  intended audited predecessor chain.
- Add a bounded primary commercial-evidence lane for Investment, starting with
  the official TeraWulf/Anthropic filing recovery case; measure unique useful
  cited-insight yield before expanding sources broadly.
- Add a durable senior-editor veto/acceptance layer, or fold that exact bar into
  a versioned post-audit product review, so mechanically valid but weakly
  inferred items cannot survive only because the audience is sparse.
- Investigate why eligible Luna calls observed little or no prompt-cache reuse;
  keep cache telemetry visible rather than changing model quality to chase it.
- Resume briefing/export, local alert/outbox, reviewer landing, and submission
  packaging only after the reconciled in-app product is protected.

## Notes For Future Runs

- Start from a manifest template that lists every expected day/audience cell,
  exact contracts, artifact cohort, and history predecessor before the first
  paid call.
- Calibrate on preserved known days, freeze an untouched holdout, and give
  sparse audiences a named fail-closed outcome rather than relabeling a zero
  day or silently relaxing yield.
- Feed rank is a bounded candidate-recall input only. Never expose it to the
  extractor/editor or mistake it for editorial importance.
- Preserve full evidence verbatim. If context limits become real, use
  deterministic source-hashed sections/chunks; do not replace citeable evidence
  with an LLM summary.
- Cost is telemetry, not a quality gate. Record provider-reported cost and cache
  behavior per attempt, including failed/retried calls, before judging an
  optimization.
