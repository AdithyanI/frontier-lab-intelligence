import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  getCachedJSON,
  type CompanyMemoSourceRef,
  type CompanyResearchMemo,
  type InvestmentCompany,
  type InvestmentCompanyUniverse,
} from '../../shared/api'

type DisclosureFilter = 'all' | 'current' | 'audited' | 'later'
type CompanySort = 'portfolio' | 'name'

const dayFormatter = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

const thesisStatusCopy: Record<CompanyResearchMemo['memo']['investment_thesis_and_tests']['public_bit_view_status'], string> = {
  explicit_thesis: 'BIT thesis',
  commentary: 'BIT commentary',
  no_public_view: 'No public BIT view',
}

const sourceTypeCopy: Record<CompanyResearchMemo['memo']['source_ledger'][number]['source_type'], string> = {
  company_primary: 'Company',
  bit_primary: 'BIT Capital',
  counterparty_primary: 'Counterparty',
  regulator_primary: 'Regulator',
  high_quality_secondary: 'Secondary',
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

function formatTaxonomy(value: string) {
  return value.replaceAll('_', ' ')
}

function cleanMemoText(value: string) {
  return value
    .replace(/\s*\(\[[^\]]+\]\(https:\/\/[^)]+\)\)/g, '')
    .trim()
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

function MemoCitations({
  sources,
  sourceIndex,
}: {
  sources: CompanyMemoSourceRef[]
  sourceIndex: Map<string, number>
}) {
  if (sources.length === 0) return null
  return (
    <span className="company-memo-citations" aria-label="Sources">
      {sources.map((source) => (
        <a
          href={source.url}
          key={source.url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open source ${sourceIndex.get(source.url)}`}
        >
          [{sourceIndex.get(source.url)}]
        </a>
      ))}
    </span>
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
    company.research_memo ? JSON.stringify(company.research_memo.memo) : '',
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
  const researchMemo = company.research_memo

  if (!researchMemo) {
    return (
      <div className="company-detail company-memo-pending">
        <p className="mono">Research memo pending</p>
        <h3>The new company memo has not been generated yet.</h3>
        <p>
          This row remains in the candidate universe, but the older hypothesis
          profile is no longer presented as the final agent context.
        </p>
      </div>
    )
  }

  const { memo, provenance } = researchMemo
  const sourceIndex = new Map(
    memo.source_ledger.map((source, index) => [source.url, index + 1]),
  )
  const thesis = memo.investment_thesis_and_tests

  return (
    <div className="company-detail company-research-memo">
      <section className="company-memo-intro">
        <div>
          <p className="mono">Investment context memo</p>
          <p className="company-memo-summary">
            {cleanMemoText(memo.business_and_economics.summary)}
            <MemoCitations
              sources={memo.business_and_economics.sources}
              sourceIndex={sourceIndex}
            />
          </p>
        </div>
        <dl className="company-memo-provenance">
          <div>
            <dt>Researched</dt>
            <dd>{formatDay(provenance.research_date)}</dd>
          </div>
          <div>
            <dt>Evidence</dt>
            <dd>{memo.source_ledger.length} sources</dd>
          </div>
        </dl>
      </section>

      <section className="company-detail-section">
        <header className="company-memo-section-head">
          <h3>How the business earns money</h3>
          <span>{memo.business_and_economics.revenue_engines.length} revenue engines</span>
        </header>
        <div className="company-memo-rows">
          {memo.business_and_economics.revenue_engines.map((engine) => (
            <article key={engine.engine}>
              <h4>{cleanMemoText(engine.engine)}</h4>
              <p className="company-memo-who">Who pays · {cleanMemoText(engine.who_pays)}</p>
              <p>{cleanMemoText(engine.economic_logic)}</p>
              <MemoCitations sources={engine.sources} sourceIndex={sourceIndex} />
            </article>
          ))}
        </div>
      </section>

      <section className="company-detail-section">
        <header className="company-memo-section-head">
          <h3>What moves the economics</h3>
          <span>{memo.operating_and_financial_drivers.length} operating drivers</span>
        </header>
        <ol className="company-driver-list">
          {memo.operating_and_financial_drivers.map((driver) => (
            <li key={driver.driver}>
              <div>
                <h4>{cleanMemoText(driver.driver)}</h4>
              </div>
              <p>{cleanMemoText(driver.why_it_matters)}</p>
              <MemoCitations sources={driver.sources} sourceIndex={sourceIndex} />
            </li>
          ))}
        </ol>
      </section>

      <section className="company-detail-section company-ai-paths">
        <header className="company-memo-section-head">
          <div>
            <h3>Where frontier AI can matter</h3>
            <p>Each path must reach an operating driver and a possible financial consequence.</p>
          </div>
          <span>{memo.frontier_ai_transmission_paths.length} testable paths</span>
        </header>
        <div className="company-path-list">
          {memo.frontier_ai_transmission_paths.map((path) => (
            <article key={path.development}>
              <header>
                <h4>{cleanMemoText(path.development)}</h4>
                <div className="company-path-meta">
                  <span className={`is-${path.direction}`}>{path.direction}</span>
                  <span>{formatTaxonomy(path.time_horizon)}</span>
                  <span>Thesis · {formatTaxonomy(path.thesis_effect)}</span>
                </div>
              </header>
              <dl className="company-causal-chain">
                <div>
                  <dt>Company exposure</dt>
                  <dd>{cleanMemoText(path.company_exposure)}</dd>
                </div>
                <div>
                  <dt>Operating driver</dt>
                  <dd>{cleanMemoText(path.affected_driver)}</dd>
                </div>
                <div>
                  <dt>Financial consequence</dt>
                  <dd>{cleanMemoText(path.financial_consequence)}</dd>
                </div>
                <div>
                  <dt>Becomes material when</dt>
                  <dd>{cleanMemoText(path.materiality_condition)}</dd>
                </div>
              </dl>
              <div className="company-path-watch">
                <span className="mono">Watch</span>
                <ul>
                  {path.watchpoints.map((watchpoint) => (
                    <li key={watchpoint}>{cleanMemoText(watchpoint)}</li>
                  ))}
                </ul>
                <MemoCitations sources={path.sources} sourceIndex={sourceIndex} />
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="company-detail-section company-thesis-tests">
        <header className="company-memo-section-head">
          <h3>BIT view and the tests that matter</h3>
          <span className="company-thesis-status">
            {thesisStatusCopy[thesis.public_bit_view_status]}
          </span>
        </header>
        {thesis.attributable_public_thesis ? (
          <p className="company-thesis-copy">
            {cleanMemoText(thesis.attributable_public_thesis)}
            <MemoCitations sources={thesis.sources} sourceIndex={sourceIndex} />
          </p>
        ) : (
          <p className="company-thesis-copy">
            No attributable public BIT thesis was found. Portfolio ownership is
            not treated as thesis evidence.
          </p>
        )}
        <div className="company-thesis-columns">
          <div>
            <h4>What would support it</h4>
            <ul>
              {thesis.what_would_support_it.map((item) => (
                <li key={item}>{cleanMemoText(item)}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4>What would challenge it</h4>
            <ul>
              {thesis.what_would_challenge_it.map((item) => (
                <li key={item}>{cleanMemoText(item)}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="company-detail-section company-memo-secondary">
        <details>
          <summary>Strategy, dependencies, and research triggers</summary>
          <div className="company-memo-secondary-grid">
            <div>
              <h4>Committed actions</h4>
              <ul className="company-memo-rich-list">
                {memo.strategy_and_committed_actions.map((item) => (
                  <li key={item.action}>
                    <strong>{cleanMemoText(item.action)}</strong>
                    <p>{cleanMemoText(item.investment_relevance)}</p>
                    <MemoCitations sources={item.sources} sourceIndex={sourceIndex} />
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Customers, suppliers, and dependencies</h4>
              <ul className="company-memo-rich-list">
                {memo.ecosystem.map((item) => (
                  <li key={`${item.relationship}-${item.entities_or_group}`}>
                    <span className="mono">{formatTaxonomy(item.relationship)}</span>
                    <strong>{cleanMemoText(item.entities_or_group)}</strong>
                    <p>{cleanMemoText(item.why_it_matters)}</p>
                    <MemoCitations sources={item.sources} sourceIndex={sourceIndex} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="company-research-triggers">
            <h4>Uncertainties and next research</h4>
            {memo.uncertainties_and_research_triggers.map((item) => (
              <article key={item.uncertainty}>
                <h5>{cleanMemoText(item.uncertainty)}</h5>
                <p>{cleanMemoText(item.why_it_matters)}</p>
                <p><strong>Next:</strong> {cleanMemoText(item.next_research_trigger)}</p>
                <MemoCitations sources={item.sources} sourceIndex={sourceIndex} />
              </article>
            ))}
          </div>
        </details>
      </section>

      <section className="company-detail-section company-memo-sources">
        <details>
          <summary>Source ledger and generation record · {memo.source_ledger.length} sources</summary>
          <ol>
            {memo.source_ledger.map((source, index) => (
              <li key={source.url} id={`${company.ticker}-source-${index + 1}`}>
                <span className="mono">[{index + 1}] {sourceTypeCopy[source.source_type]}</span>
                <a href={source.url} target="_blank" rel="noreferrer">
                  {source.title} ↗
                </a>
                <span>
                  {source.publisher}
                  {source.published_at ? ` · ${formatDay(source.published_at)}` : ''}
                </span>
              </li>
            ))}
          </ol>
          <p className="company-generation-record mono">
            {provenance.prompt_version} · {provenance.input_tokens.toLocaleString()} input ·{' '}
            {provenance.output_tokens.toLocaleString()} output ·{' '}
            {provenance.cached_tokens.toLocaleString()} cached tokens
          </p>
        </details>
      </section>
    </div>
  )
}

export default function CompanyUniversePage() {
  const [searchParams] = useSearchParams()
  const requestedCompany = (searchParams.get('company') || '').trim().toUpperCase()
  const [payload, setPayload] = useState<InvestmentCompanyUniverse | null>(null)
  const [error, setError] = useState(false)
  const [requestVersion, setRequestVersion] = useState(0)
  const [query, setQuery] = useState(requestedCompany)
  const [disclosure, setDisclosure] = useState<DisclosureFilter>('all')
  const [sort, setSort] = useState<CompanySort>('portfolio')
  const [openCompanies, setOpenCompanies] = useState<Set<string>>(
    new Set([requestedCompany || 'IREN']),
  )

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
      return !normalizedQuery || companySearchText(company).includes(normalizedQuery)
    })

    return companies.sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name)
      return comparePortfolio(a, b)
    })
  }, [payload, query, disclosure, sort])

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
          <strong>{payload.counts.companies} sourced company profiles.</strong>{' '}
          Every Event starts with this candidate universe, then retrieves complete
          context only for credible matches.{' '}
          {payload.counts.research_memos === payload.counts.companies
            ? `All ${payload.counts.companies} companies have a source-bearing research memo. `
            : `${payload.counts.research_memos} companies have a source-bearing research memo; the remaining rows stay visible while their memos are generated. `}
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
          <p>Clear the search or widen the disclosure filter.</p>
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
                  <span className={`company-memo-state ${company.research_memo ? 'is-ready' : ''}`}>
                    {company.research_memo
                      ? `Research memo · ${formatDay(company.research_memo.provenance.research_date)}`
                      : 'Memo pending'}
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
