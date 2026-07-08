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

## Tooling
- AI coding tools are explicitly expected and will be discussed at the on-site
  round — the working-log (`docs/references/working-log.md`) captures how AI
  tools were used, not just the code output.

## Stack
- Provisional default: Python core + SQLite, boring and inspectable. Final
  DB/scheduling/UI decisions are made in the Phase 0 design pass and recorded
  in `docs/references/solution-architecture.md` with reasons — not assumed.
- LLM provider/model choice per task is a deliverable in itself
  (architecture write-up requires "model selection per task, and why");
  deferred to design pass. €100 budget shapes it; spend logged in the
  working log.
