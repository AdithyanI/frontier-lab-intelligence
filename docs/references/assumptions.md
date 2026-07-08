# Assumptions

Interpretation choices made where the prompt was silent or ambiguous, and why.

## Deadline / timezone
- Deadline: 2026-07-20. Timezone not stated; assuming end-of-day Europe/Berlin
  (CEST) since BIT is Berlin-based. Lars explicitly asked "does that work for
  you?" so this is confirmable, not fixed.

## Submission method
- Not explicitly stated. Assuming: reply-all on the existing Gmail thread with
  a link to a private repo (or zip) plus the write-ups, unless Lars's reply
  says otherwise. Confirm in the reply rather than guessing further.

## Scope depth vs. breadth
- Prioritization weights from the prompt: registry 20%, signal-vs-noise 20%,
  scoring/validation 20%, actionable delivery 15%, ingestion 10%, extraction
  10%, web UI 5%. Depth in the top three areas is prioritized over broad but
  shallow coverage everywhere. The web UI is deliberately kept minimal.

## Lab/individual coverage
- "Frontier labs" scoped initially to: OpenAI, Anthropic, Google DeepMind,
  Meta AI, xAI, Mistral, DeepSeek, Qwen (Alibaba), plus room to add stealth
  spin-offs as they're identified. This list comes directly from the prompt's
  examples, not independent research; expand only with justification.

## Data window
- "~3 months" suggested in the prompt for the extraction window. Treated as a
  rolling trailing window, refreshed on each ingestion run, not a fixed
  calendar quarter.

## Phase 0 defaults (set 2026-07-08 by agent; not locked)
- **People per lab:** track ~10–20 individuals per lab — the "layer below the
  obvious names," ranked by observable signal (recent first-author papers,
  repo activity, blog bylines). Enough to demonstrate depth without drowning
  extraction in noise. Adjustable per lab once discovery runs.
- **Ground-truth labeling:** plan assumes Adi hand-labels ~50–100 extracted
  insights (high/medium/low signal, ~1–2 hours). This is both the validation
  backbone and the core DS learning exercise. NOT yet confirmed by Adi —
  confirm before scheduling the labeling session; fallback is
  hindsight-retrospective labels only.
- **Source order:** build ingestion as lab blogs/RSS → arXiv → GitHub
  releases first (free, stable, primary), then add X/Twitter as the fourth
  source. Adi said cost is not a blocker for now, but X API pricing/terms are
  volatile, so the cascade/corroboration signal from X is designed in from
  the start and switched on when the connector lands.
- **Grok/X boundary:** Grok Build CLI is useful for live X-backed search and
  thread fetches, but the current CLI tool set did not expose direct
  following-graph or full X List member enumeration. Treat Grok as a discovery
  and evidence assistant, not as the authoritative graph extractor. If full
  "who trusted anchors follow" edges become central, use the official X API
  or another explicit graph source and store observed edges with timestamps.

## Tooling
- AI coding tools are explicitly expected and will be discussed at the on-site
  round — the working-log (`docs/references/working-log.md`) captures how AI
  tools were used, not just the code output.

## Stack
- Chosen runtime stack: Python core + SQLite + FastAPI/Jinja2, boring and
  inspectable. The modeled DB schema is still open; current `data/fli.db`
  contains only the raw evidence layer.
- LLM provider/model choice per task is a deliverable in itself
  (architecture write-up requires "model selection per task, and why");
  deferred to design pass. €100 budget shapes it; spend logged in the
  working log.
