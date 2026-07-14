# URL Corpus Audit — 2026-07-14

## Verdict

The corrected kept-envelope corpus is large enough to justify **catalog all,
fetch bounded**:

- Nine completed canonical-v8 triage snapshots contain 4,402 kept
  envelope-day rows, 3,661 distinct events, and 7,561 distinct referenced X
  post IDs.
- The envelopes contain 4,264 URL occurrences and 2,925 distinct
  wrapper-post/expanded-URL edges. Those reduce to 1,671 distinct expanded
  URLs and 1,793 distinct observed `t.co` aliases.
- 1,586 expanded URLs are locally artifact-like. A conservative pre-fetch
  identity projection produces 1,568 provisional artifacts across 642 hosts.
  Fetching all of those immediately is not a useful first quality oracle: 497
  hosts occur once and 580 occur no more than twice.
- 85 expanded URLs should not become v1 artifacts: 66 ordinary X statuses,
  ten X broadcasts/spaces pending an explicit product rule, two X media
  self-links, one X profile/internal link, three external profile/channel
  pages, two Discord invites, and one search-results page.
- Every one of the 2,970 URL-entity locations has provider `expanded_url`.
  Missing expansion exists only in provider card metadata: 31 unique card-only
  `t.co` values, seven resolvable elsewhere in the published Feed and 24 still
  ambiguous. They must not silently become separate artifacts.

The most important implementation finding is a provenance bug in the existing
triage envelope representation. URLs inside `quoted_tweet` are assigned to the
outer quoting post. All 1,128 nested URL locations have a stable nested owner
ID present in the kept Feed. Using that owner reduces all wrapper-post/URL
edges from 2,925 to 1,826, and eligible edges from 2,812 to 1,739. The artifact
importer must traverse the frozen Feed JSON, bind a URL to the tweet object that
actually contains its entity, and retain the outer disclosure post separately.

No network requests were made in this audit.

## Trusted input boundary

- Published event run:
  `f8999fcd2b674bf46557023ec8dcab2ac4a8bc115fea8158b4b713a276b588a9`
- Published Feed run:
  `adb2b4949de74a7a3120e71b62366acfcdca0656d0b49c07af10d4e5323f7f96`
- Triage runs:
  `triage-v2.2-canonical-v8-2026-07-{05..13}-top1000`

An envelope row means one kept event on one triage day. The same event can
appear on multiple days: 3,075 events appear once, 461 twice, 101 three times,
20 four times, three five times, and one seven times. Selection and fetching
must therefore deduplicate across days before doing network work.

| Day | Candidates | Keep | URL occurrences | Unique expanded | Artifact-like | Excluded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-07-05 | 560 | 233 | 203 | 149 | 145 | 4 |
| 2026-07-06 | 863 | 431 | 401 | 258 | 250 | 8 |
| 2026-07-07 | 1,000 | 566 | 522 | 299 | 289 | 10 |
| 2026-07-08 | 1,000 | 605 | 585 | 310 | 291 | 19 |
| 2026-07-09 | 1,000 | 639 | 689 | 337 | 314 | 23 |
| 2026-07-10 | 1,000 | 594 | 575 | 303 | 286 | 17 |
| 2026-07-11 | 937 | 464 | 391 | 206 | 188 | 18 |
| 2026-07-12 | 737 | 314 | 319 | 159 | 143 | 16 |
| 2026-07-13 | 1,000 | 556 | 579 | 300 | 286 | 14 |

The per-day unique columns overlap and must not be summed for corpus totals.

## Candidate composition

Counts below are unique expanded URLs before redirect fetching. “Conservative
identity” removes fragments and enumerated tracking keys, applies the X Article
and arXiv rules, lowercases the host, and removes default ports. It deliberately
preserves scheme, `www`, path/trailing-slash distinctions, and all remaining
query parameters until a redirect or declared canonical proves equivalence.

| Class | Unique expanded | Conservative identity |
| --- | ---: | ---: |
| General HTML/page | 971 | 958 |
| Paper or PDF | 205 | 201 |
| GitHub repository/tree/release/PR | 135 | 134 |
| X long-form Article | 116 | 116 |
| YouTube/video | 83 | 83 |
| Residual shortener/redirect | 74 | 74 |
| Other external social post | 2 | 2 |
| **Artifact-like total** | **1,586** | **1,568** |
| Excluded/deferred | 85 | 85 |

The most common artifact hosts after conservative identity are arXiv (184),
GitHub (134), X long-form (116), Hugging Face (63), YouTube (49 plus 34
`youtu.be`), ICML (29), OpenReview (20), OpenAI (15), Luma (13), bit.ly (12),
ACL Anthology (10), LinkedIn short links (10), NVIDIA short links (10), and
Nature (9). The long tail is much larger than the head.

Provider preview metadata is useful but not an identity source. Kept envelopes
contain 1,620 preview occurrences: 1,262 link cards and 358 X Articles. After
deduplicating the current wrapper-owned keys there are 889 link-card records
and 254 X-Article records, but only 116 distinct X-Article URLs. The difference
is primarily the quoted-wrapper attribution bug, not 254 articles.

## Alias and canonicalization evidence

- All 2,970 entity locations use an observed `t.co` URL. Provider expansion
  turns 1,793 distinct observed aliases into 1,671 distinct expanded values.
- 86 exact expanded URLs have more than one observed `t.co` alias. Broader
  fetch-time convergence fixtures include the Meta AI homepage (ten observed
  aliases / three expanded spellings), the Thinking Machines worldview post
  (four aliases), and the GPT-Live announcement (three aliases).
- 683 expanded URLs appear under multiple wrapper posts, but only 106 appear
  under multiple actual owner posts. Wrapper convergence is therefore not a
  safe proxy for independent source observations.
- Conservative local rules merge 1,586 artifact-like expanded values into
  1,568 provisional identities. A broader rule that upgrades every HTTP URL to
  HTTPS, removes `www`, strips trailing slashes, and collapses path slashes
  would produce 1,549. Those extra 19 merges are tempting but not locally
  proven; let the fetch redirect/declared-canonical phase establish them.
- There are 285 distinct HTTP artifact-like values, including every provider X
  Article URL plus ordinary sites. Apply the HTTP→HTTPS rule only to known site
  families before fetching; preserve the original alias in all cases.
- There are 26 distinct URLs with fragments. Fragments do not affect HTTP
  retrieval and should not define artifact identity, but aliases must preserve
  them because values such as arXiv `#page=72`, GitHub line/section anchors,
  slides, and documentation anchors are useful locators.

Query handling must remain conservative. Of 149 distinct artifact-like URLs
with a query, 53 contain known tracking keys and 111 contain potentially
meaningful keys (the sets overlap). Safe removal evidence covers `utm_*`,
`gclid`/`fbclid`, `mc_*`, YouTube `si`/`feature`/`pp`, and Medium `source`.
Preserve keys such as OpenReview `id`, YouTube `v`/`t`, Dropbox `rlkey`/`dl`,
Google Drive `usp`, podcast episode `i`, Figma node/page state, and publisher
gift/share tokens. Do not globally remove generic keys such as `source`, `s`,
`id`, `key`, `from`, or `r`.

arXiv `abs`, `pdf`, and `html` forms should share a document identity while
remaining aliases/representations. Do not merge different URLs merely because
their fetched body hashes happen to match.

## Data-boundary bugs and required importer behavior

### 1. Quoted URLs are assigned to the wrapper

`insight_triage_runs._expanded_urls` iterates a row payload and its
`quoted_tweet`, then stores all discovered URLs under the row's post ID.
`_provider_artifacts` does the same for cards and X Articles. The corpus has
1,128 such nested URL locations: 675 HTML, 138 X Articles, 111 paper/PDF, 85
GitHub, 59 residual redirects, 33 video, 21 X statuses, and six other links.

All 1,128 nested locations' 544 distinct owner IDs exist among the kept Feed
references. The importer must use the nested tweet's `id` as
`source_external_id`, use its own permalink, and deduplicate `(owner post,
artifact, relation)`. Preserve the outer wrapper as `disclosure_external_id`
(or equivalent provenance), rather than counting every quoting amplifier as a
post that independently linked the artifact.

Recursive depth is not a remaining hole in this corpus: three URL locations
occur at nesting depth two or greater, but all three owners are present in kept
Feed rows and add zero new owner/URL edges after owner-level deduplication.

### 2. Raw-only lookup misses embedded source rows

Every referenced post exists in the published Feed, but only 3,827 of 7,561
have an exact `(provider, post_id, raw_sha256)` row in
`x_post_observation`. All 3,734 missing exact observations have Feed role
`embedded`; 3,696 do not have any current `x_post` row, while 38 were observed
later under a different snapshot.

The immutable evidence still exists inside the disclosure wrapper's raw JSON,
but an importer that joins owner IDs only against `x_post` will silently lose
about half of the referenced posts. Read the published `feed_post.raw_json`
snapshot for import, and persist enough snapshot/disclosure provenance to trace
an embedded owner back to immutable raw evidence.

### 3. Card-only short URLs are not artifact identities

URL entities have zero missing expansions. Link-card extraction nevertheless
emits 120 occurrences / 31 unique `t.co` card URLs absent from envelope
`urls[]`. Seven aliases resolve elsewhere in the published Feed; 24 do not.
Multi-link posts make title-based guessing unsafe—for example,
`https://t.co/idELM9XZsC` has a Llama-Nemotron card while its post carries six
different arXiv links.

Use `entities.urls[]` as the local artifact-candidate boundary. Attach card
title/preview only when its `card_url` alias matches a known entity alias or a
fetch proves the redirect. Keep other card metadata as unbound diagnostics;
do not insert a second artifact or guess which link owns the title.

## Recommended first fetch cohort

Select **30 provisional artifacts**, not 30 post/URL edges:

1. For each conservative artifact identity, take its best kept-envelope score,
   using normalized within-day rank `(rank - 1) / (candidate_count - 1)` so a
   560-item day and a 1,000-item day are comparable.
2. Tie-break by root-owned observation, then more independent owner posts, then
   canonical URL.
3. Fill strata of 12 HTML pages, five paper/PDF, four GitHub, three video,
   three X long-form, and three residual redirects.
4. Cap one source event at two selections and one host at four. Exclude
   statuses, profiles, media self-links, invites, search pages, and unresolved
   card-only aliases.
5. After redirects, collapse any selected aliases that converge before
   downloading/extracting twice. Stop after this cohort for manual quality and
   failure review; do not automatically roll into all 1,568 identities.

This rule yields the following deterministic fixtures from the audited
snapshot. Rank is the frozen within-day triage rank.

| Type | Day / rank | Fixture |
| --- | --- | --- |
| HTML | 07-06 / 1 | `https://www.anthropic.com/research/global-workspace` |
| HTML | 07-09 / 1 | `https://openai.com/index/chatgpt-for-your-most-ambitious-work/` |
| HTML | 07-07 / 1 | `http://eliebak.com/viz/jspace-open` |
| HTML | 07-07 / 2 | `https://lilianweng.github.io/posts/2026-07-04-harness/` |
| HTML | 07-10 / 2 | `https://thinkingmachines.paperform.co/` |
| HTML | 07-08 / 2 | `https://openai.com/index/introducing-gpt-live/` |
| HTML | 07-10 / 2 | `https://thinkingmachines.ai/blog/the-future-worth-building-is-human/` |
| HTML | 07-07 / 2 | `https://ii.inc/blog/post/zenith` |
| HTML | 07-13 / 2 | `https://www.linkedin.com/posts/leonidboytsov_a-gentle-reminder-from-the-trenches-if-you-share-7431127785026301952-p4R8/` |
| HTML | 07-06 / 2 | `https://gwern.net/scaling-hypothesis` |
| HTML | 07-12 / 2 | `http://Eve.dev` |
| HTML | 07-09 / 3 | `https://openai.com/index/gpt-5-6/` |
| Paper | 07-11 / 4 | `https://arxiv.org/abs/2510.01123` |
| PDF | 07-11 / 4 | `https://cdn.openai.com/pdf/04d1d1e4-bc75-476a-97cf-49055cd98d31/cdc_prompt.pdf` |
| PDF | 07-07 / 10 | `https://eric-tramel.github.io/assets/doc/synthetic-data-powering-pretraining-berkeley-2026.pdf` |
| Paper | 07-07 / 11 | `https://arxiv.org/abs/2308.09124` |
| PDF + locator | 07-05 / 9 | `https://arxiv.org/pdf/2603.18073#page=72` |
| GitHub repo | 07-09 / 3 | `https://github.com/mem0ai/openmemory` |
| GitHub repo | 07-13 / 4 | `https://github.com/weklund/grok-network-monitor` |
| GitHub tree | 07-09 / 9 | `https://github.com/meta-models/meta-model-cookbook/tree/main/03_use_cases/13_macos_cua` |
| GitHub repo | 07-05 / 9 | `https://github.com/karpathy/autoresearch` |
| Video | 07-08 / 42 | `https://youtu.be/Yy3JH6dDugc` |
| Video | 07-06 / 53 | `https://www.youtube.com/watch?v=RGxqW2TDw4E` |
| Video | 07-11 / 86 | `https://www.youtube.com/watch?v=Mw60FH5iflI` |
| X Article | 07-12 / 2 | `http://x.com/i/article/2076319195718090753` |
| X Article | 07-12 / 12 | `http://x.com/i/article/2075414550644703232` |
| X Article | 07-06 / 21 | `http://x.com/i/article/2074150241390256128` |
| Redirect | 07-07 / 8 | `https://go.meta.me/7f4427` |
| Redirect | 07-09 / 8 | `https://go.meta.me/ff8e2c` |
| Redirect | 07-08 / 42 | `https://nvda.ws/4p6tDjg` |

Additional exclusion/failure fixtures should remain in tests but outside the
fetch cohort:

| Boundary | Fixture | Expected handling |
| --- | --- | --- |
| Ordinary X status | `https://x.com/AnthropicAI/status/2075005777522172146?s=20` | source context only |
| X media self-link | `https://x.com/RemiCadene/status/2074442725814878510/video/1` | exclude |
| X broadcast | `https://x.com/i/broadcasts/1DGleeQXWyOJL` | defer pending explicit rule |
| X profile/internal | `http://X.com` | exclude |
| GitHub profile | `https://github.com/cadene` | exclude |
| YouTube channel | `https://www.youtube.com/@PeterYangYT?sub_confirmation=1` | exclude |
| Invite | `https://discord.gg/6adJVU7wNJ` | exclude |
| Search navigation | `https://www.google.com/search?q=what+is+the+app+builder+for+gemini` | exclude |
| Ambiguous card alias | `https://t.co/idELM9XZsC` | retain unbound; do not guess |
| Non-HTML body | `http://x.ai/cli/install.sh` | artifact text or truthful unsupported type |

X Article raw JSON contains title and preview only, not full article text.
Video pages likewise should not be counted as successful clean-text extraction
merely because a title was found. These strata are deliberate failure probes:
store provider title/preview and a truthful terminal extraction result if the
bounded fetch cannot obtain substantive text.

## Commands and method

The exact run-discovery and daily-count commands were:

```sh
sqlite3 -header -column data/derived/signal-events/events.db \
  "SELECT * FROM signal_publication; SELECT run_id,feed_run_id,cluster_count,member_count,created_at FROM event_run ORDER BY created_at DESC LIMIT 12;"

for db in data/derived/cited-insights/triage/triage-v2.2-canonical-v8-2026-07-{05,06,07,08,09,10,11,12,13}-top1000/triage.db; do
  sqlite3 -separator '|' "$db" \
    "SELECT '$db',day,run_id,expected_count FROM run_meta; SELECT decision,status,count(*) FROM triage_item GROUP BY decision,status ORDER BY decision,status;"
done
```

The corpus join/classification was run with a temporary read-only Python audit
under `tmp/` and summarized with `jq`:

```sh
python tmp/url_corpus_audit.py > tmp/url-corpus-audit.json
jq '{kept_envelope_rows,unique_kept_event_ids,unique_envelope_post_ids,envelope_url_occurrences,unique_observed_urls,unique_expanded_urls,class_counts,subtype_unique_url_counts,provisional_canonical_eligible_count}' tmp/url-corpus-audit.json
```

The audit loaded the published Feed rows once, parsed root/quoted/retweeted URL
entities, compared the envelope's exact `(post_id,url)` set, rebound nested
entities to their own tweet IDs, checked exact snapshot rows in
`x_post_observation`, and applied the classification rules stated above. The
envelope edge set and the one-level Feed JSON edge set matched exactly (zero
missing on either side). Disposable script/output files were removed after the
durable findings were written.
