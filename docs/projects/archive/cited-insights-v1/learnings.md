# Cited Insights v1 Learnings

## What worked

- Freezing complete evidence packets before model calls made every run replayable.
- Application-owned exact-substring citation binding prevented plausible but
  altered quotations from reaching the UI.
- The five-record oracle exposed selection and citation failures cheaply before
  a broad run.
- Shared artifact identity kept external evidence independent of any one insight.

## What slowed the project

- The first prompt tried to satisfy Investment and Engineering simultaneously.
  That averaged two different jobs into one claim and one UI row.
- The tracker accumulated adjacent Network and artifact work until its live
  execution boundary became hard to see.
- X Articles were identified from provider metadata but their complete bodies
  were not yet retrieved, leaving link-led evidence incomplete.

## Guidance for v2

- Keep one evidence and citation core, but give each audience its own prompt,
  output contract, evaluation, daily selection, and product view.
- Gate broad runs behind a two-day quality check, then continue automatically.
- Treat X Article retrieval as a provider-backed artifact adapter; preserve raw
  JSON and normalized exact-citation text.
- Keep delivery, Registry expansion, and unrelated pipeline work out until the
  audience-specific insight product is proven.
