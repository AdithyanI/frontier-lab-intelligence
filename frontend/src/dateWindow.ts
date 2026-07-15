export const DATE_WINDOW_SIZE = 7

export type DateWindowDirection = 'older' | 'newer'

export interface DateWindow {
  start: number
  end: number
}

export interface ShiftedDateWindow extends DateWindow {
  selectedIndex: number
}

export function getDateWindow(windowEnd: number, itemCount: number): DateWindow {
  const end = Math.min(Math.max(windowEnd, 0), itemCount)
  return {
    start: Math.max(0, end - DATE_WINDOW_SIZE),
    end,
  }
}

export function getDateWindowEndForSelection(
  itemCount: number,
  selectedIndex: number,
): number {
  const latestWindow = getDateWindow(itemCount, itemCount)
  if (
    selectedIndex < 0 ||
    selectedIndex >= itemCount ||
    selectedIndex >= latestWindow.start
  ) {
    return latestWindow.end
  }

  const windowsBack = Math.ceil(
    (latestWindow.start - selectedIndex) / DATE_WINDOW_SIZE,
  )
  return Math.max(0, itemCount - windowsBack * DATE_WINDOW_SIZE)
}

export function shiftDateWindow(
  windowEnd: number,
  itemCount: number,
  selectedIndex: number,
  direction: DateWindowDirection,
): ShiftedDateWindow {
  const current = getDateWindow(windowEnd, itemCount)
  const currentLength = current.end - current.start
  const selectedOffset =
    selectedIndex >= current.start && selectedIndex < current.end
      ? selectedIndex - current.start
      : Math.max(0, currentLength - 1)
  const nextEnd =
    direction === 'older'
      ? current.start
      : Math.min(itemCount, current.end + DATE_WINDOW_SIZE)
  const next = getDateWindow(nextEnd, itemCount)
  const nextLength = next.end - next.start

  return {
    ...next,
    selectedIndex:
      nextLength > 0
        ? Math.min(next.start + selectedOffset, next.end - 1)
        : -1,
  }
}
