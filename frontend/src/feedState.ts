export type FeedRoutingFilter =
  | 'all'
  | 'relevant'
  | 'not_relevant'
  | 'not_evaluated'

export function initialFeedRoutingFilter(
  searchParams: URLSearchParams,
): FeedRoutingFilter {
  return searchParams.get('event')?.trim() ? 'all' : 'relevant'
}
