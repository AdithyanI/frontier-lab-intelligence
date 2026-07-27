import { useEffect, useMemo, useState } from 'react'
import {
  getCachedJSON,
  type BitPublicViewGrade,
  type CompanySource,
  type InvestmentCompany,
  type InvestmentCompanyUniverse,
} from '../../shared/api'

type DisclosureFilter = 'all' | 'current' | 'audited' | 'later'
type EvidenceFilter = 'all' | BitPublicViewGrade
type CompanySort = 'portfolio' | 'name' | 'channels'

const dayFormatter = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

const gradeCopy: Record<BitPublicViewGrade, string> = {
  explicit_thesis: 'BIT thesis',
  commentary: 'BIT commentary',
  none: 'Analyst context only',
}

const sourceScopeCopy = {
  firm: 'Firm-level public view',
  flagship: 'Flagship-fund public view',
  other_product: 'Other BIT product',
  mixed: 'Mixed public BIT sources',
  none: 'No public BIT view',
}

function formatDay(day: string) {
  return dayFormatter.format(new Date(`${day}T12:00:00Z`))
}

function formatWeight(weight: number) {
  return `${weight.toFixed(2).replace(/\.?0+$/, '')}%`
}

function SourceList({ sources }: { sources: CompanySource[] }) {
  return (
    <ul className="company-source-list">
      {sources.map((source) => (
        <li key={`${source.label}-${source.url}`}>
          <a href={source.url} target="_blank" rel="noreferrer">
            {source.label} <span aria-hidden="true">↗</span>
          </a>
        </li>
      ))}
    </ul>
  )
}

function companySearchText(company: InvestmentCompany) {
  const analyst = company.analyst_context
  return [
    company.name,
    company.ticker,
    ...company.aliases,
    analyst.business_summary,
    ...analyst.operating_drivers,
    ...analyst.frontier_ai_channels.flatMap((channel) => [
      channel.channel,
      channel.potential_upside,
      channel.potential_downside,
      ...channel.watchpoints,
    ]),
  ].join(' ').toLocaleLowerCase()
}

function comparePortfolio(a: InvestmentCompany, b: InvestmentCompany) {
  const aCurrent = a.portfolio_context.current_top_ten
  const bCurrent = b.portfolio_context.current_top_ten
  if (aCurrent && bCurrent) return (aCurrent.rank ?? 99) - (bCurrent.rank ?? 99)
  if (aCurrent) return -1
  if (bCurrent) return 1
  const aWeight = a.portfolio_context.audited_baseline?.weight_pct ?? -1
  const bWeight = b.portfolio_context.audited_baseline?.weight_pct ?? -1
  return bWeight - aWeight || a.name.localeCompare(b.name)
}

function PortfolioContext({ company }: { company: InvestmentCompany }) {
  const current = company.portfolio_context.current_top_ten
  const audited = company.portfolio_context.audited_baseline

  return (
    <div className="company-portfolio-lines">
      {current && (
        <span>
          <strong>{formatWeight(current.weight_pct)}</strong>
          <span>{formatDay(current.as_of)} top ten</span>
        </span>
      )}
      {audited && (
        <span>
          <strong>{formatWeight(audited.weight_pct)}</strong>
          <span>{formatDay(audited.as_of)} audited</span>
        </span>
      )}
      {!audited && current && (
        <small>Added after the audited baseline</small>
      )}
    </div>
  )
}

function CompanyDetail({ company }: { company: InvestmentCompany }) {
  const analyst = company.analyst_context
  const publicView = company.bit_public_view

  return (
    <div className="company-detail">
      <section className="company-detail-section company-business-context">
        <div>
          <h3>Business context</h3>
          <p>{analyst.business_summary}</p>
        </div>
        <div>
          <h3>Operating drivers</h3>
          <ul className="company-text-list">
            {analyst.operating_drivers.map((driver) => (
              <li key={driver}>{driver}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="company-detail-section">
        <div className="company-section-heading">
          <div>
            <h3>Frontier-AI transmission channels</h3>
            <p>
              Reusable hypotheses for how a frontier development could reach this
              company. The Event still has to activate the channel.
            </p>
          </div>
          <span className="mono">{analyst.frontier_ai_channels.length} channels</span>
        </div>
        <div className="company-channel-list">
          {analyst.frontier_ai_channels.map((channel) => (
            <article className="company-channel" key={channel.channel}>
              <h4>{channel.channel}</h4>
              <div className="company-channel-directions">
                <div>
                  <span>Potential upside</span>
                  <p>{channel.potential_upside}</p>
                </div>
                <div>
                  <span>Potential downside</span>
                  <p>{channel.potential_downside}</p>
                </div>
              </div>
              <div className="company-watchpoints">
                <span>Watchpoints</span>
                <ul>
                  {channel.watchpoints.map((watchpoint) => (
                    <li key={watchpoint}>{watchpoint}</li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="company-detail-section company-public-view">
        <div className="company-section-heading">
          <div>
            <h3>BIT’s public view</h3>
            <p>{sourceScopeCopy[publicView.source_scope]}</p>
          </div>
          <span className={`company-evidence-grade is-${publicView.grade}`}>
            {gradeCopy[publicView.grade]}
          </span>
        </div>
        {publicView.grade === 'none' ? (
          <p className="company-missing-view">
            No company-specific BIT thesis or commentary is represented in the
            source packet. The context above is FLI analyst research, not BIT’s view.
          </p>
        ) : (
          <dl className="company-view-grid">
            {publicView.thesis && <div><dt>Thesis</dt><dd>{publicView.thesis}</dd></div>}
            {publicView.edge && <div><dt>Edge</dt><dd>{publicView.edge}</dd></div>}
            {publicView.signals.length > 0 && (
              <div>
                <dt>Signals</dt>
                <dd>{publicView.signals.join('; ')}</dd>
              </div>
            )}
            {publicView.countercase && (
              <div><dt>Countercase</dt><dd>{publicView.countercase}</dd></div>
            )}
          </dl>
        )}
        {publicView.sources.length > 0 && <SourceList sources={publicView.sources} />}
      </section>

      <section className="company-detail-section company-detail-footer">
        <div>
          <h3>Research cautions</h3>
          {analyst.cautions.length > 0 ? (
            <ul className="company-text-list">
              {analyst.cautions.map((caution) => (
                <li key={caution}>{caution}</li>
              ))}
            </ul>
          ) : (
            <p>No company-specific caution is recorded.</p>
          )}
        </div>
        <div>
          <h3>Company sources</h3>
          <SourceList sources={company.identity_sources} />
        </div>
      </section>
    </div>
  )
}

export default function CompanyUniversePage() {
  const [payload, setPayload] = useState<InvestmentCompanyUniverse | null>(null)
  const [error, setError] = useState(false)
  const [requestVersion, setRequestVersion] = useState(0)
  const [query, setQuery] = useState('')
  const [disclosure, setDisclosure] = useState<DisclosureFilter>('all')
  const [evidence, setEvidence] = useState<EvidenceFilter>('all')
  const [sort, setSort] = useState<CompanySort>('portfolio')
  const [openCompanies, setOpenCompanies] = useState<Set<string>>(new Set())

  useEffect(() => {
    let active = true
    setError(false)
    getCachedJSON<InvestmentCompanyUniverse>('/api/bit-lens/companies')
      .then((result) => {
        if (active) setPayload(result)
      })
      .catch(() => {
        if (active) setError(true)
      })
    return () => {
      active = false
    }
  }, [requestVersion])

  const visibleCompanies = useMemo(() => {
    if (!payload) return []
    const normalizedQuery = query.trim().toLocaleLowerCase()
    const companies = payload.companies.filter((company) => {
      const portfolio = company.portfolio_context
      if (disclosure === 'current' && !portfolio.current_top_ten) return false
      if (disclosure === 'audited' && !portfolio.audited_baseline) return false
      if (
        disclosure === 'later'
        && (!portfolio.current_top_ten || portfolio.audited_baseline)
      ) return false
      if (evidence !== 'all' && company.bit_public_view.grade !== evidence) return false
      return !normalizedQuery || companySearchText(company).includes(normalizedQuery)
    })

    return companies.sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name)
      if (sort === 'channels') {
        return b.analyst_context.frontier_ai_channels.length
          - a.analyst_context.frontier_ai_channels.length
          || a.name.localeCompare(b.name)
      }
      return comparePortfolio(a, b)
    })
  }, [payload, query, disclosure, evidence, sort])

  function setCompanyOpen(ticker: string, isOpen: boolean) {
    setOpenCompanies((current) => {
      if (current.has(ticker) === isOpen) return current
      const next = new Set(current)
      if (isOpen) next.add(ticker)
      else next.delete(ticker)
      return next
    })
  }

  if (error) {
    return (
      <section className="company-universe-view company-universe-state" aria-live="polite">
        <h2>The company context could not be loaded</h2>
        <p>The canonical packet is unchanged. Retry this read-only projection.</p>
        <button type="button" onClick={() => setRequestVersion((value) => value + 1)}>
          Retry
        </button>
      </section>
    )
  }

  if (!payload) {
    return (
      <section className="company-universe-view company-universe-state" aria-live="polite">
        <h2>Loading the company universe</h2>
        <p>Reading the dated Investment context packet.</p>
      </section>
    )
  }

  return (
    <section className="company-universe-view" aria-labelledby="company-universe-title">
      <div className="company-universe-intro">
        <div>
          <h2 id="company-universe-title">The context behind each company</h2>
          <p>
            Inspect what the Investment pass will know before it reads a new
            Event: the business, operating drivers, two-sided AI channels,
            public BIT evidence, cautions, and sources.
          </p>
        </div>
        <p className="company-scope-note">
          <strong>No automatic inclusion.</strong> All {payload.counts.companies} sourced
          profiles remain visible here for review. A company appears in an
          Investment output only when the Event activates a credible channel.
        </p>
      </div>

      <dl className="company-universe-facts">
        <div>
          <dt>Profile set</dt>
          <dd>{payload.counts.companies} companies · reviewed {formatDay(payload.profiles_reviewed_at)}</dd>
        </div>
        <div>
          <dt>Latest visible holdings</dt>
          <dd>{payload.counts.current_top_ten} top-ten names · {formatDay(payload.disclosures.current_top_ten.as_of)}</dd>
        </div>
        <div>
          <dt>Complete baseline</dt>
          <dd>{payload.counts.audited_baseline} audited holdings · {formatDay(payload.disclosures.audited_baseline.as_of)}</dd>
        </div>
        <div>
          <dt>Reusable context</dt>
          <dd>{payload.counts.frontier_ai_channels} AI channels · {payload.counts.bit_public_views} public BIT views</dd>
        </div>
      </dl>

      <div className="company-universe-method">
        <p>
          The June disclosure contains only the current top ten. The December
          report is the latest complete audited portfolio. Absence from the June
          list does not prove that a position was sold.
        </p>
        <div>
          <a href={payload.disclosures.current_top_ten.source.url} target="_blank" rel="noreferrer">
            June factsheet ↗
          </a>
          <a href={payload.disclosures.audited_baseline.source.url} target="_blank" rel="noreferrer">
            Audited report ↗
          </a>
        </div>
      </div>

      <div className="company-universe-tools">
        <label className="company-search">
          <span>Search context</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Company, ticker, driver, or AI channel"
          />
        </label>
        <label>
          <span>Disclosure</span>
          <select value={disclosure} onChange={(event) => setDisclosure(event.target.value as DisclosureFilter)}>
            <option value="all">All profiles</option>
            <option value="current">Current top ten</option>
            <option value="audited">Audited baseline</option>
            <option value="later">Later additions</option>
          </select>
        </label>
        <label>
          <span>Public evidence</span>
          <select value={evidence} onChange={(event) => setEvidence(event.target.value as EvidenceFilter)}>
            <option value="all">All grades</option>
            <option value="explicit_thesis">BIT thesis</option>
            <option value="commentary">BIT commentary</option>
            <option value="none">Analyst context only</option>
          </select>
        </label>
        <label>
          <span>Sort</span>
          <select value={sort} onChange={(event) => setSort(event.target.value as CompanySort)}>
            <option value="portfolio">Portfolio disclosure</option>
            <option value="name">Company name</option>
            <option value="channels">AI channel count</option>
          </select>
        </label>
      </div>

      <div className="company-ledger-head">
        <p>
          <strong>{visibleCompanies.length}</strong> {visibleCompanies.length === 1 ? 'company' : 'companies'}
          <span>Open a row to inspect the complete profile.</span>
        </p>
        <div>
          <button
            type="button"
            onClick={() => setOpenCompanies(new Set(visibleCompanies.map((company) => company.ticker)))}
            disabled={visibleCompanies.length === 0}
          >
            Open visible
          </button>
          <button
            type="button"
            onClick={() => setOpenCompanies(new Set())}
            disabled={openCompanies.size === 0}
          >
            Close all
          </button>
        </div>
      </div>

      {visibleCompanies.length === 0 ? (
        <div className="company-universe-empty">
          <h3>No company matches these filters</h3>
          <p>Clear the search or widen the disclosure and evidence filters.</p>
        </div>
      ) : (
        <div className="company-ledger">
          {visibleCompanies.map((company) => (
            <details
              key={company.ticker}
              open={openCompanies.has(company.ticker)}
              onToggle={(event) => setCompanyOpen(company.ticker, event.currentTarget.open)}
            >
              <summary>
                <div className="company-identity">
                  <strong>{company.name}</strong>
                  <span className="mono">{company.ticker}</span>
                </div>
                <PortfolioContext company={company} />
                <p>{company.analyst_context.business_summary}</p>
                <div className="company-row-evidence">
                  <span className={`company-evidence-grade is-${company.bit_public_view.grade}`}>
                    {gradeCopy[company.bit_public_view.grade]}
                  </span>
                  <span className="mono">
                    {company.analyst_context.frontier_ai_channels.length}{' '}
                    {company.analyst_context.frontier_ai_channels.length === 1 ? 'channel' : 'channels'}
                  </span>
                </div>
              </summary>
              <CompanyDetail company={company} />
            </details>
          ))}
        </div>
      )}
    </section>
  )
}
