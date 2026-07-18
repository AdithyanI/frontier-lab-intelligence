# BIT Capital Editorial Context

This is the long-form research companion for the daily Investment Intelligence
agent. The active machine-readable packet lives in the repo-local skill at
`.agents/skills/fli-daily-intelligence/references/bit-investment-context.json`.
That packet intentionally uses the complete audited 2025 portfolio as its
working holdings baseline and preserves BIT's thesis, research process, source
cautions, outside-portfolio policy, and one reusable company profile per
holding. Company profiles distinguish views attributable to BIT from FLI's
primary-source analyst context and record whether BIT material is firm-wide,
flagship-specific, from another product, or mixed. They are background for daily reasoning, not
permanent impact calls or evidence that BIT currently holds a company. The
human-readable long-form source
remains the product's `/bit-lens` page, implemented in
`frontend/src/features/bit-lens/BitLensPage.tsx` with its structured holdings
and source ledger in `bitLensData.ts`.

## Reader and purpose

The reader is an investment team that describes its process as thesis-first,
company-specific, alternative-data-informed, and human-decided. It does not
need a generic frontier-AI digest. A useful Insight explains:

1. what changed;
2. which company in the working portfolio it may affect and whether a specific
   company outside that portfolio deserves diligence;
3. the operating and financial transmission mechanism;
4. what may be underappreciated or differently interpreted;
5. the strongest counter-case and missing evidence;
6. a measurable confirmation or falsification watchpoint; and
7. the next useful diligence action.

Never force a company connection. An empty company mapping is more useful than
an invented holding or an unsupported earnings bridge.

## Flagship fund boundary

The target is BIT Global Technology Leaders, BIT Capital's flagship global
technology-equity strategy. It began as BIT Global Internet Leaders and was
renamed in 2024 as the investable universe expanded across the technology
stack. Public material describes a benchmark-independent, concentrated,
bottom-up strategy seeking category leaders whose growth and competitive
position may not be fully recognized. The marketing emphasis often points to
companies below the most universally covered mega-caps, but the portfolio can
own mega-caps when the thesis and valuation justify it.

Do not project the broader instrument flexibility of other BIT products onto
this UCITS flagship. The legal prospectus permits a wider set of instruments
than the ordinary long-equity portfolio presentation, but that is not evidence
of a live position or a current short.

Primary references:

- [Flagship fund page](https://bitcap.com/en/fonds/bit-global-technology-leaders)
- [Investment approach](https://bitcap.com/en/investmentansatz)
- [Fund prospectus, 15 Jun 2026](https://fondswelt.hansainvest.com/uploads/documents/verkaufsprospekt/VKP_BIT_Global_Technology_Leaders_15_06_2026.pdf)
- [PRIIPs KID, 16 Apr 2026](https://fondswelt.hansainvest.com/uploads/documents/priips/PRIIPS_DE000A2N8127_1072995_DE_DE_2026-04-16_69bbe9ea22c51.pdf)

## Dated portfolio facts

Always attach a date to a holdings claim. The latest public portfolio state in
the research is the 30 June 2026 factsheet, but it exposes only the top ten and
aggregate allocations. The latest complete audited portfolio is 31 December
2025. No public source reviewed establishes the other 18 June positions.

### 30 June 2026 public snapshot

- Fund assets: approximately EUR 1.594 billion.
- Positions: 28.
- Top-ten concentration: 60.7%.
- Equity / cash and derivatives: 94.6% / 5.4%.
- Currency exposure: USD 88.9%, EUR 11.1%.
- Sector exposure: information technology 56.7%, consumer discretionary 18.5%,
  financials 12.5%, healthcare 6.8%, materials 5.5%.
- Risk class: 6 of 7.
- Recommended holding period: at least five years.

Latest disclosed top ten:

| Rank | Holding | Weight | Working public lens |
| --- | --- | ---: | --- |
| 1 | Amazon | 10.4% | AWS, Trainium, Bedrock, backlog, and conversion of AI capex into platform economics. |
| 2 | Micron | 8.6% | HBM/DRAM scarcity, yields, supply additions, and pricing. |
| 3 | IREN | 8.5% | Power, grid interconnection, data-center capacity, GPU deployment, and contracted AI-cloud revenue. |
| 4 | SanDisk | 6.0% | Enterprise flash/storage demand, NAND pricing, mix, and margins. |
| 5 | Robinhood | 5.0% | Customer asset depth, deposits, subscription and product adoption. |
| 6 | Marvell | 4.8% | Custom silicon, high-speed interconnect, networking design wins, and data-center revenue. |
| 7 | TSMC | 4.6% | Advanced nodes, CoWoS/packaging capacity, HPC mix, and geopolitics. |
| 8 | Infineon | 4.4% | Data-center power conversion against automotive/industrial cyclicality. |
| 9 | Hinge Health | 4.2% | Clinical outcomes, client retention, engagement, and employer ROI. |
| 10 | Oscar Health | 4.2% | Membership/premium growth, medical-loss ratio, and operating leverage. |

Official source: [June 2026 factsheet](https://fondswelt.hansainvest.com/uploads/documents/fs_retail/HI_DE000A2N8127_retail_2026_06_30.pdf).

### Complete audited 31 December 2025 holdings

The complete audited baseline contained: IREN 8.93%, AUTO1 8.40%, Hinge Health
6.74%, TSMC 5.66%, Micron 5.07%, Reddit 4.93%, Alphabet 4.48%, Datadog 4.34%,
Lemonade 3.95%, Robinhood 3.77%, Oscar Health 3.70%, Meta 3.49%, Rubrik 3.37%,
Kaspi 3.32%, Nvidia 3.26%, Microsoft 2.89%, HUT 8 2.22%, Duolingo 2.02%, Amazon
1.78%, Netskope 1.76%, Luckin Coffee 1.72%, Palo Alto Networks 1.66%, InPost
1.42%, Grindr 1.07%, Coherent 1.07%, AMD 1.04%, Intel 1.02%, Axon 0.97%,
Broadcom 0.82%, Pure Storage 0.78%, Lumentum 0.57%, Xometry 0.55%, Omada
Health 0.55%, and GCL-Poly 0.11%.

Official source: [Audited annual report, 31 Dec 2025](https://fondswelt.hansainvest.com/uploads/documents/jahresbericht/JB_1806_BIT_Global_Technology_Leaders_2025-12-31.pdf).

Do not call a December holding current unless the June top ten or another dated
primary disclosure confirms it. Use `historical_holding` when appropriate.

## Portfolio movement during 2026

Public factsheets show active risk changes. Position count moved from 39 in
January to 29 in February, back to 35–36 in April and May, then down to 28 in
June. Cash and derivatives moved from 3.2% to 15.1%, then close to zero, then
2.5% and 5.4%. February commentary indicates that the team exited software
exposure as application-layer disruption risk increased. The portfolio later
reconcentrated around memory, compute, energy, networking, storage, and
data-center bottlenecks while retaining selected fintech and HealthTech.

That history means a frontier-model or agent release should not automatically
be framed as positive for software. Ask whether it improves distribution and
productivity, destroys application differentiation, changes infrastructure
bottlenecks, or alters capital intensity.

## Public research process

BIT's public process can be summarized as:

1. Form a company thesis and decompose the business into observable operating
   drivers.
2. Identify an information edge: signals that may update those drivers before
   ordinary financial reporting.
3. Combine fundamental company research with alternative data, models, and
   agent-assisted extraction.
4. Translate evidence into forecasts, valuation, position construction, and
   portfolio risk rather than stopping at a qualitative narrative.
5. Challenge conviction through a Devil's Advocate or comparable counter-case
   process.
6. Keep the final investment decision with a human portfolio manager.

Public examples use a Thesis → Edge → Signal → Key Move framing. Job material
also points toward first-principles company decomposition and Volume × Price ×
Mix × Margin analysis. The daily Insight does not need to imitate those labels,
but it should provide the same causal discipline.

Useful supporting references:

- [BIT FAQ](https://bitcap.com/en/haeufig-gestellte-fragen-zum-investieren)
- [Q1 2026 equity report](https://bitcap.com/en/news/bit-capital-quartalsbericht-equity-q1-2026)
- [2026 selection commentary](https://bitcap.com/news/fondsmanager-beckers-2026-wird-das-jahr-der-auslese-podcast)
- [Duolingo alternative-data example](https://bitcap.com/en/news/fondsmanager-jan-beckers-unsere-daten-bei-duolingo-haben-gezeigt-dass-wir-verkaufen-sollten-podcast)
- [Contrarian-investing interview](https://bitcap.com/en/news/fondsmanager-jan-beckers-uber-investments-gegen-den-trend-kaufen-wenn-keiner-die-aktie-haben-will-podcast)

## Aion and the human boundary

BIT's AI Engineer and data-platform recruiting material describes production
agent infrastructure for retrieval, extraction, research signals, evaluations,
observability, and human review. Treat that as evidence of a research workflow,
not proof that an autonomous model chooses investments. The system should make
an analyst faster, preserve sources, expose uncertainty, and propose the next
test; it should not fabricate a trade recommendation or private BIT forecast.

References:

- [AI Engineer role](https://bitcap.jobs.personio.com/job/2685548?language=en)
- [Data Platforms role](https://bitcap.jobs.personio.com/job/1833794?language=en)
- [Semiconductor Analyst role](https://bitcap.jobs.personio.com/job/2701020?language=de)

## Required editorial distinctions

Each affected company uses one of two scopes:

- `portfolio`: present in the skill packet's complete audited working baseline;
- `outside_portfolio`: a specific public-company landing spot supported by the
  evidence and clearly presented as analyst mapping rather than a known BIT
  view, holding, or recommendation.

Each mapping also records a `positive`, `negative`, `mixed`, or `uncertain`
impact and one company-specific mechanism. Consider the portfolio first. Omit
the outside section when no defensible company exists.

An Insight should normally carry this causal chain:

```text
Public evidence
→ operating or competitive driver
→ company or portfolio exposure
→ revenue / margin / capex / market-share / valuation consequence
→ thesis effect and falsifiable watchpoint
```

If the financial link is not established, say that it is unknown and make the
unknown the next diligence task.

## Known public-source cautions

- BIT commentary and an IREN company announcement use conflicting descriptions
  of a large transaction. The company source governs the transaction facts;
  retain the mismatch as a provenance warning.
- Public BIT pages give inconsistent dates for the Micron entry. Do not silently
  reconcile them; it could reflect a re-entry, methodology difference, or
  content error.
- Amazon's weight rose from 1.78% in the audited December 2025 portfolio to
  10.4% in the June 2026 top ten. That proves a large exposure increase, not the
  private cost basis, target weight, or internal expected return.
- Monthly factsheets expose top holdings, not the complete current portfolio.
- Manager commentary, vendor benchmarks, and company announcements are not
  independent validation. Preserve attribution.

## Final quality test

Reject or rewrite an Investment Insight when it is merely “important for AI,”
names a holding without a dated source, lacks an operating-to-financial bridge,
omits the strongest counter-case, or ends with a vague instruction to “monitor
developments.” The watchpoint and next step should name observable evidence.
