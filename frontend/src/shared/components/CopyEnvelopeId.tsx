import { useState } from 'react'

export default function CopyEnvelopeId({ envelopeId }: { envelopeId: string }) {
  const [status, setStatus] = useState('')

  const copyEnvelopeId = async () => {
    try {
      await navigator.clipboard.writeText(envelopeId)
      setStatus('Copied')
    } catch {
      setStatus('Copy failed')
    }
  }

  return (
    <span className="copy-envelope-id">
      <button type="button" onClick={copyEnvelopeId}>
        Copy envelope ID
      </button>
      <span className="copy-envelope-status" role="status" aria-live="polite">
        {status}
      </span>
    </span>
  )
}
