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
    title: 'Publish',
    text: 'An editorial agent reviews everything that survived and must surface or explicitly suppress each candidate. What remains becomes two audience-specific briefs, and every claim in them cites its source.',
  },
]

export const SHOWCASE_INSIGHTS = [
  {
    title: 'Anthropic gives TeraWulf a long lease; execution decides its value',
    meta: '6 July · Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-06&insight=3f8ecb8de3fb7bf34d3756474ba502a43a724593e37862d72163222f3fc48065',
  },
  {
    title: 'ChatGPT Work puts the agent interface above Microsoft and Google',
    meta: '9 July · Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-09&insight=18f69c9ac6e3d5e8a0c2c737973284580978dd81c3121c755da07ff88727a9f4',
  },
  {
    title: "Claude demand strengthens Amazon's capacity exposure",
    meta: '18 July · Investment',
    to: '/insights?audience=investment&status=kept&date=2026-07-18&insight=9dee6e36371b150c60e9821006f2ece26cc60c7891cb59bd933e6a76f9d7a793',
  },
  {
    title: 'FrontierFinance gives Aion a realistic evaluation target',
    meta: '9 July · AI Engineering',
    to: '/insights?audience=ai_engineering&status=kept&date=2026-07-09&insight=70a81026bd8bd1c43afb31e11451d5ab5cc66064b529274719f9ab1479923243',
  },
  {
    title: 'Retention controls do not prove what a coding agent transmits',
    meta: '13 July · AI Engineering',
    to: '/insights?audience=ai_engineering&status=kept&date=2026-07-13&insight=b2d9973fc22c09df7c132c5f79309a612c7abed40a633a661ce4199bdeff926e',
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
      to: '/system/architecture#ranking-methods',
      linkLabel: 'Methods',
    },
    {
      weight: '15%',
      name: 'Actionable delivery',
      text: 'One brief per audience for each completed editorial day, investment and AI engineering, and every claim in them cites its source.',
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
      to: '/system/status',
      linkLabel: 'Checkpoint',
    },
  ]
}
