const shortDate = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
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
}: DateNavigatorProps) {
  return (
    <div className="feed-date-navigator">
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
        {dates.map((value) => (
          <button
            type="button"
            key={value.day}
            className={`feed-day${value.day === selectedDate ? ' is-active' : ''}`}
            aria-pressed={value.day === selectedDate}
            onClick={() => onSelectDate(value.day)}
          >
            <span>{shortDate.format(new Date(`${value.day}T12:00:00Z`))}</span>
            <span className="feed-day-count mono">
              {value.item_count.toLocaleString('en-US')}
            </span>
          </button>
        ))}
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
