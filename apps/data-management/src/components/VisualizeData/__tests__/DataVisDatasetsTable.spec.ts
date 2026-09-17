import { createPinia, setActivePinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mdiMapMarkerOutline } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import DataVisDatasetsTable from '../DataVisDatasetsTable.vue'

vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({
    fetchGraphSeries: vi.fn(),
    fetchGraphSeriesData: vi.fn(),
  }),
}))

describe('DataVisDatasetsTable query hydration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('hydrates the site qualifier while a deep-linked datastream is plotted', () => {
    const store = useDataVisStore()
    const site = {
      id: 'site-1',
      name: 'Current Site',
      workspaceId: 'workspace-1',
    }
    const datastream = {
      id: 'datastream-1',
      name: 'Discharge',
      monitoringSiteId: site.id,
      phenomenonBeginTime: '2026-01-01T00:00:00.000Z',
      phenomenonEndTime: '2026-02-01T00:00:00.000Z',
    }
    store.monitoringSites = [site] as any
    store.datastreams = [datastream] as any
    store.selectedMonitoringSites = [site] as any
    store.plottedDatastreams = [datastream] as any

    shallowMount(DataVisDatasetsTable)

    expect(store.tableSearch).toBe('site:"Current Site"')
    expect(store.selectedMonitoringSites.map((item) => item.id)).toEqual([
      site.id,
    ])
  })

  it('links a datastream row to its site details page', () => {
    const store = useDataVisStore()
    const site = {
      id: 'site-1',
      name: 'Current Site',
      workspaceId: 'workspace-1',
    }
    const datastream = {
      id: 'datastream-1',
      name: 'Discharge',
      monitoringSiteId: site.id,
      phenomenonBeginTime: '2026-01-01T00:00:00.000Z',
      phenomenonEndTime: '2026-02-01T00:00:00.000Z',
    }
    store.monitoringSites = [site] as any
    store.datastreams = [datastream] as any

    const wrapper = shallowMount(DataVisDatasetsTable, {
      global: {
        stubs: {
          VBtnIcon: true,
          VMenu: {
            template:
              '<div><slot name="activator" :props="{}" /><slot /></div>',
          },
          VList: { template: '<div><slot /></div>' },
        },
      },
    })
    const link = wrapper
      .findAllComponents({ name: 'VListItem' })
      .find(
        (item) =>
          item.attributes('data-testid') === 'datavis-view-site-datastream-1'
      )

    expect(link).toBeDefined()
    expect(link?.props('title')).toBe('View on site details page')
    expect(link?.props('prependIcon')).toBe(mdiMapMarkerOutline)
    expect(link?.props('to')).toEqual({
      name: 'SiteDetails',
      params: { id: site.id },
      query: { datastream: datastream.id },
    })
  })
})
