# Canonical Artifact Library

The Artifact Library is the deterministic boundary between **where a resource
was observed** and **the underlying resource itself**. It indexes outbound
links from the root X account's kept post and same-account reply thread without
fetching the whole corpus, then
fetches a deliberately bounded cohort into replayable raw and clean-text
snapshots.

## Mental model

```text
immutable X evidence
    -> URL candidate ledger
    -> canonical artifact + aliases
    -> independently traceable source observations
    -> bounded fetch attempts
    -> content-addressed raw body and clean text

frozen kept event + human-reviewed official source
    -> explicit event supplement ledger
    -> the same canonical artifact / fetch / snapshot boundary
```

An ordinary X status permalink remains source evidence. A paper, article,
repository, announcement, video, or X long-form Article linked by that source
may become an artifact. Event envelopes never own artifacts: observations bind
to the stable source kind, provider, external ID, and source snapshot hash, so
event regrouping cannot orphan provenance.

## Storage

- Catalog: `data/derived/artifacts/artifacts.db`
- Raw bodies: `data/raw/artifacts/body/sha256/<prefix>/<sha>.bin`
- Clean text: `data/derived/artifacts/text/sha256/<prefix>/<sha>.txt`

The SQLite store is derived and rebuildable. Raw X observations remain the
source of truth. Fetched response bodies are immutable, content-addressed
evidence.

| Table | Purpose |
| --- | --- |
| `artifact_import_run` | Frozen source runs, input fingerprint, policy, and replay outcome. |
| `artifact` | One conservative canonical URL identity and fetch-oriented kind. |
| `artifact_alias` | Observed, expanded, redirect, and declared-canonical URL forms. |
| `artifact_observation` | Stable source record that points to an artifact. |
| `artifact_disclosure` | The direct wrapper through which an embedded source became visible. |
| `artifact_import_candidate` | Accepted and excluded URL decisions, including reason codes. |
| `artifact_event_supplement` | Human-reviewed official primary sources attached to one exact frozen kept event, with triage hashes and review provenance. |
| `artifact_fetch_run` / `_item` | One frozen, ordered validation cohort. |
| `artifact_fetch` | Append-only attempts, redirects, metadata, hashes, snapshots, and explicit errors. |

## URL rules

Canonicalization is conservative and versioned as `artifact-url-v1`:

- remove fragments and known tracking parameters;
- normalize host/scheme/ports and narrow known site forms such as arXiv;
- preserve meaningful query parameters;
- retain every observed and expanded form as an alias;
- converge redirect aliases transactionally;
- never merge different URLs solely because their bodies currently match;
- ignore ordinary X status/profile/media self-links;
- admit X long-form Article URLs explicitly;
- do not guess the target of a card-only `t.co` URL.

The displayed artifact kind is a deterministic URL-shape hint, not a semantic
content classification. Known hosts and paths identify papers, repositories,
videos, articles, and announcement-like URLs; unmatched URLs remain `other`.

Artifact admission is narrower than the visible envelope. A URL is eligible
only when its owning post is the root post or a reply from the same stable X
account in the same root conversation. Other accounts' replies, quotes,
retweets, and nested links remain visible reactions in Evidence but cannot
create an artifact association or enter an Insight packet. Conversation
identity retains valid same-account links when an intermediate reply is absent
from the Feed snapshot.

## Fetch contract

`bounded-public-v1` uses one sequential worker and manually follows a bounded
redirect chain. Every initial URL and redirect target is restricted to HTTP(S),
has credentials removed, is DNS-resolved, and must resolve only to globally
routable addresses. Robots directives, response size limits, timeouts, content
types, retryability, and terminal errors are persisted.

HTML uses Trafilatura, PDFs use pypdf, and textual JSON/XML/plain responses use
bounded decoding. A page that exposes only a client-rendered loading/error shell
is a terminal extraction failure rather than misleading clean text. Successful
raw and text payloads are written atomically under their SHA-256 paths.

`jina-reader-v1` is a narrow second attempt for ordinary public HTML pages
that already failed `bounded-public-v1`. It calls Jina Reader through its JSON
API, preserves the complete provider response as the raw snapshot, stores the
returned Markdown as clean text, and records `retrieval-provider=jina_reader`
plus Reader token usage in the attempt metadata. The fetch policy remains
explicit, so Reader output cannot be mistaken for a direct origin response.
Known deferred adapters (X, LinkedIn, YouTube, and hosted forms), repositories,
papers, videos, robots-denied pages, authenticated content, and paywalls do not
enter this fallback. Reader is replaceable retrieval infrastructure, not part
of artifact identity.

The operator CLI is not a public arbitrary-URL fetch service. DNS is rechecked
before each request, but the remaining DNS-rebinding race is accepted only for
this local, trusted, one-worker command.

## Reviewed primary-source supplements

The normal catalog remains mechanically derived from outbound links. When a
kept event reports a material fact through a secondary X source but does not
link the underlying official document, a reviewer may attach that document
through a strict `artifact-reviewed-supplement-v1` manifest. This is a separate
ledger, not a synthetic X URL candidate: it records the exact triage run,
event, input/snapshot hashes, rank, official-source role, publication date,
rationale, reviewer, review timestamp, and manifest hash.

Import is idempotent. Replaying the same manifest reuses the association;
changing the assertion for the same artifact and frozen event fails instead of
silently rewriting provenance. The imported artifact still needs a successful
bounded fetch before it can strengthen an Audience Insights packet. Exact-ID
fetch selection prevents a one-source recovery from widening into a crawl.

Manifest shape:

```json
{
  "schema_version": "artifact-reviewed-supplement-v1",
  "reviewed_by": "human-review",
  "reviewed_at": "2026-07-15T08:00:00+00:00",
  "items": [
    {
      "event_id": "<stable-event-sha256>",
      "artifact_url": "https://www.sec.gov/Archives/edgar/data/...",
      "evidence_role": "official_primary_source",
      "source_published_at": "2026-07-06",
      "rationale": "The official filing directly substantiates the reported event."
    }
  ]
}
```

## Operator commands

Commands are non-interactive and emit a stable JSON envelope by default. Use
`--plain` only for local inspection.

```bash
fli artifacts import-kept --no-input
fli artifacts import-reviewed-supplements \
  --manifest path/to/supplements.json \
  --triage-db path/to/triage.db \
  --no-input
fli artifacts summary --no-input
fli artifacts inspect --limit 20 --no-input
fli artifacts fetch --limit 30 --no-input
fli artifacts fetch --artifact-id <artifact-sha256> --no-input
fli artifacts reader-fallback --no-input
fli artifacts inspect-fetches --no-input
```

Import replay returns `reused=true` when its frozen input is unchanged. Fetch
replay resumes only retryable artifacts, never repeats a success or terminal
failure, stops after three attempts, and then returns the frozen completed run.
Reader replay follows the same append-only attempt and lease rules; it resumes
retryable failures and never repeats a successful artifact. Authentication is
optional and comes only from `JINA_API_KEY` in the environment or the ignored
repo-local `.env` generated by
`scripts/local/secrets/bootstrap_local_env_from_keyvault.sh`; command-line
secret flags are deliberately absent.
`summary` reports artifact outcomes separately from network attempts.

## Operator inspection surface

The always-on app exposes the catalog at `/evidence/artifacts`, backed by read-only
`/api/artifacts/dates` and `/api/artifacts` projections. Its shared Feed-style
seven-date navigator filters by the UTC publication day of the X source
observation, never by retrieval time. Date counts are distinct canonical
artifacts; an artifact appears on each day it was observed, and exact-day
search matches every source observation for that artifact rather than only the
representative latest one. Within a selected day, one row per canonical
artifact inherits the best rank among the accepted Feed envelopes that exposed
it; the smallest rank wins when several observations converge. Source time is
shown separately, and the inherited rank is provenance rather than a new
artifact-quality score. Bounded pagination keeps the surface fast. Expanding a
row shows the canonical URL and deep-links to the exact ranked Feed envelope
that disclosed it; the Feed preserves the full evidence context and onward X
link. When that exact envelope exposes multiple canonical artifacts, the UI
keeps every artifact independently expandable while rendering their inherited
rank once in a shared left rail; no catalog records are merged. Expanded
provenance also shows first-seen time, retrieval state and
method, snapshot size, and any current error. It does not summarize or classify
artifact content; those are later cited-insight responsibilities.

## Current primary-author rebuild

The 2026-07-15 clean rebuild applied
`kept-envelope-primary-author-thread-artifacts-v1` across the complete stored
Feed. It produced 1,897 candidate decisions (1,859 accepted and 38 excluded),
1,432 source observations/disclosures, and 1,334 canonical artifacts. A
corpus-wide lineage audit found zero foreign-author or wrong-conversation rows
and zero missing source/root records. The clean store retained 32 still-eligible
successful snapshots, including all 22 fetched X Articles; old failures and
reviewed supplements were not carried forward.

Anthropic's global-workspace envelope retains the Anthropic research page and
the later Neuronpedia demo linked from Anthropic's own reply thread. Satya
Nadella's envelope retains only his X Article; the Eve link from another
account's reaction is absent.

## Historical Artifact Store v1 evidence

The superseded 2026-07-14 rebuild indexed 3,072 candidate decisions from the corrected
kept envelopes: 2,911 accepted occurrences, 161 exclusions, 1,739 source
observations/disclosures, and 1,566 final canonical artifacts after redirect
convergence. The frozen 30-artifact cohort produced 19 clean-text successes,
four explicit terminal failures, and seven exhausted retryable failures. All 19
successful texts were manually usable. See
`docs/projects/archive/canonical-artifact-library/resources/fetch-cohort-audit-2026-07-14.md`.

The first Reader fallback proof recovered all three ordinary public-page
failures in that cohort: the OpenAI GPT-5.6, GPT-Live, and ambitious-work
announcements. It produced 82,476 clean-text characters total with zero Reader
failures; the original three HTTP 403 attempts remain in the ledger alongside
the three successful Reader attempts.

The catalog intentionally stops there. Fetching the remaining long tail across
hundreds of hosts would turn this proof into a general crawler before a cited
consumer has demonstrated that breadth is useful.

## Future sources

A future RSS entry or GitHub release supplies its own stable source identity and
creates another `artifact_observation`. If it points to an existing canonical
URL, it reuses the artifact and snapshot. This compatibility does not require a
generic adapter framework today, and no RSS/GitHub ingestor is implemented in
v1.
