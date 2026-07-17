/* Shared identity card: the one entity detail surface, opened as a native
   <dialog> from any page (Registry table rows, Ranking detail panel, …). */

import { useEffect, useRef, type ReactNode } from 'react'
import { siGithub, siRss, siX } from 'simple-icons'
import type { Entity, EntityChannel } from '../../shared/api'
import { channelLabel, typeClass, typeLabel } from './entityPresentation'

const BRAND_ICON: Record<string, string> = {
  github: siGithub.path,
  x: siX.path,
  blog: siRss.path,
}

const CHANNEL_KIND_ORDER = ['x', 'website', 'github', 'blog']

const channelKindLabel = (kind: string) => {
  const labels: Record<string, string> = {
    x: 'X',
    website: 'Website',
    github: 'GitHub',
    blog: 'Blog',
  }
  return labels[kind] ?? kind
}

function ChannelGlyph({ kind }: { kind: string }) {
  if (kind === 'website') {
    return (
      <svg
        className="ch-ico"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18" />
        <path d="M12 3a15 15 0 0 1 4 9 15 15 0 0 1-4 9 15 15 0 0 1-4-9 15 15 0 0 1 4-9Z" />
      </svg>
    )
  }
  const path = BRAND_ICON[kind]
  if (!path) return null
  return (
    <svg className="ch-ico" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d={path} />
    </svg>
  )
}

export default function EntityCard({
  entity,
  fallback = null,
  context,
  onClose,
}: {
  entity: Entity | null
  /** Header identity when the account has no Registry profile yet. */
  fallback?: { name: string; handle?: string } | null
  /** Extra caller-owned section (e.g. ranking evidence) under the header. */
  context?: ReactNode
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const open = Boolean(entity || fallback)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  if (!open) return <dialog ref={ref} className="ent-card" onClose={onClose} />

  const orderedChannels = [...(entity?.channels ?? [])].sort((left, right) => {
    const priority = (channel: EntityChannel) => {
      const index = CHANNEL_KIND_ORDER.indexOf(channel.kind)
      return index === -1 ? CHANNEL_KIND_ORDER.length : index
    }
    return priority(left) - priority(right) || left.key.localeCompare(right.key)
  })
  const channelGroups = orderedChannels.reduce<
    { kind: string; channels: EntityChannel[] }[]
  >((groups, channel) => {
    const current = groups.at(-1)
    if (current?.kind === channel.kind) {
      current.channels.push(channel)
    } else {
      groups.push({ kind: channel.kind, channels: [channel] })
    }
    return groups
  }, [])
  const cardKey = entity ? `id-${entity.id}` : `handle-${fallback?.handle ?? 'x'}`
  const titleId = `entity-card-title-${cardKey}`
  const bioId = `entity-card-bio-${cardKey}`
  const bioIsSourcePreview = /(?:\.{3}|…)$/.test(entity?.bio?.trim() ?? '')

  return (
    <dialog
      ref={ref}
      className="ent-card"
      aria-labelledby={titleId}
      aria-describedby={entity?.bio ? bioId : undefined}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
    >
      <button
        className="ent-card-close"
        type="button"
        onClick={onClose}
        aria-label="Close profile"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M6.5 6.5 17.5 17.5M17.5 6.5 6.5 17.5" />
        </svg>
      </button>

      <div className="ent-card-inner">
        <header className="ent-card-head">
          {entity ? (
            <span className={`ent-type ent-type--${typeClass(entity)}`}>
              {typeLabel(entity)}
            </span>
          ) : (
            <span className="ent-type ent-type--unknown">Discovered</span>
          )}
          <h2 id={titleId}>{entity?.name ?? fallback?.name}</h2>
        </header>

        {context}

        {entity && (
        <section className="ent-card-profile" aria-labelledby={`${bioId}-label`}>
          <div className="ent-card-label-row">
            <div className="ent-card-label" id={`${bioId}-label`}>
              Profile bio
            </div>
            {bioIsSourcePreview && (
              <span className="ent-card-source-state">Source preview</span>
            )}
          </div>
          {entity.bio ? (
            <p className="ent-card-bio" id={bioId}>
              {entity.bio}
            </p>
          ) : (
            <p className="ent-card-bio muted">No bio observed yet.</p>
          )}
          {bioIsSourcePreview && (
            <p className="ent-card-source-note">
              This snapshot ends where the source preview ends. Open the profile
              for the complete text.
            </p>
          )}
        </section>
        )}

        {entity?.registry_state === 'rejected' && entity.rejection_reason && (
          <div className="ent-card-reason ent-card-reason--rejected">
            <div className="ent-card-label">Why rejected</div>
            <p>{entity.rejection_reason}</p>
          </div>
        )}

        {entity && entity.registry_state !== 'rejected' && entity.kind_reason && (
          <div className="ent-card-reason">
            <div className="ent-card-label">Why this type</div>
            <p>{entity.kind_reason}</p>
          </div>
        )}

        {orderedChannels.length > 0 && (
          <div className="ent-card-channels">
            <div className="ent-card-label">Channels</div>
            <dl className="ent-channel-list">
              {channelGroups.map((group) => (
                <div className="ent-channel-row" key={group.kind}>
                  <dt>
                    <ChannelGlyph kind={group.kind} />
                    <span>{channelKindLabel(group.kind)}</span>
                  </dt>
                  <dd>
                    {group.channels.map((channel) =>
                      channel.url ? (
                        <a
                          className="ent-card-channel"
                          href={channel.url}
                          target="_blank"
                          rel="noreferrer"
                          key={channel.id}
                        >
                          <span>{channelLabel(channel)}</span>
                          <span className="ent-channel-go" aria-hidden="true">
                            ↗
                          </span>
                        </a>
                      ) : (
                        <span
                          className="ent-card-channel is-unavailable"
                          key={channel.id}
                        >
                          {channelLabel(channel)}
                        </span>
                      ),
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </dialog>
  )
}
