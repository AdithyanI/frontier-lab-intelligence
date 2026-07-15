const NAMED_TEXT_ENTITIES: Record<string, string> = {
  amp: '&',
  apos: "'",
  gt: '>',
  hellip: '…',
  ldquo: '“',
  lsquo: '‘',
  lt: '<',
  mdash: '—',
  middot: '·',
  nbsp: ' ',
  ndash: '–',
  quot: '"',
  rdquo: '”',
  rsquo: '’',
}

const TEXT_ENTITY_PATTERN = /&(#(?:x[\da-f]+|\d+)|[a-z][a-z\d]+);/gi

/**
 * Decode common named and numeric HTML entities into display text.
 *
 * The returned value is still rendered by React as text, so source markup is
 * never interpreted and the stored citation remains unchanged.
 */
export function decodeTextEntities(value: string): string {
  return value.replace(TEXT_ENTITY_PATTERN, (match, rawEntity: string) => {
    const entity = rawEntity.toLowerCase()
    if (!entity.startsWith('#')) return NAMED_TEXT_ENTITIES[entity] ?? match

    const isHex = entity.startsWith('#x')
    const numericValue = Number.parseInt(entity.slice(isHex ? 2 : 1), isHex ? 16 : 10)
    const isSurrogate = numericValue >= 0xd800 && numericValue <= 0xdfff
    if (
      !Number.isInteger(numericValue) ||
      numericValue <= 0 ||
      numericValue > 0x10ffff ||
      isSurrogate
    ) {
      return match
    }

    return String.fromCodePoint(numericValue)
  })
}
