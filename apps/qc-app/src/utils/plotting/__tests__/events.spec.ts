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

  // A default sort compares as text, which would put 10 before 9.
  it('keeps a clicked selection in numeric order', async () => {
    const { handleNewPlot } = await import('@/utils/plotting/events')
    const Plotly = (await import('plotly.js-dist')).default
    const el = fakeGraphDiv({})
    plotlyRef.value = el
    await handleNewPlot()
    const onClick = (el.on as ReturnType<typeof vi.fn>).mock.calls.find(
      ([name]) => name === 'plotly_click'
    )?.[1] as (e: unknown) => Promise<void>

    await onClick({ points: [{ pointIndex: 9, data: { selectedpoints: [10, 2] } }] })

    expect(Plotly.restyle).toHaveBeenLastCalledWith(el, {
      selectedpoints: [[2, 9, 10]],
    })
  })

  describe('preserveZoom y ranges', () => {
    const trace = (id: string, n: number, yaxis = 'y') => ({
      id,
      yaxis,
      x: Array.from({ length: n }, (_, i) => i),
      y: Array.from({ length: n }, (_, i) => i),
    })

    /** Live plot: `ctx` alone on the primary axis, `other` on yaxis2. */
    function livePlot() {
      const gd = fakeGraphDiv({
        xaxis: { range: [0, 10] },
        yaxis: { range: [9, 11] },
        yaxis2: { range: [100, 200] },
      })
      gd.data = [trace('ctx', 5), trace('other', 5, 'y2')]
      plotlyRef.value = gd
    }

    const drawnLayout = () =>
      newPlot.mock.calls.at(-1)?.[2] as Record<string, { range?: unknown }>

    it('keeps every axis when the same series redraw', async () => {
      const { handleNewPlot } = await import('@/utils/plotting/events')
      livePlot()
      plotlyOptions.value = {
        traces: [trace('ctx', 8), trace('other', 5, 'y2')],
        layout: { xaxis: {}, yaxis: {}, yaxis2: {} },
        config: {},
      }

      await handleNewPlot(undefined, { preserveZoom: true })

      expect(drawnLayout().yaxis!.range).toEqual([9, 11])
      expect(drawnLayout().yaxis2!.range).toEqual([100, 200])
    })

    it('refits an axis that gains a series with points', async () => {
      const { handleNewPlot } = await import('@/utils/plotting/events')
      livePlot()
      plotlyOptions.value = {
        traces: [
          trace('ctx', 5),
          trace('edit', 50),
          trace('other', 5, 'y2'),
        ],
        layout: { xaxis: {}, yaxis: {}, yaxis2: {} },
        config: {},
      }

      await handleNewPlot(undefined, { preserveZoom: true })

      expect(drawnLayout().yaxis!.range).toBeUndefined()
      expect(drawnLayout().yaxis2!.range).toEqual([100, 200])
      expect(drawnLayout().xaxis!.range).toEqual([0, 10])
    })

    it('refits the axis of a series whose data was replaced', async () => {
      const { handleNewPlot } = await import('@/utils/plotting/events')
      livePlot()
      plotlyOptions.value = {
        traces: [trace('ctx', 5), trace('other', 5, 'y2')],
        layout: { xaxis: {}, yaxis: {}, yaxis2: {} },
        config: {},
      }

      await handleNewPlot(undefined, {
        preserveZoom: true,
        refitSeriesIds: ['ctx'],
      })

      expect(drawnLayout().yaxis!.range).toBeUndefined()
      expect(drawnLayout().yaxis2!.range).toEqual([100, 200])
    })
  })
})
