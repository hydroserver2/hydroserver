import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mdiMapMarkerOutline } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import { useWorkspaceStore } from '@/store/workspaces'
import DataVisDatasetsTable from '../DataVisDatasetsTable.vue'

const listMock = vi.hoisted(() => vi.fn())
vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()
  return {
    ...actual,
    default: { ...actual.default, datastreams: { list: listMock } },
  }
})
vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({
    fetchGraphSeries: vi.fn(),
    fetchGraphSeriesData: vi.fn(),
  }),
}))

const site = { id: 'site-1', name: 'Logan River', workspaceId: 'workspace-1' }
const datastream = {
  id: 'datastream-1',
  name: 'Discharge',
  monitoringSiteId: site.id,
  phenomenonBeginTime: '2026-01-01T00:00:00.000Z',
  phenomenonEndTime: '2026-02-01T00:00:00.000Z',
}

function mockList(rows: object[]) {
  return listMock.mockResolvedValue({
    ok: true,
    status: 200,
    data: rows,
    meta: { numberMatched: rows.length },
  } as any)
}

// Render rows through the virtual table's slots so they can be inspected.
const VDataTableVirtual = {
  props: ['items'],
  methods: { scrollToIndex: () => {} },
  template: `<div><slot name="top" /><table><tbody><template v-for="item in items" :key="item.id"><slot name="item" :item="item" :item-ref="() => {}" /></template></tbody><slot name="tbody" :columns="[]" /></table></div>`,
}
const mountTable = () =>
  shallowMount(DataVisDatasetsTable, {
    global: {
      stubs: {
        VDataTableVirtual,
        VBtnIcon: true,
        VMenu: {
          template: '<div><slot name="activator" :props="{}" /><slot /></div>',
        },
        VList: { template: '<div><slot /></div>' },
      },
    },
  })
const rowIds = (wrapper: ReturnType<typeof mountTable>) =>
  wrapper
    .findAll('[data-testid^="plot-datastream-"]')
    .map((input) => input.attributes('data-testid')!.slice(16))

describe('DataVisDatasetsTable', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('copies the current URL', async () => {
    mockList([])
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const wrapper = mountTable()
    await wrapper.get('[data-testid="copy-state-url"]').trigger('click')
    expect(writeText).toHaveBeenCalledWith(window.location.href)
    wrapper.unmount()
  })

  it('clears selections and returns to the complete paged list', async () => {
    mockList([datastream, { ...datastream, id: 'datastream-2' }])
    const store = useDataVisStore()
    store.plottedDatastreams = [datastream] as any
    const wrapper = mountTable()
    await flushPromises()
    await wrapper
      .get('[data-testid="toggle-selected-datastreams"]')
      .trigger('click')
    await wrapper
      .get('[data-testid="clear-selected-datastreams"]')
      .trigger('click')
    expect(store.plottedDatastreams).toEqual([])
    expect(rowIds(wrapper)).toEqual(['datastream-1', 'datastream-2'])
    wrapper.unmount()
  })

  it('restores server filters when lookup data arrives after the query', async () => {
    vi.useFakeTimers()
    mockList([])
    const store = useDataVisStore()
    store.tableSearch =
      'workspace:"River Network" site:"Logan River" observed-property:"Water temperature" unit:"Degrees Celsius" method:"Shielded sensor" processing-level:"Quality controlled"'
    const wrapper = mountTable()
    expect(store.selectedWorkspaces).toEqual([])
    store.workspaces = [{ id: 'workspace-1', name: 'River Network' }] as any
    store.monitoringSites = [site] as any
    store.observedProperties = [
      { id: 'property-1', name: 'Water temperature' },
    ] as any
    store.units = [{ id: 'unit-1', name: 'Degrees Celsius' }] as any
    store.methods = [{ id: 'method-1', name: 'Shielded sensor' }] as any
    store.processingLevels = [
      { id: 'level-1', name: 'Quality controlled' },
    ] as any
    await vi.advanceTimersByTimeAsync(300)
    expect(listMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        workspaceId: ['workspace-1'],
        monitoringSiteId: ['site-1'],
        observedPropertyId: ['property-1'],
        unitId: ['unit-1'],
        methodId: ['method-1'],
        processingLevelId: ['level-1'],
        offset: 0,
      })
    )
    wrapper.unmount()
  })

  it('resolves public workspaces independently of management memberships', async () => {
    mockList([])
    const management = useWorkspaceStore()
    management.setWorkspaces([
      { id: 'member-workspace', name: 'My workspace' } as any,
    ])
    const store = useDataVisStore()
    store.workspaces = [
      { id: 'public-workspace', name: 'Public river network' },
      ...management.workspaces,
    ] as any
    store.tableSearch = 'workspace:"Public river network"'
    const wrapper = mountTable()
    await flushPromises()
    expect(store.selectedWorkspaces.map((item) => item.id)).toEqual([
      'public-workspace',
    ])
    expect(listMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ workspaceId: ['public-workspace'] })
    )
    expect(management.selectedWorkspace?.id).toBe('member-workspace')
    wrapper.unmount()
  })

  it('requests the first page filtered by a typed multi-word site name', async () => {
    vi.useFakeTimers()
    const list = mockList([datastream])
    const store = useDataVisStore()
    store.monitoringSites = [
      site,
      { ...site, id: 'site-2', name: 'Bear River' },
    ] as any
    const wrapper = mountTable()
    expect(list).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 0, limit: 25, monitoringSiteId: [] })
    )

    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit('update:modelValue', 'site:Logan River')
    await vi.advanceTimersByTimeAsync(300)

    expect(store.selectedMonitoringSites.map((item) => item.id)).toEqual([
      'site-1',
    ])
    expect(list).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 0, monitoringSiteId: ['site-1'] })
    )
  })

  it('hydrates the site qualifier while a deep-linked datastream is plotted', () => {
    mockList([])
    const store = useDataVisStore()
    store.monitoringSites = [site] as any
    store.selectedMonitoringSites = [site] as any
    store.plottedDatastreams = [datastream] as any

    mountTable()

    expect(store.tableSearch).toBe('site:"Logan River"')
    expect(store.selectedMonitoringSites.map((item) => item.id)).toEqual([
      site.id,
    ])
  })

  it('preserves legacy site filters when a bookmarked link also has search text', async () => {
    mockList([datastream])
    const store = useDataVisStore()
    store.monitoringSites = [site] as any
    store.selectedMonitoringSites = [site] as any
    store.tableSearch = 'temperature'
    const wrapper = mountTable()
    await flushPromises()
    expect(store.tableSearch).toBe('site:"Logan River" temperature')
    expect(store.selectedMonitoringSites.map((item) => item.id)).toEqual([
      site.id,
    ])
    expect(listMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        monitoringSiteId: [site.id],
        q: 'temperature',
        offset: 0,
      })
    )
    wrapper.unmount()
  })

  it('preserves plotted selections while displaying only the new filtered results', async () => {
    mockList([{ ...datastream, id: 'datastream-2' }, datastream])
    const store = useDataVisStore()
    store.monitoringSites = [site] as any
    const wrapper = mountTable()
    await flushPromises()
    expect(rowIds(wrapper)).toEqual(['datastream-2', 'datastream-1'])

    store.plottedDatastreams = [datastream] as any
    mockList([{ ...datastream, id: 'datastream-3' }])
    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit('update:modelValue', 'temperature')
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()

    expect(store.plottedDatastreams.map((item) => item.id)).toEqual([
      'datastream-1',
    ])
    expect(rowIds(wrapper)).toEqual(['datastream-3'])
    expect(wrapper.text()).toContain('1 selected for plotting (maximum 5)')
    expect(
      wrapper.findComponent({ name: 'DataVisTableFilters' }).exists()
    ).toBe(true)
    wrapper.unmount()
  })

  it('sorts selected rows numerically by observations in both directions without changing plot order', async () => {
    const selected = [
      { ...datastream, id: 'empty', valueCount: 0 },
      { ...datastream, id: 'few', valueCount: 2 },
      { ...datastream, id: 'many', valueCount: 10 },
      { ...datastream, id: 'unknown', valueCount: null },
    ]
    mockList(selected)
    const store = useDataVisStore()
    store.plottedDatastreams = selected as any
    const wrapper = mountTable()
    await flushPromises()
    await wrapper
      .get('[data-testid="toggle-selected-datastreams"]')
      .trigger('click')
    store.tableSearch = 'sort:observations-desc'
    await flushPromises()
    expect(rowIds(wrapper)).toEqual(['many', 'few', 'empty', 'unknown'])
    store.tableSearch = 'sort:observations-asc'
    await flushPromises()
    expect(rowIds(wrapper)).toEqual(['empty', 'unknown', 'few', 'many'])
    expect(store.plottedDatastreams.map((item) => item.id)).toEqual([
      'empty',
      'few',
      'many',
      'unknown',
    ])
    wrapper.unmount()
  })

  it('sorts selected rows without observations last by last updated in both directions', async () => {
    const selected = [
      { ...datastream, id: 'no-data-b', phenomenonEndTime: null },
      { ...datastream, id: 'older', phenomenonEndTime: '2025-01-01T00:00:00Z' },
      { ...datastream, id: 'no-data-a', phenomenonEndTime: null },
      { ...datastream, id: 'newer', phenomenonEndTime: '2026-01-01T00:00:00Z' },
    ]
    mockList(selected)
    const store = useDataVisStore()
    store.plottedDatastreams = selected as any
    const wrapper = mountTable()
    await flushPromises()
    await wrapper
      .get('[data-testid="toggle-selected-datastreams"]')
      .trigger('click')
    store.tableSearch = 'sort:updated-desc'
    await flushPromises()
    expect(rowIds(wrapper)).toEqual([
      'newer',
      'older',
      'no-data-a',
      'no-data-b',
    ])
    store.tableSearch = 'sort:updated-asc'
    await flushPromises()
    expect(rowIds(wrapper)).toEqual([
      'older',
      'newer',
      'no-data-a',
      'no-data-b',
    ])
    wrapper.unmount()
  })

  it('shows only the selected datastreams while "Show selected" is on', async () => {
    mockList([datastream, { ...datastream, id: 'datastream-2' }])
    const store = useDataVisStore()
    store.monitoringSites = [site] as any
    const wrapper = mountTable()
    await flushPromises()
    store.plottedDatastreams = [{ ...datastream, id: 'datastream-2' }] as any
    await flushPromises()
    const toggle = () =>
      wrapper
        .get('[data-testid="toggle-selected-datastreams"]')
        .trigger('click')

    await toggle()
    expect(rowIds(wrapper)).toEqual(['datastream-2'])
    await toggle()
    expect(rowIds(wrapper)).toEqual(['datastream-1', 'datastream-2'])
  })

  it('keeps site context for a method filter until one specific site is selected', async () => {
    vi.useFakeTimers()
    mockList([datastream])
    const store = useDataVisStore()
    store.monitoringSites = [
      site,
      { ...site, id: 'site-2', name: 'Bear River' },
    ] as any
    store.methods = [{ id: 'method-1', name: 'Shielded sensor' }] as any
    store.tableSearch = 'method:"Shielded sensor"'
    const wrapper = mountTable()
    await flushPromises()
    expect(store.selectedMonitoringSites).toEqual([])
    expect(wrapper.find('.datastream-name__thing').text()).toBe('Logan River')
    expect(wrapper.find('.datastream-name').attributes('title')).toBe(
      'Discharge @ Logan River'
    )

    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit(
        'update:modelValue',
        'site:"Logan River" method:"Shielded sensor"'
      )
    await vi.advanceTimersByTimeAsync(300)
    expect(wrapper.findAll('.datastream-name__thing')).toHaveLength(0)

    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit(
        'update:modelValue',
        'site:"Logan River" site:"Bear River" method:"Shielded sensor"'
      )
    await vi.advanceTimersByTimeAsync(300)
    expect(wrapper.find('.datastream-name__thing').text()).toBe('Logan River')
    wrapper.unmount()
  })

  it('shows site context for selections across sites despite a single-site filter', async () => {
    vi.useFakeTimers()
    const otherSite = { ...site, id: 'site-2', name: 'Bear River' }
    const otherStreams = ['datastream-2', 'datastream-3'].map((id) => ({
      ...datastream,
      id,
      monitoringSiteId: otherSite.id,
    }))
    mockList([datastream])
    const store = useDataVisStore()
    store.monitoringSites = [site, otherSite] as any
    store.selectedMonitoringSites = [site] as any
    const wrapper = mountTable()
    await flushPromises()
    expect(wrapper.findAll('.datastream-name__thing')).toHaveLength(0)
    await wrapper
      .get('[data-testid="plot-datastream-datastream-1"]')
      .setValue(true)

    mockList(otherStreams)
    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit('update:modelValue', 'site:"Bear River"')
    await vi.advanceTimersByTimeAsync(300)
    for (const stream of otherStreams)
      await wrapper
        .get(`[data-testid="plot-datastream-${stream.id}"]`)
        .setValue(true)
    expect(store.selectedMonitoringSites.map((item) => item.id)).toEqual([
      otherSite.id,
    ])
    await wrapper
      .get('[data-testid="toggle-selected-datastreams"]')
      .trigger('click')

    expect(rowIds(wrapper)).toEqual([
      'datastream-1',
      'datastream-2',
      'datastream-3',
    ])
    expect(
      wrapper.findAll('.datastream-name__thing').map((item) => item.text())
    ).toEqual(['Logan River', 'Bear River', 'Bear River'])
    expect(wrapper.find('.datastream-name').attributes('title')).toBe(
      'Discharge @ Logan River'
    )

    // Removing the only selection from the first site leaves one site's rows.
    await wrapper
      .get('[data-testid="plot-datastream-datastream-1"]')
      .setValue(false)
    expect(wrapper.findAll('.datastream-name__thing')).toHaveLength(0)

    // A filter for a different site does not describe these selected rows.
    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit('update:modelValue', 'site:"Logan River"')
    await vi.advanceTimersByTimeAsync(300)
    expect(
      wrapper.findAll('.datastream-name__thing').map((item) => item.text())
    ).toEqual(['Bear River', 'Bear River'])
    wrapper.unmount()
  })

  it('links a datastream row to its site details page', async () => {
    mockList([datastream])
    const store = useDataVisStore()
    store.monitoringSites = [site] as any

    const wrapper = mountTable()
    await flushPromises()
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
