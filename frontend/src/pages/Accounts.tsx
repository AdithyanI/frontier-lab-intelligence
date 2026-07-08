import { useEffect, useState } from 'react'
import { getJSON, type Account } from '../api'

const PAGE = 100

export default function Accounts() {
  const [rows, setRows] = useState<Account[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load(query: string, offset: number) {
    setLoading(true)
    try {
      const d = await getJSON<{ total: number; accounts: Account[] }>(
        `/api/accounts?limit=${PAGE}&offset=${offset}&q=${encodeURIComponent(query)}`,
      )
      setTotal(d.total)
      setRows((prev) => (offset === 0 ? d.accounts : [...prev, ...d.accounts]))
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const t = setTimeout(() => void load(q, 0), q ? 250 : 0)
    return () => clearTimeout(t)
  }, [q])

  return (
    <>
      <h1 className="page-title">Accounts</h1>
      <p className="page-sub">
        Every X account observed in the Digg graph pull — ranked accounts plus
        the followers they surfaced. Candidates, not confirmed people: the
        registry review decides who becomes an entity.
      </p>
      <div className="table-tools">
        <input
          className="search"
          type="search"
          placeholder="Search handle or name…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search accounts"
        />
        {total !== null && (
          <span className="table-count">
            {rows.length.toLocaleString('en-US')} of {total.toLocaleString('en-US')}
          </span>
        )}
      </div>
      {error && <div className="error-note">Could not load accounts: {error}</div>}
      <table>
        <thead>
          <tr>
            <th className="num">Digg rank</th>
            <th>Account</th>
            <th>Role</th>
            <th className="num">Tracked followers</th>
            <th className="num">X followers</th>
            <th>Bio</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => (
            <tr key={a.id}>
              <td className="num">{a.digg_rank ?? '—'}</td>
              <td className="handle">
                <a
                  href={`https://x.com/${a.handle}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  @{a.handle}
                </a>
                {a.display_name && (
                  <div className="muted" style={{ fontSize: 12.5, fontWeight: 400 }}>
                    {a.display_name}
                  </div>
                )}
              </td>
              <td>{a.role ?? <span className="muted">—</span>}</td>
              <td className="num">{a.tracked_followers.toLocaleString('en-US')}</td>
              <td className="num">
                {a.followers_count?.toLocaleString('en-US') ?? '—'}
              </td>
              <td>
                <div className="bio">{a.bio}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {total !== null && rows.length < total && (
        <button
          className="load-more"
          onClick={() => void load(q, rows.length)}
          disabled={loading}
        >
          {loading ? 'Loading…' : `Load ${Math.min(PAGE, total - rows.length)} more`}
        </button>
      )}
    </>
  )
}
