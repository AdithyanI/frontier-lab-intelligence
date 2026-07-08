# Build Log

Chronological record of how this system was built. This combines the previous
working log, build journal, tool/budget notes, and learning notes.

Use this after every meaningful chunk of work:

- **Intent:** what Adi asked for or what changed.
- **Decision / action:** what the agent changed.
- **Evidence:** commands, files, data counts, or validation.
- **Impact / next:** why it matters and what should happen next.
- **Tools / spend:** AI tools used and any API/service spend.

## Build Timeline

| Date | Intent / trigger | Decision / action | Evidence | Impact / next | Tools / spend |
| --- | --- | --- | --- | --- | --- |
| 2026-07-07 | Start the BIT case-study build as a real product, not a throwaway answer. | Scaffolded the repo and captured the original prompt plus source material. | `docs/references/case-prompt.md`, `docs/references/source-material/`, tracker. | Requirements became repo-owned facts instead of chat memory. | Copilot CLI; €0. |
| 2026-07-08 | Make the repo product-shaped and agent-native before deep implementation. | Renamed to Frontier Lab Intelligence; added product/design docs and a weighted execution plan. | `PRODUCT.md`, `DESIGN.md`, tracker. | The repo now has a durable identity and rubric-aware plan. | Copilot CLI + impeccable; €0. |
| 2026-07-08 | Choose a boring stack that maximizes rubric value. | Chose Python 3.13, SQLite, FastAPI/Jinja2, one installable `src/fli` package. | `pyproject.toml`, `src/fli/`, architecture overview. | Avoids spending effort on frontend infrastructure when UI is only 5% of the rubric. | Copilot CLI; €0. |
| 2026-07-08 | Understand prior art before locking architecture. | Researched smol.ai/AI News, Digg, Techmeme/HN, and market gaps. | Research notes and sources in `docs/references/research-notes.md`. | Adopted source curation, denominator disclosure, "nothing significant today," reason-for-inclusion slots, and human-in-the-loop review. | Copilot CLI with research subagents; €0. |
| 2026-07-08 | Stop designing the DB in the abstract; get real data first. | Built `fli.store` and `fli.fetch`; fetched blogs/sitemap, arXiv, and GitHub releases into SQLite. | `data/fli.db` with 1,599 raw items; 8 tests green at the time. | Real payloads showed arXiv text search false positives, blog marketing noise, and GitHub authors as cheap discovery signals. Next: model from evidence. | Copilot CLI; €0. |
| 2026-07-08 | Rebuild context and clean the harness after multiple agents touched the repo. | Re-read canonical docs, removed generated egg metadata, fixed the fast-check path, and rebuilt the active tracker around evidence-first registry work. | `scripts/check-fast.sh`, tracker updates. | Reduced drift; future agents have a cleaner resume point. | Codex Desktop; €0. |
| 2026-07-08 | Verify whether Grok Build CLI could help with X-backed discovery. | Installed/authenticated Grok Build CLI and verified live X-backed search/thread fetches. | Grok CLI capability check in prior session output. | Grok is useful as a research assistant, but not as the authoritative follower/list graph extractor. | Codex Desktop + Grok Build CLI; €0 recorded. |
| 2026-07-08 | Find a strong people-discovery spine without paying for X API first. | Pivoted registry bootstrap to Digg after verifying structured rankings/profile data. | `src/fli/digg.py`, `data/digg/`, `docs/references/research-notes.md`. | Digg became the primary v1 graph-derived seed source. Next: use the graph to rank registry candidates. | Codex Desktop; €0. |
| 2026-07-08 | Pull enough Digg graph data to decide whether it is useful. | Added `fli digg --full-followers`; smoke-tested 2 profiles; ran the full paginated local pull. | 1,000 rankings, 1,000 profiles, 361,225 directed top-follower edges; `xai` returned 404. Tracked summary: `data/digg/full_graph_summary.json`; full raw files: ignored `data/raw/digg-full-2026-07-08/`. | We now have a rich local candidate graph without X API spend. Next: build a candidate review/ranking table. | Codex Desktop + Digg public endpoints; €0. |
| 2026-07-08 | Reduce doc sprawl. | Consolidated working log, build journal, learning notes, assumptions, sources, seed lists, and context docs into fewer canonical files. | `AGENTS.md`, `docs/references/build-log.md`, `docs/references/context.md`, `docs/references/research-notes.md`. | Future agents have one build log, one context doc, one research/source notes doc, one architecture doc, and one tracker. | Codex Desktop + agent-native-repo-playbook; €0. |
| 2026-07-08 | Decide how to store graph data later, without implementing it yet. | Documented the deferred graph storage plan: raw observations, accounts, directed graph edges, then reviewed real-world entities/identities/affiliations. | `docs/architecture/overview.md` §Graph Storage Plan; tracker current batch. | The next data-modeling pass should move modeled graph data into SQLite and stop treating nested JSON as the primary graph store. | Codex Desktop; €0. |

| 2026-07-08 | Verify BIT context coverage against Adi's private prep repo. | Imported distilled BIT worldview/lens into `docs/references/context.md`: Devil's Advocate process, memory-supercycle/infra worldview, respected signal types, role/stack specifics, official data-scale claims. | `docs/references/context.md` §BIT worldview and case lens; source: `~/GitHub/adi/projects/bit-capital-case-study-2026/resources/`. | Design gap identified: the funnel has no contrary-evidence concept yet; scoring/insights should carry a thesis-breaking slot. Repo is now self-sufficient on BIT context. | Copilot CLI; €0. |

| 2026-07-08 | Adi wants a real frontend for data inspection and a written plan; asked whether to use his personal design language. | Locked the batch plan (graph→SQLite, PageRank weights, curated-list layering, candidate review table, frontend shell). Stack change: React+Vite+TS SPA + sigma.js over FastAPI JSON API, retiring Jinja2. Kept FLI's own cobalt/brass identity over adi-design: the reviewer is a fund; the product should read as their instrument. | Tracker Current Batch; architecture overview stack table. | Next: implement Phase A (graph store) then B (PageRank). | Copilot CLI + adi-design skill (consulted, not applied); €0. |

| 2026-07-08 | Adi flagged redundancy in the raw edge CSVs; start Phase A. | Built `fli.graph`: normalized modeled layer (`accounts`, `account_source_facts`, `graph_edges`) loaded from raw Digg CSVs; raw stays redundant as evidence, model stores each account once. New CLI: `fli graph load|summary`. | 2,314 accounts, 6,760 facts, 361,225 deduped edges; top targets karpathy/jeffdean/sama/ilyasut/ylecun; `tests/test_graph.py`; 12 tests green. | Phase B next: PageRank source weights over the edge graph. | Copilot CLI; €0. |

| 2026-07-08 | Adi wants the frontend now, as a visual anchor: a living system map he can learn from and demo on a call. | Built the SPA: Vite+React+TS in `frontend/` building into `src/fli/web/dist`; rewrote `fli.web` as JSON API (`/api/status`, `/api/accounts`, `/api/architecture`) + SPA host; removed Jinja2/markdown deps. Pages: System (pipeline stages w/ live DB counts), Accounts (searchable candidate table), Architecture (doc + Mermaid). DESIGN.md tokens (BIT capital-blue anchored). Committed built dist so reviewers run Python only. | Screenshots of all 3 pages verified against DESIGN.md; 14 tests green; `check-fast.sh` OK. Playwright installed as frontend devDep for visual checks. | Next: PageRank (B) then list layering (C); numbers appear in the UI as they land. | Copilot CLI + impeccable + agent-native-repo-playbook; €0. |

| 2026-07-08 | Adi rejected v1 UI as plain/old-design; wants an out-of-the-box redesign in BIT's design language with a deeply visual Architecture page (image-mockup route abandoned after LiteLLM proxy failures). | Full UI v2, "editorial instrument": hex tokens from bitcap.com (alpha-black ink, capital-blue family, coin-sand whisper), top-bar shell, home as editorial split (statement + hero numerals + live pipeline rail), Accounts restyle (rank chips, mono headers, sand hover). Architecture rebuilt as three hand-built SVG diagrams — graph plane with real handles, accounts→identities→entity layering with confidence chips, signal funnel. Removed `/api/architecture` + marked/mermaid (bundle 1MB→246KB). DESIGN.md rewritten to shipped reality. | All 3 pages screenshot-verified via Playwright MCP at 1440px; overlap bugs fixed on inspection; 13 tests green; `check-fast.sh` OK. | The Architecture page is now the teach-and-demo surface Adi asked for. Next: PageRank (B), list layering (C), candidate review table (D). | Copilot CLI + impeccable + Playwright MCP; €0. |

| 2026-07-08 | Adi flagged the funnel diagram as ugly and wanted each stage explained in simple words; asked for an impeccable polish pass. | Rebuilt §03 as an HTML/CSS funnel: continuous narrowing silhouette (sand→blue→ink), mono count column with an illustrative day's volumes (~120 items → 2–3 delivered), and a plain-words explanation beside every stage. Simplified section copy; honest caption ("ingestion is not live yet"). | Desktop + 390px mobile screenshots verified via Playwright MCP (fixed count clipping on mobile); 13 tests green; `check-fast.sh` OK. | Architecture §03 now reads as a story: collect → merge → novelty → LLM → persona. | Copilot CLI + impeccable (polish) + Playwright MCP; €0. |

## Learning Notes

### Graph-Derived Discovery

**Where we used it:** `src/fli/digg.py` turns Digg rankings and top-follower
rows into candidate accounts and directed edges.

**Problem it solves here:** A hand-written list of famous AI people misses the
layer below obvious leaders. A raw X follower crawl is too large and noisy.
Graph-derived discovery starts from who the AI/tech community already pays
attention to, then gives us candidates to validate.

**How it works:** Treat each account as a node and each Digg top-follower row
as an edge. If many trusted/ranked accounts follow or appear around a target,
that is evidence the target deserves review. The graph only prioritizes review;
it does not promote anyone into the registry automatically.

**Why we chose it:** X API full follower extraction is expensive and noisy. X
lists are useful but hard to export completely. Digg already computes a smaller
graph signal from roughly 9 million follow relationships.

**If asked on-site:** "I used Digg as a graph-derived candidate generator. It
gave ranked AI accounts and top-follower edges, which is a better starting
point than scraping millions of raw followers. Then I validate candidates
against primary sources before they enter the registry."

## Budget Log

BIT explicitly expects AI coding tools and will ask how they were used. This
section tracks the reimbursable €100 API/services budget.

| Date | Service | Amount | Why | Receipt |
| --- | --- | --- | --- | --- |
| — | — | €0.00 | nothing spent yet | — |

Running total: **€0.00 / €100.00**
