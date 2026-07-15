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

// Some model/provider responses preserve Windows-1252 bytes as C1 control
// characters after JSON decoding. Browsers render those controls as missing or
// visibly broken punctuation, so normalize only the defined CP1252 positions
// at display time. The stored evidence remains byte-for-byte unchanged.
const WINDOWS_1252_CONTROLS: Record<number, string> = {
  0x80: '€',
  0x82: '‚',
  0x83: 'ƒ',
  0x84: '„',
  0x85: '…',
  0x86: '†',
  0x87: '‡',
  0x88: 'ˆ',
  0x89: '‰',
  0x8a: 'Š',
  0x8b: '‹',
  0x8c: 'Œ',
  0x8e: 'Ž',
  0x91: '‘',
  0x92: '’',
  0x93: '“',
  0x94: '”',
  0x95: '•',
  0x96: '–',
  0x97: '—',
  0x98: '˜',
  0x99: '™',
  0x9a: 'š',
  0x9b: '›',
  0x9c: 'œ',
  0x9e: 'ž',
  0x9f: 'Ÿ',
}

/**
 * Decode common named and numeric HTML entities into display text.
 *
 * The returned value is still rendered by React as text, so source markup is
 * never interpreted and the stored citation remains unchanged.
 */
export function decodeTextEntities(value: string): string {
  const normalized = value.replace(/[\u0080-\u009f]/g, (character) => (
    WINDOWS_1252_CONTROLS[character.codePointAt(0) ?? -1] ?? character
  ))

  return normalized.replace(TEXT_ENTITY_PATTERN, (match, rawEntity: string) => {
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
