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

  it('filters by a typed multi-word site name without quotes', async () => {
    const store = useDataVisStore()
    const site = {
      id: 'site-1',
      name: 'Logan River',
      workspaceId: 'workspace-1',
    }
    store.monitoringSites = [
      site,
      { ...site, id: 'site-2', name: 'Bear River' },
    ] as any
    store.datastreams = [
      { id: 'stream-1', name: 'Discharge', monitoringSiteId: 'site-1' },
      { id: 'stream-2', name: 'Discharge', monitoringSiteId: 'site-2' },
    ] as any
    const wrapper = shallowMount(DataVisDatasetsTable)
    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit('update:modelValue', 'site:Logan River')
    expect(store.selectedMonitoringSites.map((item) => item.id)).toEqual([
      'site-1',
    ])
    expect(store.filteredDatastreams.map((item) => item.id)).toEqual([
      'stream-1',
    ])
    wrapper.unmount()
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
