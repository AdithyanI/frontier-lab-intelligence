# Research Notes

Durable research facts for this build: assumptions, source provenance, and
candidate-discovery leads. Keep this compact. The tracker decides what to do
next; this file records the facts behind those decisions.

## Current Assumptions

| Topic | Assumption / decision | Status |
| --- | --- | --- |
| Deadline | 2026-07-20, interpreted as end-of-day Europe/Berlin unless Lars clarifies otherwise. | Confirmable. |
| Submission method | Likely reply on the existing thread with repo/package/write-ups. Do not submit externally without Adi approval. | Open. |
| Scope weighting | Optimize depth around registry, signal-vs-noise, scoring/validation. Keep UI light. | From prompt rubric. |
| Labs | Start with OpenAI, Anthropic, Google DeepMind, Meta AI, xAI, Mistral, DeepSeek, Qwen/Alibaba. | From prompt examples. |
| Data window | Treat the prompt's "~3 months" as a rolling trailing window. | Working assumption. |
| Stack | Python 3.13 + SQLite + FastAPI JSON API + React/Vite SPA. `data/fli.db` contains source-import backing tables and the entity/channel model. | Implemented. |
| Schema | Do not lock the modeled DB schema until real candidate evidence is reviewed. | Current build philosophy. |
| First kind pass | Classify current unknown X-backed clusters independently as `person`, `organization`, or `unsure`; model output is only `classification` and `reason`. | Adi decision 2026-07-10. |
| LLM runtime | Use the shared LiteLLM OpenAI-compatible endpoint and key; do not wire this app directly to Azure OpenAI. | Adi decision 2026-07-10. |
| Discovery | The active graph starts empty. Build it only from reviewed trusted accounts' outgoing follows; keep Digg's ranking offline for later comparison. | Updated 2026-07-10. |
| X/Grok | Grok/grok-build can help with live X-backed search and coding, but it is not the graph source. Use an explicit following-list provider for follow edges. | Rechecked 2026-07-09. |
| Budget | Do not over-optimize around the €100 budget; log real spend and revisit only if spend approaches the ceiling. | Adi decision. |

## Source Provenance

| Claim / fact used | Source | Retrieved | Notes |
| --- | --- | --- | --- |
| smol.ai/AI News monitors a large curated source set and discloses denominators. | buttondown.com/ainews issue archives + sitemap | 2026-07-08 | Prior-art pattern for source curation and denominator disclosure. |
| smol.ai tagging pipeline uses structured outputs and controlled vocabularies. | github.com/smol-ai/ainews-web-2025 (`oneoffs/process-emails.ts`, `oneoffs/preferredTags.ts`, pinned at `0fc45e2c56e2b0cad71478bbee9cf5976c9e573e`) | 2026-07-09 | Public code; `prefPeople` has 33 raw entries and 31 unique X handles. Imported as `smol_ai` evidence: 23 existing accounts, 8 new; 21 overlap AI High Signal, 17 overlap Digg, and 17 occur in all three. |
| Digg 2026 pivoted to AI-signal aggregation around top AI voices. | TechCrunch, 2026-05-11 | 2026-07-08 | Third-party context; later superseded by Digg page copy for methodology. |
| Digg community-voting phase failed because votes could not be trusted. | TechCrunch, 2026-03-13 | 2026-07-08 | Anti-pattern for community voting. |
| Techmeme uses an algorithm-plus-editorial model. | techmeme.com/about | 2026-07-08 | Human-in-the-loop prior art. |
| HN ranking uses gravity/time decay. | Medium explainer on HN ranking | 2026-07-08 | Freshness/time-decay reference. |
| Market gap: no obvious product combines researcher moves, frontier-lab signal, and persona-specific re-scoring. | Landscape audit across Zeta Alpha, CB Insights, Emergent Mind, Crunchbase, Ben's Bites, TLDR | 2026-07-08 | Differentiation claim. |
| X API is pay-per-use for posts/users/follows. | docs.x.com pricing | 2026-07-09 | Pricing is volatile; verify before spend. Following/followers reads are currently priced per returned resource. |
| X API `GET /2/users/{id}/following` returns the users followed by a specific user and paginates up to 1,000 results per request. | docs.x.com API reference | 2026-07-09 | Correct endpoint for the target graph, but third-party following reads are currently expensive at official rates. |
| `@karpathy` currently reports `following=1,108`. | TwitterAPI.io `GET /twitter/user/info?userName=karpathy` | 2026-07-10 | One bounded profile lookup cost about `$0.00018`. A complete 200-item-page snapshot would be about 1,216 credits / `$0.01216` through the existing adapter; the official X API would charge about `$11.08` at its current `$0.010` per third-party following resource. |
| xAI X Search can search X posts, user profiles, and threads; it does not document a structured following-list export. | docs.x.ai X Search + pricing | 2026-07-09 | Useful for discovery/validation prompts, not for building the PageRank edge table. |
| FxEmbed/FxTwitter exposes a public unofficial `GET /2/profile/{handle}/following` endpoint with paginated profile results. | docs.fxembed.com API reference + `api.fxtwitter.com` spot check | 2026-07-09 | OpenAI spot check returned the actual four accounts followed by `@openai`; useful for a tiny pilot, but provenance/reliability/terms need care. |
| Digg says rankings are built from the X social graph using roughly 9 million follow relationships. | digg.com/tech/x/rankings page copy | 2026-07-08 | Primary methodology claim. |
| Digg ranking snapshot contains 1,000 accounts. | digg.com/tech/x/rankings | 2026-07-08 | Preserved only in `data/digg/rankings.csv`; see `docs/references/digg-ranking-baseline.md`. Digg edge data and import/ranking code were removed. |

## Candidate Source Inventory

Build the active graph from reviewed outgoing-follow snapshots. Use the frozen
Digg ranking only as an offline comparison after the new ranking stands on its
own.

| Priority | Source | Type | Why useful | Status |
| --- | --- | --- | --- | --- |
| 1 | Trusted-person X following snapshots | Graph/ranking | Pull who reviewed trusted X channels follow; bounded, high-signal attention graph. | Not fetched yet; graph starts empty. |
| Compare only | Digg Tech / AI Rankings (`digg.com/tech/x/rankings`) | Offline ranking baseline | Compare overlap and rank disagreement after the new graph is evaluated independently. | Frozen 1,000-row CSV at `data/digg/rankings.csv`; not loaded into the database. |
| 3 | smol.ai AINews `prefPeople` | GitHub file | Small, clean, machine-readable list of high-signal AI people used by an existing AI news workflow. | Imported 2026-07-09: 31 unique handles, 23 existing accounts and 8 new. Stored as validation evidence, not automatic tracking. |
| 4 | swyx AI people X list | X List | Broad high-signal AI list used by smol.ai workflows. | Imported 2026-07-09 with `fli sources import-x-list --list-id 1585430245762441216 --source ai_high_signal`: 609 members, 230 already in Digg, 379 new versus Digg. |
| 5 | Aldo Cortesi Anthropic staff list | X List | Lab-specific Anthropic coverage, likely cleaner than broad AI lists. | URL known; membership not verified/exported yet. |
| Later | Scobleizer AI Newsmakers / Founders lists | X Lists | Large expansion set for founders/builders. | Useful later; noisy. |
| Later | L3S/twitter-researcher | GitHub dataset | Academic Twitter/DBLP-linked researcher mapping. | Useful for academic coverage if Digg misses depth. |
| Later | Editorial rankings (TIME100 AI, Feedspot, Om Bharatiya, etc.) | Articles/rankings | Good sanity checks and public names. | Use sparingly; can be stale or influencer-heavy. |
| Later | Conference signals (NeurIPS/ICML/ICLR speakers/award winners) | Academic lists | Useful for high-signal researchers outside social graph. | Not pulled yet. |
| Later | China-lab coverage | Articles/lists | Helps DeepSeek/Qwen undercoverage. | Needs targeted research. |

## X Following Data Options

Checked 2026-07-09. Do not run paid APIs or scrapers without explicit current-
session approval and a small hard cap.

| Option | Current pricing signal | Fit for our graph |
| --- | --- | --- |
| FxEmbed / FxTwitter public API | Free/unofficial public API; documented rate limit is 1,000 requests/min/IP; following endpoint page size max `100`. | Very interesting zero-spend pilot path for a small curated watchlist. Do not rely on it as production infrastructure without reviewing terms, rate limits, and self-hosting/backup options. |
| Official X API | Following/followers reads: `$0.010` per returned resource; owned-account reads: `$0.001` per returned resource. | Cleanest provenance, but expensive for third-party watchlist pulls. Good long-term target if cost/access is acceptable. |
| TwitterAPI.io | Followers/following: from `$0.01 / 1K`, tiered; profiles `$0.18 / 1K`. | Selected adapter for the future trusted-seed pilot. API key is a machine-local file at `~/.secrets/twitterapi-io/api-key`. |
| SocialData.tools | Get User Following: `$0.0002` per followed user (`$0.20 / 1K`). | Simple paid API fallback; more expensive than the cheapest TwitterAPI.io/Apify paths but still far below official X third-party reads. |
| Apify actors | Public X following/follower actors range roughly from `$0.10 / 1K` to `$1.50 / 1K` delivered profiles, depending on actor. | Fast pilot path, but provenance/terms/reliability need review per actor. |
| xAI Grok / X Search | `grok-build-0.1`: `$1` input / `$2` output per 1M tokens; X Search tool: `$5 / 1K` tool calls plus tokens. | Good for search, summaries, candidate validation, and maybe resolving ambiguous handles; not a direct follow-edge source. |

## Deep Research Prompt Summary

On 2026-07-08, an external deep-research prompt was drafted to find machine-
readable AI people sources: public X lists, editorial rankings, academic
rankings, conference signals, GitHub handle lists, newsletters that disclose
followed sources, and China-lab coverage.

The results were distilled into the candidate inventory above. Do not recreate
the old `data/raw/registry-seed/` scratch folder. The next useful artifact is a
reviewable candidate table derived from active sources in `data/fli.db`; the
offline Digg ranking is comparison evidence only.
