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
| Stack | Python 3.13 + SQLite + FastAPI/Jinja2. Current `data/fli.db` is raw evidence only, not the final schema. | Chosen. |
| Schema | Do not lock the modeled DB schema until real candidate evidence is reviewed. | Current build philosophy. |
| Discovery | Use Digg as the primary v1 graph-derived seed source; use smol.ai/list sources as validation or coverage supplements. | Current direction. |
| X/Grok | Grok Build CLI can help with live X-backed search/thread fetches, but is not an authoritative follower/list graph extractor. Use official X API or another explicit graph source if full follow edges become central. | Observed 2026-07-08. |
| Budget | Do not over-optimize around the €100 budget; log real spend and revisit only if spend approaches the ceiling. | Adi decision. |

## Source Provenance

| Claim / fact used | Source | Retrieved | Notes |
| --- | --- | --- | --- |
| smol.ai/AI News monitors a large curated source set and discloses denominators. | buttondown.com/ainews issue archives + sitemap | 2026-07-08 | Prior-art pattern for source curation and denominator disclosure. |
| smol.ai tagging pipeline uses structured outputs and controlled vocabularies. | github.com/smol-ai/ainews-web-2025 (`oneoffs/process-emails.ts`, `oneoffs/preferredTags.ts`) | 2026-07-08 | Public code; reference pattern for extraction. |
| Digg 2026 pivoted to AI-signal aggregation around top AI voices. | TechCrunch, 2026-05-11 | 2026-07-08 | Third-party context; later superseded by Digg page copy for methodology. |
| Digg community-voting phase failed because votes could not be trusted. | TechCrunch, 2026-03-13 | 2026-07-08 | Anti-pattern for community voting. |
| Techmeme uses an algorithm-plus-editorial model. | techmeme.com/about | 2026-07-08 | Human-in-the-loop prior art. |
| HN ranking uses gravity/time decay. | Medium explainer on HN ranking | 2026-07-08 | Freshness/time-decay reference. |
| Market gap: no obvious product combines researcher moves, frontier-lab signal, and persona-specific re-scoring. | Landscape audit across Zeta Alpha, CB Insights, Emergent Mind, Crunchbase, Ben's Bites, TLDR | 2026-07-08 | Differentiation claim. |
| X API is pay-per-use for posts/users/follows. | docs.x.com pricing | 2026-07-08 | Pricing is volatile; verify before spend. |
| Digg says rankings are built from the X social graph using roughly 9 million follow relationships. | digg.com/tech/x/rankings page copy | 2026-07-08 | Primary methodology claim. |
| Digg profile pages expose ranked accounts plus initial top-follower rows. | digg.com/tech/x/rankings and digg.com/u/x/{handle} | 2026-07-08 | `fli digg` tracked snapshot: 1,000 accounts and 49,950 first-slice edges. |
| Digg public follower API exposes a larger paginated top-follower graph. | digg.com/api/profile/{handle}/followers | 2026-07-08 | Full local pull: 361,225 directed edges across 999 target accounts; `xai` returned 404. |

## Candidate Source Inventory

Use Digg first. Augment only when a source has clear provenance, useful
coverage, or machine-readable handles.

| Priority | Source | Type | Why useful | Status |
| --- | --- | --- | --- | --- |
| 1 | Digg Tech / AI Rankings (`digg.com/tech/x/rankings`) | Graph/ranking | Primary v1 source: 1,000 ranked accounts and full local top-follower graph. | Extracted into `data/digg/`; full raw under ignored `data/raw/digg-full-2026-07-08/`. |
| 2 | smol.ai AINews `prefPeople` | GitHub file | Small, clean, machine-readable list of high-signal AI people used by an existing AI news workflow. | Use as validation/anchor label, not as the graph spine. |
| 3 | swyx AI people X list | X List | Broad high-signal AI list used by smol.ai workflows. | URL known; membership not verified/exported yet. |
| 4 | Aldo Cortesi Anthropic staff list | X List | Lab-specific Anthropic coverage, likely cleaner than broad AI lists. | URL known; membership not verified/exported yet. |
| 5 | Scobleizer AI Newsmakers / Founders lists | X Lists | Large expansion set for founders/builders. | Useful later; noisy. |
| Later | L3S/twitter-researcher | GitHub dataset | Academic Twitter/DBLP-linked researcher mapping. | Useful for academic coverage if Digg misses depth. |
| Later | Editorial rankings (TIME100 AI, Feedspot, Om Bharatiya, etc.) | Articles/rankings | Good sanity checks and public names. | Use sparingly; can be stale or influencer-heavy. |
| Later | Conference signals (NeurIPS/ICML/ICLR speakers/award winners) | Academic lists | Useful for high-signal researchers outside social graph. | Not pulled yet. |
| Later | China-lab coverage | Articles/lists | Helps DeepSeek/Qwen undercoverage. | Needs targeted research. |

## Deep Research Prompt Summary

On 2026-07-08, an external deep-research prompt was drafted to find machine-
readable AI people sources: public X lists, editorial rankings, academic
rankings, conference signals, GitHub handle lists, newsletters that disclose
followed sources, and China-lab coverage.

The results were distilled into the candidate inventory above. Do not recreate
the old `data/raw/registry-seed/` scratch folder. The next useful artifact is a
reviewable candidate table derived from `data/fli.db`, Digg, and any explicitly
approved supplement such as smol.ai.

