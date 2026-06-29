import { describe, expect, it } from 'vitest'
import {
  buildBrowseFilterQuery,
  filterThingMarkers,
  parseBrowseFilterQuery,
} from '../browseFilters'

describe('filterThingMarkers', () => {
  const things = [
    {
      id: 'thing-1',
      workspaceId: 'workspace-1',
      name: 'Lake Site',
      siteType: 'Lake',
      isPrivate: false,
      latitude: 41.7,
      longitude: -111.8,
    },
    {
      id: 'thing-2',
      workspaceId: 'workspace-2',
      name: 'River Site',
      siteType: 'Stream',
      isPrivate: false,
      latitude: 41.8,
      longitude: -111.7,
    },
    {
      id: 'thing-3',
      workspaceId: 'workspace-1',
      name: 'Spring Site',
      siteType: 'Spring',
      isPrivate: false,
      latitude: 41.9,
      longitude: -111.6,
    },
  ]

  it('returns all things when no filters are selected', () => {
    expect(
      filterThingMarkers(things as any, [], []).map((thing) => thing.id)
    ).toEqual(['thing-1', 'thing-2', 'thing-3'])
  })

  it('filters things by selected workspaces', () => {
    const selectedWorkspaces = [{ id: 'workspace-1', name: 'Workspace 1' }]

    expect(
      filterThingMarkers(things as any, selectedWorkspaces as any, []).map(
        (thing) => thing.id
      )
    ).toEqual(['thing-1', 'thing-3'])
  })

  it('filters things by selected site types', () => {
    expect(
      filterThingMarkers(things as any, [], ['Lake', 'Stream']).map(
        (thing) => thing.id
      )
    ).toEqual(['thing-1', 'thing-2'])
  })

  it('requires a thing to match both workspace and site type filters', () => {
    const selectedWorkspaces = [{ id: 'workspace-1', name: 'Workspace 1' }]

    expect(
      filterThingMarkers(things as any, selectedWorkspaces as any, [
        'Spring',
      ]).map((thing) => thing.id)
    ).toEqual(['thing-3'])
  })

  it('filters things by selected site', () => {
    expect(
      filterThingMarkers(things as any, [], [], things[1] as any).map(
        (thing) => thing.id
      )
    ).toEqual(['thing-2'])
  })

  it('requires a selected site to match the other filters', () => {
    const selectedWorkspaces = [{ id: 'workspace-1', name: 'Workspace 1' }]

    expect(
      filterThingMarkers(
        things as any,
        selectedWorkspaces as any,
        ['Stream'],
        things[1] as any
      ).map((thing) => thing.id)
    ).toEqual([])
  })
})

describe('parseBrowseFilterQuery', () => {
  it('reads canonical query params', () => {
    expect(
      parseBrowseFilterQuery({
        selectedSite: 'thing-1',
        search: 'Logan',
        workspaces: ['workspace-1', 'workspace-2'],
        siteTypes: ['Lake', 'Stream'],
        drawer: '0',
      })
    ).toEqual({
      siteIds: ['thing-1'],
      searchText: 'Logan',
      workspaceIds: ['workspace-1', 'workspace-2'],
      siteTypes: ['Lake', 'Stream'],
      drawer: false,
    })
  })

  it('deduplicates canonical values and accepts comma-separated lists', () => {
    expect(
      parseBrowseFilterQuery({
        selectedSite: ['thing-1', 'thing-1'],
        workspaces: 'workspace-1,workspace-2',
        siteTypes: ['Lake', 'Lake'],
        search: 'Logan',
        drawer: 'yes',
      })
    ).toEqual({
      siteIds: ['thing-1'],
      searchText: 'Logan',
      workspaceIds: ['workspace-1', 'workspace-2'],
      siteTypes: ['Lake'],
      drawer: true,
    })
  })

  it('returns null for an absent or unrecognized drawer state', () => {
    expect(parseBrowseFilterQuery({ drawer: 'maybe' }).drawer).toBeNull()
    expect(parseBrowseFilterQuery({}).drawer).toBeNull()
  })
})

describe('buildBrowseFilterQuery', () => {
  it('writes selected Browse state to canonical query params and omits an open drawer', () => {
    expect(
      buildBrowseFilterQuery(
        {},
        {
          siteId: 'thing-1',
          searchText: 'Logan',
          workspaceIds: ['workspace-1', 'workspace-2'],
          siteTypes: ['Lake'],
          drawer: true,
        }
      )
    ).toEqual({
      selectedSite: 'thing-1',
      search: 'Logan',
      workspaces: ['workspace-1', 'workspace-2'],
      siteTypes: 'Lake',
    })
  })

  it('removes stale Browse query params while preserving unrelated query params', () => {
    expect(
      buildBrowseFilterQuery(
        {
          selectedSite: 'thing-1',
          workspaces: 'workspace-1',
          siteTypes: 'Lake',
          page: '2',
        },
        {
          siteId: null,
          searchText: '',
          workspaceIds: [],
          siteTypes: [],
          drawer: false,
        }
      )
    ).toEqual({
      page: '2',
      drawer: '0',
    })
  })
})
