# Editorial Standard

## Contents

- Reader-facing shape
- Evidence roles
- Grouping boundary
- Editorial rank
- Investment analysis
- AI Engineering analysis
- Citation and coverage rules

## Reader-facing shape

An Insight is a compact decision memo built directly from one or more Events.
It contains:

- `title`: the judgment, not merely the release name;
- `rank_rationale`: one concise explanation of why the Insight has this
  decision priority relative to the rest of the audience's daily brief;
- `what_changed`: concise factual synthesis with exact attribution;
- `interpretation`: one audience-specific argument connecting the evidence to
  the operating, financial, thesis, or engineering consequence;
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

## Grouping boundary

Group Events into one Insight only when they support one audience judgment,
one intelligible causal chain, and one decision or next action. Repeated posts
about the same primary artifact normally consolidate. Distinct developments may
support one broader conclusion, but `what_changed` must preserve their separate
attribution and the Event roles must explain the relationship.

Keep them separate when combining them would require two unrelated judgments,
two materially different causal chains, or two different audience decisions.
An exact shared artifact is strong evidence of a relationship, not proof that
every surrounding claim is identical. Lexical matches and embedding neighbors
are discovery aids only. No URL rule, threshold, or connected component makes
the grouping decision.

Each routed Event may support at most one selected Insight per audience. This
forces the author to choose the clearest editorial home instead of duplicating
evidence across the daily brief.

## Editorial rank

Rank selected Insights contiguously from one by the order in which this audience
should act on or investigate them. Use a qualitative, lexicographic judgment:

1. decision consequence for a BIT thesis, exposure, or engineering system;
2. strength and directness of the evidence;
3. time sensitivity or risk of waiting;
4. specificity and usefulness of the next action; and
5. novelty relative to the rest of the day's brief.

Do not calculate a synthetic score. Feed rank may help locate evidence but does
not determine editorial rank. Similarity is never a ranking input. If two items
are close, prefer the one with the clearer causal chain and falsifiable next
step.

Write a `rank_rationale` for every selected Insight. It should name the decisive
relative factors—such as portfolio breadth, consequence, evidence quality,
urgency, or actionability—without pretending that rank is a calculated score.

## Investment analysis

Use the structured BIT context returned by `context --audience investment`.
It contains the public fund thesis and the complete audited portfolio baseline.
For each affected company record:

- `scope`: `portfolio` or `outside_portfolio`;
- `impact`: `positive`, `negative`, `mixed`, or `uncertain`; and
- `mechanism`: the company-specific operating or competitive transmission path.

Do not repeat portfolio dates or disclosure caveats in every entity. They live
once in the context packet and the reader's portfolio note. `portfolio` means
the company appears in that working baseline. `outside_portfolio` is an analyst
mapping, not a known BIT view, holding, or recommendation. Consider the
portfolio first and omit the outside section when no direct public-company
connection is defensible.

Then provide one `key_uncertainty` and one to three measurable `watchpoints`.
Do not create separate operating-driver, financial-driver, edge, impact-chain,
or counter-case fields. Their useful substance belongs in one coherent
`interpretation`, while the uncertainty and watchpoints explain how the reader
could challenge it.

The desired chain is:

```text
public evidence
→ operating or competitive driver
→ company or portfolio exposure
→ revenue / margin / capex / share / valuation consequence
→ thesis consequence and falsifiable watchpoint
```

If a step is not supported, say so. Do not fill a structural field with
speculation merely to make the memo look complete.

## AI Engineering analysis

Use the common fields rather than a second experiment memo. `interpretation`
explains the affected system, practical implication, transfer limits, and why
the evidence matters. `next_step` states one bounded, reproducible action.
The only Engineering-specific field is `decision_rule`: one concise statement
of the measurable result that justifies proceeding and the result that rejects,
pauses, or constrains the idea.

The author should still reason about hypothesis, workload, hardware,
quantization, context, benchmark conditions, security limits, and operator
cost when they affect transferability. Include their useful substance in the
three reader fields above instead of preserving each as a separate label. A
provider microbenchmark is not evidence of end-to-end production improvement.

## Citation and coverage rules

`event` and `artifact` citations must point to frozen URLs from the workspace.
Use `web` for newly researched sources and include `retrieved_at` and a concise
supporting excerpt. Use `context` for the encoded BIT or Engineering context
and retain the underlying public URL when making a factual portfolio claim.

Every positively routed Event/audience pair must be accounted for exactly once.
This is an audit requirement, not a request to publish weak items. Put weak,
duplicative, stale, or non-actionable candidates in `not_selected` with a
specific reason.
