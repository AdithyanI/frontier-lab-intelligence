# Frontier Lab Intelligence — Agent Guide

Frontier Lab Intelligence: a system that tracks frontier AI labs and their key
people, extracts and scores signal from their public output, and delivers
reports + alerts to investment and AI-team personas. Origin: BIT Capital
AI Engineer case study; built as a real product intended to outlive it.

## Operating model
- Human sets intent and approves external submission; agents implement, validate, and maintain docs.
- **Budget: do not over-optimize.** The €100 API budget is not a binding design constraint (Adi, 2026-07-08). Don't design around cost minimization or repeatedly raise cost trade-offs; just log spend in the working log and move on. Revisit only if actual spend approaches the ceiling.
- **Data first.** Current build philosophy (Adi, 2026-07-08): get real data flowing and visible before designing schemas/abstractions on top of it. Fetch raw → inspect → model from evidence, not theory. The modeled DB schema is intentionally not locked yet.
- **Do not import Dobby machinery.** This repo may use Adi's agent-native habits (tracker, docs, checks, working log), but it is not a Dobby/person-memory workspace. Keep personal-agent architecture in `~/GitHub/adi`/`~/GitHub/agents`, not here.
- Work from `docs/projects/frontier-lab-intelligence/tasks.md` as the canonical tracker.
- Preserve the original prompt in `docs/references/case-prompt.md`; do not rely on chat memory.
- Do not send, upload, message, publish, push to a public remote, or submit anything externally without explicit Adi approval in the current session.
- Put scratch files in `tmp/`; keep durable notes in `docs/references/`.
- Run `scripts/check-fast.sh` before handoff; if a check is skipped, record why in the tracker.

## Standing contracts
- **Builder context.** Read `docs/references/builder-context.md` to know who
  Adi is, what he knows, and what he is learning. Calibrate explanations and
  learning entries to that background (systems engineer, not data scientist).
- **Dual purpose, cleanup later.** Until submission this repo is both Adi's
  learning workbench and the future submission. Rich/private context is
  allowed now, but keep it in clearly marked sections/files (never scattered
  in code comments or commit messages) so the Phase 4 pre-submission cleanup
  pass can strip it cleanly.
- **Learning log — do → learn.** Adi is learning data science through this
  build. Any DS/ML technique used in a change (scoring models, validation,
  ground truth, ranking metrics, calibration, …) gets a plain-words entry in
  `docs/learning/` in the same change. Contract: `docs/learning/README.md`.
- **Working log.** Record AI-tool usage per session and every euro of the
  €100 API budget in `docs/references/working-log.md`. BIT will explicitly
  ask "how you worked"; the log is the answer.
- **Design system.** `PRODUCT.md` and `DESIGN.md` at repo root govern all UI
  work (impeccable-compatible). The web UI is 5% of the rubric; keep it light.

## Skill routing
- Repo cleanliness / agent-native harness questions: use
  `$agent-native-repo-playbook`.
- Tracker refresh, current batch planning, or long-running execution state:
  use `$project`.
- UI review or frontend polish: use `$impeccable`, but defer this until real
  registry/insight/report data exists.
- Cross-repo personal Dobby architecture (`~/GitHub/adi`, `~/GitHub/agents`,
  hooks, memory, workspace ownership): read `dobby-system` only when the work
  actually crosses that boundary. Do not copy Dobby's personal-memory system
  into this product repo.

## Source-of-truth order
1. `docs/references/case-prompt.md` — original external requirements from BIT/Lars.
2. `docs/projects/frontier-lab-intelligence/tasks.md` — current plan, status, blockers, and validation evidence.
3. `docs/references/*` — durable assumptions, sources, design notes, and reviewer instructions.
4. Chat/session context — useful only after captured into repo docs.

If repo docs conflict with chat memory, preserve the conflict in the tracker and follow the captured prompt until Adi decides otherwise.

## Docs contract
- `docs/architecture/overview.md` is the living visual map (Mermaid): pipeline, funnel, data model, repo layout, module status. Any change to system shape updates it in the same change.
- `docs/projects/frontier-lab-intelligence/tasks.md` is active execution state only.
- `docs/references/case-prompt.md` stores the original prompt and submission instructions verbatim.
- `docs/references/bit-context.md` stores submission-safe company/role context.
- `docs/references/builder-context.md` stores who Adi is, his background, learning goals, and how to calibrate explanations. Mixed private/submission-safe; cleaned at Phase 4.
- `docs/references/assumptions.md` stores assumptions, interpretation choices, and why they were made.
- `docs/references/sources.md` stores source links and provenance for factual/company/market claims.
- `docs/references/working-log.md` stores AI-tool usage and budget spend.
- `docs/references/reviewer-guide.md` stores the final review path: commands, expected outputs, files to inspect, and submission package.
- `docs/learning/` stores plain-words entries for DS/ML concepts as they are used.
- Architecture/design explanations belong in `docs/references/solution-architecture.md` or `docs/references/solution-memo.md`, not in `AGENTS.md`.

## Confidentiality and data handling
- Treat Lars's prompt, attachments, and provided data as private case-study material.
- Do not publish, push to a public remote, paste into public tools, or reuse externally unless the prompt explicitly allows it and Adi approves.
- Do not commit large/private raw data unless the prompt permits it; prefer `data/README.md` plus local ignored data paths.
- Record data provenance and allowed usage in `docs/references/sources.md` or `docs/references/data-notes.md`.

## Quality bar
- Prefer small, working, inspectable deliverables over broad architecture.
- Make assumptions explicit.
- Include provenance for factual/market/company claims.
- Include evals/monitoring/failure-mode thinking for LLM/agentic systems.
- Keep investment decisions human-in-the-loop.
- Avoid dashboard-only or toy-demo work unless the prompt specifically asks for it.

## Submission guardrail
Agents may prepare drafts, packages, and instructions, but must not email, upload, submit forms, publish, push to public remote, or message BIT/Lars/Marc/Vlad without Adi's explicit approval.

Before asking Adi to approve submission, produce:
- exact files/artifacts to submit;
- exact proposed message/email text, if any;
- validation evidence;
- known limitations;
- confirmation that every explicit prompt requirement was checked.
