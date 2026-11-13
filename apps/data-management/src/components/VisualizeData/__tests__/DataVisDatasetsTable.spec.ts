import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mdiMapMarkerOutline } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import { useWorkspaceStore } from '@/store/workspaces'
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

  it('copies the current URL', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const wrapper = shallowMount(DataVisDatasetsTable)

    await wrapper.get('[data-testid="copy-state-url"]').trigger('click')

    expect(writeText).toHaveBeenCalledWith(window.location.href)
    wrapper.unmount()
    vi.unstubAllGlobals()
  })

  it('clears plotted datastreams and restores the full table', async () => {
    const store = useDataVisStore()
    const datastream = { id: 'stream-1', name: 'Discharge' }
    store.datastreams = [datastream] as any
    store.plottedDatastreams = [datastream] as any
    const wrapper = shallowMount(DataVisDatasetsTable)

    await wrapper.get('[data-testid="toggle-selected-datastreams"]').trigger('click')
    await wrapper.get('[data-testid="clear-selected-datastreams-button"]').trigger('click')

    expect(store.plottedDatastreams).toEqual([])
    expect(wrapper.find('[data-testid="clear-selected-datastreams-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="plot-datastream-stream-1"]').exists()).toBe(true)
    wrapper.unmount()
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

  it('restores every query selection when lookup data arrives after the query', async () => {
    const store = useDataVisStore()
    store.tableSearch =
      'workspace:"River Network" site:"Logan River" observed-property:"Water temperature" unit:"Degrees Celsius" method:"Shielded sensor" processing-level:"Quality controlled"'
    const wrapper = shallowMount(DataVisDatasetsTable)
    expect(store.selectedWorkspaces).toEqual([])

    store.workspaces = [{ id: 'workspace-1', name: 'River Network' }] as any
    store.monitoringSites = [
      { id: 'site-1', name: 'Logan River', workspaceId: 'workspace-1' },
    ] as any
    store.observedProperties = [
      { id: 'property-1', name: 'Water temperature' },
    ] as any
    store.processingLevels = [
      { id: 'level-1', name: 'Quality controlled' },
    ] as any
    store.datastreams = [
      {
        id: 'stream-1',
        name: 'Temperature',
        monitoringSiteId: 'site-1',
        observedPropertyId: 'property-1',
        processingLevelId: 'level-1',
        unitName: 'Degrees Celsius',
        methodName: 'Shielded sensor',
      },
    ] as any
    await flushPromises()

    expect(store.selectedWorkspaces.map((item) => item.id)).toEqual([
      'workspace-1',
    ])
    expect(store.selectedMonitoringSites.map((item) => item.id)).toEqual([
      'site-1',
    ])
    expect(store.selectedObservedPropertyNames).toEqual(['Water temperature'])
    expect(store.selectedUnitNames).toEqual(['Degrees Celsius'])
    expect(store.selectedMethodNames).toEqual(['Shielded sensor'])
    expect(store.selectedProcessingLevelNames).toEqual(['Quality controlled'])
    expect(store.filteredDatastreams.map((item) => item.id)).toEqual([
      'stream-1',
    ])
    wrapper.unmount()
  })

  it('resolves public workspace filters independently of management memberships', () => {
    const management = useWorkspaceStore()
    management.setWorkspaces([
      { id: 'member-workspace', name: 'My workspace' } as any,
    ])
    const store = useDataVisStore()
    store.workspaces = [
      { id: 'public-workspace', name: 'Public river network' },
      ...management.workspaces,
    ] as any
    store.monitoringSites = [
      { id: 'site-1', name: 'Logan River', workspaceId: 'public-workspace' },
    ] as any
    store.datastreams = [
      { id: 'stream-1', name: 'Discharge', monitoringSiteId: 'site-1' },
    ] as any
    store.tableSearch = 'workspace:"Public river network"'
    const wrapper = shallowMount(DataVisDatasetsTable)

    expect(store.selectedWorkspaces.map((item) => item.id)).toEqual([
      'public-workspace',
    ])
    expect(store.filteredDatastreams.map((item) => item.id)).toEqual([
      'stream-1',
    ])
    expect(management.workspaces.map((item) => item.id)).toEqual([
      'member-workspace',
    ])
    expect(management.selectedWorkspace?.id).toBe('member-workspace')
    wrapper.unmount()
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
