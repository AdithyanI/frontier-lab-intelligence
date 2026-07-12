# Signal Feed Operations

The Feed is the deterministic evidence layer between stored public output and
future LLM extraction. It currently accepts X posts, but its API contract is
source-oriented so later blog, paper, and release evidence can enter as another
provider without changing Registry identity.

## Storage Boundary

- `data/raw/x/x-content.db`: immutable provider responses plus normalized
  top-level X posts and exact model-evidence bundles.
- `data/derived/signal-feed/feed.db`: rebuildable versioned Feed runs,
  normalized embedded targets, direct/embedded membership, and quote/retweet
  relations.
- `data/fli.db`: current Registry identity and rejection state. It is read at
  API request time and is never copied into a Feed run.
- `data/derived/following/*/analysis.db`: accepted entity-overlap network
  support used as one score input.

All large data files are intentionally ignored. The tracked schema, CLI, tests,
and this runbook are the reproducible contract.

## Refresh

```bash
.venv/bin/fli signal-feed refresh --days 7
```

The default end date is the previous UTC calendar day. Pin a historical end
date when reproducing a demo:

```bash
.venv/bin/fli signal-feed refresh --days 7 --through 2026-07-11
```

The command emits one JSON object. An unchanged selection reuses its existing
content-addressed run. It makes no provider or LLM call.

## Read Contract

- `GET /api/feed/dates` lists complete materialized dates.
- `GET /api/feed?date=YYYY-MM-DD` returns one Registry-aware ranked page.
- `lane=all|network|firsthand` changes eligibility without changing scores.
- `sort=attention|recent|engagement` changes ordering.
- `q`, `limit`, and `offset` provide server-side search and pagination.

Registry rejection changes are dynamic. On the next request, a rejected author
is absent and a rejected amplifier no longer votes. Raw/derived evidence is not
deleted, so reversing the curation decision restores the evidence.

## Attention Score

`attention-v1` is an experimental, day-relative ordering aid:

- 55% Registry attention percentile: distinct active Registry amplifiers, with
  a visible boost for top-quintile network-support amplifiers;
- 25% originator network-support percentile;
- 20% public-interaction percentile (log-scaled likes, replies, reposts, and
  quotes).

Every component is returned beside the score. Each canonical entity votes at
most once, self-amplification is excluded, and switching lanes or searching
cannot change an item's score. The score does not claim relevance, quality,
truth, novelty, or investment importance.
