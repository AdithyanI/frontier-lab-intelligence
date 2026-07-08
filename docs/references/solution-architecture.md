# Solution Architecture

Living doc. Started 2026-07-08 with the stack decision; pipeline design
sections get added as Phase 0/1 work lands.

## Stack decision (2026-07-08)

**One Python codebase — a modular monolith. No separate frontend framework.**

| Layer | Choice | Why |
| --- | --- | --- |
| Language | Python 3.13 | 60% of the rubric (registry, ingestion, extraction, scoring) is data + LLM work — Python's strongest territory, and the builder's production strength. |
| Package | `src/fli/` (frontier lab intelligence) | Single installable package; pipeline stages are modules, not services. |
| Database | SQLite (single file) | The prompt requires delivering "the database." A single inspectable file the reviewer can open beats a hosted DB. Zero ops; ships with the repo or as an artifact. Volume (hundreds of entities, thousands of documents) is far below SQLite's limits. |
| Web UI | FastAPI + Jinja2 server-rendered HTML, plain CSS from `DESIGN.md` tokens | UI is 5% of the rubric. A split React/Next frontend adds an API contract, CORS, a node build chain, and a second runtime for zero rubric gain. Server-rendered HTML consumes the design tokens directly and gives near-free PDF export via print CSS. |
| API | The same FastAPI app exposes the few JSON endpoints needed (if any) | One process, one port, one `uvicorn` command. |
| Pipeline entrypoint | CLI (`fli ingest`, `fli extract`, `fli score`, `fli report`, …) | Each stage is independently runnable and inspectable — good for demos, evals, and debugging. |
| Scheduling | cron/launchd (or a simple loop) invoking the CLI | "Scheduled ingestion" at this scale is a timer, not a queue framework. Retry/dedup live in the pipeline code where they're testable. |
| Reports/PDF | HTML report template → print-CSS PDF (tool decided when built; likely WeasyPrint or headless-browser print) | Reuses the same template as the in-app view; one source of truth for report layout. |
| Dependency mgmt | `pyproject.toml` + venv | Standard, reviewer-friendly. Runtime deps are added when the code that uses them lands, not speculatively. |

### The alternative considered, and why not

**Split stack (Python backend + JS frontend):** rejected. It optimizes the
5%-weight surface at the cost of everything else — two codebases, an API
contract to maintain, slower iteration, and a harder "clone and run" story
for the reviewer. If the UI ever needs interactivity beyond forms and links,
the escape hatch is a sprinkle of vanilla JS or htmx inside the same app —
still no build step.

**Everything-in-one frameworks (Streamlit/Gradio):** rejected. They make the
UI easy but fight the design system (`DESIGN.md` is plain-CSS tokens), look
like a toy demo, and couple pipeline code to a UI runtime. The AGENTS.md
quality bar explicitly warns against dashboard-only/toy-demo work.

### Decision drivers (ranked)

1. Rubric weighting: pipeline 60%, delivery 15%, UI 5%.
2. Reviewer experience: clone → one install → one command → working system.
3. Iteration speed inside the €100 budget and ~2-week deadline.
4. Builder leverage: production Python is the known-strong path; the learning
   budget is reserved for the DS territory (scoring, validation), not for a
   frontend framework.

### Deferred decisions

- LLM provider(s) and model-per-task mapping — Phase 0/1, recorded here.
- Exact PDF tool — when reports are built (Phase 2).
- Alert channel (Slack vs email) — Phase 2.
