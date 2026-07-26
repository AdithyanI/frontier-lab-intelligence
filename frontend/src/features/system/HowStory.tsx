import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SignalFunnel, { type FunnelStage } from './SignalFunnel'
import { HOW_BEATS, SCROLL_STAGES } from './howContent'

function scrollToBeat(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function useBeatKeys(active: FunnelStage) {
  useEffect(() => {
    const order: FunnelStage[] = ['universe', ...SCROLL_STAGES]
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return
      const target = event.target as HTMLElement | null
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return
      if (document.querySelector('.how-figure-overlay')) return

      const canvas = document.querySelector('.how-canvas')
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      if (rect.bottom < window.innerHeight * 0.6 || rect.top > window.innerHeight * 0.6) return

      const next = event.key === 'ArrowDown' || event.key === 'ArrowRight' || event.key === 'j'
      const prev = event.key === 'ArrowUp' || event.key === 'ArrowLeft' || event.key === 'k'
      if (!next && !prev) return

      const index = order.indexOf(active)
      const destination = order[index + (next ? 1 : -1)]
      if (!destination) return
      event.preventDefault()
      scrollToBeat(destination)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active])
}

function useActiveStage(): FunnelStage {
  const [active, setActive] = useState<FunnelStage>('universe')

  useEffect(() => {
    let animationFrame = 0
    const update = () => {
      animationFrame = 0
      const cut = window.innerHeight * 0.5
      let current: FunnelStage = 'universe'
      for (const id of SCROLL_STAGES) {
        const element = document.getElementById(id)
        if (element && element.getBoundingClientRect().top <= cut) current = id
      }
      setActive(current)
    }
    const onScroll = () => {
      if (!animationFrame) animationFrame = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (animationFrame) cancelAnimationFrame(animationFrame)
    }
  }, [])

  return active
}

function WhyLink({ stage }: { stage: string }) {
  return (
    <button
      type="button"
      className="how-why"
      onClick={() =>
        document
          .getElementById(`why-${stage}`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    >
      Why this choice &darr;
    </button>
  )
}

function NextButton({ to }: { to: string }) {
  return (
    <button type="button" className="how-next mono" onClick={() => scrollToBeat(to)}>
      next &darr;
    </button>
  )
}

export default function HowStory({ insightsPath }: { insightsPath: string }) {
  const activeStage = useActiveStage()
  useBeatKeys(activeStage)

  return (
    <div className="how-canvas">
      <figure className="how-funnel" aria-hidden="false">
        <div className="how-funnel-sticky">
          <SignalFunnel active={activeStage} />
        </div>
      </figure>

      <div className="how-story">
        <div className="how-beat how-beat-intro" id="universe">
          <p className="how-beat-kicker mono">The problem</p>
          <h3>Almost everything is noise</h3>
          <p>
            Somewhere in the flood is the handful of developments a decision
            depends on, and attention is limited. So the system is a funnel:
            stage by stage it raises the signal-to-noise ratio, keeping the
            signal and dropping the noise, until one data source becomes two
            cited briefs.
          </p>
          <NextButton to="watch" />
          <p className="how-key-hint mono" aria-hidden="true">or use &uarr; &darr; arrow keys</p>
        </div>

        {HOW_BEATS.map((beat, index) => (
          <div className="how-beat" id={beat.id} key={beat.id}>
            <p className="how-beat-kicker mono">Stage {beat.step}</p>
            <h3>{beat.title}</h3>
            <p>{beat.text}</p>
            <WhyLink stage={beat.id} />
            <NextButton to={HOW_BEATS[index + 1]?.id ?? 'complete'} />
          </div>
        ))}

        <div className="how-beat how-beat-outro" id="complete">
          <p className="how-beat-kicker mono">The result</p>
          <h3>Two briefs, fully traceable</h3>
          <p>
            Every conclusion keeps its path back through the funnel: from
            the Insight to its sources, to the exact Event, to the original
            post or frozen document. Nothing has to be taken on trust.
          </p>
          <div className="how-beat-links">
            <Link className="how-primary-link" to={insightsPath}>Open Insights</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
