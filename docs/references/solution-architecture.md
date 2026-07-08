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

---

## Phase 0 strawman designs (2026-07-08 — DRAFT, pending Adi's reaction)

> Status: brainstorm output written down so it survives the session. Nothing
> below is implemented or final. Each section ends with the open questions
> Adi should weigh in on.

### System shape

Five stages, each an independently runnable CLI step over one SQLite DB:

```
registry ──► ingestion ──► extraction ──► scoring ──► delivery
 (who)        (what)        (structured    (how much   (reports +
                             insights)      signal)     alerts)
```

### 1. Registry design (20% of rubric)

**Entities.** Three tables at the core:

- `entities` — labs and people, both first-class (`kind: lab | person`).
- `affiliations` — person↔lab with start/end dates and provenance, because
  people move; an affiliation is a dated claim, never a fixed attribute.
- `identities` — platform handles per entity (X, arXiv author, GitHub,
  personal site), each with a confidence and a provenance link.

**Going a layer below the obvious names** (the prompt's real test) —
discovery is a repeatable job, not a hand-curated list:

1. Seed ~6–10 labs by hand (OpenAI, Anthropic, DeepMind, Meta AI, Mistral,
   xAI, DeepSeek, Qwen team, …) — this is judgment, and defensible.
2. From each lab, expand mechanically: author lists of the lab's recent
   arXiv papers, GitHub org members, names on lab blog posts, team pages.
3. Rank discovered people by observable signal (recent first-author papers,
   repo activity, citation velocity) and keep the top slice per lab.
4. Re-run on schedule → the register stays current; new names surface
   because they start appearing on papers/releases, not because we knew them.

**Identity resolution.** Precision-first tiering: (a) explicit self-links
(bio says "github.com/x", personal site links both) = auto-accept;
(b) LLM-assisted match on name + affiliation + topic overlap = accept above
a confidence threshold, else queue for human review. Every identity row
keeps its evidence.

**Open for Adi:** which labs seed the list; how many people per lab is
useful vs noise (proposal: ~10–20); is X/Twitter ingestion worth the API
cost given the €100 budget?

### 2. Signal-vs-noise design (20%)

"Genuinely important, novel, actionable" made operational — a funnel where
each stage is cheap enough to run on everything that survives the previous
one:

- **Stage 0 — source scoping (editorial, free):** ingest only justified
  sources. Scoped-well beats broad-badly; the source list is itself a
  documented judgment.
- **Stage 1 — dedup/canonicalization (mechanical, free):** same paper via
  arXiv + blog + X thread = one event with multiple citations, not three.
- **Stage 2 — cheap novelty gate (embeddings, ~free):** embed each item;
  near-duplicates of recently seen content get suppressed as "not novel."
- **Stage 3 — LLM extraction + rubric scoring (costs tokens):** only
  survivors get the expensive treatment.
- **Stage 4 — persona thresholds (free):** what alerts an investor differs
  from what alerts an AI team; same scored insight, different cut-lines.

Judgment is encoded in exactly two visible places: the source list (stage 0)
and the scoring rubric (stage 3). Everything else is mechanical and testable.

### 3. Scoring design (20% — the heart, and the DS learning centerpiece)

**The trap to avoid** (named in the prompt): an arbitrary weighted sum
dressed as a score. `0.3*novelty + 0.5*materiality + 0.2*credibility` with
invented weights is exactly that.

**Strawman instead — separate, visible dimensions + validated combination:**

1. An LLM scores each extracted insight on independent dimensions, each with
   a written rubric and a required evidence quote: **novelty** (vs what's
   already known), **materiality** (does this change capability/cost/
   competitive position), **credibility** (primary announcement vs rumor;
   who said it), **actionability per persona** (separately for investment
   team vs AI team).
2. Dimensions stay visible in the UI/report — the "why flagged" answer is
   the dimension scores + evidence quotes, not one opaque number.
3. The combination into a ranking is **fit to ground truth, not invented**:
   start with the simplest combiner (e.g., max-of-dimensions or unweighted
   mean), then check against the validation set and only add complexity if
   the data demands it.

**Validation plan (what makes the score defensible):**

- **Retrospective ground truth:** take a past window (e.g., 3 months), run
  the pipeline over it, and label what *actually mattered* with hindsight —
  events that became consensus-important (major coverage, follow-on work,
  market reaction). Score-then-check against hindsight is the cleanest
  ground truth available without paying annotators.
- **Human judgment baseline:** Adi labels a sample (~50–100 insights) as
  high/medium/low signal; measure agreement between the model ranking and
  the human ranking.
- **Metrics:** precision@k ("of the top 10 the system flags, how many did
  the human/hindsight also flag?") and rank correlation — chosen because
  the product decision is "what makes the digest," a ranking problem, not
  a classification problem.

**Open for Adi:** how much labeling time is he willing to spend (directly
sets validation quality); which past window to use for retrospective ground
truth.

### 4. Delivery design (15%) — sketch only

One shared core of scored insights → two persona lenses (investment: money,
moats, market moves; AI team: techniques, models, tooling). Digest = top-k
above persona threshold, rendered as HTML in-app and print-CSS PDF. Alerts =
score crosses the alert threshold → push (channel TBD) with citation.

### Suggested build order after Phase 0 sign-off

1. Registry schema + seed + discovery (biggest single rubric item).
2. Ingestion for 2–3 sources end-to-end (thin but real).
3. Extraction + scoring on real ingested data.
4. Validation harness + ground-truth labeling.
5. Delivery + UI last.
