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

export interface InvestmentCompany {
  name: string
  frontier_lab_relevance: 'in_scope' | 'out_of_scope'
  frontier_lab_relevance_reason?: string
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
  schema_version: 'investment-company-universe-v3'
  source_context_schema_version: string
  profiles_reviewed_at: string
  scope: {
    status: 'curated'
    label: string
    note: string
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
    in_scope_companies: number
    out_of_scope_companies: number
    current_top_ten: number
    audited_baseline: number
    later_top_ten_additions: number
    frontier_ai_channels: number
    bit_public_views: number
    bit_public_view_grades: Record<BitPublicViewGrade, number>
  }
  companies: InvestmentCompany[]
}
