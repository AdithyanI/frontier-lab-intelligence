import { useSearchParams } from 'react-router-dom'
import { AION_SURFACES } from './aionStack'

export default function AionStackPage() {
  const [searchParams] = useSearchParams()
  const requestedSurface = (searchParams.get('surface') || '').trim().toUpperCase()

  return (
    <section className="company-universe-view aion-stack-view" aria-label="Aion engineering context">
      <div className="company-universe-method">
        <p>
          <strong>
            {AION_SURFACES.length} surfaces of the research platform BIT&rsquo;s AI team
            operates.
          </strong>{' '}
          BIT describes Aion publicly as an agentic research platform its investment team
          uses daily, but not its internals. Every Engineering Insight points at one of
          these, so a reader always knows which part of their system a development would
          land on.
        </p>
        <p className="aion-boundary">
          Inferred from BIT&rsquo;s public AI Engineer and Data Platform roles. A map for
          judging relevance, not a claim about their private architecture.
        </p>
      </div>

      <ol className="aion-surface-list">
        {AION_SURFACES.map((surface) => (
          <li
            key={surface.id}
            id={surface.id}
            className="aion-surface"
            data-requested={surface.id === requestedSurface ? 'true' : undefined}
          >
            <span className="mono aion-surface-id">{surface.id}</span>
            <h3>{surface.name}</h3>
            <p>{surface.what}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
