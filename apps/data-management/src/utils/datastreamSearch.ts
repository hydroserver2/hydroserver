export const DATASTREAM_QUALIFIER_KEYS = [
  'workspace',
  'site',
  'observed-property',
  'processing-level',
] as const

export type DatastreamQualifierKey = (typeof DATASTREAM_QUALIFIER_KEYS)[number]

export type DatastreamQueryFilters = Record<DatastreamQualifierKey, string[]>

export const DATASTREAM_SORT_KEYS = ['name', 'updated', 'observations'] as const
export type DatastreamSortKey = (typeof DATASTREAM_SORT_KEYS)[number]
export type DatastreamSortOrder = 'asc' | 'desc'
export type DatastreamSort = {
  key: DatastreamSortKey
  order: DatastreamSortOrder
}

const qualifierPattern = () =>
  /(workspace|site|observed-property|processing-level|sort):(?:"([^"]*)"|(\S+))/gi

const parseDatastreamSort = (value: string): DatastreamSort | null => {
  const [key, order] = value.toLocaleLowerCase().split('-')
  if (
    !DATASTREAM_SORT_KEYS.includes(key as DatastreamSortKey) ||
    (order !== 'asc' && order !== 'desc')
  ) {
    return null
  }

  return { key: key as DatastreamSortKey, order }
}

export const quoteDatastreamQualifier = (value: string) =>
  /\s/.test(value) ? `"${value}"` : value

export function parseDatastreamQuery(raw: string) {
  const filters: DatastreamQueryFilters = {
    workspace: [],
    site: [],
    'observed-property': [],
    'processing-level': [],
  }
  const textParts: string[] = []
  let sort: DatastreamSort | null = null
  const pattern = qualifierPattern()
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(raw))) {
    textParts.push(raw.slice(lastIndex, match.index))
    const key = match[1].toLocaleLowerCase()
    const value = (match[2] ?? match[3] ?? '').trim()
    if (key === 'sort') {
      const parsedSort = parseDatastreamSort(value)
      if (parsedSort) sort = parsedSort
      else textParts.push(match[0])
    } else if (value) {
      filters[key as DatastreamQualifierKey].push(value)
    }
    lastIndex = pattern.lastIndex
  }
  textParts.push(raw.slice(lastIndex))

  return {
    filters,
    sort,
    text: textParts.join(' ').replace(/\s+/g, ' ').trim(),
  }
}

export function serializeDatastreamQuery(
  filters: DatastreamQueryFilters,
  text: string,
  sort: DatastreamSort | null = null
) {
  return [
    ...DATASTREAM_QUALIFIER_KEYS.flatMap((key) =>
      filters[key].map((value) => `${key}:${quoteDatastreamQualifier(value)}`)
    ),
    ...(sort ? [`sort:${sort.key}-${sort.order}`] : []),
    ...(text.trim() ? [text.trim()] : []),
  ].join(' ')
}
