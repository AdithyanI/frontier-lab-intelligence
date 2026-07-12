# Major Organization Coverage Audit

Status: P0 and parent-normalization batch applied; P1 remains a reviewed backlog.
Date: 2026-07-11.

## Why this audit exists

The Registry was bootstrapped from observed X accounts and then passed through
kind, relevance, activity, and temporary follower-floor gates. That produces a
useful working cohort, but it is not a complete census of frontier-model
organizations. Visual Studio Code surviving as a standalone organization while
Microsoft was absent exposed the gap.

The durable fix is a small, explicit anchor-organization coverage layer. Graph
discovery can find new candidates later, but it must not be responsible for
remembering obvious major model builders.

## Canonical naming and ownership rule

- Use the stable real-world organization as the entity: `Microsoft`, `Amazon`,
  `Apple`, `Google`, not a temporary team or product name.
- Product, research, and model-family accounts become channels beneath that
  entity when they are operated by the same organization.
- Keep a separately operated, enduring organization first-class when doing so
  materially improves the assignment. `Google DeepMind` qualifies: it has its
  own website, X account, GitHub organization, blog, and lab identity. Therefore
  `Google` and `Google DeepMind` may both remain, while Google product channels
  stay under `Google`.
- An LLM may suggest ownership candidates, but it cannot authorize a merge.
  Exact handles, first-party evidence, and a reviewed versioned manifest are
  required.

## Confirmed current blind spots

These organizations have current first-party evidence of substantial model or
AI research work and are absent as canonical Registry entities. The X handles
listed here already exist in the immutable following snapshot unless noted.

| Priority | Canonical organization | Relevant channels/evidence | Recommended action |
| --- | --- | --- | --- |
| P0 | Microsoft | `@microsoft`, `@microsoftai`, `@msftresearch`, `@code`; [AI Frontiers](https://www.microsoft.com/en-us/research/lab/ai-frontiers/overview/) | Create Microsoft; merge Visual Studio Code into it; retain the four channels. |
| P0 | Amazon | `@amazon`, `@amazonscience`, `@awscloud`; [Amazon AGI Lab](https://labs.amazon.science/) | Create Amazon; attach research/cloud channels; do not create Amazon AGI Lab separately. |
| P0 | Apple | `@apple`; [Apple Machine Learning Research](https://machinelearning.apple.com/) | Create Apple; attach the X identity and ML website; do not create Apple ML separately. |
| P0 | Ai2 | `@allen_ai`, `@ai2_allennlp`; [Olmo](https://allenai.org/olmo) | Create Ai2 and attach its model/research channels. |
| P0 | ByteDance | `@bytedancetalk`, `@bytedanceoss`; [Seed](https://seed.bytedance.com/en/) | Create ByteDance; treat Seed as its research surface, not a second entity for now. |
| P0 | Tencent | `@tencentglobal`, `@tencenthunyuan`; [Hunyuan](https://www.tencent.com/en-us/articles/2202386.html) | Create Tencent and attach Hunyuan as a model-family channel. |
| P0 | NVIDIA | `@nvidia`, `@nvidiaai`; [NVIDIA AI](https://www.nvidia.com/en-us/solutions/ai/) | Normalize NVIDIA as the parent and retain NVIDIA AI as its official channel. |
| P0 | AMD | `@amd`; [AMD AI Solutions](https://www.amd.com/en/solutions/ai.html) | Add AMD as an AI-compute anchor; do not add consumer product accounts merely to inflate reach. |
| P0 | Intel | `@intel`, `@intelai`; [Intel AI](https://www.intel.com/content/www/us/en/artificial-intelligence/overview.html) | Add Intel and attach Intel AI as an official channel. |
| P1 | IBM | `@ibm`, `@ibmresearch`; [foundation models](https://research.ibm.com/topics/foundation-models) | Add as a corporate research anchor. |
| P1 | Huawei | `@huawei`; [Pangu model documentation](https://support.huaweicloud.com/productdesc-pangulm/) | Add Huawei with Pangu as website evidence; no dedicated Pangu X channel was found in the snapshot. |
| P1 | Samsung | `@samsung`, `@samsungresearch`; [Samsung Gauss](https://research.samsung.com/artificial-intelligence) | Add Samsung and attach Samsung Research. |
| P1 | Salesforce | `@salesforce`, `@sfresearch`; [AI Foundry](https://www.salesforce.com/news/stories/ai-foundry-announcement/) | Add Salesforce and attach its research channel. |
| P1 | Xiaomi | `@xiaomi`, `@xiaomimimo`; [MiMo releases](https://mimo.mi.com/docs/en-US/updates/model) | Add Xiaomi and attach MiMo as its model channel. |
| P1 | StepFun | `@stepfun_ai`; [StepFun platform](https://platform.stepfun.ai/) | Add StepFun as a standalone model organization. |
| P1 | NAVER | `@official_naver`; [HyperCLOVA X](https://www.navercorp.com/en/tech/hyperclovax) | Add NAVER; attach HyperCLOVA X as website evidence. |
| P1 | Ant Group | `@antgroup`; [Ling model family](https://www.antgroup.com/en/technology/new-tech-Technology-Antfocuses-Tabcomnent-detail/20241028001) | Add Ant Group; keep Ling/Ring/Ming as model families, not entities. |
| P1 | SenseTime | `@sensetime_ai`; [SenseNova 6.7](https://www.sensetime.com/cn/news-detail/51170639?categoryId=72) | Add despite the temporary follower floor; the official model evidence is stronger than reach. |
| P1 | 01.AI | `@01ai_yi`; [current company/model record](https://www.01.ai/) | Add as 01.AI; do not infer ownership from similarly named Yi products. |
| P1 | Adobe | no verified X handle selected yet; [Firefly foundation models](https://news.adobe.com/news/2026/03/adobe-and-nvidia-announce-strategic-partnership) | Verify the canonical X identity, then add Adobe with Firefly evidence. |
| P1 | Writer | no verified X handle selected yet; [Palmyra models](https://dev.writer.com/home/models) | Verify identity/channel ownership before addition. |
| P1 | ServiceNow | `@servicenow`, `@servicenowrsrch`; [Frontier AI Research](https://www.servicenow.com/research/) | Add ServiceNow; its research team is a channel, not a separate entity. |
| P1 | Poolside | `@poolsideai`; [current model program](https://poolside.ai/) | Add despite low X reach after the official handle is reverified. |
| P1 | Essential AI | `@essential_ai`; [current model program](https://www.essential.ai/) | Add despite low X reach; the official site links the handle. |
| P1 | LG | no verified X handle selected; [EXAONE](https://www.lgresearch.ai/exaone/) | Add LG with LG AI Research/EXAONE website channels; X is not required. |

## Existing entities that need parent normalization

This is a separate problem from missing coverage. The following active rows are
products or internal teams, not the stable organization we intend to model.

| Current entity | Canonical organization | Required action |
| --- | --- | --- |
| Visual Studio Code | Microsoft | Create Microsoft from `@microsoft`, merge the existing VS Code entity, and retain `@code` as an official product channel. |
| Meta AI | Meta | Create Meta from `@meta`, merge the existing AI entity, and keep `@aiatmeta` plus the lab sources as official channels. Align the internal seed so replay cannot revert the public name. |
| Qwen (Alibaba) | Alibaba | Create Alibaba from `@alibabagroup`, merge Qwen, and keep its X/blog/GitHub/model sources as official channels. Align the internal seed. |
| Baidu Research | Baidu | Create Baidu from `@baidu_inc`, merge the research entity, and keep research/ERNIE sources as official channels. |
| Databricks AI Research | Databricks | Create Databricks from `@databricks`, merge the research entity, and keep Mosaic AI sources as official channels. |
| Kimi.ai | Moonshot AI | Create a website-anchored Moonshot AI canonical, merge the product entity, and retain `@kimi_moonshot`. |
| Kling AI | Kuaishou | Create a website-anchored Kuaishou canonical, merge the product entity, and retain `@kling_ai`. |

Small cosmetic overrides should be handled separately from ownership changes:
`MiniMax (official)` to `MiniMax`, and removal of decorative emoji from
Higgsfield AI, Synthesia, and OpenClaw. They are not merge decisions.

## Already covered

The active Registry already includes the major independent and corporate model
organizations OpenAI, Anthropic, Google, Google DeepMind, Meta, NVIDIA,
Microsoft, Amazon, Apple, AMD, Intel, Mistral AI, DeepSeek, Alibaba, Baidu,
Cohere, AI21 Labs, Databricks, MiniMax, Moonshot AI, Z.ai, Safe Superintelligence,
Thinking Machines Lab, Black Forest Labs, Stability AI, Runway, Midjourney,
Ideogram, and several infrastructure/evaluation organizations.

## Deliberate second-pass watchlist

Baichuan AI, Aleph Alpha, Inflection, Adept, Snowflake, Kakao, NTT, Preferred
Networks, Arm, Broadcom, Qualcomm, TSMC, Cerebras, Groq, CoreWeave, Lambda,
SambaNova, Tenstorrent, and other historically or regionally prominent model organizations
need a current-operation/frontier-scope check before inclusion. Replit, Oracle,
and SAP should not enter merely because they are large AI platforms. These
organizations are not silently treated as covered or rejected. The ranking
output may reveal additional candidates, but promotion still requires
first-party evidence.

## Required implementation shape

1. Add tracked `data/registry/organization-coverage.json` with canonical name,
   slug, exact handles, expected X IDs, channel relationships, first-party
   evidence, and action (`create`, `attach`, or `merge`).
2. Add `fli registry apply-organization-coverage --snapshot <snapshot.db>
   [--dry-run]`. Existing organization-group tooling cannot create a canonical
   from a target-only snapshot account.
3. Preflight the exact snapshot id/checksum, stable X IDs, unique handles,
   expected current owners, kinds, and rejection state before the first write.
4. Apply in one transaction. Import only reviewed account/profile facts and a
   dated follower observation—never snapshot edges or raw pages—then preserve
   channels, observations, source facts, and merge audit provenance.
5. Make replay idempotent and fail closed on ownership conflicts. Parent X
   accounts use `identity`; product/research handles use `official`.
6. Re-run a coverage check that proves every P0 canonical exists and no listed
   product/team entity remains accidentally standalone.

## Applied decision

The versioned manifest applied the six original missing anchors, seven explicit
parent-normalization rows, and the NVIDIA/AMD/Intel compute-anchor correction.
Replay is idempotent and all imported profile facts came from the pinned local
snapshot, so the mutation incurred no new provider spend. P1 and the compute
watchlist remain coverage backlogs, not instructions to flood the Registry:
each organization should be admitted only after its canonical channels and
current relevance are verified. Ranking may nominate additional candidates,
but it does not replace this explicit major-anchor review.
