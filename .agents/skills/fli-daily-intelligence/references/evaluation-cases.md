# Evaluation Cases

Use these cases to evaluate the skill and client from a fresh agent context.

## 1. July 15 complete daily brief

Prompt:

> Use $fli-daily-intelligence to research, validate, and persist the daily brief
> for 2026-07-15.

Expected behavior:

- reads both audience contexts before synthesis;
- freezes 55 eligible routed-positive Events after excluding two old-only
  packets, representing 48 Investment and 40 Engineering candidate pairs;
- searches across the complete cohort rather than reviewing only the current
  kept cards;
- keeps every decision-useful Insight and ranks each audience contiguously;
- accounts for every candidate pair; and
- validates and imports without manually editing SQLite;
- inspects the imported run; and
- makes the complete run available to the normal Insights read path without
  copying the draft into frontend code.

## 2. Inkling retrieval and grouping

Prompt:

> In the 2026-07-15 workspace, find all evidence relevant to Inkling and decide
> what belongs in the same Insight for each audience.

Expected behavior:

- text search finds the eleven union-positive Inkling candidates, including the
  previously surfaced ranks 1, 4, 10, 23, 45, 55, 64, and 76;
- vector retrieval is used as a candidate aid when useful;
- a complete one-day review may skip vector retrieval when lexical and artifact
  retrieval already establish the candidate set;
- the official release/model-card evidence is treated as primary;
- kernel performance, third-party evaluation, and Databricks distribution are
  not falsely described as the identical occurrence;
- distinct developments support one broader Insight only when each passes the
  one-claim, same-mechanism, and source-subtraction tests; and
- the Investment result maps affected companies against the structured audited
  portfolio packet and does not invent a holding connection;
- any company outside the packet is labeled `outside_portfolio` and is included
  only when its operating or competitive transmission path is specific.

## 3. Similar topic that must not be merged

Prompt:

> Compare the July 15 GPT-Red and Anthropic agent-safety Events and determine
> whether they should be one Insight.

Expected behavior:

- GPT-Red repetitions can be consolidated;
- Anthropic simulation evidence remains a distinct factual development;
- a broader safety thesis may cite both only when they support the same causal
  mechanism and audience decision, not merely the same safety topic; and
- cosine similarity alone never determines the result.

## 4. Seven-day source window

For July 14, the OpenAI ChatGPT for Teachers Event rooted in the 19 November
2025 announcement must not enter the workspace merely because July reactions
resurfaced it. For July 10, the Thinking Machines Event may remain, but the 15
July 2025 financing root must be removed and Mira Murati's 10 July 2026 quote
and reply must become the current first-party evidence.

Expected behavior:

- sources exactly seven days old remain eligible; older X sources do not;
- independently authored reactions never rescue an old first-party packet;
- a current same-author quote or reply can replace the old root;
- an old-only Event is excluded before agent disposition; and
- the Feed still retains the complete raw envelope for audit.

## 5. Artifact disclosure timing and claim support

For July 14, Event #86 is rooted in Romain Huet's current Codex post. Its reply
linking the Paper Glider showcase and the showcase artifact were published on
July 15, after the brief day.

Expected behavior:

- the July 15 reply is pruned from the July 14 workspace;
- Paper Glider remains inspectable with its Jul 15 disclosure lineage, but the
  agent must not cite it as evidence available in the Jul 14 brief;
- on a day where Paper Glider is eligible, Event membership alone never makes
  it evidence for lower task cost, demand, or capacity;
- an agent may cite it only for a claim established by a short excerpt from its
  frozen text; and
- validation rejects a missing or fabricated artifact excerpt.

## 6. Missing-implication review

Prompt:

> Review the selected Kimi K3 Insights in the 2026-07-16 draft before
> validation. Identify the most important supported consequence that the draft
> has not carried through.

Expected behavior:

- compares the separate Investment and Engineering interpretations without
  merging the audience outputs;
- recognizes that K3's thinking-history requirement and sensitivity to
  mid-session model switching affect practical substitutability;
- connects the cache-hit versus cache-miss price difference to cost per
  completed task and enterprise switching friction;
- distinguishes application-owned durable memory, model-native session history,
  inference caching, and physical memory rather than treating “memory” as one
  claim;
- treats named memory, accelerator, or interconnect suppliers as diligence
  questions unless the evidence establishes a company-specific transmission
  path; and
- does not build or run an embedding index when the relevant evidence is
  already present in the inspected packets.

## 7. Reader-facing clarity pass

Prompt:

> Before validating the 2026-07-16 brief, rewrite the selected Kimi K3
> Investment Insight so a smart non-expert can understand it on the first read
> without changing the evidence or investment judgment.

Expected behavior:

- applies the shared Adi writing standard after completing the evidence and
  reasoning work;
- rewrites every reader-facing field, including company mechanisms,
  uncertainty, watchpoints, and next step rather than polishing only the title;
- keeps the judgment-led title and all material facts, causal steps,
  qualifications, company mappings, and measurable watchpoints;
- puts the conclusion first, uses one main idea per sentence, and rewrites most
  sentences over 25 words;
- states the operating and financial consequences in plain English and says
  directly when the financial impact is unknown;
- retains FLI's institutional voice without first-person opinions,
  conversational asides, marketing language, or em dashes; and
- does not trade technical precision or honest uncertainty for brevity.

## 8. Causal coherence and source pruning

Prompt:

> Review a proposed Investment Insight about Kimi K3 pricing pressure. It cites
> K3's Artificial Analysis and KernelBench results, K3's future weight-release
> date, an Inkling ARC result, a broad Chinese open-source policy speech, and a
> practitioner comparison of Terra with Sol. Decide what belongs in one
> Insight before validation.

Expected behavior:

- states one core Investment claim before deciding which sources belong;
- keeps K3's availability and K3-specific benchmark evidence together;
- uses Terra only where the same Artificial Analysis evaluation provides a
  genuinely comparable quality-and-cost reference;
- excludes the separate Terra-versus-Sol practitioner workflow because it does
  not test K3 or the same investment claim;
- treats Inkling and broad policy support as separate developments, context, or
  `not_selected` rather than evidence that automatically belongs in the K3
  causal chain;
- preserves only company mechanisms supported by the pruned evidence;
- uses `not_selected` without treating complete cohort accounting as a reason
  to publish adjacent material; and
- applies the same one-claim, source-subtraction test to other topics rather
  than memorizing the named models in this case.

## 9. Evidence strength and test calibration

Prompt:

> Review two draft decisions before validation. An Investment company is marked
> negative because a new rival announced financing and the company has a generic
> competition disclosure. An Engineering experiment changes verification,
> isolation, and duplicate suppression together and invents exact percentage
> gates without a baseline.

Expected behavior:

- treats the financing announcement and generic disclosure as evidence of
  competitive exposure, not proof of a negative company effect;
- uses `uncertain` unless development-specific evidence establishes direction;
- does not manufacture conviction by accumulating weak context sources;
- derives an Engineering gate from a baseline, cited requirement, or operating
  constraint, or labels it as provisional and calibrates it in the test;
- stages or ablates bundled controls when causal attribution matters; and
- states the attribution limit when only the complete bundle can be tested.

## 10. Reusable company context without inherited conclusions

Prompt:

> A routed Event names one company in the working portfolio and one listed
> competitor outside it. Use the Investment context to assess both mappings.

Expected behavior:

- consults the matching portfolio company profile before repeating basic
  business research;
- attributes a view to BIT only when `bit_public_view.grade` is
  `explicit_thesis` or `commentary` and cites the attached BIT source;
- respects `source_scope` and never converts commentary from another BIT
  product into the flagship fund's thesis;
- treats `analyst_context` as a primary-source research aid, not a known BIT
  view or a permanent positive, negative, or mixed call;
- derives each impact label from the current development and its evidence;
- researches the outside company on demand, labels it `outside_portfolio`, and
  does not imply that it belongs to a BIT watchlist; and
- omits either mapping when no direct operating or competitive transmission
  path is defensible.

## 11. Self-contained AI Engineering Insight

Prompt:

> Review an AI Engineering Insight about a large rollout study showing that
> identical model answers can be judged differently when their provider,
> model-family, or moral labels change. Rewrite it for an analyst who has not
> opened the Event or paper.

Expected behavior:

- explains in plain English what labels or framing were changed and that the
  compared answer content was otherwise identical;
- states the scale or method only when it helps the reader understand the
  strength and limits of the finding;
- reports the central preference shift and states that the effect varies by
  model, prompt, and task rather than implying a universal fixed bias;
- connects the finding to one named research-agent, evaluation, source-
  selection, or analyst workflow instead of saying only that bias matters;
- explains why a single retry cannot reveal a distribution-level shift;
- leaves the bounded test in `next_step` and the proceed and stop conditions in
  `decision_rule` rather than duplicating the full experiment in the opening;
  and
- remains concise by removing repetition, not by withholding the setup a new
  reader needs.
