# Architecture Overview

The living visual map of the system. **Contract: any change to system shape
(new module, new pipeline stage, schema change) updates this doc in the same
change.** Diagrams are Mermaid — they render on GitHub and in most editors.

Prose rationale (why these choices): `docs/references/solution-architecture.md`.
Status: pre-implementation — this reflects the Phase 0 design; boxes appear
here before code exists, then get annotated as they land.

## System pipeline

Five stages, each an independently runnable CLI step, sharing one SQLite DB.

```mermaid
flowchart LR
    subgraph sources [Sources]
        BLOGS[Lab blogs / RSS]
        ARXIV[arXiv]
        GH[GitHub releases]
        X[X / Twitter — later]
    end

    REG[(Registry<br/>labs + people)]
    ING[Ingestion<br/>pull · dedup · cluster]
    EXT[Extraction<br/>LLM → structured insights]
    SCO[Scoring<br/>dimensions + validation]
    DEL[Delivery<br/>digests · alerts]
    UI[Web UI<br/>FastAPI + Jinja2]

    REG -->|who to watch| ING
    BLOGS & ARXIV & GH & X --> ING
    ING --> EXT
    EXT -->|attributed, cited insights| SCO
    SCO --> DEL
    REG -.->|entity pages| UI
    SCO -.->|insights + why-flagged| UI
    DEL -.->|past reports| UI
    ING -.->|discovered names| REG
```

## Signal funnel (where noise dies)

```mermaid
flowchart TD
    S0[Stage 0 — source scoping<br/>curated source list · editorial, free]
    S1[Stage 1 — dedup / clustering<br/>many links → one event · mechanical, free]
    S2[Stage 2 — novelty gate<br/>embeddings vs recent history · ~free]
    S3[Stage 3 — LLM extraction + rubric scoring<br/>costs tokens — only survivors]
    S4[Stage 4 — persona thresholds<br/>investment vs AI team cut-lines · free]
    OUT1[Alert tier]
    OUT2[1-page persona digest]
    OUT3[Full appendix]
    NONE[“Nothing significant today”]

    S0 --> S1 --> S2 --> S3 --> S4
    S4 --> OUT1 & OUT2 & OUT3
    S4 -->|no item crosses the bar| NONE
```

Judgment is encoded in exactly two places: the source list (S0) and the
scoring rubric (S3). Everything else is mechanical and testable.

## Data model (core registry)

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
        string cluster_id "one event, many docs"
        datetime published_at
    }
    INSIGHT {
        string id PK
        string document_id FK
        string attributed_to FK "entity"
        string claim
        string evidence_quote
    }
    SCORE {
        string insight_id FK
        string dimension "novelty | materiality | credibility | actionability:persona"
        int value
        string rationale
    }

    ENTITY ||--o{ AFFILIATION : "person side"
    ENTITY ||--o{ IDENTITY : has
    ENTITY ||--o{ INSIGHT : "attributed to"
    DOCUMENT ||--o{ INSIGHT : yields
    INSIGHT ||--o{ SCORE : "scored on"
```

Affiliations are dated claims, never fixed attributes — people move, and the
move itself is a signal.

## Repo layout

```
src/fli/          the installable package — only shippable code
  cli.py          pipeline entrypoint (stages become subcommands)
  (planned) registry.py · ingest.py · extract.py · scoring.py · delivery.py · web/
tests/            mirrors src/fli one-to-one (test_scoring.py ↔ scoring.py)
docs/
  architecture/   ← this doc (visual map, kept current)
  references/     durable decisions, prompt, assumptions, logs
  learning/       plain-words DS/ML entries (do → learn contract)
  projects/       execution tracker
data/             local data paths (large/raw data stays untracked)
scripts/          check-fast.sh and repo tooling
```

## Module status

| Module | Status |
| --- | --- |
| `fli.cli` | ✅ stub (`--version`, help, `web` subcommand) |
| `fli.registry` | 📐 designed (Phase 0) |
| `fli.ingest` | 📐 designed |
| `fli.extract` | 📐 designed |
| `fli.scoring` | 📐 designed |
| `fli.delivery` | 📐 designed |
| `fli.web` | ✅ shell: home + `/architecture` (renders this doc with Mermaid); register/insights/reports pending |
