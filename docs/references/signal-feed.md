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
- `data/derived/signal-events/events.db`: rebuildable exact structural groups
  over the Feed run. It stores only multi-post relationships; singleton
  envelopes are added by the read model without duplicating post storage.
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

- `GET /api/events/dates` lists complete materialized dates and underlying
  evidence-post counts.
- `GET /api/events?date=YYYY-MM-DD` returns one unified Registry-aware page of
  evidence envelopes. An unrelated post is a singleton; provider-declared
  quote, retweet, reply-parent, and conversation links form a group.
- `sort=attention|recent|engagement` changes ordering.
- `q`, `limit`, and `offset` provide server-side search and pagination.
- The lower-level `/api/feed` endpoint remains available for inspecting the
  post ledger and score inputs; it is not a separate product mode.

Each grouped response contains one `root` and a related `evidence` list. The
root never repeats in that list. Related rows expose their exact relationship,
target or parent post ID, and reply depth. The UI renders replies parent-first,
labels same-account replies as thread continuations, keeps unique quote
commentary, and collapses retweets into one traceable amplification strip. No
URL, text, embedding, or model similarity is used.

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
