# Architecture Overview

Living map of Frontier Lab Intelligence. Update this file when the system
shape changes: new pipeline stage, schema boundary, source class, or module.

Status: data-first bootstrap. The implemented code has raw fetch/store,
Digg-derived seed graph extraction, and a lightweight web shell. The modeled
registry/extraction/scoring schema is intentionally not locked yet.

## Stack

One Python codebase, one SQLite database, one small server-rendered web app.

| Layer | Choice | Why |
| --- | --- | --- |
| Language/package | Python 3.13, `src/fli/` | Most rubric weight is data, LLM, scoring, and ingestion work. |
| Database | SQLite | The prompt asks for a database; a single inspectable file is reviewer-friendly. |
| Web UI | FastAPI + Jinja2 + plain CSS | UI is 5% of the rubric; avoid a separate frontend stack. |
| Pipeline | CLI subcommands | Each stage should be independently runnable, testable, and demoable. |
| Scheduling | Simple cron/loop later | Scheduled ingestion does not need queue infrastructure yet. |

Rejected for now: React/Next split frontend, Streamlit/Gradio toy-dashboard
shape, and Dobby/personal-memory architecture inside this product repo.

## System pipeline

```mermaid
flowchart LR
    subgraph sources [Sources]
        DIGG[Digg Tech graph]
        BLOGS[Lab blogs / RSS]
        ARXIV[arXiv]
        GH[GitHub releases]
        X[X / Twitter later]
    end

    REG[(Registry<br/>labs + people)]
    ING[Ingestion<br/>pull · dedup · cluster]
    EXT[Extraction<br/>LLM → structured insights]
    SCO[Scoring<br/>dimensions + validation]
    DEL[Delivery<br/>digests · alerts]
    UI[Web UI<br/>FastAPI + Jinja2]

    DIGG --> REG
    REG -->|who to watch| ING
    BLOGS & ARXIV & GH & X --> ING
    ING --> EXT
    EXT --> SCO
    SCO --> DEL
    REG -.-> UI
    SCO -.-> UI
    DEL -.-> UI
    ING -.->|discovered names| REG
```

Target stages:

1. **Registry:** labs, people, identities, affiliations, provenance.
2. **Ingestion:** public source pulls, dedup, clustering, freshness.
3. **Extraction:** structured/cited insights from surviving documents.
4. **Scoring:** visible dimensions plus validation, not an arbitrary weighted sum.
5. **Delivery:** persona digests, alerts, reviewable UI, PDF/export later.

## Signal Funnel

```mermaid
flowchart TD
    S0[Source scoping<br/>curated source list]
    S1[Dedup / clustering<br/>many links → one event]
    S2[Novelty gate<br/>similarity vs recent history]
    S3[LLM extraction + rubric scoring<br/>only on survivors]
    S4[Persona thresholds<br/>investment vs AI team]
    OUT1[Alert tier]
    OUT2[1-page digest]
    OUT3[Full appendix]
    NONE[Nothing significant today]

    S0 --> S1 --> S2 --> S3 --> S4
    S4 --> OUT1 & OUT2 & OUT3
    S4 --> NONE
```

Judgment is meant to live in two visible places: source selection and scoring
rubrics. Everything else should be mechanical and testable.

Design principles borrowed from prior art:

- Curated source lists and denominator disclosure from smol.ai/AI News.
- "Nothing significant today" as a trust-preserving output.
- Machine proposes, human disposes from Techmeme/Digg-style workflows.
- Reason-for-inclusion labels instead of one opaque score.
- Time decay and noise dampeners for freshness.
- Dated affiliations because people moves are themselves a signal.

## Current Data

Implemented raw table:

```text
raw_items(id, source, lab, external_id, fetched_at, payload)
```

Current file artifacts:

```text
data/fli.db                         # raw evidence SQLite corpus
data/digg/rankings.csv              # 1,000 ranked Digg/X accounts
data/digg/top_follower_edges.csv    # tracked first-slice top-follower edges
data/digg/seed_graph.json           # tracked nested Digg review artifact
data/digg/full_graph_summary.json   # summary of full paginated local pull
data/raw/digg-full-2026-07-08/      # ignored full graph artifacts
```

Known data facts:

- `fli fetch` landed 1,599 raw items from lab blogs/sitemap, arXiv, and
  GitHub releases.
- `fli digg` landed 1,000 ranked accounts and 49,950 tracked first-slice
  edges.
- `fli digg --full-followers` produced 361,225 local full-paginated edges;
  full raw files are ignored because they exceed normal git-hosting size.

## Graph Storage Plan

The Digg data is graph data: accounts are nodes, relationships are edges, and
the source URL/API response is evidence. Store the modeled graph in SQLite
rather than keeping a large nested JSON file as the main working artifact.
SQLite is enough for this scale when the edge endpoints are indexed.

Keep these layers separate:

1. **Raw observations** — source payloads or source-file references, fetched
   time, source URL, and hash. This preserves evidence and allows re-parsing.
2. **Accounts** — platform accounts such as X handles, with Digg rank/category,
   display name, bio, X id, GitHub URL, first/last seen timestamps.
3. **Graph edges** — directed observed relationships, e.g.
   `from_account -> to_account`, relationship type `top_follower_of` or
   `follows`, source `digg`, observed time, evidence URL, confidence, and raw
   observation reference.
4. **Entities** — real-world people/labs/companies promoted after review.
   Do not merge accounts into entities too early.
5. **Identities and affiliations** — links from real-world entities to
   platform accounts and lab/company affiliations, each with provenance.

Sketch:

```text
raw_observations(id, source, source_url, fetched_at, payload_ref, payload_hash)
accounts(id, platform, handle, display_name, x_id, bio, first_seen_at, last_seen_at)
account_source_facts(account_id, source, rank, role, github_url, observed_at)
graph_edges(id, from_account_id, to_account_id, relationship, source,
            observed_at, evidence_url, confidence, raw_observation_id)
entities(id, kind, canonical_name)
identities(entity_id, account_id, platform, confidence, evidence)
affiliations(person_entity_id, lab_entity_id, role, start_date, end_date, evidence)
```

Indexes likely needed first:

```text
accounts(platform, handle)
accounts(platform, x_id)
graph_edges(from_account_id, relationship)
graph_edges(to_account_id, relationship)
graph_edges(source, observed_at)
```

This structure preserves the original evidence while making ranking and
visualization straightforward. Example exports later:

```sql
SELECT f.handle AS from_handle, t.handle AS to_handle, e.relationship
FROM graph_edges e
JOIN accounts f ON f.id = e.from_account_id
JOIN accounts t ON t.id = e.to_account_id;
```

## Target Data Model Sketch

This is a hypothesis to test against real candidate evidence, not a locked
schema.

```mermaid
erDiagram
    ENTITY {
        string id PK
        string kind "lab | person"
        string canonical_name
    }
    AFFILIATION {
        string person_id FK
        string lab_id FK
        date start_date
        date end_date "null = current"
        string provenance
    }
    IDENTITY {
        string entity_id FK
        string platform "x | arxiv | github | site"
        string handle
        float confidence
        string evidence
    }
    DOCUMENT {
        string id PK
        string source_url
        string cluster_id
        datetime published_at
    }
    INSIGHT {
        string id PK
        string document_id FK
        string attributed_to FK
        string claim
        string evidence_quote
    }
    SCORE {
        string insight_id FK
        string dimension
        int value
        string rationale
    }

    ENTITY ||--o{ AFFILIATION : "person side"
    ENTITY ||--o{ IDENTITY : has
    ENTITY ||--o{ INSIGHT : "attributed to"
    DOCUMENT ||--o{ INSIGHT : yields
    INSIGHT ||--o{ SCORE : scored
```

Scoring dimensions under consideration: novelty, materiality, credibility,
actionability per persona, corroboration, and freshness. The combination into
a ranking should be checked against human/hindsight labels before becoming a
final score.

## Module Status

| Module | Status |
| --- | --- |
| `fli.cli` | `--version`, `fetch`, `digg`, `web` |
| `fli.digg` | Digg rankings and top-follower graph extraction |
| `fli.store` | raw `raw_items` SQLite layer |
| `fli.fetch` | raw fetch spike for blogs/sitemap, arXiv, GitHub releases |
| `fli.web` | shell: home + `/architecture` |
| `fli.registry` | pending, schema from candidate evidence next |
| `fli.ingest` | pending production ingestion; raw fetch spike exists |
| `fli.extract` | pending |
| `fli.scoring` | pending |
| `fli.delivery` | pending |

## Build Order

1. Build a reviewable registry-candidate table from Digg + raw evidence.
2. Decide the first modeled registry schema from reviewed candidates.
3. Promote raw fetch into production ingestion around the accepted registry.
4. Extract and score real ingested data.
5. Add validation harness and ground-truth labeling.
6. Delivery and UI last.
