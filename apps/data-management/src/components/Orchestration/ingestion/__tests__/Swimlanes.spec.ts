import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Swimlanes from '../Swimlanes.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'

const { datastreamsMock, monitoringSitesMock } = vi.hoisted(() => ({
  datastreamsMock: vi.fn(),
  monitoringSitesMock: vi.fn(),
}))

vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()
  return {
    ...actual,
    default: {
      ...actual.default,
      datastreams: { listAllItems: datastreamsMock },
      monitoringSites: { listAllItems: monitoringSitesMock },
    },
  }
})

describe('ingestion mapping targets', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    useWorkspaceStore().setWorkspaces([
      { id: 'workspace-1', name: 'Workspace 1' } as any,
    ])
    datastreamsMock.mockResolvedValue([
      {
        id: 'datastream-1',
        name: 'Water temperature',
        monitoringSiteId: 'site-1',
      },
    ])
    monitoringSitesMock.mockResolvedValue([
      { id: 'site-1', name: 'River station' },
    ])
  })

  it('loads target names and site links without opening the task editor', async () => {
    const store = useOrchestrationStore()
    expect(store.workspaceDatastreams).toEqual([])
    expect(store.workspaceMonitoringSites).toEqual([])

    const wrapper = mount(Swimlanes, {
      props: {
        mappings: [
          {
            id: 'mapping-1',
            etlTaskId: 'task-1',
            sourceIdentifier: 'temperature',
            targetDatastreamId: 'datastream-1',
          },
        ],
      },
      global: {
        stubs: {
          'v-icon': true,
          'v-menu': {
            template:
              '<div><slot name="activator" :props="{}" /><slot /></div>',
          },
          'v-btn-icon': {
            props: ['disabled'],
            template: '<button :disabled="disabled" />',
          },
          'v-list': { template: '<div><slot /></div>' },
          'v-list-item': {
            name: 'VListItem',
            props: ['to', 'title'],
            template: '<div>{{ title }}</div>',
          },
        },
      },
    })
    await flushPromises()

    expect(datastreamsMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
      expand_related: true,
    })
    expect(monitoringSitesMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
      sortby: ['name'],
    })
    expect(wrapper.text()).toContain('Water temperature')
    expect(wrapper.text()).toContain('River station')
    expect(wrapper.get('button').element.disabled).toBe(false)
    const siteLink = wrapper
      .findAllComponents({ name: 'VListItem' })
      .find((item) => item.props('title') === 'View on site details page')
    expect(siteLink?.props('to')).toEqual({
      name: 'SiteDetails',
      params: { id: 'site-1' },
      query: { datastream: 'datastream-1' },
    })
    wrapper.unmount()
  })
})
