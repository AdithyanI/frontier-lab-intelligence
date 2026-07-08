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
