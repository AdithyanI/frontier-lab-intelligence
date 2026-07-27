# Investment Company Universe

Last reviewed: 2026-07-27

This is the human inspection map for the first Investment audience fan-out.
The canonical machine-readable source remains
`.agents/skills/fli-daily-intelligence/references/bit-investment-context.json`.
Do not maintain a second independent set of company facts in this document.
The same packet is available as an auditable product view at
`/bit-lens/companies`.

## Purpose

The Investment pass should not rediscover each company on every daily run. It
should reuse one dated company lens, then decide whether the current Event
changes that lens.

Each canonical company profile already contains:

- stable name, ticker, aliases, and identity sources;
- a concise business description and operating drivers;
- one or more two-sided frontier-AI transmission channels;
- upside, downside, watchpoints, and company-specific cautions;
- any public BIT view, kept separate from FLI analyst context and graded by
  source scope.

The packet currently covers 37 companies with 114 operating drivers, 63
frontier-AI transmission channels, 189 watchpoints, 112 cautions, and 77
identity sources. Four companies have an explicit public BIT thesis, ten have
BIT commentary, and 23 have no attributable BIT view. A missing BIT view must
remain missing; the Investment pass may use the sourced analyst context but
must not invent a fund thesis.

## Disclosure Boundary

This is a working coverage universe assembled from two dated public
disclosures:

- The complete audited portfolio contains 34 holdings as of 31 December 2025.
- The 30 June 2026 factsheet discloses only the current top ten. Those weights
  supersede the older weight for those names.
- SanDisk, Marvell, and Infineon appear in the June top ten but not in the
  December baseline. They are included with the June disclosure attached.
- The other 27 companies must not be described as confirmed current holdings.
  Their last complete public basis remains 31 December 2025.

Holding weight is portfolio context, not evidence that an Event affects a
company. It may order otherwise comparable affected companies, but it must
never create a transmission mechanism.

## Company Index

The final column names the reusable channels through which frontier-AI
developments could reach the company. The daily model must still decide whether
the particular Event activates any channel.

| Company | Portfolio disclosure | What it is | Frontier-AI transmission channels |
| --- | --- | --- | --- |
| **IREN** (`IREN`) | 8.50% · 30 Jun 2026 top ten | IREN builds, owns, and operates power-dense data centers in North America for AI cloud, colocation and build-to-suit services, while retaining Bitcoin-mining operations. | Power-constrained AI data centers; Bitcoin mining as an alternate use of power |
| **AUTO1** (`AG1`) | 8.40% · 31 Dec 2025 audited holding | AUTO1 Group operates a European digital used-car platform spanning consumer sourcing, dealer remarketing and wholesale through AUTO1.com, retail through Autohero, and consumer and merchant financing. | Vehicle pricing, appraisal, and cross-market inventory matching |
| **Hinge Health** (`HNGE`) | 4.20% · 30 Jun 2026 top ten | Hinge Health provides technology-enabled care for musculoskeletal conditions through software, AI, wearable technology, and clinician oversight, primarily for employers, health plans, and benefits partners. | Automated motion tracking and personalized care delivery |
| **TSMC** (`TSM`) | 4.60% · 30 Jun 2026 top ten | TSMC is a pure-play semiconductor foundry that manufactures customer designs using leading-edge and specialty process technologies and provides advanced packaging and chip-stacking services. | Leading-edge AI accelerator fabrication and packaging; AI moving into PCs, phones, vehicles, and edge devices |
| **Micron** (`MU`) | 8.60% · 30 Jun 2026 top ten | Micron develops and manufactures memory and storage products, principally DRAM, NAND, high-bandwidth memory, and solid-state drives for data centers, clients, mobile, automotive, and embedded markets. | HBM and server DRAM for AI accelerators; AI data storage and inference memory hierarchy |
| **Reddit** (`RDDT`) | 4.93% · 31 Dec 2025 audited holding | Reddit is a community-of-communities platform where users submit, vote on, and discuss content. It monetizes primarily through advertising, with other revenue including commercial data and API arrangements. | Licensing public conversation for model training and grounding; AI-assisted translation, search, and content discovery |
| **Alphabet** (`GOOGL`) | 4.48% · 31 Dec 2025 audited holding | Alphabet is the listed parent of Google. Google Services includes Search, YouTube, Android, Maps, Play, subscriptions, and devices; Google Cloud sells infrastructure, AI platforms, cybersecurity, data tools, and collaboration software; Other Bets includes businesses such as Waymo. | AI-native Search, recommendations, and advertising; Vertically integrated frontier-model and cloud stack |
| **Datadog** (`DDOG`) | 4.34% · 31 Dec 2025 audited holding | Datadog provides a cloud observability and security platform that brings together infrastructure monitoring, application performance, logs, traces, digital experience, software delivery, incident response, and cloud security in one data model and workflow. | Observability for models and AI agents; Bits AI agents for development, operations, and security |
| **Lemonade** (`LMND`) | 3.95% · 31 Dec 2025 audited holding | Lemonade is an AI-powered, full-stack insurer offering renters, homeowners, car, pet, and life products across the United States and Europe. | Underwriting, pricing, claims, and customer-service automation |
| **Robinhood** (`HOOD`) | 5.00% · 30 Jun 2026 top ten | Robinhood is a financial-services platform offering retail brokerage, crypto, advisory, digital banking, and private-markets access to a new generation of investors. | Cortex and personalized financial guidance inside the distribution surface |
| **Oscar Health** (`OSCR`) | 4.20% · 30 Jun 2026 top ten | Oscar Health is a technology-enabled health insurer built on a full-stack platform, offering Individual and Family plans, ICHRA solutions, +Oscar technology services, and the Lucie Health Marketplace. | Oswell member support, care navigation, and plan-benefit interpretation |
| **Meta** (`META`) | 3.49% · 31 Dec 2025 audited holding | Meta operates Facebook, Instagram, Messenger, WhatsApp, Threads, and related services in Family of Apps, whose revenue is predominantly advertising. Reality Labs develops virtual- and augmented-reality hardware, software, and content, including AI glasses. | Recommendation, ranking, and generative advertising systems; Meta AI and model distribution across consumer apps |
| **Rubrik** (`RBRK`) | 3.37% · 31 Dec 2025 audited holding | Rubrik sells a subscription cyber-resilience platform spanning immutable data protection, threat detection, sensitive-data posture, identity resilience, and orchestrated recovery across enterprise, cloud, and SaaS environments. It is extending that control plane into AI data and agent operations. | Governed access to enterprise data for AI applications; Monitoring, governing, and rewinding AI agents |
| **Kaspi** (`KSPI`) | 3.32% · 31 Dec 2025 audited holding | Kaspi.kz operates consumer and merchant Super Apps that connect payments, marketplace, and fintech services in Kazakhstan, and it controls the Hepsiburada e-commerce platform in Türkiye. | Super-app personalization, merchant tools, real-time credit decisions, and fraud control |
| **NVIDIA** (`NVDA`) | 3.26% · 31 Dec 2025 audited holding | NVIDIA provides an accelerated-computing platform spanning GPUs and CPUs, networking, systems, and software for data centers, gaming, professional visualization, automotive, and edge workloads. | Training and scaling frontier models; Inference and agentic AI factories |
| **Microsoft** (`MSFT`) | 2.89% · 31 Dec 2025 audited holding | Microsoft combines productivity and business applications, Azure cloud and AI services, developer tools, Windows, search, gaming, LinkedIn, and enterprise support in a recurring-license and consumption-led platform. | Azure AI infrastructure and model platform; Copilots and agents across the installed base |
| **HUT 8** (`HUT`) | 2.22% · 31 Dec 2025 audited holding | Hut 8 is a power-first energy infrastructure platform spanning powered land and electrical systems, purpose-built digital infrastructure, and compute businesses. It develops and leases AI and high-performance-computing data centers while retaining exposure to Bitcoin mining through American Bitcoin and related infrastructure services. | Hyperscale AI data-center development and leasing; Power scarcity and interconnection as the bottleneck for AI compute |
| **Duolingo** (`DUOL`) | 2.02% · 31 Dec 2025 audited holding | Duolingo operates a freemium mobile learning platform led by language courses, with paid Super and Max subscriptions, advertising, the Duolingo English Test, and expansion into subjects such as math, music, and chess. | AI tutoring, conversational practice, and course-content generation |
| **Amazon** (`AMZN`) | 10.40% · 30 Jun 2026 top ten | Amazon operates first- and third-party commerce, fulfillment and logistics, subscriptions, advertising, and Amazon Web Services, which provides global compute, storage, database, analytics, and AI services. | AWS compute, models, and custom AI silicon; AI in retail, advertising, and logistics |
| **Netskope** (`NTSK`) | 1.76% · 31 Dec 2025 audited holding | Netskope converges security, networking, and analytics in the Netskope One platform. Its Zero Trust Engine and company-operated NewEdge network secure and accelerate access to cloud, SaaS, web, private applications, and AI as a Security Service Edge and Secure Access Service Edge provider. | Security controls for AI applications, models, agents, and MCP traffic; Agentic security and network operations |
| **Luckin Coffee** (`LKNCY`) | 1.72% · 31 Dec 2025 audited holding | Luckin Coffee operates a technology-driven coffee retail network centered on mobile ordering, cashierless transactions, a large store footprint, and data-led customer, store, and supply-chain operations. | Demand forecasting, personalized offers, menu development, and store operations |
| **Palo Alto Networks** (`PANW`) | 1.66% · 31 Dec 2025 audited holding | Palo Alto Networks provides cybersecurity platforms across network security, cloud security, security operations, AI security, and identity. Its platformization strategy seeks to consolidate point products onto integrated data, policy, and workflow layers. | Security platform for AI applications and autonomous agents; AI-driven security operations |
| **InPost** (`INPST`) | 1.42% · 31 Dec 2025 audited holding | InPost is a European e-commerce logistics platform built around automated parcel machines, out-of-home delivery, digital consumer tools, and an expanding cross-border last-mile network. | Locker placement, route optimization, capacity forecasting, and parcel support |
| **Grindr** (`GRND`) | 1.07% · 31 Dec 2025 audited holding | Grindr operates a global social and connection app for gay, bisexual, transgender, and queer adults, monetized through subscriptions and other paid features while expanding toward a broader "Global Gayborhood" platform. | AI-native discovery, conversation support, travel utility, and safety tooling |
| **Coherent** (`COHR`) | 1.07% · 31 Dec 2025 audited holding | Coherent supplies photonic materials, components, modules, subsystems, and lasers for data-center and telecom communications, industrial applications, electronics, and instrumentation. | High-speed optical interconnects inside AI data centers; Co-packaged optics and optical switching |
| **AMD** (`AMD`) | 1.04% · 31 Dec 2025 audited holding | AMD supplies high-performance and adaptive computing products across data-center CPUs and AI accelerators, client and gaming processors, networking, FPGAs, and embedded systems. | Alternative AI accelerators and rack-scale systems; Host CPUs and client AI |
| **Intel** (`INTC`) | 1.02% · 31 Dec 2025 audited holding | Intel designs x86 compute platforms for clients and data centers and is building Intel Foundry to manufacture and package chips for internal and external customers. | CPUs and platforms around AI accelerators; Foundry and advanced packaging for AI chips |
| **Axon** (`AXON`) | 0.97% · 31 Dec 2025 audited holding | Axon provides a connected public-safety ecosystem spanning TASER energy weapons, body and vehicle cameras, digital evidence and records software, real-time operations, drones and counter-drone tools, training, and AI-enabled workflows. Revenue spans connected devices and higher-margin software and services. | AI-assisted report writing, transcription, translation, and evidence review; Real-time multimodal intelligence |
| **Broadcom** (`AVGO`) | 0.82% · 31 Dec 2025 audited holding | Broadcom designs semiconductors for custom compute, networking, connectivity, broadband, wireless, storage, and industrial markets and supplies infrastructure software led by VMware Cloud Foundation. | Custom AI accelerators; Ethernet, optics, and data movement |
| **Pure Storage** (`PSTG`) | 0.78% · 31 Dec 2025 audited holding | Pure Storage provides all-flash data-storage systems and a unified storage-as-a-service platform across on-premises, hosted, and cloud environments, including FlashArray, FlashBlade, Evergreen, and Portworx. | Storage for training, retrieval, checkpoints, and AI data pipelines; Hyperscale replacement of disk with flash |
| **Lumentum** (`LITE`) | 0.57% · 31 Dec 2025 audited holding | Lumentum supplies optical and photonic lasers, modules, and subsystems for AI and cloud data-center connectivity, telecom networks, industrial manufacturing, and sensing. | Optical connectivity for scale-out AI clusters; Photonics for next-generation network architectures |
| **Xometry** (`XMTR`) | 0.55% · 31 Dec 2025 audited holding | Xometry operates an AI-native, two-sided marketplace for custom manufacturing. Its instant-quoting and sourcing models connect buyers with a global supplier network, while Thomasnet and cloud tools support supplier discovery and shop operations. | Closed-loop pricing, sourcing, and lead-time intelligence; Physical supply chain for AI and data-center infrastructure |
| **Omada Health** (`OMDA`) | 0.55% · 31 Dec 2025 audited holding | Omada Health provides virtual care for cardiometabolic conditions, musculoskeletal care, GLP-1 support, and behavioral health by combining care teams, connected devices, software, and AI for employers and health-plan buyers. | OmadaSpark, Meal Map, and AI-assisted personalized care between visits |
| **GCL-Poly** (`03800.HK`) | 0.11% · 31 Dec 2025 audited holding | GCL-Poly is the former name of GCL Technology Holdings, a Hong Kong-listed energy-materials manufacturer. Its core products include low-carbon FBR granular silicon and photovoltaic wafers, with development in perovskite solar modules and a broader move into silicon-, lithium-, and carbon-based materials. | AI-assisted materials research and manufacturing optimization; Electricity demand from AI infrastructure |
| **SanDisk** (`SNDK`) | 6.00% · 30 Jun 2026 top ten · not in Dec baseline | SanDisk designs and sells NAND flash storage, spanning client and enterprise SSDs, embedded storage, and consumer memory products. It was separated from Western Digital as a standalone flash business in 2025 and retains a joint-venture manufacturing relationship with Kioxia. | Enterprise SSD demand from AI training and inference storage tiers; Substitution pressure between flash and disk in AI data centers |
| **Marvell** (`MRVL`) | 4.80% · 30 Jun 2026 top ten · not in Dec baseline | Marvell supplies data-infrastructure semiconductors spanning custom compute (XPU) silicon for hyperscalers, electro-optics and high-speed interconnect, ethernet switching, and storage controllers, alongside legacy carrier, enterprise networking, and automotive lines. | Custom accelerator (XPU) silicon for hyperscalers; Scale-up and scale-out interconnect for heterogeneous clusters |
| **Infineon** (`IFX`) | 4.40% · 30 Jun 2026 top ten · not in Dec baseline | Infineon is a German semiconductor manufacturer supplying power semiconductors, microcontrollers, sensors, and security products across automotive, industrial and infrastructure, power and sensor systems, and connected secure systems. | Power delivery and conversion for AI data centers; Grid, renewables, and energy-infrastructure build-out around AI load growth |

## How the Investment Pass Should Use It

For each relevant Event:

1. Load this canonical company roster as the stable prompt prefix.
2. Require one verdict for every company; never let the model silently choose
   which holdings deserve consideration.
3. Treat the Event as the changing suffix and the only evidence that can
   activate a transmission channel.
4. Preserve `unaffected` decisions with a compact reason code.
5. For affected companies, return the mechanism, thesis or operating driver
   touched, direction, action tier, and supporting source identifiers.
6. Validate in code that all 37 canonical companies appear exactly once.
7. Rank the validated Event-company pairs deterministically after the model
   call. Never ask the model for a synthetic importance score.

The corresponding AI Engineering roster should be a separate, later
definition of build surfaces. It should reuse the same fan-out engine without
mixing company and engineering concepts into one prompt.

## Inspection Commands

Read the compact company index:

```bash
.venv/bin/fli daily-intelligence context \
  --audience investment --compact --json --no-input
```

Read one complete company lens:

```bash
.venv/bin/fli daily-intelligence company-context \
  --company MSFT --json --no-input
```

The complete context command remains available for audit and returns the
canonical packet path and SHA-256.
