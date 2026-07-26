# Product

## Register

product

## Users

Two internal audiences at a Berlin technology-equity fund, both time-poor
professionals who live in data-dense tools all day:

- **Investment team (PMs/analysts):** scanning for position-relevant signal
  between meetings. Job to be done: "tell me what changed at the frontier labs
  and what it means for our positions — implications, tickers, theses."
- **AI team (engineers):** deciding what to adopt or investigate. Job to be
  done: "surface the techniques, models, and papers that should change how we
  build."

Both consume periodic digests and timely pushed alerts; both need every claim
traceable to its primary source in one click. A completed daily digest
must remain readable in the product and downloadable as a self-contained,
audience-specific PDF for offline review and assignment delivery. An operator
can also explicitly send the selected brief through Slack (every cited Insight
with its complete interpretation, plus brief and PDF links) or email (up to
five ranked Insights plus the PDF attachment). Automated alert scheduling is a
separate future concern.

## Product Purpose

Frontier Lab Intelligence: track frontier AI labs and their key people, turn
their public output into scored, cited, structured insights, and deliver the
few things that matter to each audience while suppressing the noise. Success
is defined by the client's own bar: "did this surface something we'd genuinely
want to know, and did it keep the noise out?"

## Brand Personality

Precise, calm, trustworthy. A professional instrument, not a consumer app.
The interface should feel like a research terminal a fund would rely on:
information-forward, quiet chrome, zero decoration that doesn't carry meaning.

## Anti-references

- SaaS dashboard clichés: hero metrics with gradient accents, identical card
  grids, decorative charts.
- Consumer news readers: infinite feeds, engagement-bait density.
- Anything that looks vibe-coded: the client explicitly warned against a
  "vibe-coded demo that ticks the boxes."

## System Principles

Codified with Adi, 2026-07-09. These govern how the system is built, not how
it looks. Argue against them in the tracker, not by silently deviating.

1. **High quality first; cost is telemetry.** In the build phase we pick the
   model, evidence, and depth that best serve quality and usefulness. Cost is
   recorded per workflow for observability and later optimization, but it is
   not a product-selection criterion, an execution gate, or a reason to lower
   quality unless Adi explicitly sets a cap for that work. Once quality is
   known, caching and cheaper equivalent paths may bend the cost curve without
   changing the result.
2. **Automatically done, human-correctable.** Every pipeline stage runs
   end-to-end without a human gate: the LLM curates, scores, and decides,
   always writing down *why* with cited evidence and a reason. Humans audit the
   finished artifact and override where wrong; overrides are stored as data —
   the strongest evidence tier — and survive recomputation. No stage may
   require manual per-item approval to produce output.
3. **Human judgment is the bootstrap, not the loop.** Hand-made choices enter
   the system once, as inspectable inputs — the seed lab list, the curation
   rubric given to the LLM, recorded overrides — and the machine runs with
   them. Keeping judgment in versioned inputs (not in per-item clicks) is
   what lets one person operate the whole system.

## Design Principles

1. **Signal density over decoration** — every pixel earns its place by
   carrying information; the product's entire value proposition is
   noise suppression, and the UI must practice it.
2. **Provenance is a first-class UI element** — sources and citations are
   always visible and reachable, never buried in tooltips.
3. **Why-flagged over what-happened** — surface the reasoning (ranking inputs,
   filter rationale) next to every insight; trust comes from inspectability.
4. **Persona-true framing** — the same insight reads differently for an
   analyst than an engineer; the UI respects the split rather than averaging
   it.
5. **Light and quick** — the client's own words; the UI is 5% of the rubric
   and should feel effortless, not impressive.

## Accessibility & Inclusion

WCAG AA contrast (≥4.5:1 body text). Keyboard-navigable tables and lists.
Reduced-motion alternatives for any transitions. No color-only encoding of
score/severity — pair with text or shape.
