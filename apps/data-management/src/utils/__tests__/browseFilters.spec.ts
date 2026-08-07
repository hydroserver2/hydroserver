import { describe, expect, it } from 'vitest'
import {
  buildBrowseFilterQuery,
  filterMonitoringSiteMarkers,
  parseBrowseFilterQuery,
} from '../browseFilters'

describe('filterMonitoringSiteMarkers', () => {
  const monitoringSites = [
    {
      id: 'monitoringSite-1',
      workspaceId: 'workspace-1',
      name: 'Lake Site',
      type: 'Lake',
      isPrivate: false,
      latitude: 41.7,
      longitude: -111.8,
      code: 'LAKE-1',
      tags: [{ key: 'Network', value: 'Primary' }],
    },
    {
      id: 'monitoringSite-2',
      workspaceId: 'workspace-2',
      name: 'River Site',
      type: 'Stream',
      isPrivate: false,
      latitude: 41.8,
      longitude: -111.7,
      code: 'RIVER-1',
      tags: [{ key: 'Network', value: 'Secondary' }],
    },
    {
      id: 'monitoringSite-3',
      workspaceId: 'workspace-1',
      name: 'Spring Site',
      type: 'Spring',
      isPrivate: false,
      latitude: 41.9,
      longitude: -111.6,
      code: 'SPRING-1',
      tags: [{ key: 'Network', value: 'Primary' }],
    },
    {
      id: 'monitoringSite-4',
      workspaceId: 'workspace-1',
      name: 'Reservoir Site',
      type: 'Lake, Reservoir, Impoundment',
      isPrivate: false,
      latitude: 42.0,
      longitude: -111.5,
      code: 'RESERVOIR-1',
      tags: [{ key: 'Region', value: 'North' }],
    },
  ]

  it('returns all monitoringSites when no filters are selected', () => {
    expect(
      filterMonitoringSiteMarkers(monitoringSites as any, [], []).map((monitoringSite) => monitoringSite.id)
    ).toEqual(['monitoringSite-1', 'monitoringSite-2', 'monitoringSite-3', 'monitoringSite-4'])
  })

  it('filters monitoringSites by selected workspaces', () => {
    const selectedWorkspaces = [{ id: 'workspace-1', name: 'Workspace 1' }]

    expect(
      filterMonitoringSiteMarkers(monitoringSites as any, selectedWorkspaces as any, []).map(
        (monitoringSite) => monitoringSite.id
      )
    ).toEqual(['monitoringSite-1', 'monitoringSite-3', 'monitoringSite-4'])
  })

  it('filters monitoringSites by selected site types', () => {
    expect(
      filterMonitoringSiteMarkers(monitoringSites as any, [], ['Lake', 'Stream']).map(
        (monitoringSite) => monitoringSite.id
      )
    ).toEqual(['monitoringSite-1', 'monitoringSite-2'])
  })

  it('filters monitoringSites by custom site types that contain commas', () => {
    expect(
      filterMonitoringSiteMarkers(
        monitoringSites as any,
        [],
        ['Lake, Reservoir, Impoundment']
      ).map((monitoringSite) => monitoringSite.id)
    ).toEqual(['monitoringSite-4'])
  })

  it('requires a monitoringSite to match both workspace and site type filters', () => {
    const selectedWorkspaces = [{ id: 'workspace-1', name: 'Workspace 1' }]

    expect(
      filterMonitoringSiteMarkers(monitoringSites as any, selectedWorkspaces as any, [
        'Spring',
      ]).map((monitoringSite) => monitoringSite.id)
    ).toEqual(['monitoringSite-3'])
  })

  it('filters monitoringSites by selected site', () => {
    expect(
      filterMonitoringSiteMarkers(monitoringSites as any, [], [], monitoringSites[1] as any).map(
        (monitoringSite) => monitoringSite.id
      )
    ).toEqual(['monitoringSite-2'])
  })

  it('requires a selected site to match the other filters', () => {
    const selectedWorkspaces = [{ id: 'workspace-1', name: 'Workspace 1' }]

    expect(
      filterMonitoringSiteMarkers(
        monitoringSites as any,
        selectedWorkspaces as any,
        ['Stream'],
        monitoringSites[1] as any
      ).map((monitoringSite) => monitoringSite.id)
    ).toEqual([])
  })

  it('filters monitoringSites by metadata key and optional values', () => {
    expect(
      filterMonitoringSiteMarkers(monitoringSites as any, [], [], undefined, 'Network').map(
        (monitoringSite) => monitoringSite.id
      )
    ).toEqual(['monitoringSite-1', 'monitoringSite-2', 'monitoringSite-3'])

    expect(
      filterMonitoringSiteMarkers(monitoringSites as any, [], [], undefined, 'Network', [
        'Primary',
      ]).map((monitoringSite) => monitoringSite.id)
    ).toEqual(['monitoringSite-1', 'monitoringSite-3'])
  })
})

describe('parseBrowseFilterQuery', () => {
  it('reads canonical query params', () => {
    expect(
      parseBrowseFilterQuery({
        selectedSite: 'monitoringSite-1',
        search: 'Logan',
        workspaces: ['workspace-1', 'workspace-2'],
        siteTypes: ['Lake', 'Stream'],
        tagKey: 'Network',
        tagValues: ['Primary', 'Secondary'],
        mySites: '1',
        colorBy: 'metadata',
        colorTagKey: 'Network',
        drawer: '0',
      })
    ).toEqual({
      siteIds: ['monitoringSite-1'],
      searchText: 'Logan',
      workspaceIds: ['workspace-1', 'workspace-2'],
      siteTypes: ['Lake', 'Stream'],
      tagKey: 'Network',
      tagValues: ['Primary', 'Secondary'],
      mySites: true,
      colorBy: 'metadata',
      colorTagKey: 'Network',
      drawer: false,
    })
  })

  it('deduplicates canonical values and accepts comma-separated non-site-type lists', () => {
    expect(
      parseBrowseFilterQuery({
        selectedSite: ['monitoringSite-1', 'monitoringSite-1'],
        workspaces: 'workspace-1,workspace-2',
        siteTypes: ['Lake', 'Lake'],
        search: 'Logan',
        drawer: 'yes',
      })
    ).toEqual({
      siteIds: ['monitoringSite-1'],
      searchText: 'Logan',
      workspaceIds: ['workspace-1', 'workspace-2'],
      siteTypes: ['Lake'],
      tagKey: '',
      tagValues: [],
      mySites: null,
      colorBy: null,
      colorTagKey: '',
      drawer: true,
    })
  })

  it('preserves commas in site types because custom site type names can contain commas', () => {
    expect(
      parseBrowseFilterQuery({
        siteTypes: 'Lake, Reservoir, Impoundment',
      }).siteTypes
    ).toEqual(['Lake, Reservoir, Impoundment'])
  })

  it('returns null for an absent or unrecognized drawer state', () => {
    expect(parseBrowseFilterQuery({ drawer: 'maybe' }).drawer).toBeNull()
    expect(parseBrowseFilterQuery({}).drawer).toBeNull()
    expect(parseBrowseFilterQuery({ colorBy: 'maybe' }).colorBy).toBeNull()
  })

  it('accepts site type marker coloring', () => {
    expect(parseBrowseFilterQuery({ colorBy: 'type' }).colorBy).toBe(
      'type'
    )
  })

  it('preserves commas in the search text instead of truncating', () => {
    const searchText = 'Logan, UT'
    const query = buildBrowseFilterQuery(
      {},
      { searchText, workspaceIds: [], siteTypes: [] }
    )

    expect(parseBrowseFilterQuery(query).searchText).toBe(searchText)
  })

  it('preserves comma-containing site types through query round trips', () => {
    const type = 'Lake, Reservoir, Impoundment'
    const query = buildBrowseFilterQuery(
      {},
      { searchText: '', workspaceIds: [], siteTypes: [type] }
    )

    expect(parseBrowseFilterQuery(query).siteTypes).toEqual([type])
  })
})

describe('buildBrowseFilterQuery', () => {
  it('writes selected Browse state to canonical query params and omits an open drawer', () => {
    expect(
      buildBrowseFilterQuery(
        {},
        {
          siteId: 'monitoringSite-1',
          searchText: 'Logan',
          workspaceIds: ['workspace-1', 'workspace-2'],
          siteTypes: ['Lake'],
          tagKey: 'Network',
          tagValues: ['Primary', 'Secondary'],
          mySites: true,
          colorBy: 'metadata',
          colorTagKey: 'Network',
          drawer: true,
        }
      )
    ).toEqual({
      selectedSite: 'monitoringSite-1',
      search: 'Logan',
      workspaces: ['workspace-1', 'workspace-2'],
      siteTypes: 'Lake',
      tagKey: 'Network',
      tagValues: ['Primary', 'Secondary'],
      mySites: '1',
      colorBy: 'metadata',
      colorTagKey: 'Network',
    })
  })

  it('removes stale Browse query params while preserving unrelated query params', () => {
    expect(
      buildBrowseFilterQuery(
        {
          selectedSite: 'monitoringSite-1',
          workspaces: 'workspace-1',
          siteTypes: 'Lake',
          mySites: '1',
          colorByTag: '1',
          page: '2',
        },
        {
          siteId: null,
          searchText: '',
          workspaceIds: [],
          siteTypes: [],
          tagKey: '',
          tagValues: [],
          mySites: false,
          colorBy: 'none',
          colorTagKey: '',
          drawer: false,
        }
      )
    ).toEqual({
      page: '2',
      drawer: '0',
    })
  })
})
