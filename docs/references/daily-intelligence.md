# Daily Intelligence Agent Contract

The daily-intelligence boundary turns one frozen day of routed-positive Events
into a small, cited, audience-specific brief. A Codex agent owns open-ended
research and editorial judgment. Repository code owns evidence freezing,
schema validation, complete candidate disposition, atomic persistence, and the
read projection used by the product.

The repo-local [`$fli-daily-intelligence`](../../.agents/skills/fli-daily-intelligence/SKILL.md)
skill is the executable playbook. This document records the durable system
contract behind it.

The first multi-day editorial evaluation is preserved in
[`daily-intelligence-batch-audit-2026-07-05-17.md`](daily-intelligence-batch-audit-2026-07-05-17.md).
The five-Insight submission proof is editorially locked in the archived
[`submission selection`](../projects/archive/daily-intelligence-quality/resources/submission-proof-selection-2026-07-19.md);
the complete reader remains the audit corpus rather than the reviewer entry
point.
It records batch quality and proposed improvements but does not change this
contract by itself.

## Flow

```text
current routed-positive Events for one UTC day
  -> seven-day first-party X evidence projection
  -> immutable workspace and manifest
  -> agent research across packets, artifacts, context, and the web
  -> one strict draft containing both audiences
  -> deterministic validation and complete candidate disposition
  -> atomic imported daily run
  -> /api/insights canonical daily read projection
  -> Investment or AI Engineering reader
```

## One-Day Command Boundary

The date-keyed runner is the reproducible entry point:

```bash
.venv/bin/fli daily-intelligence run-day \
  --day YYYY-MM-DD --json --no-input
```

As written, it collects or reuses the dated Evidence state, runs or reuses the
top-ranked audience-routing decisions, freezes the union-positive cohort into
one immutable workspace, and stops at `prepare`. It does not launch an
editorial model.

Add `--launch-codex` to create or resume the one persisted Codex App Server
task bound to that exact workspace. The task follows this skill, researches
the complete cohort, writes both audience briefs, passes coverage preflight and
deterministic validation, imports the result atomically, and inspects the
durable run before completion. Each stage is checkpointed in the date-keyed
orchestration ledger, so retrying the same command resumes the same run rather
than creating a second brief.

There is no first-class `Development` row. Several Events can support one
Insight through explicit evidence roles. The Event remains the frozen evidence
unit; the Insight is the reader-facing judgment.

The daily workspace is a conservative semantic projection, not a raw-data
store. It keeps first-party X sources published on the brief day or the seven
preceding calendar days. When an older root has a current same-author quote or
reply, the current source becomes the workspace root. When no eligible
first-party X source remains, the routed candidate is omitted. Raw Feed and
Event history remains intact for audit. Artifact publication chronology stays
separate: neither retrieval time nor link time proves when the artifact itself
was published. The linking post does establish when that artifact became
available to the Event. The workspace preserves every attached artifact and
projects its exact stored disclosure lineage; the agent audits whether it was
available by the brief day and whether it supports the claim. When a packet is pruned,
inherited routing prose and prior per-Event
annotations are withheld because they may describe evidence that is no longer
in the workspace; the positive audience route remains only as a recall cue for
fresh editorial judgment.

## Insight Schema

Every Insight has:

- a contiguous audience-local `rank` starting at one and a concise
  `rank_rationale` explaining that relative priority;
- a judgment-led `title`;
- attributable `what_changed` facts;
- one audience-specific `interpretation` that carries the complete causal
  argument rather than exposing intermediate reasoning fields;
- one concrete `next_step`;
- audience-specific `analysis`;
- exact Event links with `primary`, `supporting`, `context`, or
  `counterevidence` roles; and
- ordered citations to frozen Events, artifacts, public context, or bounded web
  research.

Investment analysis records company mappings as `portfolio` or
`outside_portfolio`, a directional impact and mechanism for each, one key
uncertainty, and one to three measurable watchpoints. The interpretation itself
connects evidence through the operating and financial drivers to the thesis
consequence. The skill-owned BIT packet holds the complete audited portfolio,
public thesis, research process, source cautions, and the date/source disclosure
shown once in the reader rather than repeated per company. AI Engineering uses
the common interpretation plus one bounded `next_step`; its only additional
field is a concise `decision_rule` combining the measurable proceed and stop
conditions.

The authoritative machine shape and enums are returned by:

```bash
.venv/bin/fli daily-intelligence contract --json --no-input
```

The Investment context command returns the structured
`bit-investment-context-v2` packet; the Engineering context remains markdown in
the same stable response envelope.

The Engineering context encodes BIT's publicly described Aion and data-platform
operating mandate plus a current/near-term relevance map. It is a reader lens,
not a claim about BIT's private architecture. An Engineering Insight must change
a concrete research-agent, signal-production, evaluation, LLMOps, or supporting
data-platform decision; technical novelty alone is a valid reason for
`not_selected`.

Version 2 includes one reusable profile for every company in the working
portfolio baseline. Profiles keep attributable BIT views separate from FLI
analyst context and provide stable company identity, operating drivers,
two-sided frontier-AI exposure channels, and watchpoints. They reduce repeated
background research without deciding the impact of a daily development. BIT
views also carry a source scope so firm-wide or other-product commentary cannot
be mistaken for this flagship strategy's thesis.

Daily agents load the compact Investment projection first, then retrieve only
the matching company profiles by exact canonical name, ticker, or alias:

```bash
.venv/bin/fli daily-intelligence context \
  --audience investment --compact --json --no-input
.venv/bin/fli daily-intelligence company-context \
  --company MSFT --json --no-input
```

The full context command remains available for audit. Both projections carry
the same canonical packet path and SHA-256; the lookup returns the matched
profile, its working portfolio row, match type, and profile review date.

## Coverage and Selection

Every positively routed Event/audience pair must appear exactly once: either in
one selected Insight or in `not_selected` with a concrete reason. This proves
that sparse output came from reviewing the full cohort rather than silently
ignoring candidates. It does not require weak material to be published.

Keep every decision-useful Insight supported by the day, while preferring
precision over padding. Rank is an ordinal editorial priority based on decision
consequence, evidence strength, time sensitivity, actionability, and novelty.
It is not Feed rank, an embedding score, popularity, or a learned numerical
score. The stored rationale makes the qualitative choice inspectable without
inventing a synthetic formula. Selecting the strongest three to five for a submission is a separate
downstream decision, not a storage limit.

Group Events only when they support one coherent audience conclusion, causal
chain, and next action. Shared canonical artifacts are strong deterministic
relationship evidence. Text and vector similarity are retrieval aids. Neither
automatically merges Events.

## Agent Client

The client is machine-primary and defaults to one versioned JSON object with
`schema_version`, `command`, `status`, `data`, `error`, and `meta`. It supports
`--no-input`, stable error codes and exit codes, explicit `--plain` inspection,
timeouts for remote embedding work, dry-run for import, and idempotent prepare,
index, and import operations. `preflight` provides a read-only coverage ledger
for the draft: one row per expected Event/audience pair, its included or
`not_selected` disposition, and explicit missing, duplicate, or unexpected
counts. It does not replace validation or make editorial decisions.

`import-result` and `inspect-run` accept additive `--projection` values:
`summary`, `insights`, `citations`, and `dispositions`. Their default remains
`full`, preserving the existing complete payload contract. Agents should use
the smallest projection that answers the current question.

### Future-agent discovery and enforcement

This workflow is intentionally durable at four layers:

- root `AGENTS.md` routes generation, review, and reruns to the repo-local
  `$fli-daily-intelligence` skill;
- that skill requires `preflight` before validation and compact run inspection
  after import;
- this reference preserves the exact client behavior and commands;
- CLI regression tests run under `scripts/check-fast.sh`, so the shared Stop
  hook catches broken coverage or projection contracts without owning or
  executing the editorial workflow itself.

Do not duplicate these details in hook configuration. The hook is a validation
boundary; the skill and this reference are the operating contract.

The normal run is:

```bash
.venv/bin/fli daily-intelligence context --audience investment --json --no-input
.venv/bin/fli daily-intelligence context --audience ai_engineering --json --no-input
.venv/bin/fli daily-intelligence prepare --day YYYY-MM-DD --json --no-input
.venv/bin/fli daily-intelligence preflight --workspace <workspace> --draft <workspace>/draft.json --json --no-input
.venv/bin/fli daily-intelligence validate --workspace <workspace> --draft <workspace>/draft.json --json --no-input
.venv/bin/fli daily-intelligence import-result --workspace <workspace> --draft <workspace>/draft.json --json --no-input
.venv/bin/fli daily-intelligence inspect-run --run-id <run-id> --projection summary --json --no-input
```

The date-keyed orchestration entry point composes the existing Evidence,
routing, and workspace owners without replacing them:

```bash
.venv/bin/fli daily-intelligence run-day --day YYYY-MM-DD --json --no-input
.venv/bin/fli daily-intelligence inspect-day-run --day YYYY-MM-DD --json --no-input
.venv/bin/fli daily-intelligence run-day --day YYYY-MM-DD --launch-codex --json --no-input
.venv/bin/fli daily-intelligence run-day --day YYYY-MM-DD --launch-codex \
  --codex-model gpt-5.6-sol --codex-reasoning-effort xhigh \
  --json --no-input
.venv/bin/fli daily-intelligence run-batch \
  --through 2026-07-21 --days 17 --day-workers 3 \
  --codex-model gpt-5.6-sol --codex-reasoning-effort xhigh \
  --codex-service-tier standard --json --no-input
```

The default stops at a validated workspace. `--launch-codex` starts one named,
non-ephemeral task through a short-lived Codex App Server client and records the
exact Evidence, routing, workspace, task, and editorial-run identities in the
same editorial store. Retries reuse completed deterministic stages. If a
complete editorial run already exists for the workspace, that durable import
closes orchestration before any App Server connection is opened; a task that
the user later reuses for review is never resumed as pipeline work.

Codex model and reasoning selection are explicit but optional:
`--codex-model` and `--codex-reasoning-effort` inherit normal Codex
user/project configuration when omitted. Service speed is deliberately
different: `--codex-service-tier` defaults to `standard`, and the runner sends
App Server the explicit canonical `serviceTier: "default"` value that clears
any inherited Fast tier. `normal` and `default` are accepted operator aliases
for `standard`; `fast`
remains an explicit opt-in and is normalized to App Server's `priority` tier.
App Server reports the effective model, reasoning effort, and tier, and the
runner freezes that tuple in the day checkpoint.
Retries resume without sending overrides and first verify that the persisted
task still has the frozen tuple; a task whose settings changed is left
untouched rather than silently changed back.

`run-day` is the one-date entry point. `run-batch` is the historical
parallelism boundary: it selects one complete current routing run per day,
requires `daily-rank-v2`, records a separate `daily-orchestration-v2` lineage
for each date, and launches at most four independent days concurrently.
Its Evidence stage owns the single global Feed/Event publication pointer, so
several full `run-day` commands for different dates must not publish
concurrently. For an all-date rerun, publish Evidence once through the maximum
date, run one multi-day `audience-routing refresh` against that exact
publication, then use `run-batch` to prepare and launch one immutable
workspace/task per date in parallel. The routing batch automatically reuses compatible predecessor rows
only when Event ID, evidence SHA, and rendered input SHA are exact; it records
the predecessor run and reports resumed rows, exact reuses, and new model
requests separately. This makes later global snapshots cheap without weakening
lineage or copying stale judgments. Do not use routing `--replace` during an
overlapping or parallel batch.

The active goal owns the main Codex turns. The runner waits for both the goal's
terminal status and its final turn's terminal status; it never treats an early
`goal: complete` notification as permission to interrupt the finishing turn.
After a complete goal and completed final turn, the runner clears the completed
goal and sends one ordinary text-only follow-up in the same visible task. That
turn writes a short, candid harness reflection to
`data/derived/daily-intelligence/agent-feedback/YYYY-MM-DD.md`. It may identify
friction, missing tools or context, improvements, and unexpected wishes from
the concrete run. This reflection is local, non-authoritative, and never an
input to the brief. It cannot reopen the completed goal or modify the imported
run, and a missing or failed reflection never invalidates a completed brief.
The task remains a normal inspectable Codex conversation.

The agent may use `search` and `inspect-event` while researching. `index` and
`similar` are optional for paraphrase discovery or larger cross-day work. The
embedding cache is a sidecar keyed by Event ID, rendered packet contract and
hash, model, and input hash. It never mutates the immutable Event packet and
never becomes grouping truth.

Editorial grouping defaults distinct developments to separate Insights or
`not_selected`. Before validation, the agent states each selected Insight's
single core claim and removes any Event or citation that does not support or
challenge that same causal mechanism and audience decision. Comparable evidence
must examine a genuinely comparable subject and workload. Complete cohort
accounting is satisfied by explicit non-selection; it never requires widening
an Insight around a shared topic.

Investment impact direction must come from development-specific evidence;
generic company context establishes exposure but defaults to `uncertain`.
Engineering decision thresholds come from baselines or operating constraints,
or remain explicitly provisional, and bundled interventions are staged or
ablated when the result needs causal attribution.

## Storage and Read Rules

Workspaces live under `data/derived/daily-intelligence/workspaces/`. The durable
ignored SQLite store is `data/derived/daily-intelligence/editorial.db`.

An import succeeds only after the draft matches the exact workspace manifest,
passes the audience schema, and accounts for the entire routed-positive cohort.
Workspace v3 is the only executable workspace contract. Its cohort means the routed-positive candidates remaining
after the seven-day X-source projection, with Event snapshots identified by
`semantic_snapshot_sha256`. Earlier workspace packets may remain as historical
files, but no command reads, upgrades, or resumes them; new work must prepare a
fresh v3 workspace. Retained X sources carry their
application-owned publication times; Event citations inherit that date and a
conflicting agent-supplied date fails validation.
Artifacts retain inspectable disclosure lineage. An artifact citation must
identify the exact frozen Event artifact, include a short excerpt occurring in
the frozen text, and explain the specific claim that passage supports. Artifact
attachment alone never makes it a valid citation.
The normalized run, candidates, Insights, dispositions, Event provenance, and
citations are written in one transaction. Reimporting the identical result is a
no-op; a conflicting result cannot overwrite the existing run identity.

For a date with a complete imported run, `/api/insights` returns that run for
the requested audience in editorial rank order. The frontend reads only this
normalized backend projection; it never loads `draft.json` or SQLite directly.
Candidate-level Insight decisions remain an audit fallback for dates without an
imported run and for explicit suppressed/all inspection. A complete imported
run wins even when it selected zero Insights for an audience.

`GET /api/insights/report.pdf?audience=<audience>&date=<YYYY-MM-DD>` renders
only that canonical complete projection. It returns 404 for an unavailable or
non-editorial day, `application/pdf` with an audience/date filename otherwise,
and emits `ETag`, `X-FLI-PDF-Cache`, and `X-FLI-Report-Version` headers.
Conditional requests may return 304. The server-side cache is content-addressed
by report schema, read schema, date, audience, and imported result hash and is
written atomically; it never reads drafts or authors new report content.

The canonical Investment reader shows the conclusion-led title, facts, one
investment interpretation, company read-through, confirmation/challenge
signals, and two source columns: exact original Feed Events and supporting
artifacts/context. Brief rank opens an inline explanation of the item-specific
rationale and shared qualitative rubric. Evidence roles and citation provenance remain stored even
though the reader does not expose the authoring scaffolding.

No run schedules itself or performs publication, submission, alert delivery,
or another external action. Those remain separately authorized operations.
