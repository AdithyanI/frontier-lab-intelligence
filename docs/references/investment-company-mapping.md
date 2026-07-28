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

The 37 profiles remain the complete candidate index. Every profile now has a
promoted source-bearing memo. The compact index is used for shortlisting; the
complete memo is retrieved only after an Event establishes a credible match.

## Company research runner

[`scripts/company-memo-pilot.py`](../../scripts/company-memo-pilot.py) is the
durable research runner for producing a richer web-grounded company memo. It
remains a focused script rather than an `fli` command until the downstream
Event-to-company contract is settled.

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
4. polls the original background-response creation ID until it reaches a
   terminal state;
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
  tmp/company-memo-pilot-IREN-gpt-5-6-sol-xhigh.json
```

Promoted results live in `docs/references/company-memos/`. The BIT Lens API
joins them by ticker into `investment-company-universe-v5`. The expanded UI
shows the memo, exact source ledger, research date, model, and provenance. The
read path retains an explicit `Memo pending` state so a missing file can never
silently fall back to the legacy hypothesis view.

The full 37-company universe was completed on 28 July 2026. A Luna/low canary
first proved transport, schema, URL-ledger validation, and persistence. The
quality run then produced 29 promoted Sol/xhigh memos and one Terra/xhigh memo.
Seven provider exceptions were completed from primary sources in the same
schema through manual Codex research. Across the finished set, every memo has
at least seven sources and the 37 ledgers contain 482 entries.

The IREN and Microsoft Sol/xhigh quality canaries both reported
`cached_tokens = 0`. Prompt caching therefore remains measured best-effort
transport telemetry, not a claimed property of this batch or a quality signal.

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
