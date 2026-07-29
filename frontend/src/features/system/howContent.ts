import type { FunnelStage } from './SignalFunnel'

export const VIDEO_WALKTHROUGH_URL = 'https://share.descript.com/view/LZkpHP29yub'

export const SCROLL_STAGES: FunnelStage[] = [
  'watch',
  'collect',
  'rank',
  'judge',
  'publish',
  'complete',
]

export type HowBeat = {
  id: FunnelStage
  step: string
  title: string
  text: string
}

export const HOW_BEATS: HowBeat[] = [
  {
    id: 'watch',
    step: '1',
    title: 'Choose',
    text: 'The system watches one source: X. Inside it, a screened network of frontier labs and the researchers who work there. Only what this trusted cohort posts gets collected.',
  },
  {
    id: 'collect',
    step: '2',
    title: 'Collect',
    text: 'Capture complete observed X days for the screened cohort. Replies, quotes, and threads are grouped into exact Events. Linked papers, repos, and model cards enter a separate artifact catalogue, and successful text snapshots are frozen.',
  },
  {
    id: 'rank',
    step: '3',
    title: 'Rank',
    text: 'Same-day original posts that share one specific artifact become a Development. A transparent rank then asks how many trusted Registry entities authored, quoted, or reposted it; participant position and one-post public interaction only break ties. It decides where to look first; judging comes later.',
  },
  {
    id: 'judge',
    step: '4',
    title: 'Judge',
    text: 'Every Development can later be asked two independent questions. Does this change an investment position? Should an engineering team act on it? Each answer keeps its reasons attached.',
  },
  {
    id: 'publish',
    step: '5',
    title: 'Write',
    text: 'Two agents write, one per audience, and neither sees the other. The Investment agent screens all 37 portfolio companies and must either name a company in its output or record why it was rejected. The AI Engineering agent maps the same Development onto the seven surfaces of a reference AI system. Every claim cites its source, and the application supplies every link.',
  },
]

export type ShowcaseInsight = {
  title: string
  meta: string
  why: string
  to: string
}

export type ShowcaseGroup = {
  id: string
  heading: string
  blurb: string
  items: ShowcaseInsight[]
}

export const SHOWCASE_GROUPS: ShowcaseGroup[] = [
  {
    id: 'investment',
    heading: 'Five for the investment team',
    blurb:
      'Chosen from the 64 Investment Insights the system published across 24 days. Every link opens the exact Insight with its sources, the memos the agent opened, and the pre-registered bet it cited.',
    items: [
      {
        title: 'Agentic training may create a new high-throughput storage workload',
        meta: '27 July \u00b7 PSTG',
        why: 'Two hops from a lab release to a company nobody would have guessed: Moonshot open-sources its RL sandbox, the sandbox implies constant snapshot and metadata traffic, that traffic implies storage. Pure Storage appears in one of the 64 published Insights.',
        to: '/insights?audience=investment&status=kept&date=2026-07-27&insight=84a2092be2343b029edc7aa91d3dc449573bf74bbfc609b7843aa2bd2e3ce9d0',
      },
      {
        title: 'OpenAI code scanner raises benchmark for Alphabet\u2019s Wiz security stack',
        meta: '28 July \u00b7 GOOGL \u00b7 3 memos opened, 1 kept',
        why: 'The clearest picture of the agent discarding. It opened company memos for Palo Alto, Microsoft and Alphabet, then published only Alphabet \u2014 the link running through its ownership of Wiz. The two rejected candidates stay visible in the trace.',
        to: '/insights?audience=investment&status=kept&date=2026-07-28&insight=341168a68c039437e8c44ea89b41fb10830f8acbea055025f59c4d0af3b19e4e',
      },
      {
        title: 'OKLS could reduce GPU needs, but frontier-scale proof is absent',
        meta: '28 July \u00b7 IREN, NVDA, TSM \u00b7 downside',
        why: 'A bear case assembled out of an optimizer paper. One mechanism \u2014 fewer GPU-hours for a fixed target \u2014 carried to a neocloud, a chipmaker and a foundry, with TSMC labelled as the indirect, one-step-removed link. The headline states its own limit.',
        to: '/insights?audience=investment&status=kept&date=2026-07-28&insight=ce3100e1aabd9b478f18bde17fa73778a84245083c62875dd5e9e722dcb32655',
      },
      {
        title: 'OpenAI\u2019s native prompt defenses raise AI-security vendors\u2019 competitive bar',
        meta: '15 July \u00b7 PANW, NTSK \u00b7 downside',
        why: 'The answer to \u201cdoes it just repeat itself?\u201d. AI-security news usually reads as demand for Palo Alto. Here the same theme reads as a threat to it, because the lab shipped the defense itself. Microsoft was opened and dropped.',
        to: '/insights?audience=investment&status=kept&date=2026-07-15&insight=25f93358a5bee7672c6a354cb45867771cc4b449ff75da633a430c7aed4a7cf0',
      },
      {
        title: 'Treasury warning raises China sales risk for NVIDIA and AMD',
        meta: '22 July \u00b7 NVDA, AMD \u00b7 downside',
        why: 'The Treasury Secretary is not in the Registry. This arrived because 18 people who are quoted or reposted him within a day. The Insight then separates a stated warning from an enacted restriction, and drops TSMC after opening its memo.',
        to: '/insights?audience=investment&status=kept&date=2026-07-22&insight=329ab2a4edc09b7a3e8cd78737f31f7736020f1a2ce1615a64b669110559f07b',
      },
    ],
  },
  {
    id: 'ai_engineering',
    heading: 'Five for the engineering team',
    blurb:
      'Chosen from the 27 AI Engineering Insights published over the same window. Each one lands on the surfaces of a reference AI platform and says what the team would test or adopt.',
    items: [
      {
        title: 'Open-source AgentENV claims sub-100 ms snapshotting for agent sandboxes',
        meta: '27 July \u00b7 Operations, Agents',
        why: 'The same Development as the first Investment Insight above, read for a different reader. No shared prose, no shared agent: one sees a storage demand signal, the other sees a Firecracker sandbox runtime \u2014 and flags that it ships without authorization.',
        to: '/insights?audience=ai_engineering&status=kept&date=2026-07-27&insight=84a2092be2343b029edc7aa91d3dc449573bf74bbfc609b7843aa2bd2e3ce9d0',
      },
      {
        title: 'Vercel quantifies model cost and recall tradeoffs for vulnerability scans',
        meta: '27 July \u00b7 Operations, Models and cost',
        why: 'A routing decision with prices attached. The top score cost $55.98 and ran 3 hours 39 minutes; two cheaper models reached about half the score for $12.38 and $5.60. That is the frequent-scan versus deep-audit question stated in numbers.',
        to: '/insights?audience=ai_engineering&status=kept&date=2026-07-27&insight=e3ff253226a99db0b7246e805bd3823ffe7f231d74d7eb9ebe79d5a47e8d147d',
      },
      {
        title: 'camelAI replaces persistent agent VMs with scoped edge isolates',
        meta: '28 July \u00b7 Agents, Operations',
        why: 'An architecture to copy rather than a headline to read: agent state in a Durable Object, generated code in fresh V8 isolates with no credentials in reach, short-lived containers only where Linux is unavoidable. The Investment agent kept nothing here.',
        to: '/insights?audience=ai_engineering&status=kept&date=2026-07-28&insight=f29b09bdb24794ead0847e94ddf9938ae6f8b4211f928ceb77804792d21ee834',
      },
      {
        title: 'PACE predicts agent benchmark results from selected non-agentic tests',
        meta: '6 July \u00b7 Evaluation',
        why: 'Agentic evaluation at roughly a hundredth of the cost, by predicting agent scores from cheap non-agentic instances. The Insight keeps the terms of the trade on screen: 0.81 rank correlation and 3.80% mean absolute error, not yet replicated independently.',
        to: '/insights?audience=ai_engineering&status=kept&date=2026-07-06&insight=98c1b1ce20ddc0b82e359fc59b83146648244da24744cca669c2ad1471cbb428',
      },
      {
        title: 'Hashimoto\u2019s invoice agent uses token-enforced limits on outbound email',
        meta: '14 July \u00b7 Operations',
        why: 'A least-privilege pattern worth stealing: read-only access to the evidence, a recipient allowlist enforced by the API token rather than by the prompt, and a human verifying before anything irreversible. It found about $45,000 in bad invoices.',
        to: '/insights?audience=ai_engineering&status=kept&date=2026-07-14&insight=8f09b80e043048917dc720bac4e2820b9d152d757c78c6c2e182147049a61e4b',
      },
    ],
  },
]

export type ReviewRubricRow = {
  weight: string
  name: string
  text: string
  to: string
  linkLabel: string
}

type ReviewRubricPaths = {
  insightsPath: string
  feedPath: string
  artifactsPath: string
}

export function createReviewRubric({
  insightsPath,
  feedPath,
  artifactsPath,
}: ReviewRubricPaths): ReviewRubricRow[] {
  return [
    {
      weight: '20%',
      name: 'Registry of labs and people',
      text: 'A screened cohort of frontier labs and the researchers inside them, kept current and extended through the follow graph.',
      to: '/network/registry',
      linkLabel: 'Registry',
    },
    {
      weight: '20%',
      name: 'Signal vs noise',
      text: 'The funnel above is the answer: five stages, each removing what does not matter, with the suppressions as visible as the picks.',
      to: feedPath,
      linkLabel: 'A filtered day',
    },
    {
      weight: '20%',
      name: 'Scoring rigor',
      text: 'Attention ranking and audience judgments are separate steps, each with its inputs and reasoning inspectable per Event.',
      to: '/how#why-rank',
      linkLabel: 'Methods',
    },
    {
      weight: '15%',
      name: 'Actionable delivery',
      text: 'One published brief per audience per completed day, with each Insight traced to the companies or engineering surfaces it reaches and the memos the agent opened to get there.',
      to: insightsPath,
      linkLabel: 'Insights',
    },
    {
      weight: '10%',
      name: 'Ingestion pipeline',
      text: 'Completed observed X days are preserved before interpretation. Linked primary documents are catalogued, and successful normalized text snapshots are frozen with retrieval gaps visible.',
      to: artifactsPath,
      linkLabel: 'Artifacts',
    },
    {
      weight: '10%',
      name: 'Extraction',
      text: 'Posts, replies, and threads are resolved into exact Events with structured claims and their evidence attached.',
      to: feedPath,
      linkLabel: 'Events',
    },
    {
      weight: '5%',
      name: 'Web interface',
      text: 'You are in it. The live product reads the published SQLite models produced by the same pipeline.',
      to: '/how#technical-appendix',
      linkLabel: 'Technical appendix',
    },
  ]
}
