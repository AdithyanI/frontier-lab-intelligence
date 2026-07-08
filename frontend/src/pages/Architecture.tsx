import { useEffect, useRef, useState } from 'react'
import { marked } from 'marked'
import mermaid from 'mermaid'
import { getJSON } from '../api'

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  themeVariables: {
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSize: '13px',
  },
})

export default function Architecture() {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getJSON<{ markdown: string }>('/api/architecture')
      .then(async (d) => {
        const renderer = new marked.Renderer()
        const base = renderer.code.bind(renderer)
        renderer.code = (token) => {
          if (token.lang === 'mermaid') {
            return `<div class="mermaid-block"><pre class="mermaid">${token.text}</pre></div>`
          }
          return base(token)
        }
        setHtml(await marked.parse(d.markdown, { renderer }))
      })
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (html && ref.current) {
      void mermaid.run({ nodes: ref.current.querySelectorAll('pre.mermaid') })
    }
  }, [html])

  return (
    <>
      {error && <div className="error-note">Could not load doc: {error}</div>}
      {!html && !error && <div className="skeleton" style={{ width: '50%' }} />}
      {html && (
        <div
          className="doc"
          ref={ref}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )}
    </>
  )
}
