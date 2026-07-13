# Top-20 Attention Audit — 2026-07-11

## Purpose

Test whether `attention-v1` is useful as a candidate-generation ordering for
the latest complete UTC day. This is an exploratory operator audit of the live
API response, not the formal blinded evaluation: the reviewer knew the items
came from the top of the attention ranking and saw their rank order.

## Frozen Cohort

- Endpoint: `/api/events?date=2026-07-11&sort=attention&limit=20&offset=0`
- Evidence contract: `exact-structural-v1`
- Review date: 2026-07-13
- Review unit: one Feed evidence envelope
- Source boundary: locally stored X evidence only; no provider, web-search, or
  LLM calls were made for this audit.

## Rubric

Each envelope was reviewed for frontier-AI relevance, substance, usefulness to
BIT, primary or first-hand groundability, duplication, and likely usefulness to
investment or AI engineering. `Worth attention` means the event merits a later
extraction or verification pass; it does not mean the current post is ready to
publish as an insight.

## Results

- **12/20 worth attention** — exactly meets the exploratory gate.
- **5 strong extraction candidates** — enough to justify continuing the X
  slice rather than pivoting to the stored blog/arXiv/GitHub corpus now.
- **8/20 noise or too thin** — the top two results are both high-engagement
  founder banter, so `attention-v1` is not a relevance or publication score.
- **0 obvious structural false merges** in the reviewed top 20. Exact grouping
  did what it claimed; the remaining problem is semantic quality and root
  selection, not relation integrity.
- **No obvious cross-envelope duplicate** among the five strongest candidates.
  Several Sam Altman posts cover the same launch-day discourse but make
  distinct claims and remain separate under the exact-only contract.

## Envelope Audit

| Rank | Root | Verdict | Audit note |
| ---: | --- | --- | --- |
| 1 | [Sam Altman on benchmarks and Elon](https://x.com/sama/status/2075983427019612242) | noise | Frontier-adjacent but primarily banter; the benchmark claim is not grounded in the envelope. |
| 2 | [Sam Altman on space datacenters](https://x.com/sama/status/2075982617976230043) | noise | The replies contain a potentially relevant SpaceX claim, but the envelope is dominated by a personal feud and is not insight-ready. |
| 3 | [Sam Altman on AI and job creation](https://x.com/sama/status/2076036901824532530) | worth attention | Material executive view on labor impact. Publish only as an attributed belief unless independent labor evidence is added. |
| 4 | [Ethan Knight on Sol Ultra and the Cycle Double Cover Conjecture](https://x.com/__eknight__/status/2075643450196971805) | strong candidate | First-hand capability claim with links to the proof and prompt plus substantive expert reaction. Resolve and verify the primary artifacts. |
| 5 | [Sam Altman saying users love Sol](https://x.com/sama/status/2075579646373216282) | noise | Marketing reaction without a concrete claim or evidence. |
| 6 | [Elon Musk on Grok Build and 4.5](https://x.com/elonmusk/status/2075728739615281398) | worth attention | Product-positioning signal with a quoted orchestrator evaluation; needs the underlying evaluation before use. |
| 7 | [Dwarkesh Patel with Adam Brown](https://x.com/dwarkesh_sp/status/2075619763972141539) | worth attention | Substantive interview with a Google DeepMind science-and-reasoning lead; only the closing AI segment is directly in scope. |
| 8 | [Karan Singhal on GPT-5.6 health evaluations](https://x.com/thekaransinghal/status/2075689779937833302) | strong candidate | Detailed first-hand vertical-performance claim, methodology outline, and official OpenAI amplification. Resolve the evaluation source and preserve caveats. |
| 9 | [Alexandr Wang's “compute daddy” post](https://x.com/alexandr_wang/status/2075364232623956227) | noise | The headline is a meme. One quote contains substantive analysis, showing that a high-value child can hide under a low-value root. |
| 10 | [Yann LeCun on open-source AI sovereignty](https://x.com/ylecun/status/2075102766221996136) | worth attention | Relevant strategic and policy position from a frontier-lab leader; useful as an attributed viewpoint, not a factual conclusion. |
| 11 | [François Chollet on agentic coding progress](https://x.com/fchollet/status/2075646052951376196) | worth attention | Strong expert directional signal but too general to stand alone as a published insight. |
| 12 | [Marc Andreessen's farming analogy](https://x.com/pmarca/status/2075764072231129448) | noise | Missing source context and specific AI evidence; generic labor-displacement rhetoric. |
| 13 | [Mira Murati on Thinking Machines' worldview](https://x.com/miramurati/status/2075621073308311701) | strong candidate | First-hand lab strategy and positioning with a linked primary statement. Exact related posts add useful context but must not be flattened into one claim. |
| 14 | [Toby Lütke's Leviathan quotation](https://x.com/tszzl/status/2075851507464040714) | noise | No explicit frontier-AI claim in the envelope. |
| 15 | [Aravind Srinivas on near-term model economics](https://x.com/AravSrinivas/status/2075831774450770243) | worth attention | Decision-relevant executive forecast on price/performance and local models; retain explicitly as a prediction. |
| 16 | [Sebastian Raschka's model price/performance comparison](https://x.com/rasbt/status/2075982283509571666) | strong candidate | Concrete engineering/economics comparison from a credible practitioner. The chart, harness, and model inputs need capture and verification. |
| 17 | [Thibault Sottiaux on post-launch corrections](https://x.com/thsottiaux/status/2075641131002700120) | strong candidate | Detailed first-hand account of launch regressions, user feedback, and planned fixes; immediately useful for product and AI-engineering analysis. |
| 18 | [Toby Lütke on recurring model progress](https://x.com/tszzl/status/2076054888711360931) | noise | Relevant sentiment but generic and non-falsifiable. |
| 19 | [Vitalik Buterin on AI 2040](https://x.com/VitalikButerin/status/2075809437428646294) | worth attention | Substantive policy argument with a direct response from a plan author; useful for strategic context, lower priority than lab/product evidence. |
| 20 | [Thibault Sottiaux on one-day product growth](https://x.com/thsottiaux/status/2076021263945039876) | noise | Potential adoption signal, but no denominator, time-series detail, or independently inspectable metric. |

## Strong Extraction Candidates

1. **Sol Ultra mathematical proof:** what was demonstrated, whether the proof
   withstands verification, and what parallel test-time compute changed.
2. **GPT-5.6 health evaluation:** frontier-versus-cost movement, physician
   comparison methodology, and limits of the claim.
3. **Thinking Machines strategy:** differentiated model ecosystem, open-source
   positioning, and product/lab implications.
4. **Model price/performance frontier:** whether Grok 4.5 and Muse Spark 1.1
   materially shift the cost/performance curve under a comparable harness.
5. **OpenAI post-launch correction:** what failed in the release, what changed
   within 24 hours, and what this says about productization of frontier models.

## What the Audit Says About the Product

1. **Keep the evidence ledger and exact grouping.** The envelopes preserve
   provenance and reduce retweet duplication without inventing semantic links.
2. **Keep `attention-v1` only as candidate generation.** It finds real signals,
   but author prominence and public engagement can rank banter above substantive
   evidence.
3. **Do not concatenate an envelope into one claim.** Replies, quotes, related
   posts, and same-author continuations are structurally related evidence with
   different epistemic roles.
4. **Resolve linked artifacts before insight writing.** The strongest items
   point to proofs, evaluations, charts, or primary statements that carry the
   publishable evidence.
5. **Add relevance and substance after retrieval, not inside grouping.** Exact
   grouping is high precision. A later extraction/review stage should decide
   whether the root, a child, or the whole envelope contains the actual signal.

## Decision

**Conditional keep.** Continue with the X slice and the current exact evidence
contract. Do not recalibrate `attention-v1` in this project and do not expand
the graph. Use the next project to resolve primary artifacts, extract structured
claims, and evaluate relevance/substance before delivery. Run a genuinely blind
stratified review there; this exploratory audit cannot satisfy that formal
evaluation requirement because the reviewer saw the ranking order.
