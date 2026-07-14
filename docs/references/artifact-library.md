# Canonical Artifact Library

The Artifact Library is the deterministic boundary between **where a resource
was observed** and **the underlying resource itself**. It indexes outbound
links from corrected, kept X envelopes without fetching the whole corpus, then
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

Nested quoted and retweeted payloads are traversed recursively. A URL belongs
to the post that actually contains it, not to the outer wrapper that disclosed
that post.

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

## Operator commands

Commands are non-interactive and emit a stable JSON envelope by default. Use
`--plain` only for local inspection.

```bash
fli artifacts import-kept --no-input
fli artifacts summary --no-input
fli artifacts inspect --limit 20 --no-input
fli artifacts fetch --limit 30 --no-input
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

The always-on app exposes the catalog at `/artifacts`, backed by the read-only
`/api/artifacts` projection. The initial surface is intentionally narrow: one
chronological row per canonical artifact ordered by its latest source
observation (never by mutable retrieval time), its fetch-oriented kind, the source
observation that found it, and its current retrieval state. Expanding a row
shows canonical and source URLs, first-seen time, retrieval method, snapshot
size, and any current error. It does not rank, summarize, or classify artifact
content; those are later cited-insight responsibilities.

## Artifact Store v1 evidence

The 2026-07-14 rebuild indexed 3,072 candidate decisions from the corrected
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
