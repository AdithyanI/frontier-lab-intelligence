export type BitPublicViewGrade = 'explicit_thesis' | 'commentary' | 'none'

export interface CompanySource {
  label: string
  url: string
}

export interface CompanyPortfolioDisclosure {
  as_of: string
  weight_pct: number
  rank?: number
}

export interface FrontierAIChannel {
  channel: string
  potential_upside: string
  potential_downside: string
  watchpoints: string[]
}

export interface CompanyMemoSourceRef {
  url: string
  claim_date: string | null
}

export interface CompanyBet {
  id: string
  if: string
  exposure: string
  then: string
  threshold: string
  watch: string[]
  direction: 'upside' | 'downside'
  sources: CompanyMemoSourceRef[]
}

export const COMPANY_BET_DIRECTION_COPY: Record<CompanyBet['direction'], string> = {
  upside: 'Upside',
  downside: 'Downside',
}

export interface CompanyResearchMemo {
  ticker: string
  name: string
  summary: string
  summary_sources: CompanyMemoSourceRef[]
  bets: CompanyBet[]
  researched_at: string
  source_ledger: Array<{
    url: string
    title: string
    publisher: string
    published_at: string | null
    source_type:
      | 'company_primary'
      | 'bit_primary'
      | 'counterparty_primary'
      | 'regulator_primary'
      | 'high_quality_secondary'
  }>
}

export interface InvestmentCompany {
  name: string
  ticker: string
  aliases: string[]
  listing_status: 'public'
  bit_public_view: {
    grade: BitPublicViewGrade
    source_scope: 'firm' | 'flagship' | 'other_product' | 'mixed' | 'none'
    thesis: string | null
    edge: string | null
    signals: string[]
    countercase: string | null
    sources: CompanySource[]
  }
  analyst_context: {
    business_summary: string
    operating_drivers: string[]
    frontier_ai_channels: FrontierAIChannel[]
    cautions: string[]
  }
  identity_sources: CompanySource[]
  research_memo: CompanyResearchMemo | null
  portfolio_context: {
    reference_holding: CompanyPortfolioDisclosure & {
      basis: 'current_top_ten' | 'audited_baseline'
      currently_confirmed: boolean
    }
    current_top_ten: CompanyPortfolioDisclosure | null
    audited_baseline: CompanyPortfolioDisclosure | null
  }
}

export interface InvestmentCompanyUniverse {
  schema_version: 'investment-company-universe-v5'
  source_context_schema_version: string
  profiles_reviewed_at: string
  mapping_policy: {
    candidate_universe: 'all_profiles'
    connection_types: ['direct', 'indirect', 'none']
    thesis_effects: ['supports', 'challenges', 'mixed', 'unclear', 'no_public_thesis']
    shortlist_rule: string
    publication_rule: string
  }
  disclosures: {
    current_top_ten: {
      as_of: string
      position_count: number
      visible_holding_count: number
      source: CompanySource
    }
    audited_baseline: {
      as_of: string
      visible_holding_count: number
      source: CompanySource
    }
  }
  counts: {
    companies: number
    current_top_ten: number
    audited_baseline: number
    later_top_ten_additions: number
    research_memos: number
    frontier_ai_channels: number
    bit_public_views: number
    bit_public_view_grades: Record<BitPublicViewGrade, number>
  }
  companies: InvestmentCompany[]
}
