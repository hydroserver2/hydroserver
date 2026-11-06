import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mdiMapMarkerOutline } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
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

  it('keeps selected datastreams pinned above results when the search changes', async () => {
    mockList([{ ...datastream, id: 'datastream-2' }, datastream])
    const store = useDataVisStore()
    store.monitoringSites = [site] as any
    const wrapper = mountTable()
    await flushPromises()
    expect(rowIds(wrapper)).toEqual(['datastream-2', 'datastream-1'])

    store.plottedDatastreams = [datastream] as any
    await wrapper
      .getComponent({ name: 'HsQuerySearchInput' })
      .vm.$emit('update:modelValue', 'temperature')
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()

    expect(store.plottedDatastreams.map((item) => item.id)).toEqual([
      'datastream-1',
    ])
    expect(rowIds(wrapper)).toEqual(['datastream-1', 'datastream-2'])
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
