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

export const SHOWCASE_INSIGHTS = [
  {
    title: 'Kimi K3 tests AI hardware demand from both directions',
    meta: '27 July \u00b7 Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-27&insight=830eb0ef3a12ac2d9f72e3853d0ebf5e73421affbb5c66798dc566b14962e174',
  },
  {
    title: 'Moonshot\u2019s open-weight Kimi K3 imposes preserved-history harness constraints',
    meta: '27 July \u00b7 AI Engineering',
    to: '/insights?audience=ai_engineering&status=kept&date=2026-07-27&insight=830eb0ef3a12ac2d9f72e3853d0ebf5e73421affbb5c66798dc566b14962e174',
  },
  {
    title: 'Autonomous agent intrusion strengthens demand for machine-speed cyber defense',
    meta: '28 July \u00b7 Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-28&insight=a6252033a0fb5a6755eff4d8bc029291109eb638d0d600103f9e03b20c1579e6',
  },
  {
    title: 'MCP stateless requests remove session affinity from remote tool serving',
    meta: '28 July \u00b7 AI Engineering',
    to: '/insights?audience=ai_engineering&status=kept&date=2026-07-28&insight=c5302a6e6844cbb7ec42751e2cfce417c96e26c5e88a15435d06eabfe32fcb2d',
  },
  {
    title: 'Gemini controls move Google Cloud agents closer to recurring deployment',
    meta: '28 July \u00b7 Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-28&insight=069268a39cd024d1e3214490e94fbb81b44832c7d916761137b5da53e3e03887',
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
