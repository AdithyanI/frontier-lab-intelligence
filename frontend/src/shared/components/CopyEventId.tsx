import { useState } from 'react'

export default function CopyEventId({
  eventId,
  label = 'Copy Event ID',
}: {
  eventId: string
  label?: string
}) {
  const [status, setStatus] = useState('')

  const copyEventId = async () => {
    try {
      await navigator.clipboard.writeText(eventId)
      setStatus('Copied')
    } catch {
      setStatus('Copy failed')
    }
  }

  return (
    <span className="copy-event-id">
      <button type="button" onClick={copyEventId}>
        {label}
      </button>
      <span className="copy-event-status" role="status" aria-live="polite">
        {status}
      </span>
    </span>
  )
}
