# Daily Intelligence Agent Contract

The daily-intelligence boundary turns one frozen day of routed-positive Events
into a small, cited, audience-specific brief. A Codex agent owns open-ended
research and editorial judgment. Repository code owns evidence freezing,
schema validation, complete candidate disposition, atomic persistence, and the
read projection used by the product.

The repo-local [`$fli-daily-intelligence`](../../.agents/skills/fli-daily-intelligence/SKILL.md)
skill is the executable playbook. This document records the durable system
contract behind it.

## Flow

```text
current routed-positive Events for one UTC day
  -> immutable workspace and manifest
  -> agent research across packets, artifacts, context, and the web
  -> one strict draft containing both audiences
  -> deterministic validation and complete candidate disposition
  -> atomic imported daily run
  -> /api/insights canonical daily read projection
  -> Investment or AI Engineering reader
```

There is no first-class `Development` row. Several Events can support one
Insight through explicit evidence roles. The Event remains the frozen evidence
unit; the Insight is the reader-facing judgment.

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
shown once in the reader rather than repeated per company. AI Engineering analysis records
the system surface, technical implication, action, bounded experiment, success
metric, stop condition, and constraints.

The authoritative machine shape and enums are returned by:

```bash
.venv/bin/fli daily-intelligence contract --json --no-input
```

The Investment context command returns the structured
`bit-investment-context-v1` packet; the Engineering context remains markdown in
the same stable response envelope.

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
index, and import operations.

The normal run is:

```bash
.venv/bin/fli daily-intelligence context --audience investment --json --no-input
.venv/bin/fli daily-intelligence context --audience ai_engineering --json --no-input
.venv/bin/fli daily-intelligence prepare --day YYYY-MM-DD --json --no-input
.venv/bin/fli daily-intelligence validate --workspace <workspace> --draft <workspace>/draft.json --json --no-input
.venv/bin/fli daily-intelligence import-result --workspace <workspace> --draft <workspace>/draft.json --json --no-input
.venv/bin/fli daily-intelligence inspect-run --run-id <run-id> --json --no-input
```

The agent may use `search` and `inspect-event` while researching. `index` and
`similar` are optional for paraphrase discovery or larger cross-day work. The
embedding cache is a sidecar keyed by Event ID, rendered packet contract and
hash, model, and input hash. It never mutates the immutable Event packet and
never becomes grouping truth.

## Storage and Read Rules

Workspaces live under `data/derived/daily-intelligence/workspaces/`. The durable
ignored SQLite store is `data/derived/daily-intelligence/editorial.db`.

An import succeeds only after the draft matches the exact workspace manifest,
passes the audience schema, and accounts for the entire routed-positive cohort.
The normalized run, candidates, Insights, dispositions, Event provenance, and
citations are written in one transaction. Reimporting the identical result is a
no-op; a conflicting result cannot overwrite the existing run identity.

For a date with a complete imported run, `/api/insights` returns that run for
the requested audience in editorial rank order. The frontend reads only this
normalized backend projection; it never loads `draft.json` or SQLite directly.
Candidate-level Insight decisions remain an audit fallback for dates without an
imported run and for explicit suppressed/all inspection. A complete imported
run wins even when it selected zero Insights for an audience.

The canonical Investment reader shows the conclusion-led title, facts, one
investment interpretation, company read-through, confirmation/challenge
signals, and two source columns: exact original Feed Events and supporting
artifacts/context. Brief rank opens an inline explanation of the item-specific
rationale and shared qualitative rubric. Evidence roles and citation provenance remain stored even
though the reader does not expose the authoring scaffolding.

No run schedules itself or performs publication, submission, alert delivery,
or another external action. Those remain separately authorized operations.
