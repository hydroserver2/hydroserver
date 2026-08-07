import { describe, expect, it } from 'vitest'
import {
  addColorToMarkers,
  addSiteTypeColorToMarkers,
  addWorkspaceColorToMarkers,
} from '@/utils/maps/markers'

const sites = [
  {
    id: 'site-1',
    workspaceId: 'workspace-a',
    type: 'Stream',
    tags: [{ key: 'Network', value: 'Primary' }],
  },
  {
    id: 'site-2',
    workspaceId: 'workspace-a',
    type: 'Well',
    tags: [{ key: 'Network', value: 'Secondary' }],
  },
  {
    id: 'site-3',
    workspaceId: 'workspace-b',
    type: 'Stream',
    tags: [{ key: 'Network', value: 'Primary' }],
  },
] as any[]

describe('map marker colors', () => {
  it('assigns the same color to sites in the same workspace', () => {
    const colored = addWorkspaceColorToMarkers(sites)

    expect(colored[0].tagValue).toBe('workspace-a')
    expect(colored[0].color).toEqual(colored[1].color)
    expect(colored[2].tagValue).toBe('workspace-b')
    expect(colored[2].color).not.toEqual(colored[0].color)
  })

  it('assigns colors by metadata tag value independently of workspace', () => {
    const colored = addColorToMarkers(sites, 'Network')

    expect(colored[0].tagValue).toBe('Primary')
    expect(colored[0].color).toEqual(colored[2].color)
    expect(colored[1].tagValue).toBe('Secondary')
    expect(colored[1].color).not.toEqual(colored[0].color)
  })

  it('assigns colors by site type independently of workspace', () => {
    const colored = addSiteTypeColorToMarkers(sites)

    expect(colored[0].tagValue).toBe('Stream')
    expect(colored[0].color).toEqual(colored[2].color)
    expect(colored[1].tagValue).toBe('Well')
    expect(colored[1].color).not.toEqual(colored[0].color)
  })
})
