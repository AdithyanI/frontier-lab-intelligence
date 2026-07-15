import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  postJSON,
  type RegistryIntakeResult,
} from '../api'

const registryResultURL = (result: RegistryIntakeResult) => {
  const params = new URLSearchParams({ q: result.handle })
  if (result.outcome === 'rejected') params.set('group', 'rejected')
  return `/network/registry?${params}`
}

export default function AddProfile() {
  const [profile, setProfile] = useState('')
  const [mode, setMode] = useState<'screen' | 'direct'>('screen')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<RegistryIntakeResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setError(null)
    setResult(null)
    postJSON<RegistryIntakeResult>(
      '/api/registry/intake',
      { profile, mode, reason: mode === 'direct' ? reason : null },
    )
      .then(setResult)
      .catch((cause: unknown) => setError((cause as Error).message))
      .finally(() => setSubmitting(false))
  }

  return (
    <section
      className="network-view registry-intake-view"
      aria-labelledby="add-profile-title"
    >
      <h2 className="network-view-title" id="add-profile-title">Add Profile</h2>
      <p className="network-view-sub">
        Resolve one X identity, then screen it normally or record a direct,
        audited admission to the Registry.
      </p>

      <form className="registry-intake" onSubmit={submit} aria-busy={submitting}>
        <label className="registry-intake-field registry-intake-profile">
          <span>X profile</span>
          <input
            type="url"
            inputMode="url"
            placeholder="https://x.com/handle"
            value={profile}
            onChange={(event) => setProfile(event.target.value)}
            required
            autoFocus
            disabled={submitting}
          />
        </label>

        <fieldset className="registry-intake-modes">
          <legend>Admission path</legend>
          <label className={mode === 'screen' ? 'is-selected' : undefined}>
            <input
              type="radio"
              name="intake-mode"
              value="screen"
              checked={mode === 'screen'}
              onChange={() => setMode('screen')}
              disabled={submitting}
            />
            <span>
              <strong>Screen normally</strong>
              <small>
                Apply collection gates and the evidence-based Registry evaluator.
              </small>
            </span>
          </label>
          <label className={mode === 'direct' ? 'is-selected' : undefined}>
            <input
              type="radio"
              name="intake-mode"
              value="direct"
              checked={mode === 'direct'}
              onChange={() => setMode('direct')}
              disabled={submitting}
            />
            <span>
              <strong>Add directly</strong>
              <small>
                Skip relevance and follower filtering; keep identity resolution
                and audit provenance.
              </small>
            </span>
          </label>
        </fieldset>

        {mode === 'direct' && (
          <label className="registry-intake-field registry-intake-reason">
            <span>Why override the normal screen?</span>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Specific reason this source belongs in the Registry…"
              minLength={8}
              maxLength={500}
              required
              disabled={submitting}
            />
          </label>
        )}

        <div className="registry-intake-actions">
          <button
            type="submit"
            disabled={submitting || !profile || (mode === 'direct' && reason.trim().length < 8)}
          >
            {submitting
              ? 'Fetching and evaluating…'
              : mode === 'screen'
                ? 'Screen profile'
                : 'Add to Registry'}
          </button>
          <span>
            Protected profiles remain ineligible because their evidence cannot be
            collected.
          </span>
        </div>

        {error && <div className="registry-intake-error" role="alert">{error}</div>}
        {result && (
          <div className={`registry-intake-result is-${result.outcome}`} role="status">
            <strong>
              {result.outcome === 'existing'
                ? `@${result.handle} is already in the Registry.`
                : result.outcome === 'active'
                  ? `@${result.handle} is now active.`
                  : `@${result.handle} was retained in Rejected.`}
            </strong>
            <span>{result.decision_reason}</span>
            {result.entity && (
              <Link to={registryResultURL(result)}>View in Registry</Link>
            )}
          </div>
        )}
      </form>
    </section>
  )
}
