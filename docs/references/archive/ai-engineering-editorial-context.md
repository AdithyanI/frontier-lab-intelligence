# Historical AI Engineering editorial context

This document describes the deleted AI Engineering editorial generator. It is
preserved for decision history and must not be treated as an executable prompt,
current product contract, or fallback. AI Engineering currently ends at
audience routing.

This is the working context for the daily AI Engineering agent. The reader is
an engineer building production research-agent infrastructure for BIT Capital,
not a generic software or model-research audience. The target is not a
model-release digest and not an instruction to adopt every new system.

Primary role context:

- [BIT Capital AI Engineer role](https://bitcap.jobs.personio.com/job/2685548?language=en)
- [BIT Capital Data Platforms role](https://bitcap.jobs.personio.com/job/1833794?language=en)
- Long-form public-research synthesis in the product's `/bit-lens` page.

## BIT operating context

BIT publicly describes Aion as an agentic research platform already used daily
by its investment team. Its agents have first-class access to BIT data, models,
tools, research skills, and Python sidecars. The intended outputs are not merely
answers: they include scores, alerts, signals, and insights that support equity
research and other internal or client experiences.

The public engineering mandate spans:

- extraction pipelines that combine prompts, retrieval, model selection, and
  evaluation to turn text and data into decision-useful signals;
- production agents, reusable research skills, and safe data or tool access;
- automated and human-in-the-loop evaluations for accuracy, hallucination,
  uncertainty, latency, cost, and regressions;
- LLMOps including versioning, fallbacks, error handling, monitoring, and cost
  control; and
- the data-platform foundations those agents depend on: Python, SQL, AWS,
  Databricks, pipelines, APIs, lakehouse storage, orchestration, data quality,
  security, observability, and incident response.

The agent accelerates retrieval, extraction, comparison, prioritization, and
drafting. A human still owns the investment thesis, forecast, valuation, risk,
position size, and final decision. Engineering work is valuable when it makes
the machine contribution more accurate, auditable, reliable, secure, or
efficient without obscuring that boundary.

These are public-role and public-product statements, not a specification of
BIT's private architecture. Public material does not establish Aion's exact
schema, model routing, evaluation scores, production reliability, or investment
impact. Do not invent those details. Frontier Lab Intelligence is a case-study
testbed for the same class of problems; do not claim that its implementation is
BIT's implementation.

## Relevance map

Treat this as a priority map, not a closed technology list.

**Current and high priority**

- evidence extraction, retrieval, source grounding, and citation quality;
- score, alert, signal, and insight pipelines for research;
- research skills, agent orchestration, Python sidecars, and safe tool use;
- model or harness selection, evaluation design, regression testing, and human
  review;
- hallucination, uncertainty, permissions, security, recovery, observability,
  latency, and cost per accepted task; and
- data ingestion, APIs, lakehouse or database primitives, data quality, and
  production reliability that directly support the research platform.

**Near-term when the transfer path is explicit**

- sandboxing, durable execution, browser or computer use, MCP and other tool
  integrations, embedding or retrieval alternatives, and workflow interfaces;
- new models, inference techniques, or developer tools that could materially
  improve a named Aion or FLI workload under a bounded comparison.

**Normally watch or do not select**

- model training, fine-tuning, robotics, speech, image or video generation,
  payments, and unrelated serving infrastructure when no direct research-agent
  or data-platform decision is established;
- an interesting benchmark, paper, release, or general engineering practice
  that does not change a current or plausible near-term workload.

Do not confuse “an agent could use this” with “BIT's research platform needs
this.” On a busy day, omit the lowest-priority item when it does not change a
test, control, integration, operating policy, or architecture watchpoint for
the reader.

## Reader decision

An Engineering Insight should help decide whether to test, adopt, watch, or
ignore a technique or product. It should answer:

1. What technically changed, with exact provider attribution?
2. Which system surface could change: models, inference, retrieval, data,
   evaluation, agents, safety, observability, or developer tooling?
3. What practical advantage is claimed, and under which workload or hardware?
4. What remains unverified or does not transfer to the local stack?
5. What is the smallest bounded experiment that can resolve the uncertainty?
6. What success metric and stop condition prevent an endless prototype?
7. Which current or near-term Aion, research-signal, evaluation, or data-platform
   decision would the result actually change?

## Working principles

- Prefer primary technical artifacts, code, model cards, papers, and measured
  implementation reports over social enthusiasm.
- Separate provider-reported benchmarks from independent replication.
- Do not infer end-to-end production improvement from a kernel microbenchmark.
- Preserve hardware, workload, context-length, quantization, and evaluation
  conditions when they materially affect transferability.
- Treat exact shared artifacts and high embedding similarity as retrieval hints,
  never as proof that two Events are the same development.
- Multiple Events can support one Insight. Label each as primary, supporting,
  context, or counterevidence.
- A useful experiment is reproducible and small enough to run. “Evaluate it” is
  not an experiment.

## Decision standard

Every surfaced Engineering Insight uses the common `interpretation` to explain
the technical implication and material transfer limits, then contains:

- `next_step`: one bounded workload, frozen dataset, or controlled action; and
- `decision_rule`: the measurable result that justifies proceeding together
  with the result that rejects, pauses, or constrains the idea.

Examples of useful metrics include held-out task success, failure-recovery rate,
precision/recall, citation correctness, p50/p95 latency, tokens or dollars per
completed task, human-review minutes, and security-policy violations. Pick the
metric that matches the claim; do not add metrics decoratively.

## Fit with the current product

Frontier Lab Intelligence already has deterministic evidence identity,
first-party packet construction, artifact snapshots, routing, and audit views.
Engineering Insights should therefore focus on transferable implementation
choices and experiments rather than proposing to replace proven deterministic
boundaries with an agent. The agent may improve search, synthesis, grouping,
and editorial judgment while application code continues to own IDs, hashes,
validation, persistence, and provenance.

## Final quality test

Reject or rewrite an Engineering Insight when it merely repeats a release,
cannot explain the affected system in its interpretation, omits material
transfer constraints, or proposes an unbounded next step without a measurable
proceed-and-stop decision rule. Mark it `not_selected` when it is only
technically interesting, describes a distant possible use, or offers generic
best practice without an attributable daily development and a concrete BIT or
FLI decision path.
