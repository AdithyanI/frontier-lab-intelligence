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
- A deterministic-only boundary stops after workspace preparation.
- Repeating the same date reuses completed compatible stages rather than
  creating duplicate work or a second Codex task.
- Failures return stable codes, retryability, and the last durable stage.
- Progress goes to stderr; the final structured result goes to stdout.

## Codex Handoff

Use a short-lived stdio `codex app-server` child and the stable protocol:

1. `initialize`, then `initialized`;
2. `thread/start` with:
   - `cwd=/Users/dobby/GitHub/frontier-lab-intelligence`;
   - `ephemeral=false`;
   - a stable service name;
3. `thread/name/set` with `FLI Daily Brief — YYYY-MM-DD`;
4. `thread/goal/set` with an active objective equivalent to `/goal`;
5. `turn/start` with the prepared workspace and explicit skill invocation;
6. stream until `turn/completed`, then inspect the durable editorial run.

The Desktop project association is path-based: persisted thread state records
the exact `cwd` and no separate project identifier. The initial turn is started
immediately so the task is a normal visible conversation rather than an empty
thread.

## Canary Order

1. Run the command for one new date with the Codex handoff disabled.
2. Inspect evidence, routing, workspace, and ledger identifiers.
3. Enable the App Server handoff for that same date.
4. Confirm the named task appears under `frontier-lab-intelligence` in Codex
   Desktop and that its thread id is stored with the orchestration record.
5. Wait for completion and inspect the imported daily run and UI.

## Explicitly Deferred

- schedules and background automation;
- multi-day parallel task creation;
- a permanent App Server daemon or WebSocket transport;
- an SDK wrapper;
- automatic editorial retries beyond the persisted Codex goal;
- redesigning any deterministic stage owned by the existing FLI clients.
