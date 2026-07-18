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
- Codex model and reasoning effort are optional per-launch overrides; omitted
  values inherit normal Codex configuration. Service tier defaults to an
  explicit Standard override so user-level Fast configuration cannot leak into
  the run. The exact effective tuple returned by App Server is frozen before
  goal work continues.
- A resume sends no model-setting overrides. It compares the task's effective
  tuple with the frozen checkpoint and fails before naming, goal, or turn work
  if the task has changed.
- App Server notifications are scoped to the persisted parent thread; Ultra
  subagent turn notifications never replace parent activity. If a process is
  interrupted while the owned goal remains active and the parent is idle, a
  retry reactivates that same goal and lets Codex start its native continuation
  in the same task.
- Failures return stable codes, retryability, and the last durable stage.
- Progress goes to stderr; the final structured result goes to stdout.

## Codex Handoff

Use a short-lived stdio `codex app-server` child and the stable protocol:

1. `initialize`, then `initialized`;
2. `thread/start` with:
   - `cwd=/Users/dobby/GitHub/frontier-lab-intelligence`;
   - `ephemeral=false`;
   - a stable service name;
   - optional `model`, plus explicit `serviceTier: "default"` for Standard
     unless a different tier was requested;
3. `thread/name/set` with `FLI Daily Brief — YYYY-MM-DD`;
4. `thread/goal/get`, then `thread/goal/set` with one active objective that
   names the exact workspace, required skill, database, completion criteria,
   and execution instructions. Setting the goal starts its native first turn;
5. follow native goal continuation turns until both the goal is terminal and
   its final turn has emitted a terminal status. `goal: complete` alone is not
   enough because it can arrive before `turn/completed`;
6. inspect the exact durable editorial run;
7. after a complete goal and completed final turn, clear the completed goal and
   start one ordinary text-only follow-up in the same task that writes the
   local post-run harness reflection. Do not attach another goal, reopen
   editorial work, archive the task, or make reflection success a condition of
   brief success.

App Server exposes the exact thread `cwd`, not a project-assignment parameter.
Codex Desktop separately derives and records its local project association from
that exact path. The live canary therefore verifies the UI association instead
of assuming it from the protocol alone. The goal owns its turns; the client
must not manually start a competing first turn. Clearing a completed goal
before its final turn settles interrupts that turn, so the two terminal signals
form an explicit lifecycle boundary.

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
  --json --no-input
```

Routine launches explicitly use Standard service even when the surrounding
Codex configuration prefers Fast. The command defaults
`--codex-service-tier` to `standard`, which is sent to App Server as
`serviceTier: "default"`; `normal` and `default` are operator aliases. The optional value
`fast` remains an operator-facing alias for App Server's `priority` tier. The
ledger stores both the requested setting and the effective canonical value
returned by App Server.
App Server 0.144.5 reports the same Standard tier as `"default"` on launch and
`null` on resume; the client canonicalizes both responses to stored
`"default"` before comparing the frozen tuple.

## Explicitly Deferred

- schedules and background automation;
- multi-day parallel task creation;
- a permanent App Server daemon or WebSocket transport;
- an SDK wrapper;
- automatic editorial retries beyond the persisted Codex goal;
- redesigning any deterministic stage owned by the existing FLI clients.
