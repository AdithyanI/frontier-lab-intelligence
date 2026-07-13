/* Shared identity card: the one entity detail surface, opened as a native
   <dialog> from any page (Registry table rows, Ranking detail panel, …). */

import { useEffect, useRef } from 'react'
import { siGithub, siRss, siX } from 'simple-icons'
import type { Entity, EntityChannel, EntityKind } from '../api'

const BRAND_ICON: Record<string, string> = {
  github: siGithub.path,
  x: siX.path,
  blog: siRss.path,
}

const TYPE_LABEL: Record<EntityKind, string> = {
  person: 'Person',
  organization: 'Organization',
  unsure: 'Unsure',
  unknown: 'Unknown',
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

export const typeLabel = (entity: Entity) =>
  entity.registry_state === 'rejected' ? 'Rejected' : TYPE_LABEL[entity.kind]

export const typeClass = (entity: Entity) =>
  entity.registry_state === 'rejected' ? 'rejected' : entity.kind

export const xHandleLabel = (channel: EntityChannel) => {
  const label = channel.label?.trim()
  return `@${label && label.toLowerCase() === channel.key ? label : channel.key}`
}

export function ChannelGlyph({ kind }: { kind: string }) {
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

export function channelLabel(channel: EntityChannel): string {
  switch (channel.kind) {
    case 'x':
      return xHandleLabel(channel)
    case 'website':
      try {
        return channel.url
          ? new URL(channel.url).hostname.replace(/^www\./, '')
          : 'Website'
      } catch {
        return 'Website'
      }
    case 'github':
      return channel.key || channel.label || 'GitHub'
    case 'blog':
      try {
        return channel.url
          ? new URL(channel.url).hostname.replace(/^www\./, '')
          : 'Feed'
      } catch {
        return 'Feed'
      }
    default:
      return channel.label || channel.key
  }
}

export default function EntityCard({
  entity,
  onClose,
}: {
  entity: Entity | null
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (entity && !dialog.open) dialog.showModal()
    if (!entity && dialog.open) dialog.close()
  }, [entity])

  if (!entity) return <dialog ref={ref} className="ent-card" onClose={onClose} />

  const orderedChannels = [...entity.channels].sort((left, right) => {
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
  const titleId = `entity-card-title-${entity.id}`
  const bioId = `entity-card-bio-${entity.id}`
  const bioIsSourcePreview = /(?:\.{3}|…)$/.test(entity.bio?.trim() ?? '')

  return (
    <dialog
      ref={ref}
      className="ent-card"
      aria-labelledby={titleId}
      aria-describedby={entity.bio ? bioId : undefined}
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
          <span className={`ent-type ent-type--${typeClass(entity)}`}>
            {typeLabel(entity)}
          </span>
          <h2 id={titleId}>{entity.name}</h2>
        </header>

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

        {entity.registry_state === 'rejected' && entity.rejection_reason && (
          <div className="ent-card-reason ent-card-reason--rejected">
            <div className="ent-card-label">Why rejected</div>
            <p>{entity.rejection_reason}</p>
          </div>
        )}

        {entity.registry_state !== 'rejected' && entity.kind_reason && (
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
