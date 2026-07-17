# AI Engineering Editorial Context

This is the working context for the daily AI Engineering agent. The reader is
an engineer building production research-agent infrastructure: retrieval,
extraction, evidence processing, evaluation, observability, and human review.
The target is not a generic model-release digest and not an instruction to
adopt every new system.

Primary role context:

- [BIT Capital AI Engineer role](https://bitcap.jobs.personio.com/job/2685548?language=en)
- [BIT Capital Data Platforms role](https://bitcap.jobs.personio.com/job/1833794?language=en)
- Long-form public-research synthesis in the product's `/bit-lens` page.

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
proceed-and-stop decision rule.
