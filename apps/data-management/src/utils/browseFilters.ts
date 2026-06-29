import type { Workspace } from '@hydroserver/client'
import type { ThingMarker } from '@/types'
import type { LocationQuery } from 'vue-router'

export interface BrowseFilterRouteState {
  siteIds: string[]
  searchText: string
  workspaceIds: string[]
  siteTypes: string[]
  drawer: boolean | null
}

export interface BrowseFilterSelectionState {
  siteId?: string | null
  searchText?: string | null
  workspaceIds: string[]
  siteTypes: string[]
  drawer?: boolean
}

const BROWSE_FILTER_QUERY_KEYS = [
  'selectedSite',
  'search',
  'workspaces',
  'siteTypes',
  'drawer',
]

const queryValues = (value: unknown): string[] => {
  const values = Array.isArray(value) ? value : [value]

  return values
    .flatMap((item) => (typeof item === 'string' ? item.split(',') : []))
    .map((item) => item.trim())
    .filter(Boolean)
}

const uniqueValues = (values: string[]) => [...new Set(values)]

const readQueryValues = (query: LocationQuery, keys: string[]): string[] =>
  uniqueValues(keys.flatMap((key) => queryValues(query[key])))

const parseBooleanQuery = (value: unknown): boolean | null => {
  const [raw] = queryValues(value)
  if (!raw) return null

  const normalized = raw.toLowerCase()
  if (['1', 'true', 'yes'].includes(normalized)) return true
  if (['0', 'false', 'no'].includes(normalized)) return false

  return null
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
    searchText: queryValues(query.search)[0] ?? '',
    workspaceIds: readQueryValues(query, ['workspaces']),
    siteTypes: readQueryValues(query, ['siteTypes']),
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

  if (sites !== undefined) nextQuery.selectedSite = sites
  if (searchText) nextQuery.search = searchText
  if (workspaces !== undefined) nextQuery.workspaces = workspaces
  if (siteTypes !== undefined) nextQuery.siteTypes = siteTypes
  if (state.drawer === false) nextQuery.drawer = '0'

  return nextQuery
}

export function filterThingMarkers(
  things: ThingMarker[],
  selectedWorkspaces: Workspace[],
  selectedSiteTypes: string[],
  selectedSite?: ThingMarker | null
) {
  const selectedWorkspaceIds = new Set(
    selectedWorkspaces.map((workspace) => workspace.id)
  )

  return things.filter((thing) => {
    const isSelectedSite = !selectedSite || thing.id === selectedSite.id
    const inSelectedWorkspace =
      selectedWorkspaceIds.size === 0 ||
      selectedWorkspaceIds.has(thing.workspaceId)
    const inSelectedSiteType =
      selectedSiteTypes.length === 0 ||
      selectedSiteTypes.includes(thing.siteType)

    return isSelectedSite && inSelectedWorkspace && inSelectedSiteType
  })
}
