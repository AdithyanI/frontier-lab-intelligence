# Frontier Lab Intelligence — Implementation Tracker

Implementation repo for **Frontier Lab Intelligence**: a system that tracks
frontier AI labs and their key people, extracts and scores intelligence from
their public output, and delivers persona-tailored reports and alerts.

Origin: BIT Capital AI Engineer take-home case study (sent by Lars,
2026-07-07). Built as a real product, not homework; the name and framing are
deliberately generic so the system outlives the application. The
career/control-plane tracker stays at
`~/GitHub/adi/projects/bit-capital-case-study-2026/tasks.md`.

## Prompt

Full verbatim prompt: `docs/references/case-prompt.md`.
Original PDF + extracted text: `docs/references/source-material/`.
Company/role context: `docs/references/bit-context.md`.

- **Deadline:** 2026-07-20 (Lars asked "does that work for you?"; Adi
  confirmed by reply on 2026-07-07 — see career tracker).
- **Deliverable:** working system (register, ingestion, extraction, scoring,
  reports + alerts for two personas, small web UI) + code + DB + write-ups
  (architecture, prompts + rationale, evaluation, tokenomics, final report).
- **Budget:** €100 for APIs/services, reimbursable with receipts; how it is
  spent is itself evaluated. Log: `docs/references/working-log.md`.
- **Weighted rubric:** registry 20% · signal-vs-noise 20% · scoring/validation
  20% · actionable delivery 15% · ingestion 10% · extraction 10% · web UI 5%.

## Standing contracts (all agents)

- **Learning log** (`docs/learning/`): any data-science/ML technique used in
  the work gets a plain-words entry in the same change. Do → learn, never
  learn → do. Contract details: `docs/learning/README.md`.
- **Working log** (`docs/references/working-log.md`): AI-tool usage per
  session + every euro of the €100 budget. BIT will ask "how you worked."
- **Design**: `PRODUCT.md` and `DESIGN.md` at repo root govern all UI work
  (impeccable-compatible). Web UI is 5% of the rubric — keep it light.
- **No external send** (email/publish/public push/submission) without
  explicit Adi approval.

## Current Batch

| Status | Work Item | Role | Resource |
| --- | --- | --- | --- |
| in-progress | Rebuild the registry candidate review from real evidence: `data/fli.db` raw items + Digg-derived seed graph, without relying on the deleted `data/raw/registry-seed/` scratch folder. | parent | `data/digg/`, `docs/references/seed-lists.md`, `docs/references/working-log.md` |
| todo | Decide the first modeled registry/data schema only after reviewing real candidate evidence. The DB deliverable/package policy is intentionally open for now. | parent | `docs/references/assumptions.md`, `docs/references/solution-architecture.md` |
| todo | Keep frontend work deferred until registry/extraction/scoring have real modeled output to display. | parent | `PRODUCT.md`, `DESIGN.md` |

## Open Questions / Blockers

- **DB schema:** deliberately undecided. Keep the raw layer useful, but do not
  treat `data/fli.db` or the Phase 0 data model sketch as the final schema.
- **Database artifact policy:** open. The prompt asks for "the database:
  schema and real data," but packaging/committing policy should be decided
  after the modeled schema exists.
- **Dobby system boundary:** do not bring the personal Dobby memory/agent
  architecture into this repo. Use only the lightweight agent-native workflow
  patterns that help this product ship.

## Execution plan (ordered by rubric weight)

### Phase 0 — Design pass (before pipeline code)
- [x] Registry design: entity schema (labs as first-class + individuals),
      identity resolution across X/arXiv/GitHub, "layer below the obvious
      names" discovery approach, currency mechanism (people move, names emerge).
      → `docs/references/solution-architecture.md` §1.
- [x] Signal-vs-noise design: what "genuinely important, novel, actionable"
      means operationally; filtering stages; where judgment is encoded.
      → architecture doc §2 (5-stage funnel; judgment in source list + rubric).
- [x] Scoring design: model + inputs + justification; validation plan against
      ground truth / human judgment / defensible proxy. Explicit red flag from
      the prompt: an arbitrary weighted sum dressed as a score.
      → architecture doc §3 (visible dimensions + mechanical inputs; combiner
      fit to ground truth; precision@k + rank correlation). Labeling
      assumption pending Adi confirmation (`assumptions.md`).
- [x] Stack decision recorded in `docs/references/solution-architecture.md`
      (Python modular monolith + SQLite + FastAPI/Jinja2 server-rendered UI;
      alternatives considered and rejected with reasons).

### Phase 1 — Core pipeline (60% of rubric)
- [ ] Register implementation: schema, seed data (labs + individuals),
      entity resolution, update/discovery mechanism.
- [ ] Ingestion: scheduled multi-source pulls (lab blogs, org accounts,
      arXiv, GitHub, …), dedup, rate limiting, freshness; justified source
      selection — scoped-well beats broad-badly.
- [ ] Extraction: LLM-driven structured insights, attributed (person vs lab),
      every insight traceable to primary source, clean citations.
- [ ] Scoring: implemented + validated per Phase 0 design.
- [ ] Signal-vs-noise filtering implemented and demonstrable.

### Phase 2 — Delivery (15%)
- [ ] Reports: periodic digest, readable in app + exportable as PDF, cited,
      persona-tailored (investment team vs AI team) from one shared core.
- [ ] Alerts: push on material events (Slack/email), routed per audience.

### Phase 3 — Surface + proof (15% + deliverables)
- [ ] Web UI: browse register, scored insights + why-flagged, past reports,
      configure tracking. Light; per DESIGN.md.
- [ ] Evaluation write-up: extraction quality, hallucination control, scoring
      validation, ground-truth approach.
- [ ] Tokenomics: token usage + $ per workflow; cost-quality trade-offs.
- [ ] Architecture write-up: stack + why, model per task, fallbacks.
- [ ] Prompts + design rationale captured.
- [ ] Final report: what works, what's next, learnings (feed from
      `docs/learning/`), and 3–5 most interesting real insights surfaced.
- [ ] Optional: short Loom/video demo (Adi signalled intent in reply to Lars).

### Phase 4 — Submission
- [ ] **Pre-submission cleanup pass (hard gate, do first in this phase):**
      rewrite `docs/references/builder-context.md` down to submission-safe
      content; review working-log framing, learning-log entries, assumptions,
      and this tracker for private career context; scan git history for
      anything private (rewrite history or re-init if needed); no private
      local paths in any doc that ships.
- [ ] Self-review against every explicit prompt requirement
      (`docs/references/case-prompt.md` requirements map).
- [ ] Reviewer guide finalized: what to read, what to run, what output proves
      it works, known limitations.
- [ ] Submission package prepared for Adi's review; external send only on
      explicit approval.

## Proof of Work
Before handoff, record:

- Commands run:
- Results:
- Files/artifacts reviewed:
- Known limitations:
- Prompt requirements satisfied:
- Prompt requirements not satisfied / blocked:
- Submission package path:

## Decisions
- 2026-07-07 — Scaffolded as a separate repo per the agent-native template
  rule (runnable code, DB, web UI, and evals are explicitly required by the
  prompt). Career-tracker project in `~/GitHub/adi` stays the control-plane
  record and the source of the original prompt capture.
- 2026-07-08 — Renamed repo `bit-capital-case-study-2026` →
  `frontier-lab-intelligence` (Adi): product-named, generic, survives beyond
  the application. Internal tracker folder renamed to match.
- 2026-07-08 — Added standing contracts: learning log (do → learn),
  working log (AI-tool usage + budget), PRODUCT.md/DESIGN.md design system.
- 2026-07-08 — Stack: Python core + SQLite as provisional default; final
  decision deferred to the Phase 0 design pass, recorded in the architecture
  doc. LLM provider/API-key choice also deferred (Adi: don't block on it now).

## Log
- 2026-07-07: Repo scaffolded from agent-native template; prompt + source
  material captured verbatim.
- 2026-07-08: Renamed to frontier-lab-intelligence. Added PRODUCT.md,
  DESIGN.md (seeded pre-implementation), `docs/references/bit-context.md`,
  `docs/learning/` contract, `docs/references/working-log.md`. Rebuilt this
  tracker with the weighted execution plan.
- 2026-07-08 (pm): Phase 0 design pass complete. Stack decided + recorded
  (Python monolith, SQLite, FastAPI/Jinja2). Package scaffolded (`src/fli`,
  CLI stub, 2 tests, venv; check-fast green). Prior-art research (smol.ai,
  Digg 2026 pivot, Techmeme/HN, landscape audit via 3 research sub-agents)
  synthesized into architecture doc with 9 adopted design deltas; provenance
  in sources.md. Phase 0 defaults recorded in assumptions.md — pending Adi
  confirmation: ground-truth labeling appetite, X-source timing, lab seed
  list final. Next: Phase 1 registry (schema + seeds + discovery).
- 2026-07-08 (pm, later): Living visual architecture doc added
  (`docs/architecture/overview.md`, Mermaid: pipeline, funnel, data model,
  module status) + docs-contract line in AGENTS.md. Web UI shell built
  (`fli web`): FastAPI + Jinja2 + DESIGN.md tokens; home + /architecture
  page rendering the doc with client-side Mermaid. 5 tests green;
  headless-browser check confirmed all 3 diagrams render as SVG.
- 2026-07-08 (pm, UI polish): Adi flagged the UI as bland → impeccable pass:
  real fonts loaded (Inter + IBM Plex Mono), home rebuilt product-shaped
  (digest/register panels with teaching empty states, pipeline status
  table, mono provenance rows). Verdict kept: framework isn't the blandness
  — density is the design; full components arrive with real data (Phase 1–2).
- 2026-07-08 (data-first fetch spike): Adi chose data-first over
  schema-first. Built `src/fli/store.py` (raw_items table, dedup by
  source+external_id) + `src/fli/fetch.py` (blog RSS/sitemap, arXiv API,
  GitHub releases) for 3 labs (OpenAI, Anthropic, DeepMind). Ran it:
  **1,599 real raw items** in `data/fli.db`. Fixed Anthropic (no blog RSS
  exists — added sitemap `/news/` URL fallback, 237 items). Reviewed real
  payload samples together (arXiv/blog/GitHub) and found 3 concrete
  findings that will shape the modeled schema: (1) arXiv lab-name search
  gives false positives (a physics paper about "the anthropic principle"
  matched "Anthropic") — need author-identity matching, not text search;
  (2) blog feeds mix marketing/case-studies with real research signal —
  confirms the funnel/classification step is load-bearing, not optional;
  (3) GitHub release `author` fields carry real handles for free — a
  cheap registry-discovery input. 8 tests green.
- 2026-07-08 (registry bootstrap, paused mid-task): Started Phase 1
  registry work. Extracted candidate people from our own raw data (arXiv
  co-authors + GitHub release/org authors) — surfaced real researchers
  (Trieu H. Trinh, Cordelia Schmid, tomhennigan) and taught us
  `github-actions[bot]` needs filtering. Explored X API economics for
  follow-graph seeding (pay-per-use, no subscription: posts $0.005/read,
  users/follows $0.01/read; reading a big account's followers is
  expensive, reading who a *trusted* person follows is cheap — ~$10-20 per
  anchor account — and is the actual mechanic behind "bootstrap from
  curated lists"). Scraped Digg's live rankings page (Playwright, 700
  ranked people/companies; page's own text confirms method: "built from
  the X social graph, using roughly 9 million follow relationships" —
  algorithmic, not hand-curated, correcting an earlier inference). Mined
  smol.ai's public GitHub repo for their real people-tagging whitelist (33
  handles in `oneoffs/preferredTags.ts`). Both saved to
  temporary `data/raw/registry-seed/` scratch files with a README covering
  known limitations (truncated-bio false negatives, stale affiliations,
  nothing auto-verified). Wrote an external deep-research prompt
  (`docs/references/deep-research-prompt-seed-lists.md`) for Adi to run to
  find more curated lists (X Lists, TIME100 AI, Semantic Scholar,
  conference speaker lists, China-lab coverage).
  **Session paused here — Adi continuing elsewhere. Resume point:**
  regenerate/merge Digg-style, smol.ai-style, arXiv, and GitHub evidence into
  one reviewable candidate table; Adi does the human approval pass; then write
  the modeled `people`/`labs` schema from what survives review. No registry
  schema exists yet — still raw candidate pools only. The temporary
  `data/raw/registry-seed/` folder was deleted later the same day; do not
  assume those scratch files exist.
- 2026-07-08 (Digg seed graph scrape): Pivoted v1 discovery to Digg after
  verifying the site exposes structured ranking/profile data. Added
  `src/fli/digg.py` + `fli digg`; scraped `data/digg/` with **1,000 ranked
  accounts**, **1,000 profile pages**, and **49,950 initial top-follower
  edges**. No X API spend. Next: inspect/dedupe/rank these candidate nodes,
  filter org/media/investor noise, and design the first candidate review
  table from actual Digg evidence.
- 2026-07-08 (Digg full follower graph): Added `fli digg --full-followers`
  to page Digg's public follower API. Smoke test: 2 profiles → 3,126 edges.
  Full pull: **1,000 rankings**, **1,000 profiles**, **361,225 directed
  top-follower edges** across 999 target accounts; `xai` returned 404. Full
  raw artifacts are kept locally under ignored `data/raw/digg-full-2026-07-08/`
  because they exceed normal git-hosting file-size limits; tracked manifest:
  `data/digg/full_graph_summary.json`. Tracked `data/digg/` snapshot remains
  the smaller first-slice graph for reviewability. Next: build candidate
  review/ranking from the full local edge CSV and decide schema from that
  evidence.
- 2026-07-08 (build journal contract): Added
  `docs/references/build-journal.md` and AGENTS guidance requiring a concise
  narrative journal entry after each meaningful chunk of work. Purpose: make
  the take-home build path reviewable as a sequence of human intent,
  decisions, evidence, product impact, and next-step rationale, separate from
  the AI-tool/budget working log.
