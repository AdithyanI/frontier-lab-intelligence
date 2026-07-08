# BIT Capital — Company and Role Context

Submission-safe context distilled 2026-07-07 from public sources. Verify live
before relying on market/fund facts in the deliverable. Source links:
`sources.md`.

## Who they are

BIT Capital is a Berlin-based active technology-equity asset manager (founded
2017 by Jan Beckers) that presents itself as a technology company: proprietary
data infrastructure, AI models, and human judgment aimed at repeatable
outperformance. ~€3.0bn AUM; ~40-45 people including an investment team of ~20.
Final investment decisions remain human.

Public tech/data claims (official investment-approach page): >30,000
alternative data signals analyzed daily; 80 TB raw data/day; 30+ AI-supported
processes with 500M+ tokens/month; ~2.4 PB raw data processed/month.

Recent public themes: memory supercycle, AI infrastructure demand, AI bubble
skepticism, infrastructure monetization.

## The role this case study is for

AI Engineer, Berlin. Mandate: develop BIT's LLM and agentic AI capabilities
end to end — from the data science that turns data into investment signals to
the engineering behind their financial intelligence agents. Strong initial
focus on "Aion", their agentic research platform in daily production use by
the investment team. Reports to Carlos Bielsa (Chief AI Officer & Managing
Partner), works alongside Vlad Gheorghe (AI Engineer).

Stack named publicly: Python, SQL, AWS, Databricks; models and agentic
frameworks from leading labs (Anthropic Managed Agents, Codex).

Role priorities (from the posting), in their words:

- Investment signal pipelines: LLM extraction (prompts, retrieval, model
  selection, evaluations) reliable enough to drive decisions.
- Agentic systems behind Aion: research skills and Python sidecars.
- Data and tool integrations: performant, safe agent access to BIT data.
- Evaluations and model selection: automated + human-in-the-loop evals,
  regression tests, monitoring of accuracy, hallucination rates, latency,
  cost, model uncertainty; benchmark and select the right model per task.
- LLMOps at scale: versioning of prompts/configs/models, CI/CD, error
  handling, fallbacks, cost control.
- Frontier into production: new techniques shipped, not left as experiments.

Explicit anti-signals from the posting: using AI only for personal
productivity without production systems; wanting a finished stable stack to
operate.

## What this means for the case study

The case study ("Frontier Lab Intelligence") is a miniature of the role: an
LLM extraction pipeline that turns public frontier-lab output into scored,
validated, persona-tailored investment/technical intelligence. The same
qualities the role demands are what the rubric weights:

- Data-science rigor on scoring (validated, reproducible, defensible).
- Signal-vs-noise judgment (their "most important part").
- Production discipline: evals, hallucination control, cost awareness
  (tokenomics is an explicit deliverable).
- Persona awareness: investment team (implications, tickers, theses) vs AI
  team (adopt/investigate, build-relevant).
- Human-in-the-loop boundary: the system informs, humans decide.

## The two audiences, concretely

- **Investment team (PMs/analysts):** "what does this mean for our
  positions?" Star researcher leaves to found a startup; a capability jump
  threatens a holding's moat or validates a thesis; shifts in the competitive
  map; semiconductor/energy supply-chain ramifications. Most labs are private,
  so the judgment is connecting lab developments to where they land for a
  public-equity investor.
- **AI team:** "what should we adopt or investigate?" New agentic
  orchestration or evaluation techniques, cheaper/better open models, papers
  that change how a pipeline would be built.

One shared core (ingestion → register → extraction → scoring), two tailored
last-mile outputs. Not two systems.
