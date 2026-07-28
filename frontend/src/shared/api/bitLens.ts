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

export interface CompanyResearchMemo {
  schema_version: 'company-memo-pilot-result-v1'
  company: {
    name: string
    ticker: string
  }
  memo: {
    business_and_economics: {
      summary: string
      revenue_engines: Array<{
        engine: string
        who_pays: string
        economic_logic: string
        sources: CompanyMemoSourceRef[]
      }>
      sources: CompanyMemoSourceRef[]
    }
    operating_and_financial_drivers: Array<{
      driver: string
      why_it_matters: string
      financial_lines: string[]
      sources: CompanyMemoSourceRef[]
    }>
    ecosystem: Array<{
      relationship: string
      entities_or_group: string
      why_it_matters: string
      sources: CompanyMemoSourceRef[]
    }>
    strategy_and_committed_actions: Array<{
      action: string
      investment_relevance: string
      sources: CompanyMemoSourceRef[]
    }>
    frontier_ai_transmission_paths: Array<{
      development: string
      company_exposure: string
      affected_driver: string
      financial_consequence: string
      direction: 'upside' | 'downside' | 'mixed'
      materiality_condition: string
      time_horizon: 'near_term' | 'medium_term' | 'long_term' | 'unclear'
      thesis_effect: 'supports' | 'challenges' | 'mixed' | 'unclear' | 'no_public_thesis'
      watchpoints: string[]
      sources: CompanyMemoSourceRef[]
    }>
    investment_thesis_and_tests: {
      public_bit_view_status: 'explicit_thesis' | 'commentary' | 'no_public_view'
      attributable_public_thesis: string | null
      what_would_support_it: string[]
      what_would_challenge_it: string[]
      sources: CompanyMemoSourceRef[]
    }
    uncertainties_and_research_triggers: Array<{
      uncertainty: string
      why_it_matters: string
      next_research_trigger: string
      sources: CompanyMemoSourceRef[]
    }>
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
  provenance: {
    research_date: string
    model: string
    reasoning_effort: string
    prompt_version: string
    input_tokens: number
    cached_tokens: number
    output_tokens: number
    reasoning_tokens?: number
  }
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
