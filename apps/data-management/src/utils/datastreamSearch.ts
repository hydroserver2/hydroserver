export const DATASTREAM_QUALIFIER_KEYS = [
  'workspace',
  'site',
  'property',
  'processing',
] as const

export type DatastreamQualifierKey = (typeof DATASTREAM_QUALIFIER_KEYS)[number]

export type DatastreamQueryFilters = Record<DatastreamQualifierKey, string[]>

const qualifierPattern = () =>
  /(workspace|site|property|processing):(?:"([^"]*)"|(\S+))/gi

export const quoteDatastreamQualifier = (value: string) =>
  /\s/.test(value) ? `"${value}"` : value

export function parseDatastreamQuery(raw: string) {
  const filters: DatastreamQueryFilters = {
    workspace: [],
    site: [],
    property: [],
    processing: [],
  }
  const textParts: string[] = []
  const pattern = qualifierPattern()
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(raw))) {
    textParts.push(raw.slice(lastIndex, match.index))
    const key = match[1].toLocaleLowerCase() as DatastreamQualifierKey
    const value = (match[2] ?? match[3] ?? '').trim()
    if (value) filters[key].push(value)
    lastIndex = pattern.lastIndex
  }
  textParts.push(raw.slice(lastIndex))

  return {
    filters,
    text: textParts.join(' ').replace(/\s+/g, ' ').trim(),
  }
}

export function serializeDatastreamQuery(
  filters: DatastreamQueryFilters,
  text: string
) {
  return [
    ...DATASTREAM_QUALIFIER_KEYS.flatMap((key) =>
      filters[key].map((value) => `${key}:${quoteDatastreamQualifier(value)}`)
    ),
    ...(text.trim() ? [text.trim()] : []),
  ].join(' ')
}
