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
| 2026-07-08 | Dobby (Copilot CLI) | Renamed repo to frontier-lab-intelligence; added PRODUCT.md + DESIGN.md (impeccable-seeded), bit-context.md, learning-log contract, this working log; rebuilt tracker with weighted execution plan | GitHub Copilot CLI (Claude), impeccable skill | Setup complete; next: Phase 0 design pass |
| 2026-07-08 | Dobby (Copilot CLI, Fable 5) | Stack decision recorded (Python monolith + SQLite + FastAPI/Jinja2); package scaffolded (pyproject, src/fli, CLI stub, 2 tests passing); Phase 0 strawman designs drafted; 3 research sub-agents (smol.ai, Digg, landscape — 2× Fable 5, 1× Haiku) synthesized into prior-art section + design deltas in solution-architecture.md | GitHub Copilot CLI (Fable 5 main + research sub-agents) | Model-per-subagent cost discussed; Adi chose not to encode a policy for now. Pending: Phase 0 sign-off decisions (lab seeds, labeling appetite, X ingestion) |
| 2026-07-08 | Dobby (Copilot CLI, Fable 5) | Living architecture doc (Mermaid) + AGENTS.md contract; web UI shell (`fli web`, FastAPI + Jinja2, DESIGN.md tokens) with /architecture rendering the diagrams; impeccable polish pass on home (fonts, panels, empty states, status table); 5 tests green, headless-browser visual verification | GitHub Copilot CLI (Fable 5), impeccable skill, Playwright headless | UI kept deliberately light per rubric (5%) |
| 2026-07-08 (data-first spike) | Dobby (Copilot CLI) | Built `fli.store`/`fli.fetch`; ran `fli fetch` across 3 labs (blog RSS/sitemap, arXiv, GitHub releases) — 1,599 raw items landed in `data/fli.db`. Fixed Anthropic (no RSS feed exists; added sitemap `/news/` fallback). Inspected real payload samples together; found 3 concrete design lessons: arXiv name-search gives false positives (need author-based matching, not text search), blog feeds mix marketing with signal (confirms need for content classification), GitHub release `author` fields give real handles for registry discovery | GitHub Copilot CLI (Sonnet 5) | Adi requested data-before-schema; samples reviewed together before any modeled schema written |
| 2026-07-08 (registry bootstrap) | Dobby (Copilot CLI) | Extracted candidate people from our own raw data (arXiv co-authors, GitHub release/org authors — found real researchers e.g. Trieu H. Trinh, Cordelia Schmid, tomhennigan; also found `github-actions[bot]` noise, confirming a bot-filter is needed). Researched Digg's & smol.ai's list-building methods (X pricing, follow-graph economics: reading a person's followers costs $0.01/follower — expensive at scale; reading who *they follow* is cheap, ~$10-20/anchor, and is the actual bootstrap trick). Scraped Digg's live rankings page (Playwright, 20 scrolls → 700 ranked people/companies; page's own "About the rankings" text confirms: built from ~9M X follow relationships, algorithmic not hand-curated) and mined smol.ai's public tagging whitelist (33 handles, `prefPeople` in their open repo). Saved both to `data/raw/registry-seed/` with a README documenting known limitations (truncated bios, stale affiliations, no per-person verification yet). Wrote a deep-research prompt (`docs/references/deep-research-prompt-seed-lists.md`) for Adi to run externally to find more curated lists. Session paused here — Adi continuing elsewhere | GitHub Copilot CLI (Sonnet 5), Playwright headless, `gh api` | Nothing auto-admitted to a registry yet — all of this is unverified candidate pool, pending Adi's review pass before any schema/registry table is built |

## Budget log (€100 ceiling)

Keep receipts. Every spend gets a row and a stated reason.

| Date | Service | Amount | Why | Receipt |
| --- | --- | --- | --- | --- |
| — | — | €0.00 | nothing spent yet | — |

Running total: **€0.00 / €100.00**
