/**
 * Unit tests for PlottedDatastreams.vue — focused on the per-row load
 * status (subtitle text + empty-window indicator). Mocks the two
 * stores the component reads so the rendered text reflects whatever
 * we drop into `graphSeriesArray` for each case.
 */

import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const datastreamA = { id: 'ds-a', name: 'Alpha Stream', valueCount: 9999 }
const datastreamB = { id: 'ds-b', name: 'Beta Stream', valueCount: 9999 }

const plottedDatastreams = ref<any[]>([])
const qcDatastream = ref<any>(null)
const loadingStates = ref(new Map<string, boolean>())
const graphSeriesArray = ref<any[]>([])
const plotlyRef = ref<any>(null)
const plotlyOptions = ref<any>({ traces: [] })
const hiddenAxisIds = ref<Set<string>>(new Set())
const hiddenTraceIds = ref<Set<string>>(new Set())

const toggleDatastream = vi.fn().mockResolvedValue(undefined)
const setQcInStore = vi.fn().mockResolvedValue(undefined)
const clearPlottedDatastreams = vi.fn().mockResolvedValue(undefined)
const updateOptions = vi.fn()
const colorForDatastream = vi.fn(() => '#000')
const labelColorForDatastream = vi.fn(() => '#000')

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    plottedDatastreams,
    qcDatastream,
    loadingStates,
    toggleDatastream,
    setQcDatastream: setQcInStore,
    clearPlottedDatastreams,
  }),
}))

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    plotlyRef,
    graphSeriesArray,
    plotlyOptions,
    hiddenAxisIds,
    hiddenTraceIds,
    updateOptions,
    colorForDatastream,
    labelColorForDatastream,
  }),
}))

vi.mock('@/utils/plotting/plotly', () => ({
  handleNewPlot: vi.fn().mockResolvedValue(undefined),
  toggleAxisVisibility: vi.fn(),
  toggleTraceVisibility: vi.fn().mockResolvedValue(undefined),
}))

import PlottedDatastreams from '@/components/VisualizeData/PlottedDatastreams.vue'

function mountIt() {
  return mount(PlottedDatastreams, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
    },
  })
}

// `loaded` is the windowed point count surfaced to the plot trace; `cached`
// is the series' full accumulated cache (defaults to `loaded`). The row
// must report `loaded`, not `cached`.
function seedSeries(
  entries: {
    id: string
    loaded: number
    loading?: boolean
    cached?: number
  }[]
) {
  graphSeriesArray.value = entries.map((e) => ({
    id: e.id,
    data: {
      isLoading: e.loading ?? false,
      dataX: new Array(e.cached ?? e.loaded),
    },
  }))
  plotlyOptions.value = {
    traces: entries.map((e) => ({ id: e.id, x: new Array(e.loaded) })),
  }
}

describe('PlottedDatastreams.vue — load status', () => {
  beforeEach(() => {
    plottedDatastreams.value = [datastreamA]
    qcDatastream.value = datastreamA
    graphSeriesArray.value = []
    plotlyOptions.value = { traces: [] }
    hiddenAxisIds.value = new Set()
  })

  it('shows the loaded-points count in the row subtitle', () => {
    seedSeries([{ id: datastreamA.id, loaded: 73 }])
    const wrapper = mountIt()
    const subtitle = wrapper.find('.plotted-item__subtitle')
    expect(subtitle.text()).toBe('73 pts loaded')
  })

  it('uses the singular noun when exactly one point is loaded', () => {
    seedSeries([{ id: datastreamA.id, loaded: 1 }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).toBe('1 pt loaded')
  })

  it('does NOT fall back to the datastream-level valueCount', () => {
    // The datastream's nominal `valueCount` is 9999; the row must
    // surface only the windowed count from graphSeriesArray.
    seedSeries([{ id: datastreamA.id, loaded: 42 }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).not.toContain(
      '9,999'
    )
    expect(wrapper.find('.plotted-item__subtitle').text()).not.toContain(
      '9999'
    )
  })

  it('shows "loading…" while the series fetch is still in flight', () => {
    seedSeries([{ id: datastreamA.id, loaded: 0, loading: true }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).toBe('loading…')
  })

  it('treats a missing graphSeries entry as still loading', () => {
    // No series in graphSeriesArray yet (initial mount before the
    // fetch resolves). Falls back to the loading state instead of
    // claiming "0 pts loaded".
    graphSeriesArray.value = []
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).toBe('loading…')
  })

  it('renders the empty-window indicator when the loaded count is zero', () => {
    seedSeries([{ id: datastreamA.id, loaded: 0 }])
    const wrapper = mountIt()
    const flag = wrapper.find('.plotted-item__empty-flag')
    expect(flag.exists()).toBe(true)
    expect(wrapper.find('.plotted-item__subtitle').text()).toBe('0 pts loaded')
  })

  it('hides the empty-window indicator while still loading', () => {
    seedSeries([{ id: datastreamA.id, loaded: 0, loading: true }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__empty-flag').exists()).toBe(false)
  })

  it('hides the empty-window indicator when points are loaded', () => {
    seedSeries([{ id: datastreamA.id, loaded: 5 }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__empty-flag').exists()).toBe(false)
  })

  it('reports the per-row state independently for multiple datastreams', () => {
    plottedDatastreams.value = [datastreamA, datastreamB]
    seedSeries([
      { id: datastreamA.id, loaded: 12 },
      { id: datastreamB.id, loaded: 0 },
    ])
    const wrapper = mountIt()
    const rows = wrapper.findAll('.plotted-item')
    expect(rows).toHaveLength(2)
    expect(rows[0].find('.plotted-item__subtitle').text()).toBe(
      '12 pts loaded'
    )
    expect(rows[0].find('.plotted-item__empty-flag').exists()).toBe(false)
    expect(rows[1].find('.plotted-item__subtitle').text()).toBe('0 pts loaded')
    expect(rows[1].find('.plotted-item__empty-flag').exists()).toBe(true)
  })

  it('formats large loaded counts with thousands separators', () => {
    seedSeries([{ id: datastreamA.id, loaded: 12345 }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).toContain('12,345')
  })

  // Regression: the series cache keeps every point ever fetched, so after
  // an "All" load then a narrower window the subtitle must report the
  // windowed plot trace, not the full cached history.
  it('counts the windowed plot trace, not the full accumulated cache', () => {
    seedSeries([{ id: datastreamA.id, loaded: 4, cached: 10 }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).toBe('4 pts loaded')
  })

  it('flags an empty window even when the cache still holds points', () => {
    seedSeries([{ id: datastreamA.id, loaded: 0, cached: 10 }])
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).toBe('0 pts loaded')
    expect(wrapper.find('.plotted-item__empty-flag').exists()).toBe(true)
  })

  it('ignores the id-less gap-overlay trace when counting', () => {
    graphSeriesArray.value = [
      { id: datastreamA.id, data: { isLoading: false, dataX: new Array(20) } },
    ]
    plotlyOptions.value = {
      traces: [
        { id: datastreamA.id, x: new Array(6) },
        { _isGapOverlay: true, _gapOverlayFor: datastreamA.id, x: new Array(50) },
      ],
    }
    const wrapper = mountIt()
    expect(wrapper.find('.plotted-item__subtitle').text()).toBe('6 pts loaded')
  })
})
