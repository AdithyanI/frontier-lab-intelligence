# Five-Record `insight-v1` Oracle — 2026-07-11

Human-written expectations for the frozen records in
[`oracle-resume.md`](oracle-resume.md). These records define the minimum useful
output and citation standard before any broader extraction run.

The claim is the source-supported statement. “Why it matters” and both persona
implications are analysis derived from that statement; they are not presented
as source facts. Every supporting quote below is an exact substring of the
frozen evidence envelope.

## Rank 4 — Ethan Knight / Sol Ultra proof claim

- **Outcome:** `insight`
- **Claim:** OpenAI's Ethan Knight reported that GPT-5.6 Sol Ultra produced a
  proof of the Cycle Double Cover Conjecture using 64 subagents in under one
  hour.
- **Exact supporting quote:** “Today, we're sharing that it produced a proof
  of the 50-year-old Cycle Double Cover Conjecture using 64 subagents in just
  under one hour.”
- **Evidence:** authored X post `2075643450196971805`,
  <https://x.com/__eknight__/status/2075643450196971805>
- **Why it matters (analysis):** The report is a concrete example of parallel
  test-time compute applied to an open mathematical problem, with a prompt and
  proof disclosed for inspection.
- **Investment implication (analysis):** If independently validated, this
  strengthens the case that premium inference products can create value in
  research workflows where users will pay for large bursts of parallel
  compute.
- **AI-engineering implication (analysis):** Reproducing the result requires
  auditing the disclosed prompt and proof, including how the 64 subagents were
  coordinated and how their work was consolidated.

## Rank 10 — Mira Murati / Thinking Machines worldview

- **Outcome:** `insight`
- **Claim:** Mira Murati described Thinking Machines Lab's alignment thesis as
  an ecosystem of locally shaped AIs that can disagree, rather than one
  centralized model that averages human values.
- **Exact supporting quote:** “The good future has many AIs, raised in
  different places, shaped by the people they serve, disagreeing with each
  other the way we do.”
- **Evidence:** authored X post `2075621073308311701`,
  <https://x.com/miramurati/status/2075621073308311701>
- **Optional strengthening artifact:** *The Future Worth Building Is Human*,
  <https://thinkingmachines.ai/blog/the-future-worth-building-is-human/>
- **Why it matters (analysis):** This is a specific organization-level product
  and alignment philosophy that could differentiate how Thinking Machines
  designs customizable models and open components.
- **Investment implication (analysis):** The thesis suggests a strategy built
  around model plurality and customer adaptation rather than a single
  universal assistant, which changes the likely product surface and route to
  enterprise adoption.
- **AI-engineering implication (analysis):** The approach implies evaluation
  and deployment infrastructure that can preserve local behavior and compare
  multiple models without collapsing them into one averaged policy.

## Rank 12 — Thibault Sottiaux / post-launch corrections

- **Outcome:** `insight`
- **Claim:** OpenAI's Thibault Sottiaux acknowledged that the ChatGPT Work and
  Codex launch introduced regressions in existing multi-agent workflows and
  rough edges in plugins.
- **Exact supporting quote:** “And we introduced regressions for some existing
  multi-agent workflows, alongside a collection of rough edges in plugins and
  other parts of the experience.”
- **Evidence:** authored X post `2075641131002700120`,
  <https://x.com/thsottiaux/status/2075641131002700120>
- **Why it matters (analysis):** The post turns broad launch reaction into a
  first-party incident report with named workflow failures and a stated repair
  plan.
- **Investment implication (analysis):** Rapid correction can protect adoption,
  but the regressions show that consolidating agent products carries migration
  and usability risk for existing power users.
- **AI-engineering implication (analysis):** Teams depending on multi-agent or
  plugin workflows should treat major client updates as compatibility events
  and maintain regression tests around model selection, submissions, and
  agent orchestration.

## Rank 18 — Sebastian Raschka / price-performance comparison

- **Outcome:** `insight`
- **Claim:** Sebastian Raschka reported that Grok 4.5 appeared to sit on the
  cost-performance Pareto frontier in his updated comparison.
- **Exact supporting quote:** “Grok 4.5 seems to sit at the Pareto frontier.
  Good bang for the buck.”
- **Evidence:** authored X post `2075982283509571666`,
  <https://x.com/rasbt/status/2075982283509571666>
- **Why it matters (analysis):** The observation is a concrete comparative
  signal about model economics, while remaining explicitly attributable to
  the author's harness and interpretation.
- **Investment implication (analysis):** Competitive advantage may shift toward
  providers that improve useful performance per dollar rather than only the
  maximum benchmark score.
- **AI-engineering implication (analysis):** Model selection should be checked
  against the disclosed harness and workload mix before generalizing the
  author's Pareto-frontier observation to production.

## Rank 32 — Karan Singhal / GPT-5.6 health evaluation

- **Outcome:** `insight`
- **Claim:** OpenAI's Karan Singhal reported that blinded physician reviewers
  found fewer flaws in GPT-5.6 responses than in physician-written responses
  for the supplied health-evaluation task set.
- **Exact supporting quote:** “Another especially cool result: physicians
  found fewer flaws in GPT-5.6 responses than physician-written responses.”
- **Evidence:** authored X post `2075689779937833302`,
  <https://x.com/thekaransinghal/status/2075689779937833302>
- **Why it matters (analysis):** The claim describes a human-comparator result
  and supplies meaningful evaluation details, but it remains a first-party
  report whose task sampling and full result tables require inspection.
- **Investment implication (analysis):** Stronger performance at lower serving
  cost could widen health-product adoption if the result holds across real
  clinical workflows and regulatory scrutiny.
- **AI-engineering implication (analysis):** Reproduction should preserve the
  specialty matching, source blinding, five review axes, difficult-task
  sampling, and aggregation over 20,000 axis ratings described in the thread.

## Acceptance use

The runtime passes this oracle only when:

1. every returned quote binds exactly to one frozen supplied source;
2. the application supplies the source post or artifact identity and URL;
3. claims preserve attribution and do not promote first-party reports into
   independently established facts;
4. persona implications remain explicitly analytical; and
5. a rerun with the same input makes no duplicate model call.
