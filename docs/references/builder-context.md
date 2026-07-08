# Builder Context — Adi

> **PRE-SUBMISSION NOTE:** This file mixes submission-safe proof-of-work facts
> with private working context (learning goals, self-assessment, career
> framing). Before the repo is shared with BIT, this file gets rewritten down
> to the submission-safe subset (or folded into the README/final report).
> The cleanup gate lives in the tracker's Phase 4.

## Who is building this

Adithyan Ilangovan (Adi). Builder and founder, Berlin. Background: production
systems and media infrastructure engineering, not data science. This repo is
his BIT Capital AI Engineer case-study submission, built agent-natively — Adi
sets intent and reviews; coding agents implement, validate, and document.

Public handles: @AdithyanI on GitHub, adithyan-ai on LinkedIn, adithyan.io
(blog), u/phoneixAdi on Reddit.

## Professional background (submission-safe)

- **AI Podcasting (AIP)** — founded, built from scratch to ~$15k USD MRR.
  Production AI/media pipelines for paying customers: The Cognitive Revolution
  (24 months, 228 episodes, 1.14M downloads, 10.5M video views), Future of
  Life Institute (8 months, 22 episodes, 1.9M views), Network School (30
  episodes, +10.4K subscribers, 600K views in 6 months).
  Production LLM discipline from this work: queue-based jobs with retry +
  poison handling, provider fallback, cache-by-input-hash, token/cost logging
  per call, quality gates, schema validation. Failures were customer-facing,
  not benchmark failures.
- **Bitmovin** — Senior Software Engineer, Feb 2018–Oct 2022. Cloud
  video-encoding APIs and enterprise media infrastructure. Named on three
  filed US video-encoding patent applications (chief author on two). Say
  "filed patent applications," never "granted patents."
- **Agent-native harness work** — builds and runs a personal agent system
  (control-plane repo with skill/plugin/hook registries, MCP presets,
  lifecycle hooks, session/memory workflows). Public repo:
  github.com/wisdom-in-a-nutshell/agents. Writes publicly about agent
  harnesses, Codex, MCP, and production AI systems on adithyan.io.

One-line positioning: *"I don't just use coding agents; I build the harness
around them — and my production bar comes from running customer-facing AI
pipelines, which biases me toward traceability, failure handling, and human
review over impressive-but-brittle demos."*

## What Adi knows well (calibrate explanations accordingly)

- Production Python, APIs, queues, caching, media pipelines, cloud infra.
- LLM integration in production: prompting, structured outputs, cost/token
  awareness, provider fallback, eval-adjacent quality gates.
- Agent-native development: skills, hooks, MCP, subagents, repo harnesses.
- Systems thinking, tradeoff analysis, clear technical writing.

## What Adi is learning through this project (private working context)

Adi is NOT from a data-science background. This case study deliberately
exercises DS territory, and the repo doubles as his learning surface:

- Scoring/rating model design: what makes a score defensible vs arbitrary.
- Validation: ground truth construction, proxies, human-judgment baselines.
- Ranking/classification metrics: precision/recall trade-offs, calibration.
- Signal-vs-noise filtering as a measurable discipline, not vibes.

Contract for agents (binding, see `docs/learning/README.md`): when a change
uses a DS/ML technique, write the plain-words learning entry in the same
change. **Do → learn, never learn → do.** Explain in systems-engineer terms;
worked examples with our real data beat formulas. Adi wants to be able to
defend every design choice verbally at the on-site round — the "If asked about
this at the on-site" line in each learning entry is not optional.

Communication preferences: plain words, no em dashes in outgoing prose,
concrete next actions, honest pushback when something is off. He learns by
doing and by writing; structure explanations around the decision just made,
not general theory.

## Why this repo exists twice over (private working context)

1. **Case-study submission** for BIT Capital (deadline 2026-07-20) — the
   near-term driver. Judged on the weighted rubric in the tracker.
2. **A real product Adi may keep building** regardless of the application
   outcome — hence the generic product name. Design decisions should not
   assume the repo dies on the 20th.

The dual purpose is deliberate. Until submission, optimize for building well
and learning; at Phase 4, a cleanup pass strips private context (this file's
private sections, learning-log internals if desired, working-log framing) into
a submission-safe shape. Nothing in this repo should be *impossible* to clean:
keep private context in clearly marked sections/files, never scattered through
code comments or commit messages.

## Honest gap, and how to frame it (submission-relevant)

No buy-side finance background. Frame as fast domain-learning plus systems
rigor, not as pretending to be an investment analyst. The prompt itself asks
candidates to research BIT and figure out who would use the system — that
research posture *is* the answer to the gap.
