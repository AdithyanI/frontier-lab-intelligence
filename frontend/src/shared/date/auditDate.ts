export const AUDIT_DATE_PARAM = 'date'

export function readAuditDate(search: string | URLSearchParams): string {
  const params = typeof search === 'string' ? new URLSearchParams(search) : search
  return params.get(AUDIT_DATE_PARAM)?.trim() ?? ''
}

export function withAuditDate(path: string, date: string): string {
  if (!date) return path

  const [pathAndSearch, hash = ''] = path.split('#', 2)
  const [pathname, search = ''] = pathAndSearch.split('?', 2)
  const params = new URLSearchParams(search)
  params.set(AUDIT_DATE_PARAM, date)
  const nextSearch = params.toString()
  return `${pathname}${nextSearch ? `?${nextSearch}` : ''}${hash ? `#${hash}` : ''}`
}

export function setAuditDateParam(
  current: URLSearchParams,
  date: string,
  remove: string[] = [],
): URLSearchParams {
  const next = new URLSearchParams(current)
  if (date) next.set(AUDIT_DATE_PARAM, date)
  else next.delete(AUDIT_DATE_PARAM)
  for (const key of remove) next.delete(key)
  return next
}
