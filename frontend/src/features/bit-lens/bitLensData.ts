export type EvidenceGrade = 'BIT thesis' | 'BIT commentary' | 'Analyst inference'

export interface HoldingLens {
  rank: number
  name: string
  ticker: string
  weight: number
  theme: 'AI infrastructure' | 'AI platform' | 'Fintech' | 'HealthTech'
  grade: EvidenceGrade
  thesis: string
  edge: string
  signals: string[]
  risk: string
  sourceLabel: string
  sourceUrl: string
}

export const sources = {
  juneFactsheet:
    'https://fondswelt.hansainvest.com/uploads/documents/fs_retail/HI_DE000A2N8127_retail_2026_06_30.pdf',
  mayFactsheet:
    'https://fondswelt.hansainvest.com/uploads/documents/fs_retail/HI_DE000A2N8127_retail_2026_05_29.pdf',
  aprilFactsheet:
    'https://fondswelt.hansainvest.com/uploads/documents/fs_retail/HI_DE000A2N8127_retail_2026_04_30.pdf',
  annualReport:
    'https://fondswelt.hansainvest.com/uploads/documents/jahresbericht/JB_1806_BIT_Global_Technology_Leaders_2025-12-31.pdf',
  semiannualReport:
    'https://fondswelt.hansainvest.com/uploads/documents/halbjahresbericht/HJB_1806_BIT_Global_Technology_Leaders_2025-06-30.pdf',
  downloads: 'https://fondswelt.hansainvest.com/de/fonds/details/780/downloads',
  prospectus:
    'https://fondswelt.hansainvest.com/uploads/documents/verkaufsprospekt/VKP_BIT_Global_Technology_Leaders_15_06_2026.pdf',
  kid:
    'https://fondswelt.hansainvest.com/uploads/documents/priips/PRIIPS_DE000A2N8127_1072995_DE_DE_2026-04-16_69bbe9ea22c51.pdf',
  sustainability:
    'https://fondswelt.hansainvest.com/uploads/documents/nachhaltigkeitsoffenlegungen/BIT_Global_Technology_Leaders_16_03_2026.pdf',
  futureNotice:
    'https://fondswelt.hansainvest.com/uploads/documents/bekanntmachung/DauDa_BIT_Global_Technology_Leaders_03_08_2026.pdf',
  fund: 'https://bitcap.com/en/fonds/bit-global-technology-leaders',
  approach: 'https://bitcap.com/en/investmentansatz',
  faq: 'https://bitcap.com/en/haeufig-gestellte-fragen-zum-investieren',
  homepage: 'https://bitcap.com/en',
  q1Report: 'https://bitcap.com/en/news/bit-capital-quartalsbericht-equity-q1-2026',
  omrInterview:
    'https://bitcap.com/en/news/omr-podcast-mit-philipp-westermeyer-1000-prozent-rendite-borsen-update-vom-bit-capital-grunder-von-ki-hype-bis-software-aktien--und-bitcoin-krise',
  team: 'https://bitcap.com/en/team',
  rename:
    'https://bitcap.com/en/news/bit-capital-gibt-umbenennung-der-bit-global-internet-leaders-fonds-bekannt',
  duolingo:
    'https://bitcap.com/en/news/fondsmanager-jan-beckers-unsere-daten-bei-duolingo-haben-gezeigt-dass-wir-verkaufen-sollten-podcast',
  stockPicking2025:
    'https://bitcap.com/ki-krypto-gezieltes-stockpicking-so-will-jan-beckers-2025-den-markt-schlagen/',
  contrarian:
    'https://bitcap.com/en/news/fondsmanager-jan-beckers-uber-investments-gegen-den-trend-kaufen-wenn-keiner-die-aktie-haben-will-podcast',
  fazProfile:
    'https://bitcap.com/news/faz-wie-jan-beckers-und-bit-capital-nicht-nur-den-nasdaq-schlagen',
  selection2026:
    'https://bitcap.com/news/fondsmanager-beckers-2026-wird-das-jahr-der-auslese-podcast',
  aiEngineer: 'https://bitcap.jobs.personio.com/job/2685548?language=en',
  semiconductorAnalyst: 'https://bitcap.jobs.personio.com/job/2701020?language=de',
  hardwareAnalyst: 'https://bitcap.jobs.personio.com/job/2591396?language=en',
  seniorAnalyst: 'https://bitcap.jobs.personio.com/job/2591464',
  directorEngineering: 'https://bitcap.jobs.personio.com/job/2649902',
  dataPlatforms: 'https://bitcap.jobs.personio.com/job/1833794?language=en',
  technicalChiefOfStaff: 'https://bitcap.jobs.personio.com/job/2337969',
  satyaInterview: 'https://bitcap.com/en/careers-en-interview-satya-mishra/',
  oldenkottInterview:
    'https://www.buzzsprout.com/1159130/episodes/16731481-79-bit-global-leaders-renditekick-furs-depot-mit-marcel-oldenkott',
  iren:
    'https://iren.com/resources/blog/iren-signs97-billion-agreement-with-microsoft-to-deploy-ai-cloud-infrastructure',
}

export const holdings: HoldingLens[] = [
  {
    rank: 1,
    name: 'Amazon',
    ticker: 'AMZN',
    weight: 10.4,
    theme: 'AI platform',
    grade: 'BIT commentary',
    thesis:
      'AWS acceleration and the capital intensity of agentic workloads can widen Amazon’s AI platform advantage.',
    edge:
      'Read Trainium, Bedrock, backlog and infrastructure spend together rather than treating capex as a standalone negative.',
    signals: ['AWS growth and backlog', 'Trainium / Bedrock adoption', 'Capex-to-revenue conversion'],
    risk: 'AI infrastructure spend grows faster than monetization or returns.',
    sourceLabel: 'April factsheet',
    sourceUrl: sources.aprilFactsheet,
  },
  {
    rank: 2,
    name: 'Micron',
    ticker: 'MU',
    weight: 8.6,
    theme: 'AI infrastructure',
    grade: 'BIT thesis',
    thesis:
      'AI servers require more high-bandwidth memory while HBM consumes conventional DRAM capacity, tightening the whole memory complex.',
    edge:
      'BIT publicly frames memory as a multi-year physical bottleneck and follows supply, yields and pricing before the earnings print.',
    signals: ['DRAM spot prices', 'HBM yields and qualification', 'Supply additions and lead times'],
    risk: 'Yield improvement, oversupply or slower AI capex breaks the scarcity thesis.',
    sourceLabel: 'BIT fund thesis',
    sourceUrl: sources.fund,
  },
  {
    rank: 3,
    name: 'IREN',
    ticker: 'IREN',
    weight: 8.5,
    theme: 'AI infrastructure',
    grade: 'BIT thesis',
    thesis:
      'Secured power, grid interconnection and data-center capacity become scarce real assets as AI compute demand rises.',
    edge:
      'Value contracted and energizable megawatts as an AI infrastructure option, not only as legacy mining capacity.',
    signals: ['Energized MW', 'GPU deployment and utilization', 'Contracted AI-cloud revenue'],
    risk: 'Financing, construction or customer concentration prevents capacity from converting into durable cash flow.',
    sourceLabel: 'BIT fund thesis',
    sourceUrl: sources.fund,
  },
  {
    rank: 4,
    name: 'SanDisk',
    ticker: 'SNDK',
    weight: 6.0,
    theme: 'AI infrastructure',
    grade: 'Analyst inference',
    thesis:
      'Rising model context, retrieval and data movement increase demand for enterprise flash and data-center storage.',
    edge:
      'Treat NAND pricing, enterprise mix and gross margin as the observable bridge from workload growth to earnings.',
    signals: ['NAND ASPs', 'Enterprise SSD mix', 'Gross-margin recovery'],
    risk: 'Capacity expansion recreates commodity oversupply before AI storage demand matures.',
    sourceLabel: 'June holding only',
    sourceUrl: sources.juneFactsheet,
  },
  {
    rank: 5,
    name: 'Robinhood',
    ticker: 'HOOD',
    weight: 5.0,
    theme: 'Fintech',
    grade: 'BIT thesis',
    thesis:
      'A mobile broker can compound into a full-stack financial platform as customers consolidate assets and adopt more products.',
    edge:
      'Follow account depth and product adoption, not only transaction volumes or crypto sentiment.',
    signals: ['Assets under custody', 'Net deposits', 'Gold subscribers and product adoption'],
    risk: 'Regulation, weak retention or transaction dependence caps the wealth-platform transition.',
    sourceLabel: 'BIT fund thesis',
    sourceUrl: sources.fund,
  },
  {
    rank: 6,
    name: 'Marvell',
    ticker: 'MRVL',
    weight: 4.8,
    theme: 'AI infrastructure',
    grade: 'BIT commentary',
    thesis:
      'Custom accelerators still need high-speed interconnect and networking, making data movement the next AI bottleneck.',
    edge:
      'Track design wins and revenue ramps across custom silicon and electro-optical connectivity.',
    signals: ['Custom-silicon design wins', 'Data-center revenue', 'Interconnect product ramps'],
    risk: 'Customer insourcing or concentration overwhelms the networking growth cycle.',
    sourceLabel: 'June factsheet',
    sourceUrl: sources.juneFactsheet,
  },
  {
    rank: 7,
    name: 'TSMC',
    ticker: 'TSM',
    weight: 4.6,
    theme: 'AI infrastructure',
    grade: 'Analyst inference',
    thesis:
      'Advanced nodes and packaging remain critical capacity constraints for AI accelerators and high-performance compute.',
    edge:
      'Translate frontier-model compute demand into node utilization, advanced packaging and pricing power.',
    signals: ['N2 ramp', 'CoWoS capacity', 'HPC revenue and capex'],
    risk: 'Geopolitics, customer concentration or overbuild overwhelms technical leadership.',
    sourceLabel: 'June holding only',
    sourceUrl: sources.juneFactsheet,
  },
  {
    rank: 8,
    name: 'Infineon',
    ticker: 'IFX',
    weight: 4.4,
    theme: 'AI infrastructure',
    grade: 'Analyst inference',
    thesis:
      'AI data centers require more efficient power conversion, making power semiconductors part of the compute stack.',
    edge:
      'Separate an emerging AI-power ramp from the company’s automotive and industrial cycle.',
    signals: ['AI power revenue', 'Design wins', 'Data-center mix and margins'],
    risk: 'Automotive and industrial weakness obscures or offsets the AI contribution.',
    sourceLabel: 'June holding only',
    sourceUrl: sources.juneFactsheet,
  },
  {
    rank: 9,
    name: 'Hinge Health',
    ticker: 'HNGE',
    weight: 4.2,
    theme: 'HealthTech',
    grade: 'Analyst inference',
    thesis:
      'Digital musculoskeletal care can lower employer health costs while expanding access and engagement.',
    edge:
      'Tie adoption to measured outcomes, renewals and employer return on investment.',
    signals: ['Clients and covered lives', 'Retention and engagement', 'Documented customer ROI'],
    risk: 'Weak outcomes, renewals, privacy controls or payer economics limit durable growth.',
    sourceLabel: 'June holding only',
    sourceUrl: sources.juneFactsheet,
  },
  {
    rank: 10,
    name: 'Oscar Health',
    ticker: 'OSCR',
    weight: 4.2,
    theme: 'HealthTech',
    grade: 'BIT commentary',
    thesis:
      'Premium and membership growth can create operating leverage as the insurer’s technology platform matures.',
    edge:
      'Read member growth together with the medical-cost ratio and operating profitability.',
    signals: ['Membership', 'Premium growth', 'Medical-loss ratio'],
    risk: 'Medical inflation or regulatory change erodes the profitability inflection.',
    sourceLabel: 'June factsheet',
    sourceUrl: sources.juneFactsheet,
  },
]

export const snapshots = [
  { date: '30 Jan', positions: 39, cash: 3.2, top: 'IREN 9.9%', note: 'Broad starting book' },
  { date: '27 Feb', positions: 29, cash: 15.1, top: 'Micron 8.5%', note: 'Defensive reset' },
  { date: '30 Apr', positions: 35, cash: 0.9, top: 'Amazon 9.8%', note: 'Re-risked' },
  { date: '29 May', positions: 36, cash: 2.5, top: 'IREN 10.3%', note: 'Infrastructure focus' },
  { date: '30 Jun', positions: 28, cash: 5.4, top: 'Amazon 10.4%', note: 'Re-concentrated' },
]

export const auditedHoldings = [
  ['IREN', 8.93],
  ['AUTO1', 8.4],
  ['Hinge Health', 6.74],
  ['TSMC', 5.66],
  ['Micron', 5.07],
  ['Reddit', 4.93],
  ['Alphabet', 4.48],
  ['Datadog', 4.34],
  ['Lemonade', 3.95],
  ['Robinhood', 3.77],
  ['Oscar Health', 3.7],
  ['Meta', 3.49],
  ['Rubrik', 3.37],
  ['Kaspi', 3.32],
  ['Nvidia', 3.26],
  ['Microsoft', 2.89],
  ['HUT 8', 2.22],
  ['Duolingo', 2.02],
  ['Amazon', 1.78],
  ['Netskope', 1.76],
  ['Luckin Coffee', 1.72],
  ['Palo Alto Networks', 1.66],
  ['InPost', 1.42],
  ['Grindr', 1.07],
  ['Coherent', 1.07],
  ['AMD', 1.04],
  ['Intel', 1.02],
  ['Axon', 0.97],
  ['Broadcom', 0.82],
  ['Pure Storage', 0.78],
  ['Lumentum', 0.57],
  ['Xometry', 0.55],
  ['Omada Health', 0.55],
  ['GCL-Poly', 0.11],
] as const
