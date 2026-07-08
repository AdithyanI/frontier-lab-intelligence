# Context

Project context for agents and for the eventual submission cleanup.

This file merges the previous BIT/company context and builder context. It has
both submission-safe and private working sections. Before sharing anything
externally, run the Phase 4 cleanup gate in the tracker.

## BIT Capital / Role Context

Submission-safe context distilled 2026-07-07 from public sources. Verify live
before relying on market/fund facts in the deliverable.

BIT Capital is a Berlin-based active technology-equity asset manager founded
in 2017 by Jan Beckers. Public positioning: proprietary data infrastructure,
AI models, and human judgment aimed at repeatable technology-equity
outperformance. Public claims include roughly €3.0bn AUM, 40-45 people,
alternative data infrastructure, and AI-assisted investment processes.

The role is AI Engineer, Berlin. The case study maps directly to the role:
turn public frontier-lab output into scored, validated, persona-tailored
investment and technical intelligence.

Role-relevant themes:

- LLM extraction pipelines reliable enough to support investment work.
- Agentic systems and research skills behind BIT's internal Aion platform.
- Data/tool integrations with safe agent access.
- Evaluations, model selection, fallbacks, hallucination control, latency,
  cost, and model uncertainty.
- Production discipline over toy demos.

The two target audiences:

- **Investment team:** implications for positions, theses, competitive moats,
  semiconductor/energy/supply-chain exposure, and market timing.
- **AI team:** models, papers, tools, agent patterns, evals, and techniques
  worth adopting or investigating.

One shared core should serve both audiences. Do not build two systems.

## Builder Context

Adi is a systems/product engineer in Berlin, not a data scientist. This case
study is both a BIT submission and a real product seed.

Submission-safe background:

- Founded AI Podcasting and built production AI/media workflows for paying
  customers.
- Former Bitmovin Senior Software Engineer on cloud video-encoding APIs and
  media infrastructure.
- Builds and writes about agent-native harnesses, Codex, MCP, and production
  AI systems.

How to calibrate explanations:

- Assume strong production Python/API/systems background.
- Explain data-science choices in plain systems-engineer terms.
- Prefer concrete examples from this repo over textbook theory.
- Give direct pushback when a direction is likely to waste time or weaken the
  submission.

## Private Working Context

Keep this section out of the final external submission unless Adi explicitly
chooses to include it.

Adi is using this build to learn data-science territory through implementation:
scoring model design, validation, ground-truth construction, ranking metrics,
calibration, and signal-vs-noise evaluation.

Learning contract after consolidation:

- When a DS/ML technique materially enters the system, add a short note to
  `docs/references/build-log.md` under "Learning Notes."
- Do it after the technique is used, not before.
- Keep entries short and defensible in an interview.

The repo is dual-purpose until submission:

1. BIT case-study submission due 2026-07-20.
2. A real product Adi may keep building after the application.

Phase 4 cleanup must remove or rewrite private context, private career framing,
and local-only notes before any external sharing.

