# Major Organization Coverage Audit

Status: evidence audit in progress; no Registry mutations from this document.
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

## Already covered

The active Registry already includes the major independent and corporate model
organizations OpenAI, Anthropic, Google, Google DeepMind, Meta AI, NVIDIA,
Mistral AI, DeepSeek, Qwen (Alibaba), Baidu Research, Cohere, AI21 Labs,
Databricks AI Research, MiniMax, Kimi.ai, Z.ai, Safe Superintelligence,
Thinking Machines Lab, Black Forest Labs, Stability AI, Runway, Midjourney,
Ideogram, and several infrastructure/evaluation organizations.

## Deliberate second-pass watchlist

Baichuan AI, Aleph Alpha, Inflection, Adept, and other historically prominent
model organizations need a current-operation check before inclusion. They are
not silently treated as covered or rejected. The ranking output may also reveal
additional organizations, but promotion still requires first-party evidence.

## Required implementation shape

1. Freeze this reviewed roster in a versioned manifest with expected canonical
   name, exact handles, first-party evidence, and action (`create`, `attach`, or
   `merge`).
2. Preflight every handle against both `fli.db` and the immutable snapshot.
3. Apply in one transaction, preserving accounts, channels, observations,
   source facts, and merge audit provenance.
4. Make replay idempotent and fail closed on ownership conflicts.
5. Re-run a coverage report that proves every P0 anchor is present and that no
   product/team entity remains accidentally standalone.

## Decision still needed

The recommended first mutation is the six P0 organizations. P1 is a coverage
backlog, not an instruction to flood the Registry: each row should be admitted
only after its canonical channels and current relevance are verified.
