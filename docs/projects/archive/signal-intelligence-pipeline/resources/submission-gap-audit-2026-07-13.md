# Submission Gap Audit — 2026-07-13

## Verdict

The repository is a strong, unusually inspectable foundation, but it is not a
complete case-study submission yet. Registry, provenance, evidence storage,
network discovery, exact grouping, and the local evidence UI are defensible.
The case study's central proof is still missing: 3–5 genuinely useful,
primary-cited insights, a validated signal/noise decision, and actionable
delivery to the investment and AI personas.

This is not a predicted BIT score. It is an execution-risk map against the
published weights. Current weighted coverage is roughly **35–45%**: the
foundation is substantially stronger than that number suggests, but the
highest-value end-to-end product outcome has not landed.

## Rubric Map

| Area | Weight | Evidence that works now | Missing proof | Status |
| --- | ---: | --- | --- | --- |
| Registry of labs and people | 20% | 2,197 active entities: 2,104 people and 93 organizations; 2,270 active channels; reason-bearing reversible curation; entity/channel ownership; X-based discovery and network support | Deep cross-channel identity resolution is still concentrated on X; currency is runnable but not scheduled; only a small subset has GitHub/blog/website channels | Strong |
| Signal vs. noise | 20% | Seven complete X days; immutable evidence; exact relationship grouping; dynamic rejection overlay; inspectable Feed and attention inputs | No blind top-20 decision yet; no accepted relevance, novelty, or actionability gate; no demonstrated insight yield | Partial / immediate gate |
| Contributor and insight scoring | 20% | Reproducible entity-overlap network-support baseline; PageRank retained as a diagnostic; transparent `attention-v1` components and exclusions | `attention-v1` is still a hand-weighted ordering aid and must not be presented as a validated quality score; no insight rating or human-ground-truth results | Partial / high risk |
| Actionable delivery | 15% | Evidence is reviewable in the app | No insight surface, periodic digest, PDF, alert delivery, persona tailoring, or primary-cited call to action | Missing |
| Ingestion | 10% | 772 MiB cached X store; resumable provider adapters; immutable raw payloads; 1,599 stored blog/arXiv/GitHub items (1,366 / 137 / 96); deterministic Feed refresh | The non-X fetcher is still a three-lab spike; no scheduled multi-source orchestration, freshness run, or accepted source-coverage contract | Partial |
| Structured cited extraction | 10% | Reusable LiteLLM/Responses, structured-output, hosted-search, usage, cost, prompt-cache, and resumability primitives exist from Registry work | No `insight-v1` schema, prompt, run store, extraction evaluation, primary-citation verification, or hallucination-control evidence | Missing |
| Web interface | 5% | Registry, Ranking, Feed, and Architecture are fast, inspectable, tested, and coherent | No scored-insight/report history or tracking configuration surface | Strong for current stage |

## Required Deliverables

| Deliverable | Current state |
| --- | --- |
| Modular source code and runnable local demo | Working; reviewer guide and checks exist |
| Database schema and real data | Working; tracked canonical DB plus ignored raw/derived artifacts |
| Architecture, model choices, fallbacks | Partial; strong current architecture, but extraction/delivery model choices remain proposed |
| Prompts with rationale | Partial; Registry prompts exist, insight prompts do not |
| Evaluation and hallucination control | Partial; Registry evaluation is strong, insight extraction and scoring validation are absent |
| Workflow tokenomics | Partial; calls persist usage and proxy cost, but no submission-level workflow summary exists |
| Periodic report in app and PDF | Missing |
| Alerts to the correct persona | Missing; implement an inspectable delivery outbox/adapter before any approved external smoke |
| Final report with 3–5 real insights | Missing |
| Public reviewer landing page / README | Missing; explicitly required by the case prompt and therefore appropriate at packaging time |

## Submission-Critical Path

1. **Finish the Feed decision now.** Blind-audit the top 20 attention envelopes
   for correct grouping, frontier relevance, substance, usefulness, and primary
   groundability. Require at least 12/20 worth attention and at least three
   publishable candidates. Freeze the Feed after this decision.
2. **Open one narrow cited-insight project.** Implement a versioned `insight-v1`
   run over the accepted one-day candidates. The output must retain event ID,
   attributed entity, concise development, primary evidence/citation, novelty,
   relevance, confidence, and separate investment/AI-team implications.
3. **Separate eligibility from ordering.** Use an explicit keep/reject/review
   relevance/substance gate, then order eligible insights with transparent
   evidence features. Do not promote `attention-v1` into a quality score merely
   because it already exists.
4. **Create ground truth while extracting.** Extend the unchanged audit rubric
   to the planned stratified 60-item sample (attention, public engagement, and
   chronological/random). Report Precision@10/@20, useful yield, citation
   validity, duplicate rate, and persona agreement. Do not claim recall.
5. **Deliver one shared core two ways.** Produce one in-app digest with an
   investment view and an AI-engineering view, PDF export, and an alert adapter
   with a local/dry-run outbox. Any real external alert smoke requires Adi's
   explicit approval.
6. **Package proof, not more platform.** Select the best 3–5 cited insights,
   finish tokenomics, final report, reviewer README/demo path, and submission
   limitations. Defer broader graph, Registry, source, and UI expansion unless
   a demonstrated insight failure requires it.

## Immediate Decision

Do not spend another batch on Registry completeness, graph ranking, database
scale, or Feed polish. Complete M4, archive this evidence-surface project, and
move directly to cited insight extraction and delivery. The current foundation
is sufficient to test the actual case-study thesis.
