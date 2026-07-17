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

3. Freeze or reuse the day's union-positive workspace:

   ```bash
   .venv/bin/fli daily-intelligence prepare --day YYYY-MM-DD --json --no-input
   ```

   Use the returned `workspace` path for every later command. Read its
   `manifest.json` and `draft.template.json`.
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
- The title states a judgment. `what_changed` states the attributable facts.
- Connect every Insight to one or more exact Events and at least one citation.
- Assign each routed Event once per relevant audience: to one Insight or to
  `not_selected` with a concrete reason.
- Prefer primary artifacts and first-party sources. Preserve provider
  attribution and important contradictory evidence.
- Use web research actively when it can resolve an unknown. A web citation must
  retain its URL, retrieval time, supporting excerpt, and the claim it supports.
- Never invent a BIT holding, current weight, private forecast, cost basis,
  trade, target, or consensus view.
- For Investment, make the operating-to-financial-to-thesis chain explicit or
  state that the link is unknown.
- For Engineering, propose a bounded experiment with both a success metric and
  a stop condition.
- Existing per-Event Insights are working annotations, not editorial truth.
  Re-evaluate them against the complete day.

Use [references/evaluation-cases.md](references/evaluation-cases.md) when
forward-testing changes to this skill or its client.
