# Event-to-Company Mapping

Last reviewed: 2026-07-28

This document owns the next Investment boundary: turning one ranked Event into
zero or more defensible public-company implications. The canonical reusable
company facts remain in
`.agents/skills/fli-daily-intelligence/references/bit-investment-context.json`.
The Event remains the evidence; a company profile is only prior context.

## Plain-language model

- **Ticker** identifies the public company, such as `MSFT` for Microsoft.
- **Thesis** is the causal belief about why the investment should work. Use a
  BIT thesis only when the packet contains an attributable public BIT source.
- **Implication** states what the Event may change for that company and why an
  analyst should care.
- **Thesis effect** says whether the new evidence supports, challenges, mixes,
  or does not clearly change that thesis. Use `no_public_thesis` when the packet
  contains no attributable public BIT view.

The system should not ask “is this an AI company?” It should ask “does this
specific Event reach a material operating driver for this company through a
credible causal chain?”

## Minimal reusable company packet

The agent needs only:

1. **Identity:** canonical name, ticker, aliases, and listing status.
2. **Business model:** what the company sells and how it makes money.
3. **Operating drivers:** the variables that can change revenue, pricing,
   volume, mix, cost, capital intensity, or risk.
4. **Transmission hypotheses:** plausible routes from frontier AI to those
   drivers, expressed as upside, downside, and watchpoints.
5. **Public BIT view:** thesis, edge, signals, countercase, source scope, and
   evidence grade when publicly attributable.
6. **Research limits and sources:** cautions, dates, and provenance.
7. **Portfolio context:** the newest disclosed weight plus its exact date and
   basis. Weight may order comparable findings; it cannot create relevance.

The current 37 profiles remain the complete candidate index. Richer
source-bearing memos can now replace the older hypothesis view one company at a
time without removing unresearched companies from consideration.

## One-company research pilot

[`scripts/company-memo-pilot.py`](../../scripts/company-memo-pilot.py) is the
durable experiment for testing whether a richer web-grounded company memo
improves this packet. It is deliberately not an `fli` command yet.

Run one company:

```bash
.venv/bin/python scripts/company-memo-pilot.py --ticker IREN
```

For a cheap end-to-end transport and schema canary before a batch:

```bash
.venv/bin/python scripts/company-memo-pilot.py \
  --ticker IREN \
  --model gpt-5.6-luna \
  --reasoning-effort low
```

The script:

1. reads the existing canonical profile as prior context;
2. starts one `gpt-5.6-sol` / `xhigh` LiteLLM Responses background request;
3. uses hosted web search, required primary-source guidance, prompt caching,
   and a strict structured-output schema;
4. polls the latest returned response ID until it reaches a terminal state;
5. validates that every claim URL is HTTPS and present in the source ledger;
6. writes the memo, usage, request identity, web actions, and provenance to
   `tmp/company-memo-pilot-<TICKER>-<MODEL>-<EFFORT>.json`.

The model, reasoning effort, and polling interval are explicit CLI controls.
The defaults are `gpt-5.6-sol`, `xhigh`, and 30 seconds. A Luna/low run proves
transport, search, schema, validation, and persistence; it does not establish
the quality bar for the final company packet. Do not start a full Sol/xhigh
batch until at least one low-cost canary and the two-company quality/cache
audit have passed.

The pilot never mutates the canonical Investment packet. After a human audits a
result for causal usefulness, primary-source coverage, BIT-attribution
discipline, duplication, and excess structure, promote it into the durable UI
projection:

```bash
.venv/bin/python scripts/promote-company-memo.py \
  tmp/company-memo-pilot-IREN-gpt-5-6-luna-low.json
```

Promoted results live in `docs/references/company-memos/`. The BIT Lens API
joins them by ticker into `investment-company-universe-v5`. The expanded UI
shows the new memo structure and its source ledger; a company without a
promoted memo is labeled `Memo pending` and never presents the legacy
hypothesis profile as if it were the final research packet.

The two-company Luna/low canary completed for IREN and Microsoft on 28 July
2026. Both results passed transport, schema, URL-ledger validation, and a
primary-source spot check. Their shared prompt cache did not hit
(`cached_tokens = 0` for both), so caching remains a cost issue rather than a
quality proof. The promoted memos are suitable for UI and downstream contract
design, but the remaining universe has not yet been batch-generated.

## Two-stage retrieval

1. Give the model the Event and the compact index of all 37 companies.
2. Ask for a small shortlist, including an empty shortlist.
3. Retrieve complete profiles only for shortlisted companies.
4. Judge each Event–company pair against the full profile.
5. Publish direct connections and well-evidenced material indirect
   connections. Suppress `none` and weak indirect matches while retaining their
   audit disposition.

This keeps every company eligible without placing all 37 full profiles in every
prompt. Stable instructions and the compact index should precede the Event so
the shared prefix can benefit from prompt caching.

## Minimal judgment

Each reviewed pair should produce this structured shape:

```json
{
  "company": "Microsoft",
  "ticker": "MSFT",
  "connection_type": "direct",
  "mechanism": "The Event changes a named operating driver through one explicit causal chain.",
  "affected_drivers": ["Azure AI consumption"],
  "thesis_effect": "supports",
  "implication": "What changes for the analyst if the mechanism is true.",
  "watchpoints": ["The next observable confirmation or challenge"],
  "evidence_ids": ["event-or-source-id"],
  "disposition": "publish"
}
```

Allowed values:

- `connection_type`: `direct`, `indirect`, or `none`.
- `thesis_effect`: `supports`, `challenges`, `mixed`, `unclear`, or
  `no_public_thesis`.
- `disposition`: `publish` or `suppress`.

For an indirect connection, `mechanism` must name the intermediate step. For
`none`, the pair is suppressed and needs only a short audit reason. `unclear`
is not a safe harbor for a weak connection: the causal link must be established
before uncertainty about direction is useful.

## What the LLM decides

The LLM may shortlist companies, explain the mechanism, and classify the thesis
effect. Deterministic code should validate company/ticker identity, enum values,
evidence identifiers, and the publish/suppress rule. A later evaluation should
use labeled historical Events to measure false positives and missed material
connections before this becomes the production Investment selector.
