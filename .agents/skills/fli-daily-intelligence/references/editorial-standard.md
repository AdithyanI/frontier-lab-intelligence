# Editorial Standard

## Contents

- Reader-facing shape
- Evidence roles
- Investment analysis
- AI Engineering analysis
- Citation and coverage rules

## Reader-facing shape

An Insight is a compact decision memo built directly from one or more Events.
It contains:

- `title`: the judgment, not merely the release name;
- `what_changed`: concise factual synthesis with exact attribution;
- `interpretation`: the audience-specific conclusion;
- `impact_chain`: two to five causal steps from evidence to decision;
- `evidence_limitations`: important missing information, counterevidence, or
  transfer limits;
- `next_step`: one concrete diligence or engineering action;
- audience-specific `analysis`;
- `event_links`; and
- `citation_ids`.

Use `.venv/bin/fli daily-intelligence contract --json --no-input` as the authoritative
field and enum contract. Start from the workspace's `draft.template.json`.

## Evidence roles

- `primary`: the most authoritative or direct evidence establishing the claim.
- `supporting`: an additional release, implementation, benchmark, distribution,
  or independent report that strengthens the Insight.
- `context`: relevant background that helps interpretation but does not
  establish the central factual claim.
- `counterevidence`: evidence that qualifies or challenges the interpretation.

Several posts repeating one announcement can support one Insight. Several
distinct but related developments can also support one broader Insight when the
causal synthesis is defensible. Explain the role in each link rather than
asserting that similarity proves sameness.

## Investment analysis

Use the BIT context returned by `context --audience investment`. Select the
most honest `portfolio_relationship`:

- `current_disclosed_holding`
- `historical_holding`
- `portfolio_thesis`
- `candidate_or_watchlist`
- `sector_readthrough`
- `none`

When naming an affected entity, record its relationship and the date of the
public holding evidence when applicable. Then provide:

- `thesis_effect`;
- `operating_driver`;
- `financial_driver`;
- `edge`;
- `counter_case`; and
- measurable `watchpoints`.

The desired chain is:

```text
public evidence
→ operating or competitive driver
→ company or portfolio exposure
→ revenue / margin / capex / share / valuation consequence
→ thesis effect and falsifiable watchpoint
```

If a step is not supported, say so. Do not fill a structural field with
speculation merely to make the memo look complete.

## AI Engineering analysis

Identify the affected `system_surface` and the `technical_implication`. Choose
`test`, `adopt`, `watch`, or `ignore`. The experiment must contain:

- one falsifiable hypothesis;
- the smallest reproducible test;
- a success metric that justifies proceeding; and
- a stop condition that rejects or constrains the idea.

Record workload, hardware, quantization, context, benchmark, or security limits
when they affect transferability. A provider microbenchmark is not evidence of
end-to-end production improvement.

## Citation and coverage rules

`event` and `artifact` citations must point to frozen URLs from the workspace.
Use `web` for newly researched sources and include `retrieved_at` and a concise
supporting excerpt. Use `context` for the encoded BIT or Engineering context
and retain the underlying public URL when making a factual portfolio claim.

Every positively routed Event/audience pair must be accounted for exactly once.
This is an audit requirement, not a request to publish weak items. Put weak,
duplicative, stale, or non-actionable candidates in `not_selected` with a
specific reason.
