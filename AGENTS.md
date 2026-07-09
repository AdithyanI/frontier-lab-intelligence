# Frontier Lab Intelligence — Agent Guide

Frontier Lab Intelligence: a system that tracks frontier AI labs and their key
people, extracts and scores signal from their public output, and delivers
reports + alerts to investment and AI-team personas. Origin: BIT Capital
AI Engineer case study; built as a real product intended to outlive it.

## Operating model
- Human sets intent and approves external submission; agents implement, validate, and maintain docs.
- **Budget: do not over-optimize.** The €100 API budget is not a binding design constraint (Adi, 2026-07-08). Don't design around cost minimization or repeatedly raise cost trade-offs; just log spend in the build log and move on. Revisit only if actual spend approaches the ceiling.
- **Data first.** Current build philosophy (Adi, 2026-07-08): get real data flowing and visible before designing schemas/abstractions on top of it. Fetch raw → inspect → model from evidence, not theory. The modeled DB schema is intentionally not locked yet.
- **System principles (Adi, 2026-07-09), full text in `PRODUCT.md` §System Principles:** (1) high quality first, bend the cost curve later; (2) every pipeline stage is automatically done and human-correctable — LLM decides with cited reasons, human overrides are stored as data, no manual per-item approval gates; (3) human judgment enters as versioned bootstrap inputs (seed lists, rubrics, overrides), not as clicks in the loop.
- **Do not import Dobby machinery.** This repo may use Adi's agent-native habits (tracker, docs, checks, build log), but it is not a Dobby/person-memory workspace. Keep personal-agent architecture in `~/GitHub/adi`/`~/GitHub/agents`, not here.
- **Teach Adi as you build (Adi, 2026-07-09).** Adi is new to data-science/graph/entity-resolution concepts (entities, identities, entity resolution, PageRank, confidence scores, scoring models). Whenever a design uses a concept like this: (1) explain it in plain words with a concrete example (e.g. Karpathy's accounts → identity links → one entity) *before or while* building it, and (2) make the concept visible in the web UI's Architecture page as a visual explanation, not just prose. Adi needs to be able to defend every design choice in the on-site interview — chat explanations that never land in the repo/UI are lost.
- Work from `docs/projects/frontier-lab-intelligence/tasks.md` as the canonical tracker.
- Preserve the original prompt in `docs/references/case-prompt.md`; do not rely on chat memory.
- Do not send, upload, message, publish, push to a public remote, or submit anything externally without explicit Adi approval in the current session.
- Put scratch files in `tmp/`; keep durable notes in `docs/references/`.
- Run `scripts/check-fast.sh` before handoff; if a check is skipped, record why in the tracker.

## Standing contracts
- **Context.** Read `docs/references/context.md` to know BIT, the role, Adi's
  background, and private cleanup boundaries.
- **Build log.** After each meaningful chunk, update
  `docs/references/build-log.md` with intent, decision/action, evidence,
  impact/next step, tools used, and any spend. DS/ML learning notes now live
  there too.
- **Research notes.** Keep assumptions, provenance, and seed-source leads in
  `docs/references/research-notes.md`.
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
3. `docs/architecture/overview.md` — current architecture, stack, data shape, and module status.
4. `docs/references/context.md`, `docs/references/research-notes.md`, `docs/references/build-log.md` — durable context, facts, decisions, and build history.
5. Chat/session context — useful only after captured into repo docs.

If repo docs conflict with chat memory, preserve the conflict in the tracker and follow the captured prompt until Adi decides otherwise.

## Docs contract
- `docs/architecture/overview.md` is the single living architecture map:
  stack, pipeline, funnel, data artifacts, model sketch, module status.
- `docs/projects/frontier-lab-intelligence/tasks.md` is active execution state only.
- `docs/references/case-prompt.md` stores the original prompt and submission instructions; `docs/references/source-material/` stores the original PDF and OCR text.
- `docs/references/context.md` stores BIT/role context plus clearly marked private builder context for Phase 4 cleanup.
- `docs/references/research-notes.md` stores assumptions, source provenance, and seed-source leads.
- `docs/references/build-log.md` stores build history, AI-tool usage, budget spend, and DS/ML learning notes.
- `docs/references/reviewer-guide.md` stores the final review path: commands, expected outputs, files to inspect, and submission package.

## Confidentiality and data handling
- Treat Lars's prompt, attachments, and provided data as private case-study material.
- Do not publish, push to a public remote, paste into public tools, or reuse externally unless the prompt explicitly allows it and Adi approves.
- Do not commit large/private raw data unless the prompt permits it; prefer `data/README.md` plus local ignored data paths.
- Record data provenance and allowed usage in `docs/references/research-notes.md`.

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
