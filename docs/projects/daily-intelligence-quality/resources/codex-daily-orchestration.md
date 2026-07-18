# Codex Daily Orchestration Contract

## Purpose

Prove one narrow end-to-end handoff for a requested date:

1. run the repository's existing deterministic evidence refresh;
2. freeze the date's audience routing;
3. prepare the immutable daily-intelligence workspace;
4. inspect and checkpoint the exact identifiers;
5. optionally start one visible Codex Desktop task that performs the existing
   `$fli-daily-intelligence` workflow.

The command orchestrates existing owners. It does not reimplement evidence,
routing, editorial validation, or editorial persistence.

## V1 Command Contract

- One ISO `--day` is required.
- JSON is the default machine contract; `--plain` is an inspection convenience.
- `--no-input` is supported and normal operation never prompts.
- The default command stops after workspace preparation; `--launch-codex`
  explicitly crosses into agent execution.
- Repeating the same date reuses completed compatible stages rather than
  creating duplicate work or a second Codex task.
- Workspace v3 is the only launchable workspace contract. Obsolete packets are
  never upgraded or rebound to a task; preparation creates a fresh current
  packet before launch.
- A complete imported editorial run for the exact workspace is terminal. The
  ledger closes from that row before opening App Server, even if the original
  task has since been reused for unrelated human review.
- Codex model, reasoning effort, and service tier are optional per-launch
  overrides. Omitted values inherit normal Codex configuration; the exact
  effective tuple returned by App Server is frozen before goal work continues.
- A resume sends no model-setting overrides. It compares the task's effective
  tuple with the frozen checkpoint and fails before naming, goal, or turn work
  if the task has changed.
- Failures return stable codes, retryability, and the last durable stage.
- Progress goes to stderr; the final structured result goes to stdout.

## Codex Handoff

Use a short-lived stdio `codex app-server` child and the stable protocol:

1. `initialize`, then `initialized`;
2. `thread/start` with:
   - `cwd=/Users/dobby/GitHub/frontier-lab-intelligence`;
   - `ephemeral=false`;
   - a stable service name;
   - optional `model` and `serviceTier` overrides;
3. `thread/name/set` with `FLI Daily Brief — YYYY-MM-DD`;
4. `turn/start` with the complete objective, prepared workspace, explicit
   skill invocation, and optional `model`, `effort`, and `serviceTier`
   overrides;
5. after that turn is running, `thread/goal/set` with the same active objective
   (the persisted equivalent of `/goal`);
6. follow native goal continuation turns until the goal is terminal, then
   inspect the exact durable editorial run.

App Server exposes the exact thread `cwd`, not a project-assignment parameter.
Codex Desktop separately derives and records its local project association from
that exact path. The live canary therefore verifies the UI association instead
of assuming it from the protocol alone. The initial turn is started immediately
so the task is a normal visible conversation rather than an empty thread.

The order matters: activating a goal on an idle thread can auto-start a native
continuation. Starting the explicit first turn before activating the goal avoids
racing two turns while still giving the task the full objective in context.

## Canary Order

1. Run the command for one new date with the Codex handoff disabled.
2. Inspect evidence, routing, workspace, and ledger identifiers.
3. Enable the App Server handoff for that same date.
4. Confirm the named task appears under `frontier-lab-intelligence` in Codex
   Desktop and that its thread id is stored with the orchestration record.
5. Wait for completion and inspect the imported daily run and UI.

```bash
.venv/bin/fli daily-intelligence run-day \
  --day 2026-07-16 --json --no-input

.venv/bin/fli daily-intelligence run-day \
  --day 2026-07-16 --launch-codex \
  --codex-model gpt-5.6-sol \
  --codex-reasoning-effort xhigh \
  --codex-service-tier fast \
  --json --no-input
```

`fast` is the operator-facing alias for the current App Server catalog tier
`priority`; the ledger stores the canonical value returned by App Server.

## Explicitly Deferred

- schedules and background automation;
- multi-day parallel task creation;
- a permanent App Server daemon or WebSocket transport;
- an SDK wrapper;
- automatic editorial retries beyond the persisted Codex goal;
- redesigning any deterministic stage owned by the existing FLI clients.
