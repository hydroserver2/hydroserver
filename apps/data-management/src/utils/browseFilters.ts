import type { Workspace } from '@hydroserver/client'
import type { MonitoringSiteMapSummary } from '@/types'
import type { LocationQuery } from 'vue-router'

export type MarkerColorMode = 'none' | 'workspace' | 'type' | 'metadata'

export interface BrowseFilterRouteState {
  siteIds: string[]
  searchText: string
  workspaceIds: string[]
  siteTypes: string[]
  tagKey: string
  tagValues: string[]
  mySites: boolean | null
  colorBy: MarkerColorMode | null
  colorTagKey: string
  drawer: boolean | null
}

export interface BrowseFilterSelectionState {
  siteId?: string | null
  searchText?: string | null
  workspaceIds: string[]
  siteTypes: string[]
  tagKey?: string | null
  tagValues?: string[]
  mySites?: boolean
  colorBy?: MarkerColorMode
  colorTagKey?: string | null
  drawer?: boolean
}

const BROWSE_FILTER_QUERY_KEYS = [
  'selectedSite',
  'search',
  'workspaces',
  'siteTypes',
  'tagKey',
  'tagValues',
  'mySites',
  'colorBy',
  'colorTagKey',
  'colorByTag',
  'drawer',
]

const queryValues = (value: unknown): string[] => {
  const values = Array.isArray(value) ? value : [value]

  return values
    .flatMap((item) => (typeof item === 'string' ? item.split(',') : []))
    .map((item) => item.trim())
    .filter(Boolean)
}

// Free-text search is a single value that may legitimately contain commas, so
// it must not be run through queryValues() (which splits on commas).
const querySingleValue = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const queryExactValues = (value: unknown): string[] => {
  const values = Array.isArray(value) ? value : [value]

  return values
    .map((item) => (typeof item === 'string' ? item.trim() : ''))
    .filter(Boolean)
}

const uniqueValues = (values: string[]) => [...new Set(values)]

const readQueryValues = (query: LocationQuery, keys: string[]): string[] =>
  uniqueValues(keys.flatMap((key) => queryValues(query[key])))

const readExactQueryValues = (query: LocationQuery, keys: string[]): string[] =>
  uniqueValues(keys.flatMap((key) => queryExactValues(query[key])))

const parseBooleanQuery = (value: unknown): boolean | null => {
  const [raw] = queryValues(value)
  if (!raw) return null

  const normalized = raw.toLowerCase()
  if (['1', 'true', 'yes'].includes(normalized)) return true
  if (['0', 'false', 'no'].includes(normalized)) return false

  return null
}

const parseMarkerColorMode = (value: unknown): MarkerColorMode | null => {
  const mode = querySingleValue(value)
  return mode === 'none' ||
    mode === 'workspace' ||
    mode === 'type' ||
    mode === 'metadata'
    ? mode
    : null
}

const queryArray = (values: string[]): string | string[] | undefined => {
  const normalized = uniqueValues(values)
  if (!normalized.length) return undefined
  return normalized.length === 1 ? normalized[0] : normalized
}

export function parseBrowseFilterQuery(
  query: LocationQuery
): BrowseFilterRouteState {
  return {
    siteIds: readQueryValues(query, ['selectedSite']),
    searchText: querySingleValue(query.search),
    workspaceIds: readQueryValues(query, ['workspaces']),
    siteTypes: readExactQueryValues(query, ['siteTypes']),
    tagKey: querySingleValue(query.tagKey),
    tagValues: readExactQueryValues(query, ['tagValues']),
    mySites: parseBooleanQuery(query.mySites),
    colorBy: parseMarkerColorMode(query.colorBy),
    colorTagKey: querySingleValue(query.colorTagKey),
    drawer: parseBooleanQuery(query.drawer),
  }
}

export function buildBrowseFilterQuery(
  query: LocationQuery,
  state: BrowseFilterSelectionState
): LocationQuery {
  const nextQuery: LocationQuery = { ...query }

  BROWSE_FILTER_QUERY_KEYS.forEach((key) => delete nextQuery[key])

  const siteIds = state.siteId ? [state.siteId] : []
  const searchText = state.searchText?.trim()
  const sites = queryArray(siteIds)
  const workspaces = queryArray(state.workspaceIds)
  const siteTypes = queryArray(state.siteTypes)
  const tagKey = state.tagKey?.trim()
  const tagValues = queryArray(state.tagValues ?? [])
  const colorTagKey = state.colorTagKey?.trim()

  if (sites !== undefined) nextQuery.selectedSite = sites
  if (searchText) nextQuery.search = searchText
  if (workspaces !== undefined) nextQuery.workspaces = workspaces
  if (siteTypes !== undefined) nextQuery.siteTypes = siteTypes
  if (tagKey) nextQuery.tagKey = tagKey
  if (tagValues !== undefined) nextQuery.tagValues = tagValues
  if (state.mySites) nextQuery.mySites = '1'
  if (state.colorBy && state.colorBy !== 'none')
    nextQuery.colorBy = state.colorBy
  if (state.colorBy === 'metadata' && colorTagKey)
    nextQuery.colorTagKey = colorTagKey
  if (state.drawer === false) nextQuery.drawer = '0'

  return nextQuery
}

export function filterMonitoringSiteMarkers(
  monitoringSites: MonitoringSiteMapSummary[],
  selectedWorkspaces: Workspace[],
  selectedSiteTypes: string[],
  selectedSite?: MonitoringSiteMapSummary | null,
  tagKey = '',
  selectedTagValues: string[] = []
) {
  const selectedWorkspaceIds = new Set(
    selectedWorkspaces.map((workspace) => workspace.id)
  )

  return monitoringSites.filter((monitoringSite) => {
    const isSelectedSite = !selectedSite || monitoringSite.id === selectedSite.id
    const inSelectedWorkspace =
      selectedWorkspaceIds.size === 0 ||
      selectedWorkspaceIds.has(monitoringSite.workspaceId)
    const inSelectedSiteType =
      selectedSiteTypes.length === 0 ||
      selectedSiteTypes.includes(monitoringSite.type)
    const tagValue = tagKey ? monitoringSite.tags[tagKey] : undefined
    const hasSelectedTag =
      !tagKey ||
      (tagValue !== undefined &&
        (selectedTagValues.length === 0 || selectedTagValues.includes(tagValue)))

    return (
      isSelectedSite &&
      inSelectedWorkspace &&
      inSelectedSiteType &&
      hasSelectedTag
    )
  })
}
