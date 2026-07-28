export type FeedRoutingFilter =
  | 'all'
  | 'relevant'
  | 'not_relevant'
  | 'not_evaluated'

export function initialFeedRoutingFilter(
  _searchParams: URLSearchParams,
): FeedRoutingFilter {
  return 'all'
}
