# Editorial Standard

## Contents

- Reader-facing shape
- Reader-facing writing
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

## Reader-facing writing

After the evidence and reasoning are complete, edit every reader-facing field
against the shared
[Adi writing standard](../../adi-writing/references/voice.md). This is a
mandatory clarity pass, not permission to change the evidence or weaken the
analysis.

Apply the standard to `title`, `rank_rationale`, `what_changed`,
`interpretation`, `next_step`, company `mechanism`, `key_uncertainty`,
`watchpoints`, and Engineering `decision_rule`:

- put the conclusion first, followed by the detail and background;
- give each sentence one main idea and each paragraph one topic;
- prefer active voice, concrete nouns, exact dates and everyday words;
- aim for 15 to 20 words per sentence and rewrite most sentences over 25 words;
- make the operating, financial, thesis, or engineering consequence explicit
  instead of hiding it behind terms such as “bridge”, “transmission path”, or
  “substitutability” when plain English is more precise;
- preserve material qualifications as direct sentences, including “the
  financial impact is still unknown” when that is the honest conclusion; and
- remove filler, repetition, inflated language and em dashes.

Keep FLI's institutional voice. Do not add first-person opinions,
conversational asides, marketing language, or personal calls to the reader.
The result should sound like a clear analyst, not like Adi speaking personally.

For example, avoid compressing several steps into one sentence:

> The operating bridge is greater buyer choice and the financial bridge would
> be lower pricing or higher spending, but the magnitude is unknown.

Prefer the same judgment in direct sentences:

> K3 gives buyers another near-frontier option. That could pressure API prices
> or force incumbents to spend more to maintain quality. The financial impact
> is still unknown.

Before validation, ask whether a smart non-expert and an expert could both
understand every sentence on the first read. If simplification removes a
material fact, causal step, uncertainty, or decision condition, restore it in
clearer language.

## Evidence roles

- `primary`: the most authoritative or direct evidence establishing the claim.
- `supporting`: an additional release, implementation, benchmark, distribution,
  or independent report that strengthens the Insight.
- `context`: relevant background that helps interpretation but does not
  establish the central factual claim.
- `counterevidence`: evidence that qualifies or challenges the interpretation.

Several posts repeating one announcement can support one Insight. Context may
explain an affected-company mapping or uncertainty, but it does not justify
merging a separate development into the central claim. Explain the exact role
of every link rather than asserting that similarity proves sameness.

## Grouping boundary

Default distinct developments to separate Insights or `not_selected`. Group
Events into one Insight only when they support one audience judgment, one
intelligible causal chain, and one decision or next action. Repeated posts about
the same primary artifact normally consolidate.

Before validation, state the Insight's core claim privately in one sentence and
run a source-subtraction test over every attached Event and citation:

- identify the exact clause it supports or challenges;
- confirm that a comparison uses a genuinely comparable subject, workload,
  method, and decision context;
- confirm that it belongs to the same operating, financial, thesis, or
  engineering mechanism; and
- ask whether removing it would materially weaken the conclusion or its key
  uncertainty.

Remove, separate, or mark `not_selected` any evidence that fails this test. A
source that merely shows the breadth of a trend is not necessary evidence for
the central claim.

Keep Events separate when combining them would require two judgments, two
materially different causal chains, or two audience decisions. Sharing a broad
topic, company, model class, policy direction, or phrase is insufficient. A
result from a different benchmark or practitioner workflow is context for a
separate question unless the Insight explicitly analyzes that difference. An
exact shared artifact is strong evidence of a relationship, not proof that
every surrounding claim is identical. Lexical matches and embedding neighbors
are discovery aids only. No URL rule, threshold, or connected component makes
the grouping decision.

Each routed Event may support at most one selected Insight per audience. This
forces the author to choose the clearest editorial home instead of duplicating
evidence across the daily brief. Complete cohort accounting is satisfied by a
specific `not_selected` disposition; it never requires attaching an adjacent
Event to a published Insight.

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
It contains the public fund thesis, the complete audited portfolio baseline,
and one reusable profile for every company in that baseline. A profile provides
identity aliases, stable business drivers, two-sided frontier-AI exposure
channels, and watchpoints so the agent does not reconstruct basic company
context during every run.

The profile has a strict attribution boundary. `bit_public_view` contains only
views supported by a cited BIT source and records whether the evidence is an
explicit thesis, broader commentary, or absent. `analyst_context` is FLI's
primary-source research aid. It is never a known BIT thesis, holding decision,
or directional conclusion. Use both as a starting lens, then determine the
effect of the current development from current evidence.

`source_scope` distinguishes firm-wide research, flagship commentary, another
BIT product, mixed sources, or no BIT view. Commentary from another product can
inform how the manager reasons, but it must not be presented as the flagship
fund's own thesis. `company_profiles_reviewed_at` is an internal freshness
marker; verify time-sensitive identity or listing facts when needed.

For each affected company record:

- `scope`: `portfolio` or `outside_portfolio`;
- `impact`: `positive`, `negative`, `mixed`, or `uncertain`; and
- `mechanism`: the company-specific operating or competitive transmission path.

Match the impact label to the evidence for this development. A product page,
partnership description, or generic risk-factor disclosure can establish that
a company is exposed to a market or competitor. It does not establish that the
current development has a positive or negative effect. Use `uncertain` unless
development-specific evidence supports the direction. Do not use several weak
context sources to simulate one strong causal source.

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

An internal research-method control without a defensible fund-thesis, company,
or portfolio consequence normally belongs under AI Engineering or
`not_selected`, not in the Investment brief.

## AI Engineering analysis

Use the common fields rather than a second experiment memo. `interpretation`
explains the affected system, practical implication, transfer limits, and why
the evidence matters. `next_step` states one bounded, reproducible action.
The only Engineering-specific field is `decision_rule`: one concise statement
of the measurable result that justifies proceeding and the result that rejects,
pauses, or constrains the idea.

Numerical gates need a basis. Derive them from an observed baseline, a cited
requirement, or a known operating constraint. When none exists, call the values
provisional criteria and make baseline calibration part of the next step; do
not present convenient percentages, sample counts, or latency limits as
validated thresholds.

Design the action so its result is interpretable. If verification, isolation,
deduplication, routing, or other controls are introduced together, stage them
or include an ablation that isolates their effects. If that is impractical,
state that the combined test can assess the bundle but cannot identify which
control caused the change.

The author should still reason about hypothesis, workload, hardware,
quantization, context, benchmark conditions, security limits, and operator
cost when they affect transferability. Include their useful substance in the
three reader fields above instead of preserving each as a separate label. A
provider microbenchmark is not evidence of end-to-end production improvement.

## Citation and coverage rules

`event` and `artifact` citations must point to frozen URLs from the workspace.
The workspace uses a seven-day inclusive window for first-party X evidence and
stores the authoritative `posted` time on each retained X source. Raw Feed
history remains available for audit, but it is not authoring evidence once
pruned. If an Event's old root was replaced by a current same-author update,
write and cite the update—not the historical announcement it referenced.
Event citation dates are filled from frozen source truth; a conflicting date is
invalid. Artifacts remain visible with their exact stored disclosure lineage;
they are not automatically removed with X sources. The agent must audit that a
disclosure was available by the brief day and that the artifact supports the
Insight. Every artifact citation must include a short verbatim excerpt from the
frozen artifact and a claim-specific explanation of what that passage
establishes. Omit a later-disclosed or non-supporting artifact.
Use `web` for newly researched sources and include `retrieved_at` and a concise
supporting excerpt. Use `context` for the encoded BIT or Engineering context
and retain the underlying public URL when making a factual portfolio claim.

Every positively routed Event/audience pair must be accounted for exactly once.
This is an audit requirement, not a request to publish weak items. Put weak,
duplicative, stale, or non-actionable candidates in `not_selected` with a
specific reason.
