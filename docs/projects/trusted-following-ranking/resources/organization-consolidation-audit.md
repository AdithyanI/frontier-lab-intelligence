# Organization consolidation and low-follower sanity audit

Audited 2026-07-11 against the active Registry and `registry-relevance-v1`.
This is a recommendation only; no Registry or database mutation was made.

## Decision rule

Follower count is not a deletion rule. It is useful only for choosing an audit
order. An organization stays when current first-party evidence shows recurring,
original signal for the AI or investment audience. A corporate relationship is
not sufficient to merge two actors: the merge must produce one coherent actor
whose channels can reasonably be read as that actor's output.

X does not expose reliable public timeline dates to the available web index, so
an exact latest-X-post date could not be independently verified for most
handles. The activity checks below therefore use dated first-party websites,
documentation, blogs, releases, or repositories. The only channel clearly
dormant as a source is `@paperswithcode`, because its underlying product was
retired. Do not infer X dormancy from the absence of an indexed post.

## Actionable identity and consolidation findings

| Entity ID | Current entity and channels | Recommendation | Canonical organization | Confidence | Evidence and reason |
|---:|---|---|---|---|---|
| 951 | **NVIDIA AI** — `@nvidiaai` | **Keep; canonicalize name, not a merge.** Rename the entity to **NVIDIA** while retaining `@nvidiaai` as its AI-specific official channel. There is no second NVIDIA organization in the active Registry to merge. | NVIDIA | High | NVIDIA describes itself as one company engineering chips, systems, software, and models for AI; “NVIDIA AI” is its platform/subject area rather than a separate organization. [NVIDIA company](https://www.nvidia.com/en-gb/about-nvidia/) · [NVIDIA AI platform](https://www.nvidia.com/en-us/ai-data-science/generative-ai.html) |
| 4 | **Meta AI (FAIR / superintelligence)** — `@aiatmeta`, GitHub `facebookresearch`, `ai.meta.com`, Meta AI RSS | **Keep as one entity; already consolidated correctly.** Prefer the shorter display name **Meta AI**. Do not create or merge a generic Facebook entity. | Meta AI | High | Meta's official material places FAIR-era research, Meta Superintelligence Labs models, AI infrastructure, and the Meta AI product inside Meta's AI program. The historic `facebookresearch` GitHub namespace is an owned technical channel, not a second current organization. [Meta AI](https://ai.meta.com/) · [Muse Spark / MSL](https://about.fb.com/news/2026/04/introducing-muse-spark-meta-superintelligence-labs/) · [Meta AI infrastructure](https://about.fb.com/news/2026/03/expanding-metas-custom-silicon-to-power-our-ai-workloads/) |
| 2621 + 2384 | **Moonvalley** — `@moonvalley`; **Reka** — `@rekaailabs` | **Merge Moonvalley into Reka.** Retain `@moonvalley` only if it still emits useful technical/product evidence; otherwise retire the channel without deleting Reka. | Reka | High | Reka's first-party announcement calls the transaction a merger and says Moonvalley's researchers and engineers joined Reka to develop physical-AI models and infrastructure. Moonvalley is no longer the best canonical actor. [Reka–Moonvalley announcement](https://reka.ai/news/reka-and-moonvalley-join-forces-to-advance-models-and-infrastructure-for-physical-ai) |
| 2449 | **Papers with Code** — `@paperswithcode` | **Remove the entity / retire the X channel; do not merge it into Meta AI.** It was formerly Meta-supported, but it is no longer a recurring current source. Keep historical data only as provenance outside the active Registry if needed. | None (retired source) | High | Its first-party About page identifies the core team as Meta AI Research, but the service ceased operation on 2025-07-24 and the domain redirected; its GitHub organization shows the data repository last updated 2025-09-08 and most product repositories older. Corporate ownership is not a reason to attach a dormant channel to Meta AI. [First-party About page](https://paperswithcode.com/about) · [GitHub organization/activity](https://github.com/paperswithcode) · [archived shutdown record](https://world-snapshot.github.io/papers-with-code/) |
| 2470 | **ikka** — `@shahules786` (currently typed organization) | **Do not merge this handle into a company. Correct the identity instead:** this is the person Shahul ES, co-founder of Vibrant Labs. Either reclassify the entity as a person named **Shahul ES**, or replace it with a distinct **Vibrant Labs** organization entity sourced from an official organization channel. | Shahul ES (person), not an organization | High | Vibrant Labs' first-party team page identifies Shahul ES as co-founder, and its current research page shows recurring agent-evaluation work. A person's X identity should not be owned by an organization entity. [Vibrant Labs team](https://vibrantlabs.com/about) · [Vibrant Labs research](https://vibrantlabs.com/research) |
| 2495 | **Paperspace (now DigitalOcean)** — `@hellopaperspace` | **Keep; no merge candidate exists.** The existing canonical label is accurate. If DigitalOcean is later added, consolidate under **DigitalOcean / Paperspace** only after deciding whether generic DigitalOcean output belongs in scope. | Paperspace (DigitalOcean) | High | DigitalOcean still operates and updates Paperspace GPU machines and pricing; documentation was verified in June 2026. [Paperspace docs](https://docs.digitalocean.com/products/paperspace/) · [current pricing](https://docs.digitalocean.com/products/paperspace/pricing/) |
| 841 + 2 | **Google** — `@google`, `@googleai`, product/research channels; **Google DeepMind** — `@googledeepmind`, DeepMind site/blog/GitHub | **Keep separate.** Google owns DeepMind, but each is a coherent recurring source actor: Google covers products and infrastructure; Google DeepMind is the frontier lab/research publisher. | Google; Google DeepMind | High | The Registry's identity model benefits from preserving the lab boundary. [Google Research](https://research.google/) · [Google DeepMind research](https://deepmind.google/research/) |

No other high-confidence duplicate organization pair was found. Existing
multi-channel groupings for Anthropic, OpenAI, Mistral AI, Hugging Face,
Anysphere, Vercel, Stanford AI Lab, and Google already represent coherent
organizations with multiple owned channels.

## Low-follower organization slice

These are intentionally audited on current work rather than audience size.

| Entity ID | Entity / X handle | Recommendation | Canonical organization | Confidence | Current activity and relevance evidence |
|---:|---|---|---|---|---|
| 2694 | **Daytona** — `@daytonaio` | Keep | Daytona | High | Active agent-runtime infrastructure with dated technical updates through 2026-07-06, including GPU sandboxes and agent execution. [Daytona articles](https://www.daytona.io/dotfiles/articles) · [GPU sandboxes](https://www.daytona.io/dotfiles/gpu-sandboxes) |
| 2397 | **Glass Health** — `@glasshealthhq` | Keep, but outside the first trusted-seed tranche | Glass Health | Medium | Active clinical model/API with disclosed retrieval architecture, clinician evaluation, and a 900-question benchmark. It is relevant vertical AI, but less central than frontier labs and evaluators. [API documentation](https://glass.health/api-documentation) |
| 2329 | **Transluce** — `@transluceai` | Keep | Transluce | High | Current original interpretability and frontier-model evaluation research; the first-party research feed includes work through late 2025. [Transluce research](https://transluce.org/) |
| 2725 | **npm i task-master-ai** — `@taskmasterai` | Keep; canonicalize display name to **Task Master** | Task Master | High | Active open-source agent workflow infrastructure with releases in 2026 and technical documentation. [GitHub releases](https://github.com/eyaltoledano/claude-task-master/releases) · [documentation](https://docs.task-master.dev/introduction) |
| 2901 | **Pipedream** — `@pipedream` | Keep | Pipedream | High | Current MCP and managed-auth infrastructure for production agents, with documentation updated in 2026. [MCP docs](https://pipedream.com/docs/connect/mcp) |
| 2556 | **Common Crawl Foundation** — `@commoncrawl` | Keep | Common Crawl Foundation | High | Its latest first-party crawl is `CC-MAIN-2026-21`; the corpus remains a recurring original data source for model training and analysis. [latest crawl](https://commoncrawl.org/latest-crawl) |
| 2372 | **SkyPilot** — `@skypilot_org` | Keep | SkyPilot | High | Open-source control plane for AI workloads across clouds and clusters; direct AI-compute and infrastructure signal. [SkyPilot documentation](https://docs.skypilot.co/en/latest/overview.html) |
| 2354 | **MatX** — `@matxcomputing` | Keep | MatX | High | Builds LLM-specific training/inference chips and publishes architecture claims relevant to accelerators, memory, and interconnect. [MatX](https://matx.com/) |
| 2888 | **argmax** — `@argmax` | Keep; capitalize display name to **Argmax** | Argmax | High | Active on-device inference company publishing original benchmarks and product/research posts through April 2026. [Argmax blog](https://www.argmaxinc.com/blog) · [technical documentation](https://app.argmaxinc.com/docs) |
| 2623 | **Bitrig** — `@bitrigapp` | Keep, but outside the first trusted-seed tranche | Bitrig | High | AI-native coding agent with original Swift interpreter work and continuing 2026 product/technical updates. [Bitrig blog](https://bitrig.com/blog) · [agent architecture](https://bitrig.com/blog/meet-bitrig-agent) |
| 2959 | **The Cognitive Revolution Podcast** — `@cogrev_podcast` | Keep | The Cognitive Revolution | Medium | Active specialist-intelligence source with current 2026 interviews and analysis concentrated on models, evaluations, chips, and AI companies. [latest episodes](https://www.cognitiverevolution.ai/latest/) |
| 2884 | **Axolotl AI** — `@axolotl_ai` | Keep | Axolotl | High | Actively maintained open-source LLM fine-tuning/post-training framework, with documented updates through April 2026. [Axolotl docs](https://docs.axolotl.ai/index.html) |
| 3017 | **KI Bundesverband** — `@ki_verband` | Keep, but outside the first trusted-seed tranche | KI Bundesverband | Medium | Repeated first-party analysis on European AI regulation, training infrastructure, and gigafactory finance; useful primarily to the investment audience. [position papers](https://ki-verband.de/positionspapiere-stellungnahmen/) |
| 2366 | **Metal** — `@metal__ai` | Keep provisionally; outside the first trusted-seed tranche | Metal | Medium | AI-native context/MCP infrastructure for private-capital teams, but much of the public output is product marketing. Retain for now and evaluate its realized signal after ingestion. [technical teams](https://www.metal.ai/solutions/technical-teams) |

## Recommended bounded cleanup

1. Merge entity **2621 Moonvalley** into **2384 Reka**.
2. Remove entity **2449 Papers with Code** from the active Registry; do not add
   its dormant channel to Meta AI.
3. Canonicalize **951 NVIDIA AI** to **NVIDIA**, **4 Meta AI (FAIR /
   superintelligence)** to **Meta AI**, **2725** to **Task Master**, and **2888**
   to **Argmax** without changing channel ownership.
4. Correct entity **2470 ikka / `@shahules786`** to a person identity rather
   than treating it as an organization merge.
5. Keep the remaining low-follower organizations. Apply seed selection after
   identity cleanup; do not delete them merely because they are below 10K X
   followers.
