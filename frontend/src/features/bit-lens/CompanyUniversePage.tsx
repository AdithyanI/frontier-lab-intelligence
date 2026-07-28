import { useEffect, useMemo, useRef, useState } from 'react'
import {
  getCachedJSON,
  type BitPublicViewGrade,
  type CompanySource,
  type InvestmentCompany,
  type InvestmentCompanyUniverse,
} from '../../shared/api'

type DisclosureFilter = 'all' | 'current' | 'audited' | 'later'
type ScopeFilter = 'in_scope' | 'all' | 'out_of_scope'
type CompanySort = 'portfolio' | 'name'

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

interface CompanyMenuOption<T extends string> {
  value: T
  label: string
  description: string
}

const disclosureOptions: readonly CompanyMenuOption<DisclosureFilter>[] = [
  { value: 'all', label: 'All profiles', description: 'Show every company profile' },
  { value: 'current', label: 'Current top ten', description: 'Show the June 2026 top ten' },
  { value: 'audited', label: 'Audited baseline', description: 'Show companies in the complete December 2025 portfolio' },
  { value: 'later', label: 'Later additions', description: 'Show current top-ten names absent from the audited baseline' },
]

const scopeOptions: readonly CompanyMenuOption<ScopeFilter>[] = [
  { value: 'in_scope', label: 'FLI universe', description: 'Show companies with a direct frontier-lab transmission path' },
  { value: 'all', label: 'All profiles', description: 'Show every sourced company profile' },
  { value: 'out_of_scope', label: 'Outside current scope', description: 'Show disclosed companies excluded from the focused FLI universe' },
]

const sortOptions: readonly CompanyMenuOption<CompanySort>[] = [
  { value: 'portfolio', label: 'Portfolio disclosure', description: 'Show current top-ten names first, then the audited baseline by weight' },
  { value: 'name', label: 'Company name', description: 'Sort companies alphabetically' },
]

function formatDay(day: string) {
  return dayFormatter.format(new Date(`${day}T12:00:00Z`))
}

function formatWeight(weight: number) {
  return `${weight.toFixed(2).replace(/\.?0+$/, '')}%`
}

function joinContextItems(items: string[]) {
  if (items.length < 2) return items[0] ?? ''
  if (items.length === 2) return `${items[0]} and ${items[1]}`
  return `${items.slice(0, -1).join(', ')}, and ${items.at(-1)}`
}

function CompanyMenuSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: readonly CompanyMenuOption<T>[]
  onChange: (value: T) => void
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const selected = options.find((option) => option.value === value) ?? options[0]

  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!detailsRef.current?.contains(event.target as Node)) {
        detailsRef.current?.removeAttribute('open')
      }
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') detailsRef.current?.removeAttribute('open')
    }
    window.addEventListener('pointerdown', closeOnOutsideClick)
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      window.removeEventListener('pointerdown', closeOnOutsideClick)
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  return (
    <details className="feed-menu company-filter-menu" ref={detailsRef}>
      <summary aria-label={`${label}: ${selected.description}`}>
        <span className="feed-menu-label mono">{label}</span>
        <span className="feed-menu-value">{selected.label}</span>
        <span className="feed-menu-caret" aria-hidden="true" />
      </summary>
      <div className="feed-menu-panel" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            className={option.value === value ? 'is-active' : ''}
            onClick={() => {
              onChange(option.value)
              detailsRef.current?.removeAttribute('open')
            }}
            aria-pressed={option.value === value}
            title={option.description}
          >
            <span>{option.label}</span>
          </button>
        ))}
      </div>
    </details>
  )
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
    company.frontier_lab_relevance_reason ?? '',
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
  const reference = company.portfolio_context.reference_holding

  return (
    <div className="company-portfolio-lines">
      <span>
        <strong>{formatWeight(reference.weight_pct)}</strong>
        <span>
          {reference.basis === 'current_top_ten'
            ? `${formatDay(reference.as_of)} top ten`
            : `Last confirmed ${formatDay(reference.as_of)}`}
        </span>
      </span>
    </div>
  )
}

function CompanyDetail({ company }: { company: InvestmentCompany }) {
  const analyst = company.analyst_context
  const publicView = company.bit_public_view
  const knownExposureNames = analyst.frontier_ai_channels.map((channel) => channel.channel)
  const isInScope = company.frontier_lab_relevance === 'in_scope'

  return (
    <div className="company-detail">
      <section className="company-detail-section company-agent-context">
        <div className="company-context-heading">
          <div>
            <h3>Context used by the agent</h3>
            <p>
              {isInScope
                ? 'The company mental model available when the agent reads a new Event.'
                : 'Retained for portfolio audit, outside the focused FLI universe.'}
            </p>
          </div>
          <span className="mono">
            {isInScope ? 'FLI universe' : 'Outside current scope'}
          </span>
        </div>
        <div className="company-context-copy">
          <p>{analyst.business_summary}</p>
          {!isInScope && company.frontier_lab_relevance_reason && (
            <p className="company-scope-reason">
              <strong>Why it is outside the focused universe.</strong>{' '}
              {company.frontier_lab_relevance_reason}
            </p>
          )}
          <p>
            <strong>What moves the economics.</strong>{' '}
            {joinContextItems(analyst.operating_drivers)}.
          </p>
          <p>
            <strong>Known AI exposure.</strong>{' '}
            {joinContextItems(knownExposureNames)}.
          </p>
          <p className="company-context-rule">
            These are starting hypotheses, not a closed list. The Event must
            establish a defensible connection to an operating driver, or support
            another mechanism.
          </p>
        </div>
        <details className="company-supporting-context">
          <summary>Inspect supporting hypotheses and watchpoints</summary>
          <div className="company-channel-list">
            {analyst.frontier_ai_channels.map((channel) => (
              <article className="company-channel" key={channel.channel}>
                <h4>{channel.channel}</h4>
                <div className="company-channel-directions">
                  <div>
                    <span>Opportunity</span>
                    <p>{channel.potential_upside}</p>
                  </div>
                  <div>
                    <span>Risk</span>
                    <p>{channel.potential_downside}</p>
                  </div>
                </div>
                <div className="company-watchpoints">
                  <span>Watch</span>
                  <ul>
                    {channel.watchpoints.map((watchpoint) => (
                      <li key={watchpoint}>{watchpoint}</li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
          </div>
        </details>
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

      <section className="company-detail-section company-support-grid">
        <div>
          <h3>Research limits</h3>
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
        <div className="company-disclosure-history">
          <h3>Disclosure history</h3>
          <dl>
            {company.portfolio_context.current_top_ten && (
              <div>
                <dt>Top ten · {formatDay(company.portfolio_context.current_top_ten.as_of)}</dt>
                <dd>{formatWeight(company.portfolio_context.current_top_ten.weight_pct)}</dd>
              </div>
            )}
            {company.portfolio_context.audited_baseline && (
              <div>
                <dt>Audited · {formatDay(company.portfolio_context.audited_baseline.as_of)}</dt>
                <dd>{formatWeight(company.portfolio_context.audited_baseline.weight_pct)}</dd>
              </div>
            )}
          </dl>
          <p>The row shows the newest available reference weight. Values are never blended.</p>
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
  const [scope, setScope] = useState<ScopeFilter>('in_scope')
  const [disclosure, setDisclosure] = useState<DisclosureFilter>('all')
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
      if (scope !== 'all' && company.frontier_lab_relevance !== scope) return false
      if (disclosure === 'current' && !portfolio.current_top_ten) return false
      if (disclosure === 'audited' && !portfolio.audited_baseline) return false
      if (
        disclosure === 'later'
        && (!portfolio.current_top_ten || portfolio.audited_baseline)
      ) return false
      return !normalizedQuery || companySearchText(company).includes(normalizedQuery)
    })

    return companies.sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name)
      return comparePortfolio(a, b)
    })
  }, [payload, query, scope, disclosure, sort])

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
    <section className="company-universe-view" aria-label="Company context">
      <div className="company-universe-method">
        <p>
          <strong>
            {payload.counts.in_scope_companies} frontier-linked companies.
          </strong>{' '}
          The focused universe is drawn from {payload.counts.companies} sourced
          profiles.{' '}
          June shows only the current top ten; December 2025 is the latest complete
          audited portfolio, and absence from June does not prove a sale.
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
            placeholder="Company, ticker, business, or driver"
          />
        </label>
        <div className="company-filter-controls">
          <CompanyMenuSelect
            label="FLI scope"
            value={scope}
            options={scopeOptions}
            onChange={setScope}
          />
          <CompanyMenuSelect
            label="Disclosure"
            value={disclosure}
            options={disclosureOptions}
            onChange={setDisclosure}
          />
          <CompanyMenuSelect
            label="Sort"
            value={sort}
            options={sortOptions}
            onChange={setSort}
          />
        </div>
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
                  {company.frontier_lab_relevance === 'out_of_scope' && (
                    <span className="company-scope-mark">Outside FLI scope</span>
                  )}
                  <span className={`company-evidence-grade is-${company.bit_public_view.grade}`}>
                    {gradeCopy[company.bit_public_view.grade]}
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
