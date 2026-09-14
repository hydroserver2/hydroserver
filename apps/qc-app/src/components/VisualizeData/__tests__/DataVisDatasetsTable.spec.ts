/**
 * Unit tests for DataVisDatasetsTable.vue — focused on the plot checkbox.
 * A source with managed (QC) datastreams opens a chooser instead of
 * toggling, so the row's checked state has to speak for the whole group.
 */

import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import PlotSourceDialog from '../PlotSourceDialog.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as any).visualViewport ||= {
  addEventListener() {},
  removeEventListener() {},
}

const raw = { id: 'src', name: 'Raw', valueCount: 10, thing: { id: 't-1' } }
const lonely = { id: 'solo', name: 'Solo', valueCount: 5, thing: { id: 't-1' } }

const filteredDatastreams = ref<any[]>([raw, lonely])
const plottedDatastreams = ref<any[]>([])
const qcDatastream = ref<any>(null)
const historiesBySource = ref(
  new Map<string, any[]>([
    ['src', [{ id: 'h-1', managedDatastreamId: 'mgd', sourceDatastreamId: 'src' }]],
  ])
)

const toggleDatastream = vi.fn().mockResolvedValue(undefined)
const clearPlottedDatastreams = vi.fn().mockResolvedValue(undefined)
const plotSourceSelection = vi.fn().mockResolvedValue(undefined)
const sourceGroupIds = (id: string) => (id === 'src' ? ['src', 'mgd'] : [id])

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    filteredDatastreams,
    plottedDatastreams,
    qcDatastream,
    historiesBySource,
    toggleDatastream,
    clearPlottedDatastreams,
    sourceGroupIds,
    plotSourceSelection,
  }),
}))

const loadForSource = vi.fn().mockResolvedValue([
  {
    historyId: 'h-1',
    managed: { id: 'mgd', name: 'Raw (QC)', valueCount: 8 },
    sessions: [],
  },
])

vi.mock('@/composables/useManagedDatastreams', () => ({
  useManagedDatastreams: () => ({ loadForSource }),
}))

vi.mock('@/utils/csvExport', () => ({
  downloadDatastreamsCsvZip: vi.fn().mockResolvedValue(undefined),
}))

const snackbarError = vi.fn()
vi.mock('@uwrl/qc-utils', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>
  return { ...actual, Snackbar: { error: snackbarError, success: vi.fn() } }
})

beforeEach(() => {
  vi.clearAllMocks()
  plottedDatastreams.value = []
  qcDatastream.value = null
})

const mountTable = async () => {
  const DataVisDatasetsTable = (await import('../DataVisDatasetsTable.vue'))
    .default
  const wrapper = mount(DataVisDatasetsTable, {
    global: { plugins: [createTestVuetify()] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

const checkbox = (wrapper: any, id: string) =>
  wrapper.find(`[data-testid="plot-checkbox-${id}"]`)

describe('DataVisDatasetsTable plot checkbox', () => {
  it('toggles directly when the source has no managed datastreams', async () => {
    const wrapper = await mountTable()
    await checkbox(wrapper, 'solo').trigger('click')
    await flushPromises()

    expect(toggleDatastream).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'solo' })
    )
    expect(wrapper.findComponent(PlotSourceDialog).exists()).toBe(false)
  })

  it('opens the chooser when the source has managed datastreams', async () => {
    const wrapper = await mountTable()
    await checkbox(wrapper, 'src').trigger('click')
    await flushPromises()

    expect(toggleDatastream).not.toHaveBeenCalled()
    expect(loadForSource).toHaveBeenCalledWith('src')
    expect(wrapper.findComponent(PlotSourceDialog).exists()).toBe(true)
  })

  it('reports a chooser failure and still offers the raw option', async () => {
    loadForSource.mockRejectedValueOnce(new Error('boom'))
    const wrapper = await mountTable()
    await checkbox(wrapper, 'src').trigger('click')
    await flushPromises()

    expect(snackbarError).toHaveBeenCalledWith('boom')
    const dialog = wrapper.findComponent(PlotSourceDialog)
    expect(dialog.exists()).toBe(true)
    expect(dialog.props('options')).toEqual([])
  })

  it('applies the chooser selection through the batched store action', async () => {
    const wrapper = await mountTable()
    await checkbox(wrapper, 'src').trigger('click')
    await flushPromises()

    wrapper.findComponent(PlotSourceDialog).vm.$emit('apply', ['mgd'])
    await flushPromises()

    expect(plotSourceSelection).toHaveBeenCalledWith('src', ['mgd'])
  })

  it('shows a checked box when the raw datastream is plotted', async () => {
    plottedDatastreams.value = [raw]
    const wrapper = await mountTable()
    expect(checkbox(wrapper, 'src').html()).toContain('mdi-checkbox-marked')
  })

  // The row must not claim the raw line is plotted when only a QC version is.
  it('shows an indeterminate box when only a managed datastream is plotted', async () => {
    plottedDatastreams.value = [{ id: 'mgd', name: 'Raw (QC)' }]
    const wrapper = await mountTable()
    const html = checkbox(wrapper, 'src').html()
    expect(html).toContain('mdi-checkbox-intermediate')
    expect(checkbox(wrapper, 'src').attributes('aria-pressed')).toBe('true')
  })

  it('shows an empty box when nothing from the group is plotted', async () => {
    const wrapper = await mountTable()
    expect(checkbox(wrapper, 'src').html()).toContain(
      'mdi-checkbox-blank-outline'
    )
  })
})
