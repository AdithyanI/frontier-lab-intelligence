# BIT Capital Case Study — Agent Guide

This repo contains Adi's BIT Capital AI Engineer case-study work ("Frontier Lab
Intelligence": track frontier AI labs, extract/score signal from their public
output, deliver reports + alerts to investment and AI team personas).

## Operating model
- Human sets intent and approves external submission; agents implement, validate, and maintain docs.
- Work from `docs/projects/bit-capital-case-study/tasks.md` as the canonical tracker.
- Preserve the original prompt in `docs/references/case-prompt.md`; do not rely on chat memory.
- Do not send, upload, message, publish, push to a public remote, or submit anything externally without explicit Adi approval in the current session.
- Put scratch files in `tmp/`; keep durable notes in `docs/references/`.
- Run `scripts/check-fast.sh` before handoff; if a check is skipped, record why in the tracker.

## Source-of-truth order
1. `docs/references/case-prompt.md` — original external requirements from BIT/Lars.
2. `docs/projects/bit-capital-case-study/tasks.md` — current plan, status, blockers, and validation evidence.
3. `docs/references/*` — durable assumptions, sources, design notes, and reviewer instructions.
4. Chat/session context — useful only after captured into repo docs.

If repo docs conflict with chat memory, preserve the conflict in the tracker and follow the captured prompt until Adi decides otherwise.

## Docs contract
- `docs/projects/bit-capital-case-study/tasks.md` is active execution state only.
- `docs/references/case-prompt.md` stores the original prompt and submission instructions verbatim.
- `docs/references/assumptions.md` stores assumptions, interpretation choices, and why they were made.
- `docs/references/sources.md` stores source links and provenance for factual/company/market claims.
- `docs/references/reviewer-guide.md` stores the final review path: commands, expected outputs, files to inspect, and submission package.
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
