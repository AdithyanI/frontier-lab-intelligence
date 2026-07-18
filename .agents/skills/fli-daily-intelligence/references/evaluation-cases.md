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
- they may still support one defensible broader Insight; and
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
- a broader safety thesis may cite both only when its causal argument is
  explicit; and
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
