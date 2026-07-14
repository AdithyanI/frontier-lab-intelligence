# System Status

Last verified: 2026-07-14

This is the conceptual handoff for Frontier Lab Intelligence. Read it before
planning across projects or changing the system direction. It explains what
the product is, what is already real, what remains unproven, and which durable
document answers each deeper question.

This file is not the execution tracker and not a chronological log. The active
project tracker owns detailed work state; the build log owns history.

## North Star

Earn the next BIT Capital interview with one coherent, defensible, working
case study: turn public frontier-lab evidence into 3–5 excellent, checkable,
decision-useful insights for an investment team and an AI engineering team.

The product thesis is:

> A curated network can identify important frontier-AI activity early; exact
> evidence grouping, transparent routing, and primary-source citations can
> turn that activity into intelligence a human can trust.

The submission deadline is 2026-07-20. Until then, a narrow evaluated path
from evidence to cited delivery is more valuable than broader crawling, a
larger graph, or additional UI polish.

## Product Story

```text
Registry
  -> trusted X collection cohort
  -> exact quote / retweet / reply envelopes over time
  -> transparent daily-score ordering
  -> keep / drop evidence routing
  -> cited extraction from stored first-party X
       + optional canonical-artifact strengthening
  -> primary-source-cited insights
  -> investor + AI-engineer briefing
```

The stored-X and optional canonical-artifact evidence paths are implemented.
The first five-record cited-extraction proof and its audit UI are now live;
generalizing that proof to another day and delivery remains the active boundary.

## Where the System Stands

| Layer | Status | What is established |
| --- | --- | --- |
| Registry | Implemented and inspectable | One entity can own multiple channels; structural kind and Registry admission are separate; rejected records remain reversible and reason-bearing. The current checkpoint contains 2,220 auditable identities. |
| Trusted-following graph | Evaluated candidate generator | A fresh immutable snapshot contains 2,456,305 outgoing-follow edges. Entity overlap is the accepted inspectable support feature; personalized PageRank remains a diagnostic, not truth. |
| X evidence store | Implemented source boundary | Raw provider evidence is preserved locally and normalized into replayable posts and relations. X is the only implemented discovery source today. |
| Exact event projection | Implemented and regression-tested | Provider-declared quote, retweet, and reply relations form stable envelopes with cutoff-correct daily snapshots and deduplicated weekly views. The current nine-day run contains 20,159 posts and 5,202 exact events. |
| Feed + daily score | Implemented audit surface | The Feed is date-filterable, shows one stable daily score rank across Audit/search filters, and explains its transparent tracked-amplification, author-support, and public-engagement inputs on demand. Registry changes affect derived views without rewriting raw evidence. |
| Keep/drop triage | Evaluated routing layer | The current default is `gpt-5.6-luna`/medium through LiteLLM and still returns only `decision` and `reason`; a 64-envelope migration cohort matched the accepted mini-medium decisions 64/64 and observed a 61.86% cache-read ratio. The historical corrected mini run evaluated 8,097 envelopes with zero failures. This validates execution, not downstream insight quality. |
| Canonical artifact library | Bounded implementation + operator index | Outbound primary-resource links are conservatively canonicalized, source-linked, fetched once, snapshotted, and replayable. The catalog contains 1,566 canonical artifacts and a read-only inspection page; the bounded cohort now has 22 clean-text snapshots (19 native plus three Jina Reader recoveries). |
| Cited insights | Bounded proof live | The current `insight-v1.1` default is `gpt-5.6-luna`/medium. On the same frozen five-record oracle, Luna produced five application-verified exact citations; the historical mini proof published four and retained one exact-span failure. This is a bounded migration result, not yet the required blind-day quality proof. |
| Insights UI + briefing | Initial UI live; briefing missing | The Insights API and dated audit surface expose only the four citation-verified records with direct evidence links and both audience lenses. A blind second day, reproducible briefing, and broader evaluation remain. |
| Submission package | Not complete | The rubric-mapped write-up, limitations, prompt/evaluation evidence, and final delivery review remain. Nothing has been submitted externally. |

Counts above are dated checkpoint evidence, not live contracts. Query the
current databases or APIs before using them as present-tense product claims.

## The Most Important Unproven Claim

The repository has proved collection, identity, graph support, exact grouping,
temporal correctness, daily-score ordering, triage, artifact storage, and one
bounded four-insight cited extraction. It has not yet proved that the same
quality reliably yields 3–5 excellent, primary-source-cited insights across
days.

That is now the critical path. The next useful experiment is to review the
first prompt/schema against its four published records and one honest citation
miss, then run one blind day without weakening application-owned citation
verification. It should answer:

1. Can the system state a concrete claim without inventing evidence?
2. Can every shipped claim quote and link to checkable primary evidence—an
   authored first-party X source or an external artifact?
3. Can it explain why the claim matters without disguising hypotheses as
   facts?
4. Does the result help the investment or AI-engineering audience make a
   decision?

Do not reopen broad Registry cleanup, graph tuning, corpus backfills, or Feed
redesign unless this oracle exposes a concrete dependency.

## Submission Finish Line

The active tracker owns the detail. At system level, the remaining proof is:

1. Review the bounded `insight-v1.1` proof and freeze or revise the prompt only
   from the recorded four successes and one exact-span miss.
2. Produce 3–5 primary-source-cited insights for 2026-07-11 and one blind day.
3. Ship the Insights surface and one reproducible daily briefing.
4. Record citation validity, human worth-attention judgment, hallucination
   controls, and workflow tokenomics.
5. Add the public reviewer landing page, local alert/outbox proof, final
   report, and one package smoke path required by the assignment.

External submission or alert delivery remains blocked without Adi's explicit
current-session approval.

## What Is Deliberately Deferred

- Broad RSS, blog, GitHub, arXiv, or second-source ingestion.
- Semantic/topic event clustering beyond exact provider relations.
- A learned ranking model or renewed daily-score weight tuning.
- Large discovered-account admission or recursive graph crawling.
- Mobile/responsive polish.
- Real external alerts, publishing, uploading, or submission without Adi's
  explicit current-session approval.

These are valid future extensions, not prerequisites for proving the current
case-study thesis.

## Current Direction

The only active tracker is
[`docs/projects/cited-insights/tasks.md`](projects/cited-insights/tasks.md).
Its current batch owns the executable next step: use the frozen
[`oracle evaluation`](projects/cited-insights/resources/insight-oracle-evaluation-2026-07-14.md)
and live Insights surface to review the prompt/schema, then run one blind day,
build one daily briefing, and finish the evaluation and submission package.

Completed phases and their reasoning are preserved under
[`docs/projects/archive/`](projects/archive/). They should be consulted when a
new decision touches a frozen boundary, not read front-to-back during ordinary
handoff.

## Which Document to Read

| Question | Source of truth |
| --- | --- |
| What is the external assignment? | [`references/case-prompt.md`](references/case-prompt.md) |
| What are we optimizing for and what context matters? | [`references/context.md`](references/context.md) |
| What should be done next, exactly? | Active [`projects/<project>/tasks.md`](projects/cited-insights/tasks.md) |
| How is the system implemented? | [`architecture/overview.md`](architecture/overview.md) |
| What product and UI principles are frozen? | [`../PRODUCT.md`](../PRODUCT.md) and [`../DESIGN.md`](../DESIGN.md) |
| Why was a past decision made? | Active/archived project decisions and resources |
| What happened chronologically, including spend and tools? | [`references/build-log.md`](references/build-log.md) |
| How should an external reviewer inspect the repository? | [`references/reviewer-guide.md`](references/reviewer-guide.md) |

If this brief conflicts with the active tracker, the tracker wins for execution
state. If either conflicts with implemented behavior, stop, record the mismatch
in the tracker, and reconcile the documentation before building on it.

## Cold-Agent Handoff

A new architect or implementation agent should:

1. Read this file and the case prompt.
2. Read the active tracker's Goal, Decisions, Current Batch, blockers, and Done
   When.
3. Read only the architecture section and project resources relevant to the
   current batch.
4. Inspect code and data at the named boundary before proposing a new
   abstraction.
5. Update the tracker while executing; update this brief only when the
   conceptual system status or critical path changes.

Update this file when an active project changes, a major layer moves between
planned/proven, the critical unproven claim changes, or a foundational status
claim becomes false. Do not append progress notes here.
