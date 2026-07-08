# Working Log — AI tools and budget

BIT explicitly said: "Use any AI coding tools you want. We expect you to, and
we'll ask how you worked." This log is the answer to that question, kept as we
go rather than reconstructed at the end. It also tracks the €100 API/services
budget (reimbursable with receipts; they are interested in how it is spent).

## How this project is being built (living summary)

- Harness: agent-native repo driven by coding agents (Codex/Claude-family)
  with a human (Adi) setting intent, reviewing, and approving all external
  effects. Canonical tracker: `docs/projects/frontier-lab-intelligence/tasks.md`.
- Agents implement, validate, and document; repo docs are the source of truth
  over chat memory; `scripts/check-fast.sh` gates handoffs.
- (Update this section as the workflow evolves: subagent patterns, eval loops,
  prompt-iteration workflow, etc.)

## Session log

Append one row per meaningful working session.

| Date | Driver | What was done | AI tools used | Notes |
| --- | --- | --- | --- | --- |
| 2026-07-07 | Dobby (Codex CLI) | Repo scaffolded from agent-native template; prompt captured verbatim | GitHub Copilot CLI (Claude) | Pre-code setup |
| 2026-07-08 | Dobby (Codex CLI) | Renamed repo to frontier-lab-intelligence; added PRODUCT.md + DESIGN.md (impeccable-seeded), bit-context.md, learning-log contract, this working log; rebuilt tracker with weighted execution plan | GitHub Copilot CLI (Claude), impeccable skill | Setup complete; next: Phase 0 design pass |

## Budget log (€100 ceiling)

Keep receipts. Every spend gets a row and a stated reason.

| Date | Service | Amount | Why | Receipt |
| --- | --- | --- | --- | --- |
| — | — | €0.00 | nothing spent yet | — |

Running total: **€0.00 / €100.00**
