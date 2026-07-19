---
name: fli-daily-intelligence
description: Produces and persists one evidence-grounded Frontier Lab Intelligence daily brief by researching across positively routed Events, retrieving related packets, grouping supporting evidence, applying BIT Capital Investment or AI Engineering context, and validating complete cited outputs. Use when asked to generate, test, review, or improve a daily intelligence run for a specific date.
---

# FLI Daily Intelligence

Use the repository's deterministic workbench for evidence and persistence. Use
your own judgment for research, retrieval, grouping, and synthesis.

## Required workflow

1. Confirm the requested ISO date and work from the repository root.
2. Read both audience contexts before inspecting candidates:

   ```bash
   .venv/bin/fli daily-intelligence context --audience investment --compact --json --no-input
   .venv/bin/fli daily-intelligence context --audience ai_engineering --json --no-input
   ```

   The Investment context is the structured
   [BIT investment packet](references/bit-investment-context.json). It is the
   authoritative skill reference for the fund's public thesis, complete audited
   portfolio baseline, reusable company profiles, and the boundary for companies
   outside that portfolio. Each company profile separates BIT's attributable
   public view from FLI analyst context; never present the latter as BIT's thesis.
   `source_scope` distinguishes firm-wide research, this flagship strategy,
   another BIT product, or mixed commentary.

3. Freeze or reuse the day's union-positive workspace:

   ```bash
   .venv/bin/fli daily-intelligence prepare --day YYYY-MM-DD --json --no-input
   ```

   Use the returned `workspace` path for every later command. Read its
   `manifest.json` and `draft.template.json`. Only the current workspace v3
   contract is supported; never reuse or adapt an older packet after a schema
   migration. Run `prepare` again from the same frozen routing lineage instead.
   Workspace v3 retains only
   first-party X sources published from the brief day through seven days
   earlier. Raw Feed evidence is not deleted. If an old root has a current
   same-author quote or reply, that current post becomes the packet root; if no
   current first-party X source remains, the Event is absent from the workspace.
   Artifacts are not automatically pruned with X sources. Their exact stored
   `disclosures` remain inspectable even when a disclosure post is not part of
   the compact semantic packet. Before citing one, check that its disclosure
   timing is appropriate for the brief and that its content supports the claim.
   A pruned packet deliberately withholds inherited routing prose and prior
   per-Event annotations; judge it from the retained evidence.
4. Investigate across the whole cohort. Start with deterministic retrieval,
   then broaden only where it improves the judgment:
   - for an Investment candidate, fetch every matching profile before web
     research and use its identity, operating drivers, AI exposure channels,
     and watchpoints as a starting lens rather than a daily conclusion:

     ```bash
     .venv/bin/fli daily-intelligence company-context \
       --company "NAME, TICKER, OR ALIAS" --json --no-input
     ```
   - inspect `exact_artifact_groups` in the manifest;
   - use `search` for entities, products, concepts, and repeated claims;
   - use `inspect-event` before relying on a candidate;
   - use `index`, then `similar`, only when lexical and artifact retrieval may
     miss materially different wording; a normal one-day run does not require it;
   - perform broader web research when packets do not establish the relevant
     company, technical, competitive, or portfolio transmission path.
5. Write `draft.json` beside the template. Use
   [references/editorial-standard.md](references/editorial-standard.md) for the
   reasoning and field contract. Default distinct developments to separate
   Insights or `not_selected`. Multiple Events may support one Insight only
   when they support the same audience conclusion, causal mechanism, and
   decision; do not create a separate development object.
6. Before expanding the analysis, run one distinct causal-coherence and source-
   pruning review over every selected Insight. State its core claim privately
   in one sentence, then test every attached Event and citation: what exact
   clause does it support or challenge, is any comparison genuinely like-for-
   like, and would removing it materially weaken the conclusion or its
   uncertainty? Remove, separate, or mark `not_selected` any source that shares
   only a topic, trend, entity, or vocabulary. Complete cohort coverage never
   requires attaching an Event to a selected Insight.
7. Before validation, run one distinct missing-implication review over every
   selected Insight. Ask: **What important consequence does this evidence
   support that the draft has not carried through?** Follow the evidence one
   additional causal step and revise only when the consequence is material and
   supported. This review may deepen the existing causal chain; it must not
   broaden the Insight into a second development or unrelated mechanism. When
   the same development appears for both audiences, compare the two
   interpretations so a relevant technical constraint can inform the
   Investment consequence, or a business constraint can inform the Engineering
   decision, without merging the audience outputs. If the missing bridge can be
   resolved with bounded web research, resolve it; otherwise preserve it as an
   uncertainty or watchpoint rather than speculation. This is a reasoning
   review, not a reason to build or run an embedding index when the evidence is
   already present.
8. After the reasoning is complete, run one mandatory reader-facing writing
   pass over every selected Insight. Load and apply the shared
   [Adi writing skill](../adi-writing/SKILL.md), including its voice standard,
   and follow the institutional adaptation in
   [the editorial standard](references/editorial-standard.md#reader-facing-writing).
   Apply it to every field the reader sees, not only the title. Preserve the
   facts, causal chain, technical precision, and honest uncertainty; simplify
   the language and sentence structure, not the judgment.
9. Validate repeatedly until the complete cohort passes:

   ```bash
   .venv/bin/fli daily-intelligence validate \
     --workspace <workspace> --draft <workspace>/draft.json --json --no-input
   ```

10. For a requested daily brief, import the validated result atomically and
   inspect the durable run:

   ```bash
   .venv/bin/fli daily-intelligence import-result \
     --workspace <workspace> --draft <workspace>/draft.json --json --no-input
   .venv/bin/fli daily-intelligence inspect-run --run-id <returned-run-id> --json --no-input
   ```

   Review-only and client-evaluation tasks may stop after validation or use
   `import-result --dry-run`. Never edit the SQLite store directly. Once a
   complete run is imported, the Insights backend and UI select it
   automatically for that date and audience.

## Parallel historical dates

Do not start several full `daily-intelligence run-day` Evidence stages in
parallel. Feed and Event publication is one global deterministic snapshot, so
competing publishers can invalidate one another even though later workspaces
are independent.

For a historical batch:

1. Publish Evidence once through the latest requested date with a retained
   window that covers the earliest requested date.
2. Run one `fli audience-routing refresh --through MAX --days N` command. Use
   `--day-workers` for bounded per-day parallelism and do not use `--replace`.
   The refresh reuses complete predecessor judgments only for exact matching
   Event/evidence/model-input hashes under the same model contract, even when
   the global publication ID changed.
3. Prepare one immutable workspace per date. These local preparations may run
   independently once the routing batch is complete.
4. Launch one Codex task per exact workspace and let authoring, validation, and
   import proceed in parallel. Never let a task inspect another date's draft or
   workspace.

This is a fan-out after one shared deterministic freeze, not several competing
end-to-end publishers. A new or changed Event is evaluated; unchanged routed
evidence is reused with explicit provenance.

Do not schedule, publish, submit, or take another external action unless the
user explicitly requests that action in the current session.

## Retrieval commands

```bash
.venv/bin/fli daily-intelligence company-context \
  --company "Microsoft" --json --no-input

.venv/bin/fli daily-intelligence search \
  --workspace <workspace> --query "Inkling" --limit 20 --json --no-input

.venv/bin/fli daily-intelligence inspect-event \
  --workspace <workspace> --event-id <event-id> --json --no-input

.venv/bin/fli daily-intelligence index \
  --workspace <workspace> --progress plain --json --no-input

.venv/bin/fli daily-intelligence similar \
  --workspace <workspace> --event-id <event-id> \
  --limit 15 --min-score 0.7 --json --no-input
```

The embedding index is a cached retrieval sidecar keyed by Event ID, rendered
packet hash, embedding contract, and model. A cosine neighbor is only a
candidate. Never treat a threshold, connected component, shared vocabulary, or
shared theme as an automatic merge.

## Editorial invariants

- Keep every decision-useful Insight supported by the day, while preferring
  precision over padding. Selecting the best three to five for a submission is
  a separate later step, not a persistence limit.
- Rank only the selected Insights. Rank is the audience's daily decision
  priority, not Feed rank, popularity, confidence, or embedding similarity.
  Give each selected Insight one concise `rank_rationale` that explains its
  position relative to the rest of that audience's complete daily brief.
- The title states a judgment. `what_changed` states the attributable facts.
- Connect every Insight to one or more exact Events and at least one citation.
- Assign each routed Event once per relevant audience: to one Insight or to
  `not_selected` with a concrete reason.
- Treat `not_selected` as a successful editorial disposition. Never attach an
  Event merely because it is interesting, adjacent, or needed for cohort
  accounting.
- Prefer primary artifacts and first-party sources. Preserve provider
  attribution and important contradictory evidence.
- Never cite an artifact merely because it is attached to an Event. Read the
  frozen artifact text, identify the exact claim it establishes, and include a
  short verbatim `excerpt` plus a claim-specific `supports` explanation. If no
  passage directly supports the Insight, omit that artifact citation. The
  validator rejects missing excerpts and excerpts absent from frozen text.
- Treat artifact disclosure timing as an editorial audit, not an automatic
  code gate. Do not use a disclosure later than the brief day as if it were
  available then; retain the later source only as auditable packet context.
- Treat each retained X source's `posted` date as application-owned truth.
  Never assign the brief day to an older source or cite a pruned URL. Event
  citation dates are filled from the frozen workspace and conflicting dates
  fail validation.
- Use web research actively when it can resolve an unknown. A web citation must
  retain its URL, retrieval time, supporting excerpt, and the claim it supports.
- Never invent a BIT holding, private forecast, cost basis, trade, target, or
  consensus view. For this version, treat the packet's audited portfolio as the
  working portfolio context and keep its date and source in the packet rather
  than repeating them in every reader-facing company row.
- The audited portfolio report is page-level context, not a default Insight
  citation. Do not attach it to an individual Insight merely to establish that
  a named company belongs to the working portfolio. Cite it inside an Insight
  only when a report passage directly supports a development-specific claim.
- Treat a company profile as reusable background, not evidence that today's
  development has an effect. Attribute a view to BIT only when
  `bit_public_view.grade` is `explicit_thesis` or `commentary` and cite its BIT
  source. Respect `source_scope`: commentary from another BIT product is not the
  flagship fund's thesis. When the grade is `none`, use the analyst context only
  to guide diligence and derive direction from development-specific evidence.
- For Investment, classify every named company as `portfolio` or
  `outside_portfolio`. Consider the portfolio first. Include an outside company
  only when a direct public-equity transmission path is defensible; omit that
  section rather than padding it.
- For Investment, write one coherent `interpretation` that makes the
  operating-to-financial-to-thesis chain explicit or states that the link is
  unknown. Keep the strongest challenge in `key_uncertainty` and use one to
  three measurable `watchpoints`; do not split the same argument across
  parallel mechanics fields.
- For Investment, use `impact` as the potential development-specific company
  direction, not as proof of a realized financial result or a stock call. Use
  `positive` or `negative` only when one material operating or thesis direction
  is better supported than its opposite; keep realization and magnitude in the
  key uncertainty and watchpoints. Use `mixed` only when the current development
  supports material benefit and harm. Use `uncertain` only when no defensible
  net direction exists because opposite branches remain comparably plausible or
  an unresolved variable determines the sign. Generic exposure, company-profile
  context, rival financing, or risk disclosures do not establish direction.
  Omit mappings without a direct material transmission path; `uncertain` is not
  a safe harbor for weak mappings. Never optimize toward a target distribution.
- For Investment, keep internal research-method controls under AI Engineering
  or `not_selected` unless they produce a defensible fund-thesis, company, or
  portfolio consequence. A shared model, company, or market theme is not such
  a consequence by itself.
- For Engineering, put the concrete bounded action in `next_step` and combine
  its measurable proceed and stop conditions into one concise `decision_rule`.
  Keep affected surfaces, implications, hypotheses, and material constraints
  in the interpretation rather than duplicating them as parallel fields.
- For Engineering, derive numerical gates from an existing baseline or label
  them explicitly as provisional criteria to calibrate in the proposed test.
  Do not present agent-chosen percentages or sample counts as validated
  thresholds. When several controls change at once, stage or ablate them so the
  result can identify which intervention helped; otherwise state that causal
  attribution will remain unresolved.
- Existing per-Event Insights are working annotations, not editorial truth.
  Re-evaluate them against the complete day.

Use [references/evaluation-cases.md](references/evaluation-cases.md) when
forward-testing changes to this skill or its client.
