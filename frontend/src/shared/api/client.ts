export async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}

export async function postJSON<T>(
  url: string,
  body: unknown,
): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as {
      detail?: string | { message?: string; hint?: string }
    } | null
    const detail = payload?.detail
    const message = typeof detail === 'string'
      ? detail
      : [detail?.message, detail?.hint].filter(Boolean).join(' ')
    throw new Error(message || `Request failed with status ${response.status}.`)
  }
  return response.json() as Promise<T>
}

const jsonCache = new Map<string, unknown>()
const jsonRequests = new Map<string, Promise<unknown>>()

/**
 * Cache immutable/read-model API responses for the lifetime of this page.
 * Concurrent callers share one request, so route prefetch and the destination
 * page never duplicate the same expensive read.
 */
export function getCachedJSON<T>(url: string): Promise<T> {
  if (jsonCache.has(url)) return Promise.resolve(jsonCache.get(url) as T)

  const pending = jsonRequests.get(url)
  if (pending) return pending as Promise<T>

  const request = getJSON<T>(url)
    .then((value) => {
      jsonCache.set(url, value)
      return value
    })
    .finally(() => jsonRequests.delete(url))

  jsonRequests.set(url, request)
  return request
}
