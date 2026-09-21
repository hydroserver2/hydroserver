import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive, ref } from 'vue'

const newPlot = vi.fn()

vi.mock('plotly.js-dist', () => ({
  default: {
    newPlot,
    update: vi.fn(),
    restyle: vi.fn(),
    relayout: vi.fn(),
  },
}))

const { plotlyOptions, plotlyRef, mainPlotEpoch, pendingShareZoom } = vi.hoisted(
  () => {
    const { ref: r } = require('vue') as typeof import('vue')
    return {
      plotlyOptions: r<any>({ traces: [], layout: {}, config: {} }),
      plotlyRef: r<any>(null),
      mainPlotEpoch: r(0),
      pendingShareZoom: r<any>(null),
    }
  }
)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () =>
    reactive({
      plotlyOptions,
      plotlyRef,
      mainPlotEpoch,
      pendingShareZoom,
      zoomUndoStack: ref([]),
      pushZoomState: vi.fn(),
    }),
}))

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => reactive({ hasSelectionShape: ref(false) }),
}))

vi.mock('../relayout', () => ({ handleRelayout: vi.fn() }))
vi.mock('../selected', () => ({ handleSelected: vi.fn() }))
vi.mock('../zoom', () => ({
  captureCurrentZoomState: vi.fn(() => null),
  installZoomTracking: vi.fn(),
}))
vi.mock('../interaction', () => ({
  handleMouseMove: vi.fn(),
  handleMouseOut: vi.fn(),
  handleWheel: vi.fn(),
  widenYAxisDragRects: vi.fn(),
  suppressHiddenAxisDragRects: vi.fn(),
  updateAxisChips: vi.fn(),
}))

/** Enough of a Plotly graph div for `handleNewPlot` to re-plot onto. */
function fakeGraphDiv(layout: Record<string, unknown>) {
  const el = document.createElement('div') as unknown as Record<string, unknown>
  el.data = []
  el.layout = layout
  el.on = vi.fn()
  el.removeListener = vi.fn()
  return el
}

describe('handleNewPlot', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    newPlot.mockReset().mockImplementation(async (el: unknown) => el)
    plotlyOptions.value = { traces: [], layout: {}, config: {} }
    plotlyRef.value = null
    pendingShareZoom.value = null
  })

  it('exports handleNewPlot as a function', async () => {
    const { handleNewPlot } = await import('@/utils/plotting/events')
    expect(typeof handleNewPlot).toBe('function')
  })

  it('carries the live stage band through a re-plot', async () => {
    const { handleNewPlot } = await import('@/utils/plotting/events')
    plotlyRef.value = fakeGraphDiv({
      shapes: [{ name: 'stage', type: 'rect' }],
    })
    plotlyOptions.value = { traces: [], layout: {}, config: {} }

    await handleNewPlot()

    const layout = newPlot.mock.calls[0]?.[2] as { shapes: any[] }
    expect(layout.shapes.map((s) => s.name)).toEqual(['stage'])
  })

  it('draws a first mount with the layout it was given', async () => {
    const { handleNewPlot } = await import('@/utils/plotting/events')
    const layout = { dragmode: 'pan' }
    plotlyOptions.value = { traces: [], layout, config: {} }

    await handleNewPlot(fakeGraphDiv({}) as unknown as HTMLElement)

    expect(newPlot.mock.calls[0]?.[2]).toStrictEqual(layout)
  })
})
