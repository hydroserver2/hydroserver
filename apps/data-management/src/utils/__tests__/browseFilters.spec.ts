import { describe, expect, it } from 'vitest'
import { filterThingMarkers } from '../browseFilters'

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
    expect(filterThingMarkers(things as any, [], []).map((thing) => thing.id)).toEqual(
      ['thing-1', 'thing-2', 'thing-3']
    )
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
      filterThingMarkers(things as any, selectedWorkspaces as any, ['Spring']).map(
        (thing) => thing.id
      )
    ).toEqual(['thing-3'])
  })
})
