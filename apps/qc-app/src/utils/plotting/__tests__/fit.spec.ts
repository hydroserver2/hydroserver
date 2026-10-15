import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'

const { relayout } = vi.hoisted(() => ({ relayout: vi.fn() }))
vi.mock('plotly.js-dist', () => ({ default: { relayout } }))
vi.mock('../events', () => ({ handleNewPlot: vi.fn() }))

const plotlyRef = ref<any>(null)
const isUpdating = ref(false)
vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ plotlyRef, isUpdating }),
}))

const qcDatastream = ref<{ id: string } | null>(null)
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ qcDatastream }),
}))

import { fitXaxisToVisible, fitYaxisToVisible } from '../operations'
import { plotCoordToDate, plotX } from '../plotTime'

const HOUR = 3_600_000
const T0 = Date.UTC(2014, 0, 15)
// Trace x as handed to Plotly; `plotX` gives where it draws them.
const xs = Array.from({ length: 6 }, (_, i) => T0 + i * HOUR)
const drawn = Array.from(plotX(xs))
const ys = [10, 12, 500, 11, 13, 14]

const at = (i: number) => plotCoordToDate(drawn[i]!)

/** A plot showing points `from`..`to` (inclusive) and y in `yRange`. */
const showPlot = (from: number, to: number, yRange: [number, number]) => {
  plotlyRef.value = {
    data: [{ id: 'qc', x: xs, y: ys }],
    layout: { xaxis: { range: [at(from), at(to)] }, yaxis: { range: yRange } },
  }
}

const lastRelayout = () => relayout.mock.calls.at(-1)?.[1]

beforeEach(() => {
  relayout.mockReset()
  qcDatastream.value = { id: 'qc' }
  isUpdating.value = false
})

describe('fitYaxisToVisible', () => {
  it('fits the points on screen, edges included', async () => {
    showPlot(0, 4, [0, 100])
    await fitYaxisToVisible()
    // 500 is inside the x window but above the view.
    expect(lastRelayout()).toEqual({
      'yaxis.range': [10, 13],
      'yaxis.autorange': false,
    })
    expect(isUpdating.value).toBe(false)
  })

  it('does nothing without an edit target or its trace', async () => {
    showPlot(0, 4, [0, 100])
    qcDatastream.value = null
    await fitYaxisToVisible()
    qcDatastream.value = { id: 'other' }
    await fitYaxisToVisible()
    expect(relayout).not.toHaveBeenCalled()
  })

  it('does nothing while the trace is hidden', async () => {
    showPlot(0, 4, [0, 100])
    plotlyRef.value.data[0].visible = 'legendonly'
    await fitYaxisToVisible()
    expect(relayout).not.toHaveBeenCalled()
  })

  it('does nothing with fewer than two distinct values on screen', async () => {
    showPlot(1, 1, [0, 100])
    await fitYaxisToVisible()
    showPlot(0, 4, [600, 700])
    await fitYaxisToVisible()
    expect(relayout).not.toHaveBeenCalled()
  })
})

describe('fitXaxisToVisible', () => {
  it('fits the points on screen, edges included', async () => {
    showPlot(0, 5, [11, 13])
    await fitXaxisToVisible()
    expect(lastRelayout()).toEqual({
      'xaxis.range': [at(1), at(4)],
      'xaxis.autorange': false,
    })
  })

  it('keeps a fitted range on a second fit', async () => {
    showPlot(1, 4, [0, 100])
    await fitXaxisToVisible()
    expect(lastRelayout()['xaxis.range']).toEqual([at(1), at(4)])
  })

  it('does nothing without an edit target, its trace or a plot', async () => {
    showPlot(0, 5, [0, 100])
    qcDatastream.value = { id: 'other' }
    await fitXaxisToVisible()
    qcDatastream.value = null
    await fitXaxisToVisible()
    plotlyRef.value = null
    await fitXaxisToVisible()
    expect(relayout).not.toHaveBeenCalled()
  })

  it('does nothing with fewer than two points on screen', async () => {
    showPlot(2, 2, [0, 1000])
    await fitXaxisToVisible()
    showPlot(0, 5, [600, 700])
    await fitXaxisToVisible()
    expect(relayout).not.toHaveBeenCalled()
  })
})
