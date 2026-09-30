import type { HsQueryQualifier } from './types'

export type QueryQualifier = Pick<HsQueryQualifier, 'key' | 'values'>

// Match known names before falling back to a single word, so spaces do not
// require quotes and text following a complete name stays a separate search.
export function queryQualifierTokens(
  raw: string,
  qualifiers: readonly QueryQualifier[]
) {
  const keys = qualifiers
    .map(({ key }) => key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  if (!keys) return []

  const pattern = new RegExp(`(?:^|\\s)(${keys}):`, 'gi')
  const tokens: {
    start: number
    end: number
    key: string
    value: string
    quoted: boolean
  }[] = []
  let match: RegExpExecArray | null
  while ((match = pattern.exec(raw))) {
    const key = match[1]!
    const start = pattern.lastIndex - key.length - 1
    const remainder = raw.slice(pattern.lastIndex)
    const quoted = remainder.startsWith('"')
    const qualifier = qualifiers.find(
      (item) => item.key.toLocaleLowerCase() === key.toLocaleLowerCase()
    )!
    const knownValue = quoted
      ? undefined
      : [...qualifier.values]
          .sort((a, b) => b.length - a.length)
          .find(
            (value) =>
              value.length > 0 &&
              remainder
                .toLocaleLowerCase()
                .startsWith(value.toLocaleLowerCase()) &&
              (!remainder[value.length] || /\s/.test(remainder[value.length]!))
          )
    const value = quoted
      ? remainder.slice(1).split('"')[0]!
      : remainder.slice(
          0,
          knownValue?.length ?? remainder.match(/^\S*/)?.[0].length ?? 0
        )
    const closingQuote = quoted && remainder[value.length + 1] === '"'
    const end =
      pattern.lastIndex + value.length + Number(quoted) + Number(closingQuote)
    tokens.push({ start, end, key, value, quoted })
    pattern.lastIndex = end
  }
  return tokens
}
