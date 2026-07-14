# Artifact Store v1 — Content Extraction Decision

## Recommendation

Use a small, explicit three-part runtime stack:

- `httpx>=0.28,<1` for bounded streaming HTTP and inspectable manual redirects;
- `trafilatura>=2.1,<3` for HTML title/metadata and main-text extraction;
- `pypdf>=6,<7` for digitally born PDFs.

All three must be declared runtime dependencies. `httpx` is currently only a
development dependency, `trafilatura` is not installed, and the locally
available `pypdf` is supplied by the machine rather than this project. Relying
on the current environment would make extraction non-reproducible.

Do not use Trafilatura's downloader. Fetching is an application security and
provenance boundary; the application should own URL validation, redirects,
limits, snapshots, retry state, and response metadata. Feed the preserved body
bytes into Trafilatura offline. Its current API can return main text plus
metadata and can omit comments while retaining tables and structural
formatting ([official core API](https://trafilatura.readthedocs.io/en/latest/corefunctions.html)).
Version 2.1.0 supports Python 3.13 and 3.14
([PyPI metadata](https://pypi.org/project/trafilatura/)).

`pypdf` is sufficient for text-layer PDFs, but it is deliberately not OCR and
cannot recover text from scanned images. PDF reading order, headers, tables,
math, and whitespace can be imperfect because PDF has no semantic text layer
([official limitations](https://pypdf.readthedocs.io/en/5.7.0/user/extract-text.html)).
That limitation should become an explicit extraction result, not an OCR
project hidden inside v1.

## Fetch contract

### Request safety

Accept only `http` and `https`, with no username/password and only ports 80 or
443. Before the initial request **and every redirect hop**:

1. parse and normalize the host;
2. resolve all A/AAAA addresses;
3. reject the hop if any resolved address is loopback, private, link-local,
   multicast, reserved, unspecified, or otherwise non-global;
4. reject hostnames such as `localhost` and literal non-global IPs;
5. disable ambient proxies (`trust_env=False`).

Follow at most five redirects manually and preserve every status and `Location`
in `redirect_chain_json`. HTTPX does not follow redirects by default and makes
the next request/history inspectable
([official redirect behavior](https://www.python-httpx.org/compatibility/#redirects)).
Manual traversal is required because automatic redirect following would skip
per-hop SSRF validation.

This DNS check does not fully eliminate a DNS-rebinding race because the HTTP
transport may resolve the hostname again. For v1, keep fetching as an
operator-run CLI over stored X candidates—never a public arbitrary-URL API—and
record this residual limitation. A pinned-IP/SNI-aware transport or controlled
egress proxy is a later hardening step if public fetch input is introduced.

Use one recognizable user agent, for example
`frontier-lab-intelligence/0.1 artifact-fetch (+local research project)`, and
explicitly advertise `gzip, deflate` only. Avoid cookies, authorization, browser
state, JavaScript rendering, paywall bypasses, and login flows.

### Robots and politeness

For the bounded research cohort, cache one `robots.txt` decision per origin
during a run. Fetch robots through the same safe client and parse its lines
with `urllib.robotparser`; do not call `RobotFileParser.read()` separately.
An explicit disallow is terminal (`robots_disallowed`), a 404 means no rules,
and a transient robots failure is recorded as unknown but does not block one
operator-selected public-page fetch. `urllib.robotparser` exposes `can_fetch`,
`crawl_delay`, and request-rate information
([Python documentation](https://docs.python.org/3/library/urllib.robotparser.html)).

Use at most four global workers and one active request per origin. Honor a
reasonable declared crawl delay, capped for the bounded run, and otherwise use
at least a small per-origin delay. This is page retrieval, not site crawling:
never follow page links beyond the requested redirect chain.

### Streaming and limits

Issue one streaming `GET`; do not add a preliminary `HEAD`, because many sites
treat it differently and it doubles requests. Early-reject a trustworthy
`Content-Length` over the limit, but also enforce the limit while reading
because lengths may be absent or false. HTTPX supports conditional streaming
and decoded byte iteration
([official streaming behavior](https://www.python-httpx.org/quickstart/#streaming-responses)).

Recommended configurable decoded-body limits:

| Kind | Limit | Reason |
| --- | ---: | --- |
| HTML, plain text, JSON/XML | 8 MiB | comfortably covers articles and READMEs while bounding pathological pages |
| PDF | 32 MiB | accommodates normal research papers without accepting arbitrary large downloads |
| Unknown/binary | 8 MiB | enough for sniffing and audit; never treat video/audio/archive/image as extractable text |

Define the raw snapshot as the **HTTP entity body after transfer/content
decoding but before document parsing**. Hash and store exactly those bytes.
This makes replay independent of gzip/deflate choices while preserving the
actual HTML/PDF/text supplied to the extractor. Preserve a safe response-header
subset (`Content-Type`, `Content-Language`, `ETag`, `Last-Modified`,
`Cache-Control`, declared length) rather than cookies or other sensitive
headers.

Use explicit connect/read/write/pool timeouts; never disable them. HTTPX has
timeouts by default, but v1 should persist its chosen values with the fetch
contract ([official timeout behavior](https://www.python-httpx.org/quickstart/#timeouts)).

## Extraction contract

Dispatch using both declared `Content-Type` and body magic; servers regularly
mislabel PDFs as `application/octet-stream`.

### HTML and XHTML

- Pass preserved bytes plus the final URL to `trafilatura.bare_extraction()`.
- Use balanced extraction, `include_comments=False`, `include_tables=True`,
  `include_links=False`, and retain simple structural formatting as Markdown
  or deterministic plain text.
- Take title/author/date/site metadata from the same extraction result. Use
  `og:title` or `<title>` only as a deterministic fallback.
- If main text is empty or implausibly short, record
  `extraction_empty_or_client_rendered`; do not silently replace it with the
  entire navigation-heavy page.
- Do not add a headless browser fallback in v1.

### PDF

- Use `PdfReader` over the preserved bytes, reject encrypted/unreadable files
  truthfully, and extract pages in their stored order.
- Bound both page count and extracted character count in addition to body size
  (recommended 500 pages and 5 million characters).
- Prefer PDF metadata `/Title`; otherwise leave title null rather than guessing
  from the first line.
- If the PDF has pages but negligible extractable text, record
  `pdf_no_text_layer`. Defer OCR.

For arXiv, keep `abs` as the conservative artifact identity while preserving
`pdf` as an alias. A PDF alias may be the requested content URL for full-text
extraction, so `artifact_fetch` must record `requested_url`; it cannot assume
the canonical identity URL was fetched. If only an `abs` page was observed,
extract its HTML/abstract and do not invent an unobserved PDF request in v1.

### Plain text and structured text

Accept `text/*`, `application/json`, and XML media types within the 8 MiB
limit. Decode BOM first, then an explicit `charset` parameter, then UTF-8 with
replacement while recording whether replacements occurred. Normalize only
newlines, trailing whitespace, Unicode NFC, and the final newline; do not
reformat JSON/XML or collapse meaningful internal spacing. A URL basename may
be a display fallback, but it is not extracted title metadata.

GitHub repository, release, and blob pages remain ordinary HTML in v1. Do not
call the GitHub API, rewrite to `raw.githubusercontent.com`, or add per-site
credentials yet. Direct raw/text links are handled as plain text. A JavaScript-
only or extraction-empty GitHub page remains an explicit limitation to review
after the real cohort.

### Snapshot layout and reproducibility

Use content-addressed files written atomically:

```text
data/raw/artifacts/body/sha256/ab/<body_sha256>.bin
data/derived/artifacts/text/sha256/cd/<text_sha256>.txt
```

The clean-text hash covers deterministic UTF-8 bytes after the normalization
above. Keep title separate from clean body text. Record the extractor name,
exact installed package version, and an application options/schema version
such as `html-trafilatura-v1`, `pdf-pypdf-v1`, or `text-v1`. A future extractor
upgrade may derive a new clean-text snapshot from the same raw body without a
network request.

The proposed `artifact_fetch` outline needs a few explicit fields for this
contract: `requested_url`, `status`, `redirect_chain_json`, `response_headers_json`,
`raw_snapshot_ref`, `text_snapshot_ref`, `extractor`, `extractor_version`,
`extracted_title`, `text_char_count`, `error_code`, `error_message`, and
`retryable`. A single free-form `fetch_error` cannot support safe resume or an
auditable terminal/retryable boundary.

## Failure semantics

Every attempt is inserted before network work and completed transactionally.
Never leave an ambiguous missing row.

### Retryable after a bounded attempt

- DNS/connect/TLS/read/write/pool timeout or connection interruption;
- HTTP 408, 425, 429, 500, 502, 503, 504;
- truncated body where the server advertised or framed more data.

Use at most three attempts, respect bounded `Retry-After`, and retain each
attempt. Exhaustion remains `failed_retryable`, so a later explicit resume can
try again. A successful existing snapshot makes the default fetch idempotently
skip; refresh/conditional GET policy is deferred.

### Terminal for v1

- unsafe URL/host/port, credentials, unsupported scheme, or unsafe redirect;
- redirect loop or more than five hops;
- explicit robots disallow;
- ordinary non-retryable 4xx, including authentication/paywall denial and 404;
- body over its limit;
- unsupported media (image, audio, video, archive, executable);
- malformed/encrypted PDF, PDF without a text layer, or empty/client-rendered
  HTML after a successful fetch.

Terminal means “v1 cannot extract this snapshot,” not “the artifact is
unimportant.” Preserve enough metadata and any complete bounded body to audit
or re-extract later.

## Explicit v1 scope

Implement now:

1. safe, bounded GET with manual redirect provenance;
2. content-addressed decoded-body snapshots;
3. deterministic HTML, text, and text-layer PDF extraction;
4. title plus clean-text snapshots;
5. structured retryable/terminal failures and idempotent replay;
6. a small real cohort stratified across HTML, PDF, plaintext/GitHub, arXiv,
   redirects, and known failures.

Defer:

- OCR, browser rendering, login/cookie/paywall handling;
- site-specific GitHub or arXiv APIs, RSS ingestion, or crawling linked pages;
- image/audio/video transcription, Office documents, archives, notebooks;
- semantic duplicate merging, LLM cleanup/classification, cited insights;
- scheduled refresh, conditional GETs, change detection, and public arbitrary-
  URL fetching;
- fully pinned DNS transport or egress proxy unless the fetch surface becomes
  externally callable.

This is the smallest boundary that extracts useful text without confusing a
successful HTTP response with a successful document extraction or turning the
artifact store into a general crawler.
