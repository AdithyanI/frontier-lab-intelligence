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
   .venv/bin/fli daily-intelligence context --audience investment --json --no-input
   .venv/bin/fli daily-intelligence context --audience ai_engineering --json --no-input
   ```

   The Investment context is the structured
   [BIT investment packet](references/bit-investment-context.json). It is the
   authoritative skill reference for the fund's public thesis, complete audited
   portfolio baseline, and the boundary for companies outside that portfolio.

3. Freeze or reuse the day's union-positive workspace:

   ```bash
   .venv/bin/fli daily-intelligence prepare --day YYYY-MM-DD --json --no-input
   ```

   Use the returned `workspace` path for every later command. Read its
   `manifest.json` and `draft.template.json`. Workspace v2 retains only
   first-party X sources published from the brief day through seven days
   earlier. Raw Feed evidence is not deleted. If an old root has a current
   same-author quote or reply, that current post becomes the packet root; if no
   current first-party X source remains, the Event is absent from the workspace.
   A pruned packet deliberately withholds inherited routing prose and prior
   per-Event annotations; judge it from the retained evidence.
4. Investigate across the whole cohort. Start with deterministic retrieval,
   then broaden only where it improves the judgment:
   - inspect `exact_artifact_groups` in the manifest;
   - use `search` for entities, products, concepts, and repeated claims;
   - use `inspect-event` before relying on a candidate;
   - use `index`, then `similar`, only when lexical and artifact retrieval may
     miss materially different wording; a normal one-day run does not require it;
   - perform broader web research when packets do not establish the relevant
     company, technical, competitive, or portfolio transmission path.
5. Write `draft.json` beside the template. Use
   [references/editorial-standard.md](references/editorial-standard.md) for the
   reasoning and field contract. Multiple Events may support one Insight; do
   not create a separate development object.
6. Validate repeatedly until the complete cohort passes:

   ```bash
   .venv/bin/fli daily-intelligence validate \
     --workspace <workspace> --draft <workspace>/draft.json --json --no-input
   ```

7. For a requested daily brief, import the validated result atomically and
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

Do not schedule, publish, submit, or take another external action unless the
user explicitly requests that action in the current session.

## Retrieval commands

```bash
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
- Prefer primary artifacts and first-party sources. Preserve provider
  attribution and important contradictory evidence.
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
- For Investment, classify every named company as `portfolio` or
  `outside_portfolio`. Consider the portfolio first. Include an outside company
  only when a direct public-equity transmission path is defensible; omit that
  section rather than padding it.
- For Investment, write one coherent `interpretation` that makes the
  operating-to-financial-to-thesis chain explicit or states that the link is
  unknown. Keep the strongest challenge in `key_uncertainty` and use one to
  three measurable `watchpoints`; do not split the same argument across
  parallel mechanics fields.
- For Engineering, put the concrete bounded action in `next_step` and combine
  its measurable proceed and stop conditions into one concise `decision_rule`.
  Keep affected surfaces, implications, hypotheses, and material constraints
  in the interpretation rather than duplicating them as parallel fields.
- Existing per-Event Insights are working annotations, not editorial truth.
  Re-evaluate them against the complete day.

Use [references/evaluation-cases.md](references/evaluation-cases.md) when
forward-testing changes to this skill or its client.
