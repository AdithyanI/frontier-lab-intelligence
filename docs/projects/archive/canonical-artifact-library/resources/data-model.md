# Canonical Artifact Library — Data Model

## The simple mental model

```text
ingestion adapter        source evidence             shared artifact
-----------------        ---------------             ---------------
X                  ->    X post 207...       --+-->  openai.com/announcement
RSS (later)        ->    feed entry abc       --+
GitHub (later)     ->    release v1.2         --+
```

The left side answers **where did we observe this?** The right side answers
**what underlying thing can we fetch, reuse, and cite?**

Today only the X adapter exists. RSS and GitHub are examples used to test that
the boundary is not X-specific; they are not part of the first implementation.

## Where the X URL lives today

An ordinary post permalink such as
`https://x.com/openai/status/2074704958419792299` already lives in the raw
`x_post.url` column. It is copied into the rebuildable Feed as `feed_post.url`,
and a triage run freezes its root URL for audit. The stable identity is the
pair `(provider, post_id)`.

That URL remains a **source URL**. It should not also create an `artifact` row.
Otherwise every post becomes both evidence and an alleged primary document,
which duplicates storage and blurs the distinction between detection and
substantiation.

Links *inside* the post are artifact candidates. Stored provider JSON usually
preserves both:

```text
observed URL:  https://t.co/abc123
expanded URL:  https://openai.com/index/example-announcement/
```

Both are retained. The expanded/final/canonical form becomes the artifact
identity; the `t.co` form remains an alias showing exactly what was observed.

### Explicit X exception

- Ordinary status, reply, quote, or retweet permalink: source evidence only.
- X long-form Article (`x_article`): may be an artifact because it is the
  substantive document itself.
- X media self-links and author-profile links: not artifacts.

## Physical model implemented in v1

The catalog lives at `data/derived/artifacts/artifacts.db`. The operational
contract and exact commands are documented in
`docs/references/artifact-library.md`.

### `artifact`

One row per canonical underlying resource.

```text
artifact_id          SHA-256 of canonical_url
canonical_url        UNIQUE
host
artifact_kind        paper | repository | announcement | article | video | other
first_seen_at
last_seen_at
```

`artifact_kind` describes fetching/rendering behavior. It is not an LLM topic
category and does not determine whether the resource is important.

### `artifact_alias`

Every URL form that resolved to the artifact.

```text
alias_url             PRIMARY KEY
artifact_id           -> artifact
alias_kind            observed | expanded | redirect | declared_canonical
first_seen_at
last_seen_at
```

This is what makes `t.co/A`, `t.co/B`, and the final publisher URL converge
without losing provenance.

### `artifact_observation`

One independently traceable source record pointing at one artifact.

```text
observation_id        deterministic hash of source identity + artifact
artifact_id           -> artifact
source_kind           x_post initially; rss_entry/github_release later
source_provider       twitterapi_io initially
source_external_id    X post ID initially
source_url            X status permalink initially
observed_url          exact URL present in the source record
source_snapshot_sha256 immutable source observation identity
source_published_at
first_envelope_day
best_source_rank
relation              links_to | self_publishes
UNIQUE(source_kind, source_provider, source_external_id, artifact_id, relation)
```

This table does not copy the full X post. It points back to the immutable source
record. There is intentionally no required `event_id`: events may be rebuilt,
merged, split, or projected by day without changing artifact provenance.

### `artifact_fetch`

Append-only fetch attempts and content snapshot metadata.

```text
fetch_id
fetch_run_id
artifact_id           -> artifact
attempt_number
status                 in_progress | success | failed_retryable | failed_terminal
requested_url
final_url
http_status
content_type
body_sha256
text_sha256
raw_snapshot_ref       content-addressed local path
text_snapshot_ref      content-addressed local path
extracted_title
error_code / message / retryable
```

Successful identical bodies reuse the same content-addressed snapshot. Failures
remain visible and resumable rather than becoming missing rows.

### `artifact_tag` (deferred until used)

Tags must not be baked into artifact identity. When a real consumer needs
them, use a separate provenance-bearing relation:

```text
artifact_id
namespace
tag
assigned_by           human | rule | model
run_id
assigned_at
```

## Ingestion flow for the first implementation

```text
stored X post
    |
    +-- keep X permalink as source_url
    |
    +-- read entities.urls[]
            |
            +-- retain observed t.co alias
            +-- use provider expanded_url when present
            +-- follow only residual redirects
            +-- remove fragment and known tracking parameters
            +-- apply narrow site rules (for example arXiv abs/pdf)
                    |
                    +-- UPSERT artifact
                    +-- UPSERT aliases
                    +-- INSERT source observation
                    +-- fetch once when selected for the bounded oracle
```

Canonicalization is deliberately conservative. Different canonical URLs are
not auto-merged merely because their current bodies hash identically; mirrors,
syndication, and mutable landing pages make that unsafe.

## How a future GitHub source fits without building it now

A GitHub release adapter would preserve its own raw response and emit a stable
source reference such as:

```text
source_kind        github_release
source_provider    github
source_external_id openai/repo:release:v1.2
source_url         https://github.com/openai/repo/releases/tag/v1.2
```

If that release page is itself the substantive resource, the observation uses
`relation=self_publishes` and points to the page’s artifact row. If an X post
and an RSS entry also point there, they add observations to that same artifact.
Nothing about the artifact identity or fetch store changes.

## Query behavior

- “Show every source that noticed this paper” queries
  `artifact_observation` for one `artifact_id`.
- “Show artifacts associated with this event” joins current event membership
  to X post IDs, then joins observations. This is a derived view, not ownership.
- “Has this page already been fetched?” looks up the artifact and its latest
  successful `artifact_fetch`.
- A future artifact Feed can group by artifact and show first/last seen plus
  source convergence, but that UI is intentionally deferred.
