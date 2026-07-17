import type { ReactNode } from 'react'
import { auditedHoldings, holdings, snapshots, sources } from './bitLensData'

function SourceLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children} <span aria-hidden="true">↗</span>
    </a>
  )
}

const holdingNotes: Record<string, ReactNode> = {
  Amazon: (
    <>
      The size change is itself important evidence: Amazon was 1.78% in the complete
      31 December 2025 portfolio and 10.4% in the June 2026 top-ten disclosure. Public
      documents do not reveal the cost basis or the exact internal reason for every
      increment, so the defensible claim is that exposure increased sharply—not that we
      know BIT’s private target or expected return.
    </>
  ),
  IREN: (
    <>
      One public-source conflict needs to remain visible. BIT’s May commentary refers to
      a $3.4 billion Nvidia contract, while IREN’s own announcement describes a $9.7
      billion Microsoft agreement with Nvidia-linked equipment and financing. The company
      source should govern the transaction facts; the mismatch is an example of why FLI
      must preserve exact citations rather than repeat manager commentary uncritically.
    </>
  ),
  Micron: (
    <>
      BIT’s public pages also contain an unresolved date inconsistency: one Micron example
      lists a July 2023 entry date while another sentence says accumulation began in
      October 2021. That could reflect a re-entry, methodology difference, or content
      error. It should not be silently reconciled.
    </>
  ),
}

const sourceLedger = [
  {
    date: '30 Jun 2026',
    label: 'Official June factsheet',
    use: 'Latest public top ten, weights, allocations, position count and manager commentary.',
    href: sources.juneFactsheet,
  },
  {
    date: '31 Dec 2025',
    label: 'Audited annual report',
    use: 'Latest complete public portfolio, fund accounts and audited reporting baseline.',
    href: sources.annualReport,
  },
  {
    date: '30 Jun 2025',
    label: 'Semiannual report',
    use: 'Complete historical midyear holdings for longitudinal comparison.',
    href: sources.semiannualReport,
  },
  {
    date: '15 Jun 2026',
    label: 'Prospectus',
    use: 'Legal mandate, permitted instruments, borrowing and derivative boundaries.',
    href: sources.prospectus,
  },
  {
    date: '16 Apr 2026',
    label: 'PRIIPs KID',
    use: 'Risk class, recommended holding period and current cost disclosures.',
    href: sources.kid,
  },
  {
    date: 'Current',
    label: 'Flagship fund page',
    use: 'Public strategy language and selected Thesis–Edge–Signal–Key Move examples.',
    href: sources.fund,
  },
  {
    date: 'Current',
    label: 'Investment approach',
    use: 'Research loop, alternative data, position construction and Devil’s Advocate review.',
    href: sources.approach,
  },
  {
    date: 'Current',
    label: 'BIT FAQ',
    use: 'Current public description of people, models, agents and investment decisions.',
    href: sources.faq,
  },
  {
    date: '5 Mar 2025',
    label: 'Marcel Oldenkott interview',
    use: 'Thesis-first alternative data, information-edge ambition, turnover and challenge process.',
    href: sources.oldenkottInterview,
  },
  {
    date: 'Current role',
    label: 'Semiconductor analyst',
    use: 'First-principles company decomposition and Volume × Price × Mix × Margin method.',
    href: sources.semiconductorAnalyst,
  },
  {
    date: 'Current role',
    label: 'AI Engineer / Aion',
    use: 'Production agent platform, retrieval, extraction, signals, evaluations and human review.',
    href: sources.aiEngineer,
  },
  {
    date: 'Current roles',
    label: 'Engineering and data platform roles',
    use: 'Alternative-data ingestion, research tools, RAG, quality, observability and security.',
    href: sources.dataPlatforms,
  },
]

export default function BitLensPage() {
  return (
    <div className="page bit-lens-page">
      <header className="bit-lens-head">
        <h1 className="page-title">BIT Lens</h1>
        <p className="page-sub">
          A detailed public-research briefing on BIT Global Technology Leaders,
          BIT’s investment process, and the standard Frontier Lab Intelligence
          should meet when writing for the fund.
        </p>
      </header>

      <article className="lens-reading">
        <section className="lens-reading-intro" aria-labelledby="lens-purpose-title">
          <h2 id="lens-purpose-title">What this page is for</h2>
          <p>
            This page condenses the public research on BIT Capital into one place. Its
            purpose is to make the rest of Frontier Lab Intelligence easier to judge. When
            the product produces an investment insight, we should be able to compare that
            insight against the way BIT appears to form a company thesis, search for an
            information edge, translate evidence into operating drivers, update forecasts,
            challenge conviction, and make a human portfolio decision.
          </p>
          <p>
            The central conclusion is that BIT does not appear to want a generic AI-news
            digest. Its public material describes a thesis-first, company-specific process.
            The useful output is therefore not merely “this development matters for AI.” It
            is: what changed; which dated holding, portfolio bottleneck, or candidate it may
            affect; which operating variable and financial-model line could move; why the
            implication may differ from consensus; what evidence would confirm or falsify
            it; and what an analyst should investigate next.
          </p>
          <p>
            This is necessarily an outside-in reconstruction. Mandatory fund documents can
            establish dated holdings and legal facts. BIT’s own pages, interviews, podcasts,
            and job descriptions can establish its public language and working methods.
            They cannot establish private forecasts, current cost bases, valuation targets,
            live trades, or the actual output of internal models. Those boundaries are kept
            explicit throughout.
          </p>
        </section>

        <nav className="lens-contents" aria-label="BIT Lens contents">
          <h2>Contents</h2>
          <ol>
            <li><a href="#flagship">The flagship fund and its mandate</a></li>
            <li><a href="#portfolio">What the dated portfolio disclosures show</a></li>
            <li><a href="#holdings">How to read the current top ten</a></li>
            <li><a href="#research-process">How BIT appears to build and test theses</a></li>
            <li><a href="#aion">Aion, data infrastructure, and the human boundary</a></li>
            <li><a href="#fli-standard">What this means for Frontier Lab Intelligence</a></li>
            <li><a href="#cautions">Contradictions, uncertainties, and missing information</a></li>
            <li><a href="#sources">Source ledger</a></li>
          </ol>
        </nav>

        <section className="lens-reading-section" id="flagship" aria-labelledby="flagship-title">
          <h2 id="flagship-title">1. The flagship fund and its mandate</h2>
          <p>
            BIT Global Technology Leaders is BIT Capital’s flagship global technology-equity
            strategy. It began as BIT Global Internet Leaders and was renamed in 2024 because
            the investable universe had expanded beyond internet businesses into the broader
            technology stack. BIT describes it as benchmark-independent and concentrated,
            with a preference for emerging category leaders whose growth and competitive
            position may not yet be fully recognized. The public strategy repeatedly points
            toward companies in roughly the $2–100 billion range, where deep company knowledge
            and alternative data may create more edge than in universally covered mega-caps.
            The portfolio can still own mega-caps when the thesis and valuation warrant it, as
            the current Amazon weight demonstrates. Sources: <SourceLink href={sources.fund}>flagship fund page</SourceLink> and <SourceLink href={sources.rename}>2024 renaming explanation</SourceLink>.
          </p>
          <p>
            The legal mandate is broader than the marketing strategy. The prospectus permits
            a global equity fund with at least 51% in equities, certificates, derivatives for
            investment or hedging, and short-term borrowing within stated limits. The
            operating reality shown in manager material is narrower: a relatively small set
            of high-conviction growth companies, selected bottom-up and weighted with regard
            to valuation, operational evidence, liquidity, factor exposure, and portfolio
            risk. The fund is not a passive “AI basket,” and the public holdings change too
            quickly to treat any old list as current.
          </p>

          <dl className="lens-facts">
            <div><dt>Latest public snapshot</dt><dd>30 June 2026</dd></div>
            <div><dt>Fund assets</dt><dd>€1.594 billion</dd></div>
            <div><dt>Positions</dt><dd>28</dd></div>
            <div><dt>Top-ten concentration</dt><dd>60.7%</dd></div>
            <div><dt>Equity / cash and derivatives</dt><dd>94.6% / 5.4%</dd></div>
            <div><dt>Currency exposure</dt><dd>USD 88.9% · EUR 11.1%</dd></div>
            <div><dt>Sector exposure</dt><dd>IT 56.7% · consumer discretionary 18.5% · financials 12.5% · healthcare 6.8% · materials 5.5%</dd></div>
            <div><dt>Risk class</dt><dd>6 of 7</dd></div>
            <div><dt>Recommended holding period</dt><dd>At least five years</dd></div>
            <div><dt>Current disclosed costs</dt><dd>1.9% ongoing operating costs plus an estimated 0.4% transaction costs</dd></div>
            <div><dt>Subscription charge</dt><dd>3% current · 5% prospectus maximum</dd></div>
            <div><dt>Performance fee</dt><dd>No current performance fee disclosed for R-I</dd></div>
            <div><dt>Sustainability classification</dt><dd>Article 8</dd></div>
            <div><dt>Dealing</dt><dd>Daily, subject to the prospectus’s redemption restriction and suspension provisions under stress</dd></div>
          </dl>

          <p>
            These terms describe the R-I share class and should not be generalized to every
            BIT product or share class. The institutional BIT Global Technology Opportunities
            vehicle has broader instrument flexibility, including selective shorts; that must
            not be projected onto the UCITS flagship. A shareholder notice published in June
            also announces changes effective 3 August 2026, including formalized ESG limits,
            the possibility of an ETF share class and stock-exchange tradability, and related
            cost provisions. On this page those remain future-effective, not current. Source:
            {' '}<SourceLink href={sources.futureNotice}>18 June 2026 shareholder notice</SourceLink>.
          </p>
        </section>

        <section className="lens-reading-section" id="portfolio" aria-labelledby="portfolio-title">
          <h2 id="portfolio-title">2. What the dated portfolio disclosures show</h2>
          <p>
            The most important portfolio lesson is temporal: “BIT owns X” is incomplete
            without a date. The latest complete public portfolio is the audited annual report
            from 31 December 2025. The latest public portfolio state is the 30 June 2026
            factsheet, but that document discloses only the top ten and aggregate allocations.
            No authoritative public source found in this research exposes the other 18 current
            positions. A defensible product must therefore distinguish current top-ten
            exposure, historical holding, inferred thematic exposure, watchlist candidate,
            and unknown current holding.
          </p>
          <p>
            The document history is stronger than the current-position coverage. HANSAINVEST
            exposes complete year-end reports for every fund year from 2019 through 2025 and
            complete midyear reports from 2019 through 2025. Those reports can support a
            longitudinal holdings history. Monthly factsheets are less durable: some older
            official PDFs disappear from their origin URLs even while search indexes retain
            them. A production system should archive the original document and its retrieval
            date rather than assume a manager URL will remain available indefinitely.
          </p>

          <h3>Portfolio movement during 2026</h3>
          <p>
            The monthly factsheets show active changes in both breadth and risk. Position count
            moved from 39 in January to 29 in February, back to 35–36 in April and May, then
            down to 28 in June. Cash and derivatives moved from 3.2% to 15.1%, then close to
            zero, then 2.5% and 5.4%. February commentary indicates that the team exited
            software exposure as progress around Claude and application-layer AI increased its
            disruption concern. The portfolio later reconcentrated around memory, compute,
            energy, networking, storage, and data-center bottlenecks, while retaining selected
            fintech and HealthTech exposure.
          </p>

          <div className="lens-table-wrap">
            <table className="lens-data-table">
              <thead>
                <tr><th scope="col">Snapshot</th><th scope="col">Positions</th><th scope="col">Cash + derivatives</th><th scope="col">Largest disclosed holding</th><th scope="col">Reading</th></tr>
              </thead>
              <tbody>
                {snapshots.map((snapshot) => (
                  <tr key={snapshot.date}>
                    <td className="mono">{snapshot.date} 2026</td>
                    <td className="num">{snapshot.positions}</td>
                    <td className="num">{snapshot.cash.toFixed(1)}%</td>
                    <td>{snapshot.top}</td>
                    <td>{snapshot.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="lens-source-note">
            March factsheet not found. April cash is approximated from 99.1% reported equity.
            January and February figures were recovered from indexed official factsheets whose
            origin URLs no longer resolve. April, May, and June remain directly public.
          </p>

          <h3>The current disclosed top ten</h3>
          <p>
            At 30 June 2026 the top ten accounted for 60.7% of the fund. Six of those names—
            Micron, IREN, SanDisk, Marvell, TSMC, and Infineon—represent 36.9 percentage points
            of disclosed AI-infrastructure exposure. Amazon adds a 10.4% AI-platform exposure;
            Robinhood contributes 5.0% fintech; Hinge Health and Oscar Health contribute 8.4%
            HealthTech. These percentages describe only the disclosed top ten, not the whole
            portfolio’s thematic exposure.
          </p>

          <h3>The current public worldview behind the concentration</h3>
          <p>
            BIT’s April through June commentary and Q1 material form a coherent high-level
            picture. Agentic applications increase demand for compute, memory, networking,
            storage, and energy because they use more inference, more context, and more data
            movement. At the same time, AI coding and capable general models can weaken the
            economics of some application-software companies. The fund therefore appears to
            favor scarce physical or technical bottlenecks—memory capacity, advanced chips and
            packaging, secured power, data-center capacity, high-speed networking, and storage—
            while being more selective about software. Fintech and HealthTech remain separate
            company-specific growth theses rather than part of the infrastructure basket.
            Factor rotations can still move these stocks independently of company fundamentals,
            which is why this thematic reading cannot replace valuation and portfolio-risk work.
            Sources: <SourceLink href={sources.q1Report}>Q1 2026 equity report</SourceLink> and <SourceLink href={sources.omrInterview}>March 2026 OMR discussion</SourceLink>.
          </p>

          <div className="lens-table-wrap">
            <table className="lens-data-table">
              <thead><tr><th scope="col">Rank</th><th scope="col">Holding</th><th scope="col">Weight</th><th scope="col">Public thesis evidence</th><th scope="col">First KPI to watch</th></tr></thead>
              <tbody>
                {holdings.map((holding) => (
                  <tr key={holding.ticker}>
                    <td className="num">#{holding.rank}</td>
                    <td><strong>{holding.name}</strong><span className="lens-secondary mono">{holding.ticker} · {holding.theme}</span></td>
                    <td className="num">{holding.weight.toFixed(1)}%</td>
                    <td>{holding.grade}</td>
                    <td>{holding.signals[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3>What changed since the latest complete portfolio</h3>
          <p>
            Only five of the December top ten remained in the June top ten: IREN, Hinge
            Health, TSMC, Micron, and Robinhood. Amazon moved from 1.78% in the complete
            year-end portfolio to 10.4% in June. SanDisk, Marvell, and Infineon were absent
            from the complete December roster but entered the June top ten. Reddit, Alphabet,
            Datadog, Lemonade, and AUTO1 left the disclosed top ten. This does not prove that
            every departing name was fully sold; it proves that the visible concentration
            changed materially.
          </p>

          <h3>Latest complete audited holdings: 31 December 2025</h3>
          <p>
            The annual report provides the latest complete public holdings baseline. It is
            included here so a later insight can distinguish “current disclosed top ten” from
            “recent historical holding” instead of treating absence from June’s top ten as
            proof of a zero position.
          </p>
          <div className="lens-table-wrap">
            <table className="lens-data-table lens-audited-table">
              <thead><tr><th scope="col">Holding</th><th scope="col">Portfolio weight</th></tr></thead>
              <tbody>
                {auditedHoldings.map(([name, weight]) => (
                  <tr key={name}><td>{name}</td><td className="num">{weight.toFixed(2)}%</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="lens-reading-section" id="holdings" aria-labelledby="holdings-title">
          <h2 id="holdings-title">3. How to read the current top ten</h2>
          <p>
            Public evidence strength differs by company. Micron, IREN, and Robinhood have
            full company examples on BIT’s public pages that state a thesis, information edge,
            signal, and key move. Amazon, Marvell, and Oscar have dated manager commentary
            that supports only part of that chain. SanDisk, TSMC, Infineon, and Hinge Health
            are disclosed holdings without a current public company-specific BIT thesis. For
            those four, the interpretations below are analyst inference and must never be
            written in BIT’s voice.
          </p>

          {holdings.map((holding) => (
            <section className="lens-holding-reading" key={holding.ticker} aria-labelledby={`holding-${holding.ticker}`}>
              <h3 id={`holding-${holding.ticker}`}>{holding.rank}. {holding.name} <span className="mono">{holding.ticker}</span></h3>
              <p className="lens-holding-meta">
                <strong>{holding.weight.toFixed(1)}% at 30 Jun 2026</strong> · {holding.theme} ·
                evidence level: <strong>{holding.grade}</strong> · <SourceLink href={holding.sourceUrl}>{holding.sourceLabel}</SourceLink>
              </p>
              <p><strong>Current research reading.</strong> {holding.thesis}</p>
              <p><strong>Where an information edge may exist.</strong> {holding.edge}</p>
              <p><strong>Observable signals.</strong> {holding.signals.join('; ')}.</p>
              <p><strong>Disconfirming case.</strong> {holding.risk}</p>
              {holdingNotes[holding.name] && <p><strong>Important qualification.</strong> {holdingNotes[holding.name]}</p>}
            </section>
          ))}
        </section>

        <section className="lens-reading-section" id="research-process" aria-labelledby="research-title">
          <h2 id="research-title">4. How BIT appears to build and test investment theses</h2>
          <p>
            Across BIT’s fund pages, interviews, case studies, job descriptions, and current
            investment-approach material, one recurring grammar stands out: <strong>Thesis →
            Edge → Signal → Key Move</strong>. That grammar is more useful for FLI than a generic
            sector taxonomy because it explains how evidence becomes a portfolio-relevant
            research object.
          </p>

          <ol className="lens-process-list">
            <li>
              <h3>Thesis: state the structural change the market may be underestimating</h3>
              <p>
                The process begins with a qualitative company view, not with a broad scrape of
                every available dataset. The analyst needs a view of how a market, product,
                capacity constraint, customer behavior, or competitive position is changing;
                why the change can persist; and which company can capture the economics.
              </p>
            </li>
            <li>
              <h3>Edge: explain why BIT could know earlier or more accurately</h3>
              <p>
                Public material combines fundamental company work, management and expert
                access, sector knowledge, internal models, alternative data, and technology
                infrastructure. Marcel Oldenkott describes an ambition for a large position to
                be among the ten best-informed investors in that stock. That ambition is most
                credible in under-covered mid-cap companies, not in names where every major
                investor has similar information.
              </p>
            </li>
            <li>
              <h3>Signal: define what would confirm or falsify the thesis</h3>
              <p>
                Signals can include app downloads, Google Trends, payments data, web-scraped
                traces, niche-vendor datasets, product usage, pricing, capacity, hiring,
                customer behavior, or conventional financial KPIs. The important point is
                selection: BIT first asks whether the company leaves an observable digital or
                operational trace, then curates or builds the dataset that can test the thesis.
                Alternative data is not presented as an indiscriminate stock screener.
              </p>
            </li>
            <li>
              <h3>Key Move: connect evidence and valuation to an investment action</h3>
              <p>
                Public examples suggest that evidence affects timing and weight, not just
                inclusion. A signal may support entry, re-entry, a larger or smaller position,
                a watchlist change, a risk review, or a full exit. Valuation remains part of
                the decision. A correct long-term thesis does not automatically justify owning
                a stock at every price or at the same size.
              </p>
            </li>
          </ol>

          <h3>From first principles to the P&amp;L</h3>
          <p>
            BIT’s semiconductor analyst role gives the clearest public statement of the
            practical research unit: decompose the company through <strong>Volume × Price ×
            Mix × Margin</strong>, distinguish signal from noise, and connect the observation
            to the income statement before consensus catches up. Other analyst roles reinforce
            the same expectations: KPI forecasts, financial models, valuation, management and
            expert work, alternative data, and an explicit search for disconfirming evidence.
            For FLI, this means a frontier-lab development is incomplete until it can be mapped
            to a plausible operating driver and forecast line.
          </p>

          <h3>Signals can change timing and weight</h3>
          <p>
            BIT’s Duolingo example is unusually concrete. App usage and other internal models
            initially anticipated a strong operating result. Later signals showed fading
            momentum, supporting a full exit before a drawdown; improved data then supported
            a re-entry. The important lesson is not that alternative data is always right. It
            is that BIT appears to use data as a continuously updated test of an existing
            company thesis and valuation, with portfolio weight allowed to respond. Source:
            {' '}<SourceLink href={sources.duolingo}>Duolingo case discussion</SourceLink>.
          </p>

          <h3>Contrarian investing still requires superior evidence</h3>
          <p>
            The public Carvana example is not “buy because the stock fell.” BIT argued that
            the market’s bankruptcy assumption conflicted with its work on unit economics,
            margin, and market share. Public interviews also indicate that such contrarian
            positions remain small unless the team believes it understands the company
            exceptionally well. This is a useful standard for FLI: a negative consensus is not
            an edge by itself; the product needs evidence that challenges the consensus model.
            Source: <SourceLink href={sources.contrarian}>contrarian-investing discussion</SourceLink>.
          </p>

          <h3>Large positions receive an explicit adversarial review</h3>
          <p>
            BIT describes a Devil’s Advocate process for positions above 5% of NAV. A senior
            challenger spends several days constructing a pre-mortem, modeling the downside,
            and assembling the strongest failure case. The purpose is not to add another
            approval click; it is to force conviction to survive independent challenge. The
            resulting portfolio response can be to retain, resize, hedge, or exit. For FLI,
            high-conviction exposures should receive better falsifiers and stronger contrary
            evidence—not more confirming headlines.
          </p>

          <h3>Bottom-up selection coexists with top-down exposure control</h3>
          <p>
            BIT sometimes describes security selection as strictly bottom-up, while post-2022
            material also discusses macro monitoring, factor-risk monitoring, conditional loss
            models, liquidity awareness, selective hedging, and stronger portfolio controls.
            The most coherent interpretation is that bottom-up work governs idea eligibility
            and the company thesis, while top-down risk tools can still change position sizes
            and aggregate exposure. Source: <SourceLink href={sources.fazProfile}>2024 process profile</SourceLink> and <SourceLink href={sources.selection2026}>2026 selection discussion</SourceLink>.
          </p>
        </section>

        <section className="lens-reading-section" id="aion" aria-labelledby="aion-title">
          <h2 id="aion-title">5. Aion, data infrastructure, and the human boundary</h2>
          <p>
            BIT’s current AI Engineer role calls its production AI platform <strong>Aion</strong>.
            The role describes agents with first-class access to internal data, financial
            models, tools, and external sources. Intended outputs include scores, alerts,
            signals, and insights. The public FAQ adds that agents can analyze earnings and new
            company information and help create or update financial models. This places AI
            inside the investment research workflow rather than beside it as a generic chatbot.
          </p>
          <p>
            Public team material helps locate responsibility. Jan Beckers and Marcel Oldenkott
            lead the investment function. Oldenkott’s remit spans systematic strategies,
            macro, risk, and data engineering, making him a bridge between fundamental research
            and portfolio-level controls. Carlos Bielsa is presented as leading AI integration
            across product and strategy. That division supports the same interpretation found
            elsewhere: fundamental analysts, quantitative and risk work, and engineering are
            distinct capabilities joined by shared data and research tools rather than one
            monolithic model making decisions. Source: <SourceLink href={sources.team}>BIT team</SourceLink>.
          </p>
          <p>
            The engineering language is also revealing. Current roles emphasize retrieval,
            structured extraction, RAG and agent workflows, alternative-data ingestion,
            evaluations, uncertainty, hallucination monitoring, data quality, observability,
            security, and adoption through analyst feedback and usage. A Technical Chief of
            Staff role explicitly sits between analysts, quants, and engineering to specify
            problems and measure whether tools are actually used. Older team interviews describe
            separate fundamental, quantitative, and risk-team use cases, with reliable data
            inflow and data quality treated as foundational. Sources: <SourceLink href={sources.aiEngineer}>AI Engineer role</SourceLink>, <SourceLink href={sources.directorEngineering}>Director of Engineering role</SourceLink>, <SourceLink href={sources.dataPlatforms}>Data &amp; Platforms role</SourceLink>, and <SourceLink href={sources.technicalChiefOfStaff}>Technical Chief of Staff role</SourceLink>.
          </p>
          <p>
            This operating model predates the current AI-agent branding. A 2021 fund factsheet
            already combined entrepreneurial company understanding, fundamental analysis, and
            alternative data. The more recent Aion language appears to extend and automate an
            established research architecture rather than replace it with an LLM-first process.
            That historical continuity matters when comparing FLI with BIT: the technology is
            useful because it serves a durable investment method, not because “agents” are the
            thesis by themselves.
          </p>
          <p>
            The decision boundary remains human. Agents can retrieve, extract, compare,
            calculate, prioritize, and draft. The analyst or portfolio manager remains
            responsible for the company thesis, forecast assumptions, causal interpretation,
            valuation, position size, risk challenge, and final trade—or the choice to do
            nothing. This distinction matters for the case study: FLI should automate the
            production of a decision-ready research object, not claim to automate portfolio
            management.
          </p>
          <p>
            Public pages quote inconsistent system-scale figures: approximately 3.1 PB per day
            and more than one billion monthly tokens on one page; 80 TB per day, 2.4 PB per
            month, and more than 500 million tokens on another; and more than 200 TB per month
            elsewhere. These may refer to different dates, scopes, or pipelines, but BIT does
            not reconcile them. No single figure should be encoded as canonical. The meaningful
            conclusion is qualitative: BIT has built a large internal data and AI platform that
            is used by the investment team, but public evidence does not expose its exact
            current scale or effectiveness.
          </p>
        </section>

        <section className="lens-reading-section" id="fli-standard" aria-labelledby="fli-title">
          <h2 id="fli-title">6. What this means for Frontier Lab Intelligence</h2>
          <p>
            The Investment audience should not receive the same generic summary as the AI
            Engineering audience with a ticker appended. It should receive a structured
            translation from frontier evidence to a fund-specific research question. The same
            evidence core can remain shared, but the final judgment and output need to follow
            the investment workflow below.
          </p>

          <ol className="lens-standard-list">
            <li><strong>Development.</strong> State exactly what changed and cite the primary source.</li>
            <li><strong>Exposure.</strong> Identify a current top-ten holding, dated historical holding, known portfolio bottleneck, or plausible candidate. Label the relationship honestly.</li>
            <li><strong>Operating driver.</strong> Name the volume, price, mix, margin, user, capacity, utilization, or unit-economics variable that could move.</li>
            <li><strong>KPI and P&amp;L translation.</strong> Explain which forecast line may change, in which direction, and on what horizon.</li>
            <li><strong>Expectation gap.</strong> Explain why the implication may differ from current consensus, valuation, or the dominant narrative.</li>
            <li><strong>Opportunity and downside.</strong> Present both the upside mechanism and the strongest plausible disconfirming case.</li>
            <li><strong>Horizon.</strong> Distinguish an immediate earnings signal, a 6–18 month operating effect, and a multi-year structural change.</li>
            <li><strong>Next evidence.</strong> Name what the analyst should monitor to confirm or falsify the interpretation.</li>
            <li><strong>Human action.</strong> End with investigate, update the model, add to watchlist, challenge the thesis, monitor, or ignore—not an automatic buy or sell.</li>
          </ol>

          <h3>Worked example: frontier context growth → Micron</h3>
          <p>
            Suppose frontier-lab evidence shows that agentic systems are using longer context,
            retrieval, and memory-intensive inference. The generic version says “AI agents
            require more memory.” The BIT-specific version starts with the dated exposure:
            Micron was 8.6% of the flagship’s disclosed portfolio at 30 June 2026. It then maps
            the development to HBM volume, DRAM pricing, high-value product mix, and yield-driven
            gross margin. The potential expectation gap is whether HBM capacity displacement
            keeps conventional memory tighter for longer than consensus expects. The next
            evidence is DRAM spot pricing, HBM qualification and yields, lead times, and announced
            supply additions. The disconfirming cases are rapid yield improvement, new supply,
            or slower AI capex. The human action is to update the supply and margin model and
            rerun the downside scenario—not to trade automatically.
          </p>

          <h3>How to compare future FLI insights against this page</h3>
          <p>
            A useful comparison question is: does the insight move from source evidence to a
            company-specific driver and falsifiable research action, or does it stop at a broad
            claim about AI? If it stops early, this page explains what is missing. The product
            can still publish early-stage signals when evidence is thin, but it should label the
            missing links rather than fill them with confident prose. Repeated developments can
            be grouped before this translation, yet grouping quality and investment relevance
            remain separate judgments: two posts can describe the same event without proving
            that the event matters to the flagship.
          </p>
        </section>

        <section className="lens-reading-section" id="cautions" aria-labelledby="cautions-title">
          <h2 id="cautions-title">7. Contradictions, uncertainties, and missing information</h2>
          <p>
            The following limits are not footnotes; they determine which claims FLI can make
            defensibly.
          </p>
          <ul className="lens-caution-list">
            <li><strong>No complete current portfolio.</strong> June discloses 28 positions but names only the top ten. The remaining 18 are unknown publicly.</li>
            <li><strong>No private model inputs.</strong> Public sources do not expose cost bases, forecasts, valuation targets, sell thresholds, position-level confidence, or live orders.</li>
            <li><strong>No model-effectiveness evidence.</strong> There is no public precision/recall, forecast-error, attribution, signal-ablation, or trading-impact record for Aion or the alternative-data models.</li>
            <li><strong>No canonical agent schema.</strong> BIT names scores, alerts, signals, and insights but does not publish their exact structures, evaluation gates, or decision rights.</li>
            <li><strong>Marketing examples are selected.</strong> Public case studies skew toward successful investments and cannot establish the base rate of thesis failure.</li>
            <li><strong>Concentrated versus “broad.”</strong> Formal and current strategy material strongly supports a concentrated interpretation even though one public blurb uses broader language.</li>
            <li><strong>Long horizon versus high turnover.</strong> A five-year recommended holding period coexists with interview evidence of turnover above three times annually. The likely reconciliation is long-duration company theses with active valuation- and signal-driven weighting.</li>
            <li><strong>Bottom-up versus macro overlays.</strong> Bottom-up describes idea selection; macro, factor, liquidity, and stress controls can still change portfolio exposure.</li>
            <li><strong>Inconsistent infrastructure scale.</strong> Public data and token figures vary materially by page and should not be treated as one verified metric.</li>
            <li><strong>Micron dates conflict.</strong> Public BIT examples contain incompatible entry and accumulation dates.</li>
            <li><strong>IREN transaction description conflicts.</strong> BIT commentary and IREN’s company announcement describe different counterparties and contract values; the primary company source governs.</li>
            <li><strong>Interview transcripts can be noisy.</strong> Machine-generated transcripts are useful process evidence but weaker than official written policy for exact internal names and figures.</li>
            <li><strong>Product boundaries differ.</strong> Broader shorting or instrument flexibility in the institutional Technology Opportunities vehicle must not be imputed to the flagship UCITS fund.</li>
            <li><strong>Future changes are not current.</strong> Terms announced for 3 August 2026 remain future-effective as of this review.</li>
          </ul>
        </section>

        <section className="lens-reading-section" id="sources" aria-labelledby="sources-title">
          <h2 id="sources-title">8. Source ledger</h2>
          <p>
            Source precedence is: current mandatory HANSAINVEST documents; current official
            BIT/HANSAINVEST factsheets; historical regulatory reports; dated BIT commentary
            and thesis material; distributor copies only as corroboration; and cached or
            third-party portfolio data only when labeled provisional. The most useful sources
            for this condensation are listed below.
          </p>

          <div className="lens-table-wrap">
            <table className="lens-data-table lens-source-ledger">
              <thead><tr><th scope="col">Date / status</th><th scope="col">Source</th><th scope="col">What it establishes</th></tr></thead>
              <tbody>
                {sourceLedger.map((source) => (
                  <tr key={source.label}>
                    <td className="mono">{source.date}</td>
                    <td><SourceLink href={source.href}>{source.label}</SourceLink></td>
                    <td>{source.use}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3>Additional useful public material</h3>
          <ul>
            <li><SourceLink href={sources.downloads}>HANSAINVEST document downloads</SourceLink> — current and archived mandatory fund documents.</li>
            <li><SourceLink href={sources.team}>BIT team</SourceLink> — current responsibility map across investment, risk, systematic work, data, and AI integration.</li>
            <li><SourceLink href={sources.q1Report}>Q1 2026 equity report</SourceLink> — current view on agentic-AI compute demand, software repricing, and factor rotations.</li>
            <li><SourceLink href={sources.omrInterview}>March 2026 OMR interview</SourceLink> — current software-disruption and AI-infrastructure positioning.</li>
            <li><SourceLink href={sources.stockPicking2025}>2025 stock-picking review</SourceLink> — selected examples of data-assisted timing and weighting.</li>
            <li><SourceLink href={sources.hardwareAnalyst}>Hardware &amp; Robotics analyst role</SourceLink> and <SourceLink href={sources.seniorAnalyst}>Senior Analyst / Portfolio Manager role</SourceLink> — forecasting, valuation, expert work, and disconfirming-evidence expectations.</li>
            <li><SourceLink href={sources.satyaInterview}>Satya Mishra interview</SourceLink> — historical data-platform priorities and distinct research-team use cases.</li>
            <li><SourceLink href={sources.iren}>IREN company announcement</SourceLink> — primary source used to resolve the public transaction-description conflict.</li>
          </ul>
        </section>
      </article>
    </div>
  )
}
