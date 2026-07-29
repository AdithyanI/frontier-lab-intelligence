---
name: fli-daily-intelligence
description: Runs, inspects, and validates one day of Frontier Lab Intelligence company-aware Investment Insights. Use when asked to generate, re-run, audit, or debug the daily Investment brief for a specific date, or to inspect the BIT company packet the agent screens against.
---

# FLI Daily Intelligence

One path produces every Insight: the company-aware Investment agent in
`src/fli/insights/investment_agent.py`. There is no editorial lane, no Codex
App Server handoff, and no fallback renderer. If a day is not published, the
product says so rather than showing older content.

The model owns judgment. The repository owns evidence, schema, persistence, and
every URL the reader sees.

## What the agent does

For one day it selects the highest-ranked Developments with a positive
Investment route, and for each one:

1. Screens all 37 companies in the compact BIT universe from a single packet.
2. Calls `get_company_memo` only for companies it can already name a causal
   path to. The call requires the ticker plus the mechanism, the affected
   operating driver, and why the memo is needed — so the claim exists before
   the file opens. `ticker` is an enum over the covered holdings, so an
   out-of-portfolio name is schema-impossible.
3. Emits mechanism groups. Each group carries one causal path, the companies
   exposed through it, and per company: direction, affected operating driver,
   materiality, size basis, and impact.
4. Declares every opened-but-unused company in `rejected_after_memo` with a
   reason. Validation fails the run if a memo was opened and neither used nor
   rejected.

The loop ends when the model stops calling tools. Ceilings are
`MAX_UNIQUE_MEMOS = 8`, `MAX_MODEL_TURNS = 4`, `MAX_RESPONSE_ATTEMPTS = 3`;
none has ever bound in production.

## Required workflow

1. Confirm the requested ISO date and work from the repository root.
2. Read the live contract before assuming any field exists:

   ```bash
   .venv/bin/fli insights contract --json --no-input
   ```

   It reports the active prompt version, model identity, output schema, and
   loop ceilings from the running code, not from documentation.

3. Read the company packet the agent screens against:

   ```bash
   .venv/bin/fli insights company-universe --json --no-input
   .venv/bin/fli insights company-context --company NTSK --json --no-input
   ```

   The packet is the structured
   [BIT investment context](references/bit-investment-context.json) plus the
   37 web-grounded memos in `docs/references/company-memos/`. Each profile
   separates BIT's attributable public view from FLI analyst context; never
   present the latter as BIT's thesis. `source_scope` distinguishes firm-wide
   research, this flagship strategy, another BIT product, or mixed commentary.
   A company profile is prior context, never proof that an Event affects the
   company.

4. Preview the exact cohort without model calls or writes:

   ```bash
   .venv/bin/fli insights run-investment-agent \
     --through YYYY-MM-DD --days 1 --top-ranked 10 \
     --dry-run --json --no-input
   ```

   Inspect the selected Development IDs, daily ranks, prompt version, model,
   and request count before spending.

5. Run the day through the canonical machine client:

   ```bash
   .venv/bin/fli insights run-investment-agent \
     --through YYYY-MM-DD --days 1 --top-ranked 10 --workers 6 \
     --json --no-input
   ```

   It completes one warm request for the stable prompt prefix, runs the
   remaining ranks with bounded parallelism, writes the exact request and
   response for every turn under
   `data/derived/insights/investment-agent-traces/<day>/`, and imports each
   validated result.

6. Confirm the day actually published:

   ```bash
   .venv/bin/fli insights summary --json --no-input
   ```

   **Publication is all-or-nothing.** A day becomes visible only when every
   requested rank succeeds. One failed Insight leaves the whole day invisible
   even though its rows are stored. This is deliberate — it is what stops a
   partial re-run from mixing prompt versions on one page. If `published_days`
   omits the date, read the traces to find which rank failed. Retrying the
   batch runs its requested targets again; do not assume completed calls are
   automatically reused or free.

7. Verify the reader surface, not just the database:

   ```bash
   curl -s "http://127.0.0.1:8797/api/insights?audience=investment&status=kept&date=YYYY-MM-DD"
   ```

   The always-on app serves the built SPA at `http://127.0.0.1:8797`. It caches
   routing at process start; if a re-run changed routing, restart it.

## Quality bar

Enforced by `_validate_final`, so a violation fails the run:

- headline is at most 18 words and is a judgment, not a release name;
- every opened memo is either used or explicitly rejected;
- `splits` is consistent with the directions inside its mechanism group;
- `size_basis` states a magnitude when materiality is `material`;
- no model-authored URLs anywhere.

Requested by prompt but not machine-checkable — inspect these by reading:

- plain English, short sentences, no unexplained jargon;
- `impact` explains the company's position in the mechanism, and never refers
  to rank;
- `main_uncertainty` names what would falsify the read;
- `prior_assumption` names the belief this Development moves.

## Known limitations

Name these rather than hiding them:

- Each call sees one Development in isolation, so two Developments about the
  same underlying shift can produce near-duplicate Insights on one day. There
  is no cohort-level dedup pass.
- `materiality: unknown` is common and usually correct: only 11 of 37 memos
  carry a revenue base, so scale often cannot be stated honestly.
- AI Engineering has no run on this path yet. The endpoint returns an explicit
  reason instead of older content.

## Boundaries

- Route every model call through the shared LiteLLM endpoint. See
  `docs/references/model-routing.md`.
- Never commit `data/raw/`, `data/derived/`, or secrets.
- Do not send, publish, or share output without Adi's explicit approval in the
  current session.
