import type { Entity, EntityChannel, EntityKind } from '../../shared/api'

const typeLabels: Record<EntityKind, string> = {
  person: 'Person',
  organization: 'Organization',
  unsure: 'Unsure',
  unknown: 'Unknown',
}

export const typeLabel = (entity: Entity) =>
  entity.registry_state === 'rejected' ? 'Rejected' : typeLabels[entity.kind]

export const typeClass = (entity: Entity) =>
  entity.registry_state === 'rejected' ? 'rejected' : entity.kind

export const xHandleLabel = (channel: EntityChannel) => {
  const label = channel.label?.trim()
  return `@${label && label.toLowerCase() === channel.key ? label : channel.key}`
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
