# Frontier Lab Intelligence

Frontier Lab Intelligence turns public output from frontier AI labs and key
people into ranked evidence and company-aware investment intelligence. I built
it for the BIT Capital AI Engineer case study.

[Live app](https://frontier-lab-intelligence.adithyan.io/) ·
[Video walkthrough](https://share.descript.com/view/LZkpHP29yub) ·
[How it works](https://frontier-lab-intelligence.adithyan.io/how) ·
[Technical appendix](https://frontier-lab-intelligence.adithyan.io/how#technical-appendix)

## Review the project

1. Start with the [video walkthrough](https://share.descript.com/view/LZkpHP29yub).
   The system is interactive, so this is the quickest way to see the complete
   path working.
2. Read [How it works](https://frontier-lab-intelligence.adithyan.io/how) for
   the product decisions, trade-offs, models, evaluation, and cost.
3. Open [Insights](https://frontier-lab-intelligence.adithyan.io/insights) and
   follow any citation backwards through its Event, evidence, and source post.

The closed
[technical appendix](https://frontier-lab-intelligence.adithyan.io/how#technical-appendix)
keeps the deployed stack, current model boundaries, and auditable account
intake figures available without adding another product section.

## System at a glance

The evidence stays inspectable before judgment:

```text
Registry and trusted network
  -> complete X evidence
  -> exact structural Events
  -> same-artifact, same-day Developments
  -> transparent daily rank
  -> independent audience routing
  -> company-aware Investment analysis
  -> web brief, PDF, and explicit delivery
```

The current Investment agent screens every routed Development against the full
company universe. It opens detailed company memos only for plausible matches,
records why a candidate was kept or rejected, and publishes a day only when the
complete requested cohort succeeds.

AI Engineering still has an independent routing decision, but it has no current
Insight generator. The product says this directly instead of showing output
from a retired fallback.

## Run it locally

```bash
./demo.command
```

The local client is the reproducibility path. On macOS, you can also
double-click `demo.command`. The first run needs Python 3.13 and an internet
connection. It downloads a 357 MB verified snapshot, installs the app, opens
`http://127.0.0.1:8797`, and serves the frozen data in read-only mode. It does
not need API keys or provider credentials.

If the local app is already running on that port, the launcher simply opens it
and leaves its data and process unchanged.

The product keeps the evidence trail visible at every step. A reviewer can move
from a final Insight to its source Event, original post, artifact, routing
reason, and frozen run provenance.

## What is proven

- A curated Registry connects 2,500+ frontier AI entities to their public
  channels and a 557,363-account trust graph.
- A deterministic Feed and exact structural Events keep source chronology and
  relationships inspectable.
- Independent audience routing separates AI Engineering relevance from
  Investment relevance.
- Company-aware Investment runs produce ranked, cited web briefs and
  deterministic PDF reports.
- Real Slack and email delivery adapters have been validated. They remain
  operator actions rather than part of the passive reviewer walkthrough.

The final submission-era Insights remain visible in the product. The
[reviewer guide](docs/references/reviewer-guide.md) maps the current proof to
the case-study rubric.

## How the repository is organized

| Start here | Purpose |
| --- | --- |
| [`docs/STATUS.md`](docs/STATUS.md) | Current proof, limitations, and submission state |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | System boundaries and data flow |
| [`docs/architecture/code-map.md`](docs/architecture/code-map.md) | Code, store, command, and test ownership |
| [`docs/references/case-prompt.md`](docs/references/case-prompt.md) | Preserved external requirements |
| [`docs/references/demo-release.md`](docs/references/demo-release.md) | Exact demo snapshot and reproduction contract |
| [`AGENTS.md`](AGENTS.md) | Working rules for coding agents |

Code, tests, documentation, compact manifests, and the 14 MB Registry database
live in Git. Large raw and derived stores do not. The reviewer snapshot is an
immutable, checksummed object-storage release, so a clean clone remains small
without becoming an empty demo.

## Known limits

X is the implemented discovery source. Artifacts add papers, repositories,
articles, documents, and videos when first-party evidence points to them. Event
grouping follows exact provider relationships rather than semantic topic
clustering. AI Engineering routing exists, but its current last-mile Insight
generator is still unbuilt. The release is a bounded case-study proof, not a
production alert service.

Adithyan Ilangovan  
[adi@aipodcast.ing](mailto:adi@aipodcast.ing)
