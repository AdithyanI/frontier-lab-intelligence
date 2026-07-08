# Build Journal

Narrative construction log for Frontier Lab Intelligence.

This is not the same as `working-log.md`. The working log tracks AI tools and
budget. This journal tracks how the product changed: intent, decisions,
evidence, tradeoffs, and what the next agent should understand.

Append after every meaningful chunk of work:

| Date | Human intent / trigger | What changed | Evidence | Product impact | Next useful step |
| --- | --- | --- | --- | --- | --- |
| 2026-07-07 | Start BIT case-study build as a real product, not a throwaway answer. | Created the repo, captured the original prompt and source material, and established the tracker as the active execution record. | `docs/references/case-prompt.md`, `docs/references/source-material/`, `docs/projects/frontier-lab-intelligence/tasks.md` | External requirements became repo-owned facts instead of chat memory. | Build from the prompt requirements, not remembered interpretations. |
| 2026-07-08 | Make the repo product-shaped and agent-native before deep implementation. | Renamed the repo to Frontier Lab Intelligence, added product/design docs, standing learning/working-log contracts, and a weighted implementation plan. | `PRODUCT.md`, `DESIGN.md`, `docs/learning/README.md`, `docs/references/working-log.md` | The project now has a durable identity, docs structure, and case-study evidence trail. | Keep future work small, inspectable, and tied to rubric weight. |
| 2026-07-08 | Stop designing the database in the abstract; get real data first. | Built raw fetch/store for lab blogs, arXiv, and GitHub releases, then fetched 1,599 raw items into SQLite. | `src/fli/fetch.py`, `src/fli/store.py`, `data/fli.db` | Real payloads exposed immediate modeling lessons: arXiv text search has false positives, blog feeds mix marketing with research, and GitHub authors are useful discovery signals. | Let real evidence shape the first modeled registry/schema. |
| 2026-07-08 | Find a strong people-discovery spine without immediately paying for X API. | Pivoted registry bootstrap to Digg's public Tech rankings and top-follower graph after verifying Digg exposes structured ranking/profile data. | `src/fli/digg.py`, `data/digg/`, `docs/references/sources.md` | Digg became the primary v1 graph-derived seed source for people/accounts to review. | Use the graph to rank candidates before adding more sources. |
| 2026-07-08 | Pull enough Digg graph data to decide whether it is useful for registry discovery. | Added `fli digg --full-followers`, smoke-tested it, and ran a full paginated local pull: 361,225 directed top-follower edges across 999 target accounts. | `data/digg/full_graph_summary.json`, ignored `data/raw/digg-full-2026-07-08/` | We now have a rich local graph for candidate ranking without X API spend; full raw artifacts are ignored because they exceed normal git-hosting size. | Build a candidate review table from the full local edge CSV, then decide schema from reviewed evidence. |
| 2026-07-08 | Make the build process itself reviewable as part of the take-home. | Added this build journal and made it a standing repo contract in `AGENTS.md`. | `AGENTS.md`, `docs/references/build-journal.md` | Future agents must preserve the narrative of decisions and pivots, not just implementation diffs. | Append here after each meaningful chunk, especially schema, scoring, evaluation, and delivery decisions. |

