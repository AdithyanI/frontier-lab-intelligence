const shortDate = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})

const compactDate = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})

export interface DateNavigatorItem {
  day: string
  item_count: number
}

interface DateNavigatorProps {
  dates: DateNavigatorItem[]
  selectedDate: string
  onSelectDate: (day: string) => void
  canShowOlderDates: boolean
  canShowNewerDates: boolean
  onShowOlderDates: () => void
  onShowNewerDates: () => void
  ariaLabel: string
  loading?: boolean
}

export default function DateNavigator({
  dates,
  selectedDate,
  onSelectDate,
  canShowOlderDates,
  canShowNewerDates,
  onShowOlderDates,
  onShowNewerDates,
  ariaLabel,
  loading = false,
}: DateNavigatorProps) {
  const showLoadingDates = loading && dates.length === 0

  return (
    <div className="feed-date-navigator" aria-busy={loading}>
      <button
        type="button"
        className="feed-date-page feed-date-page--previous"
        aria-label="Show previous 7 available days"
        disabled={!canShowOlderDates}
        onClick={onShowOlderDates}
      >
        <span aria-hidden="true">←</span>
      </button>
      <div className="feed-days" role="group" aria-label={ariaLabel}>
        {showLoadingDates
          ? Array.from({ length: 7 }, (_, index) => (
              <span className="feed-day-placeholder" aria-hidden="true" key={index}>
                <span className="feed-date-placeholder-label skeleton" />
                <span className="feed-date-placeholder-count skeleton" />
              </span>
            ))
          : dates.map((value) => {
              const parsedDate = new Date(`${value.day}T12:00:00Z`)
              const fullDateLabel = shortDate.format(parsedDate)
              const itemCountLabel = value.item_count.toLocaleString('en-US')
              return (
                <button
                  type="button"
                  key={value.day}
                  className={`feed-day${value.day === selectedDate ? ' is-active' : ''}`}
                  aria-label={`${fullDateLabel}, ${itemCountLabel} posts`}
                  aria-pressed={value.day === selectedDate}
                  onClick={() => onSelectDate(value.day)}
                >
                  <span className="feed-day-label" aria-hidden="true">
                    <span className="feed-day-label-long">{fullDateLabel}</span>
                    <span className="feed-day-label-compact">
                      {compactDate.format(parsedDate)}
                    </span>
                  </span>
                  <span className="feed-day-count mono" aria-hidden="true">
                    {itemCountLabel}
                  </span>
                </button>
              )
            })}
      </div>
      <button
        type="button"
        className="feed-date-page feed-date-page--next"
        aria-label="Show next 7 available days"
        disabled={!canShowNewerDates}
        onClick={onShowNewerDates}
      >
        <span aria-hidden="true">→</span>
      </button>
    </div>
  )
}
