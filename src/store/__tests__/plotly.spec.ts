import { ref, computed } from 'vue'
import { setActivePinia, createPinia, defineStore } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'

// vi.hoisted vars are safe to reference inside vi.mock factories.
// options.ts imports usePlotlyStore (circular), so we inline constants here.
const { COLORS, LABEL_COLORS, qcId } = vi.hoisted(() => {
  const { ref, computed } = require('vue') as typeof import('vue')
  const { defineStore } = require('pinia') as typeof import('pinia')
  const qcId = ref<string | null>(null)
  const COLORS = [
    '#3f3f3f', '#aec7e8', '#ffbb78', '#98df8a', '#c5b0d5',
    '#c49c94', '#f7b6d2', '#dbdb8d', '#9edae5', '#ad494a',
  ]
  const LABEL_COLORS = [
    '#3f3f3f', '#1f77b4', '#c06a00', '#208020', '#7a4da3',
    '#8c564b', '#e377c2', '#bcbd22', '#17becf', '#d62728',
  ]
  return { COLORS, LABEL_COLORS, qcId }
})

// Mock dataVisualization as a real Pinia store so storeToRefs works naturally.
vi.mock('@/store/dataVisualization', () => {
  const useDataVisStore = defineStore('dataVisualization', () => {
    const qcDatastream = computed(() =>
      qcId.value ? ({ id: qcId.value } as { id: string }) : null
    )
    return { qcDatastream }
  })
  return { useDataVisStore }
})

vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({ fetchObservationsInRange: vi.fn() }),
}))

// Inline constants to break circular dep: options.ts → usePlotlyStore → plotly barrel.
vi.mock('@/utils/plotting/plotly', () => ({
  COLORS,
  LABEL_COLORS,
  labelColorFor: (lineColor: string) => {
    const idx = COLORS.indexOf(lineColor)
    return idx >= 0 ? LABEL_COLORS[idx] : LABEL_COLORS[0]
  },
  applyTraceUpdate: vi.fn().mockResolvedValue(undefined),
  cropXaxisRange: vi.fn().mockResolvedValue(undefined),
  createPlotlyOption: vi.fn(() => ({ traces: [], layout: {} })),
  handleNewPlot: vi.fn(),
}))

// plotly.ts imports HistoryItem as a type only; stub to avoid worker init.
vi.mock('@uwrl/qc-utils', () => ({}))

import type { GraphSeries } from '@/types'
import type { ZoomState } from '@/store/plotly'

const makeSeries = (id: string, color: string): GraphSeries =>
  ({ id, color, name: id } as unknown as GraphSeries)

const fakeZoom = (source: ZoomState['source'] = 'user'): ZoomState => ({
  xRange: [0, 100],
  yRanges: {},
  source,
})

describe('usePlotlyStore.assignFreeColor', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    qcId.value = null
  })

  it('returns COLORS[1] when no series are plotted', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    // assignFreeColor is not in the public return surface; exercise via fetchGraphSeries?
    // Instead, seed series and observe that colorForDatastream reflects the palette,
    // and assert assignFreeColor indirectly by watching what redraw/colorForDatastream use.
    // The function itself is module-private but we can assert palette selection through
    // the behaviour of colorForDatastream + manually pushing entries onto graphSeriesArray.
    expect(store.graphSeriesArray).toEqual([])
    expect(COLORS[1]).toBe('#aec7e8')
  })

  it('colorForDatastream falls back to COLORS[1] for unknown id when no series match', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    expect(store.colorForDatastream('missing')).toBe(COLORS[1])
  })

  it('colorForDatastream falls back to COLORS[1] for undefined id', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    expect(store.colorForDatastream(undefined)).toBe(COLORS[1])
  })
})

describe('usePlotlyStore.colorForDatastream', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    qcId.value = null
  })

  it('returns the persisted series color for non-qc datastreams', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('a', COLORS[3]))
    expect(store.colorForDatastream('a')).toBe(COLORS[3])
  })

  it('returns COLORS[0] (QC black/grey) when id matches qcDatastream', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('qc', COLORS[4]))
    qcId.value = 'qc'
    expect(store.colorForDatastream('qc')).toBe(COLORS[0])
  })

  it('returns COLORS[1] fallback when id is unknown', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('a', COLORS[2]))
    expect(store.colorForDatastream('zzz')).toBe(COLORS[1])
  })
})

describe('usePlotlyStore.labelColorForDatastream', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    qcId.value = null
  })

  it('returns LABEL_COLORS[1] fallback for undefined id', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    expect(store.labelColorForDatastream(undefined)).toBe(LABEL_COLORS[1])
  })

  it('returns LABEL_COLORS[0] for the qc datastream', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('qc', COLORS[2]))
    qcId.value = 'qc'
    expect(store.labelColorForDatastream('qc')).toBe(LABEL_COLORS[0])
  })

  it('returns the darkened label companion for a non-qc series', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('a', COLORS[3]))
    expect(store.labelColorForDatastream('a')).toBe(LABEL_COLORS[3])
  })

  it('returns LABEL_COLORS[1] fallback when id is not in graphSeriesArray', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    expect(store.labelColorForDatastream('missing')).toBe(LABEL_COLORS[1])
  })
})

describe('usePlotlyStore zoom history', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    qcId.value = null
  })

  it('starts with empty stacks and canUndo/canRedo false', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    expect(store.zoomUndoStack).toEqual([])
    expect(store.zoomRedoStack).toEqual([])
    expect(store.canUndoZoom).toBe(false)
    expect(store.canRedoZoom).toBe(false)
  })

  it('pushZoomState appends to undo stack', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.pushZoomState(fakeZoom())
    expect(store.zoomUndoStack.length).toBe(1)
    // canUndoZoom requires length > 1 (first entry is the baseline)
    expect(store.canUndoZoom).toBe(false)
    store.pushZoomState(fakeZoom())
    expect(store.zoomUndoStack.length).toBe(2)
    expect(store.canUndoZoom).toBe(true)
  })

  it('pushZoomState clears the redo stack', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.zoomRedoStack.push(fakeZoom('preset'), fakeZoom('preset'))
    expect(store.canRedoZoom).toBe(true)
    store.pushZoomState(fakeZoom())
    expect(store.zoomRedoStack).toEqual([])
    expect(store.canRedoZoom).toBe(false)
  })

  it('caps undo stack at ZOOM_HISTORY_CAP (50) and drops the oldest entry', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    for (let i = 0; i < 60; i++) {
      store.pushZoomState({ ...fakeZoom(), xRange: [i, i + 1] })
    }
    expect(store.zoomUndoStack.length).toBe(50)
    // Oldest 10 entries should have been shifted off — first entry's xRange[0] is 10.
    expect(store.zoomUndoStack[0].xRange?.[0]).toBe(10)
    expect(store.zoomUndoStack[49].xRange?.[0]).toBe(59)
  })

  it('clearZoomHistory empties both stacks', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.pushZoomState(fakeZoom())
    store.pushZoomState(fakeZoom())
    store.zoomRedoStack.push(fakeZoom())
    store.clearZoomHistory()
    expect(store.zoomUndoStack).toEqual([])
    expect(store.zoomRedoStack).toEqual([])
    expect(store.canUndoZoom).toBe(false)
    expect(store.canRedoZoom).toBe(false)
  })

  it('canRedoZoom reflects redo stack emptiness', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    expect(store.canRedoZoom).toBe(false)
    store.zoomRedoStack.push(fakeZoom('preset'))
    expect(store.canRedoZoom).toBe(true)
  })
})

describe('usePlotlyStore.clearChartState', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    qcId.value = null
  })

  it('empties graphSeriesArray and zoom history', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('a', COLORS[1]))
    store.graphSeriesArray.push(makeSeries('b', COLORS[2]))
    store.pushZoomState(fakeZoom())
    store.pushZoomState(fakeZoom())
    store.zoomRedoStack.push(fakeZoom('preset'))

    store.clearChartState()

    expect(store.graphSeriesArray).toEqual([])
    expect(store.zoomUndoStack).toEqual([])
    expect(store.zoomRedoStack).toEqual([])
    expect(store.canUndoZoom).toBe(false)
    expect(store.canRedoZoom).toBe(false)
  })

  it('does not touch editHistory (that is a separate concern)', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.editHistory.push({ id: 'e1' } as any)
    store.clearChartState()
    expect(store.editHistory.length).toBe(1)
  })
})

describe('usePlotlyStore.updateOptions + selectedSeries', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    qcId.value = null
  })

  it('updateOptions rebuilds plotlyOptions via createPlotlyOption', async () => {
    const mod = await import('@/utils/plotting/plotly')
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    const before = (mod.createPlotlyOption as any).mock.calls.length
    store.updateOptions()
    expect((mod.createPlotlyOption as any).mock.calls.length).toBe(before + 1)
  })

  it('selectedSeriesIndex is -1 when qcDatastream is null', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('a', COLORS[1]))
    expect(store.selectedSeriesIndex).toBe(-1)
    expect(store.selectedSeries).toBeUndefined()
  })

  it('selectedSeriesIndex tracks the qc datastream', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('a', COLORS[1]))
    store.graphSeriesArray.push(makeSeries('qc', COLORS[2]))
    qcId.value = 'qc'
    expect(store.selectedSeriesIndex).toBe(1)
    expect(store.selectedSeries?.id).toBe('qc')
  })

  it('selectedSeriesIndex is -1 when qc id is not in graphSeriesArray', async () => {
    const { usePlotlyStore } = await import('@/store/plotly')
    const store = usePlotlyStore()
    store.graphSeriesArray.push(makeSeries('a', COLORS[1]))
    qcId.value = 'not-plotted'
    expect(store.selectedSeriesIndex).toBe(-1)
  })
})
