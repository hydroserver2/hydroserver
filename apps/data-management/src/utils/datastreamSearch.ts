import {
  queryQualifierTokens,
  type QueryQualifier,
} from '@hydroserver/design-system/vue'

export const DATASTREAM_QUALIFIER_KEYS = [
  'workspace',
  'site',
  'observed-property',
  'unit',
  'method',
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

export function parseDatastreamQuery(
  raw: string,
  qualifiers: readonly QueryQualifier[] = []
) {
  const filters: DatastreamQueryFilters = {
    workspace: [],
    site: [],
    'observed-property': [],
    unit: [],
    method: [],
    'processing-level': [],
  }
  const textParts: string[] = []
  let sort: DatastreamSort | null = null
  let lastIndex = 0
  const tokens = queryQualifierTokens(
    raw,
    [...DATASTREAM_QUALIFIER_KEYS, 'sort'].map((key) => ({
      key,
      values: qualifiers.find((item) => item.key === key)?.values ?? [],
    }))
  )

  for (const token of tokens) {
    textParts.push(raw.slice(lastIndex, token.start))
    const key = token.key.toLocaleLowerCase()
    const value = token.value.trim()
    if (key === 'sort') {
      const parsedSort = parseDatastreamSort(value)
      if (parsedSort) sort = parsedSort
      else textParts.push(raw.slice(token.start, token.end))
    } else if (value) {
      filters[key as DatastreamQualifierKey].push(value)
    }
    lastIndex = token.end
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
