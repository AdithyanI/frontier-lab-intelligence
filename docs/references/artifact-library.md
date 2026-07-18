# Canonical Artifact Library

The Artifact Library is the deterministic boundary between **where a resource
was observed** and **the underlying resource itself**. It indexes outbound
links from a Feed Event's root X post and same-account reply thread without
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

frozen Event snapshot + human-reviewed official source
    -> explicit event supplement ledger
    -> the same canonical artifact / fetch / snapshot boundary
```

An ordinary X status permalink remains source evidence. A paper, article,
repository, announcement, video, or X long-form Article linked by that source
may become an artifact. Events never own artifacts: observations bind
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
| `artifact_event_supplement` | Human-reviewed official primary sources attached to one exact frozen Event, with source hashes and review provenance. |
| `artifact_fetch_run` / `_item` | One frozen, ordered validation cohort. |
| `artifact_fetch` | Append-only attempts, redirects, metadata, hashes, snapshots, and explicit errors. |

## URL rules

Canonicalization and candidate admission are conservative and versioned as
`artifact-url-v2`:

- remove fragments and known tracking parameters;
- normalize host/scheme/ports and narrow known site forms such as arXiv;
- preserve meaningful query parameters;
- retain every observed and expanded form as an alias;
- converge redirect aliases transactionally;
- never merge different URLs solely because their bodies currently match;
- ignore ordinary X status/profile/media self-links;
- admit X long-form Article URLs explicitly;
- do not guess the target of a card-only `t.co` URL.
- exclude exact generic `/search` navigation endpoints both at candidate
  admission and after redirects, before content snapshot or identity
  convergence.

The stored artifact kind is a deterministic, fetch-oriented URL-shape hint,
not a semantic content classification. The product exposes five stable types:
`web`, `x_article`, `document`, `repository`, and `video`. X long-form Article
URLs map to `x_article` because they have an exact URL identity and dedicated
retrieval contract. Papers map to `document`; ordinary articles,
announcements, and unmatched HTML pages map to `web`. This keeps the UI honest
without requiring fragile Article-versus-page inference, while preserving the
one article subtype that is operationally exact.

Artifact admission is narrower than the visible Event. A URL is eligible
only when its owning post is the root post or a reply from the same stable X
account in the same root conversation. Other accounts' replies, quotes,
retweets, and nested links remain visible reactions in Evidence but cannot
create an artifact association or enter an Insight packet. Conversation
identity retains valid same-account links when an intermediate reply is absent
from the Feed snapshot. An Event preview is never sufficient by itself: the
URL must also be bound to that exact post in its immutable raw payload, or the
candidate fails closed.

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

The Artifact UI loads normalized text only when the default-collapsed Preview
control inside a retrieved row is explicitly expanded,
shows the extractor and character count beside a bounded preview, and links to
`/api/artifacts/{artifact_id}/text` for the complete plain-text response. The
endpoint resolves the content-addressed snapshot server-side and never exposes
local filesystem paths. Jina Reader snapshots preserve Markdown syntax; HTML,
PDF, and X Article adapters expose their normalized text representation.

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
fli artifacts import-feed --no-input
fli artifacts import-reviewed-supplements \
  --manifest path/to/supplements.json \
  --triage-db path/to/triage.db \
  --no-input
fli artifacts summary --no-input
fli artifacts inspect --limit 20 --no-input
fli artifacts audit-lineage --no-input
fli artifacts fetch --limit 30 --no-input
fli artifacts fetch --artifact-id <artifact-sha256> --no-input
fli artifacts reader-fallback --no-input
fli artifacts revalidate-content --no-input
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
All extraction adapters share the same deterministic content validator. It
rejects placeholder-dominated bodies and recognizable bot, consent,
authentication, client-rendering, loading, not-found, region, and error shells.
`revalidate-content` applies the current contract to stored successes,
quarantines only their derived normalized-text projection, preserves immutable
raw snapshots, and is idempotent.
`summary` reports artifact outcomes separately from network attempts.
`audit-lineage` is read-only and exits nonzero with `E_INTEGRITY` when the live
catalog contains a foreign author, wrong conversation, unbound URL, stale
snapshot, unsupported observation, or artifact without provenance. The proof
uses the frozen import candidate and its raw Feed conversation, so historical
triage databases may be removed without disabling the guard. It emits the same
versioned JSON envelope as the other commands. `scripts/check-fast.sh` runs it
automatically when the ignored local catalog exists; clean clones without
derived data skip the guard. The report's `coverage` object distinguishes roots
rechecked directly from replies whose roots were not retained in the frozen
Feed run; those replies still require an unchanged accepted import candidate,
raw source snapshot, URL owner, observation, and disclosure.

## Operator inspection surface

The always-on app exposes the catalog at `/evidence/artifacts`, backed by read-only
`/api/artifacts/dates` and `/api/artifacts` projections. Its shared Feed-style
seven-date navigator filters by the UTC publication day of the X source
observation, never by retrieval time. Date counts are distinct canonical
artifacts; an artifact appears on each day it was observed, and exact-day
search matches every source observation for that artifact rather than only the
representative latest one. Within a selected day, one row per canonical
artifact inherits the best rank among the Feed Events that exposed
it; the smallest rank wins when several observations converge. Source time is
shown separately, and the inherited rank is provenance rather than a new
artifact-quality score. Bounded pagination keeps the surface fast. Expanding a
row shows the canonical URL and deep-links to the exact ranked Feed Event
that disclosed it; the Feed preserves the full evidence context and onward X
link. When that exact Event exposes multiple canonical artifacts, the UI
keeps every artifact independently expandable while rendering their inherited
rank once in a shared left rail; no catalog records are merged. Expanded
provenance also shows first-seen time, retrieval state and
method, snapshot size, and any current error. It does not summarize or classify
artifact content; those are later cited-insight responsibilities.

## Current primary-author rebuild

The active 2026-07-18 import applies
`feed-event-primary-author-thread-artifacts-v2` across the complete stored
Feed. It produced 5,032 candidate decisions (4,627 accepted, 405 excluded, and
zero failed), 4,627 source observations, 4,633 disclosures, and 3,999 canonical
artifacts. The catalog currently has usable text for 3,453 artifacts; 252 are
catalogued but unfetched, 25 are retryable, and 269 are unavailable. A
corpus-wide lineage audit verified all 4,627 accepted candidates and found zero
foreign-author, wrong-conversation, or missing source/root violations. Root
posts and same-author replies are selected directly from the published
Feed/Event pair; no keep/drop or audience
routing database participates in artifact discovery. The repeatable
`audit-lineage` guard also found zero unbound raw URLs, stale snapshots, orphan
observations, undisclosed observations, or artifacts without lineage. Later
imports prune observations absent from the current Feed/Event snapshot while
retaining successful content snapshots for canonical artifacts that remain.

Anthropic's global-workspace Event retains the Anthropic research page and
the later Neuronpedia demo linked from Anthropic's own reply thread. Satya
Nadella's Event retains only his X Article; the Eve link from another
account's reaction is absent.

## Historical Artifact Store v1 evidence

The superseded 2026-07-14 rebuild indexed 3,072 candidate decisions from the corrected
Feed Events: 2,911 accepted occurrences, 161 exclusions, 1,739 source
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

On 2026-07-15, a second frozen proof tested only ordinary Web artifacts. The
30 selected source identities converged to 29 canonical pages; native bounded
retrieval extracted 27 and the existing Reader fallback recovered the two
native terminal failures. Twenty-six snapshots contain at least 1,000
characters and the cohort contains 428,942 extracted characters total. The
three thin results are interactive/profile shells rather than evidence-rich
pages. A repeated Meta short-link exposed and now has regression coverage for
an idempotency edge: when a later catalog import recreates a redirect source,
the fetcher reconnects it to the already-fetched canonical target instead of
creating a duplicate deterministic fetch attempt.

A rendered-source audit then compared 18 varied Web pages with their stored
snapshots. Native Trafilatura snapshots consistently retained the substantive
source text while removing navigation and page chrome. The two Jina Reader
recoveries also retained the complete underlying Nature and OpenAI content,
but were less selective: the Nature paper begins after roughly 4,400
characters of cookie/navigation material, and the OpenAI article begins after
roughly 1,500 characters of navigation. Reader output is therefore a strong
availability fallback, not a cleaner default than native extraction.

The remaining long tail is still not fetched indiscriminately. Further
expansion should remain source-class specific and should follow demonstrated
use by the cited-insight consumer.

## Future sources

A future RSS entry or GitHub release supplies its own stable source identity and
creates another `artifact_observation`. If it points to an existing canonical
URL, it reuses the artifact and snapshot. This compatibility does not require a
generic adapter framework today, and no RSS/GitHub ingestor is implemented in
v1.
