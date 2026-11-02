import { describe, it, expect, beforeEach, vi } from 'vitest'
import { reactive, ref } from 'vue'

const { relayout } = vi.hoisted(() => ({ relayout: vi.fn() }))
vi.mock('plotly.js-dist', () => ({ default: { relayout } }))

const { graphSeriesArray, lockedAxisIds, plotlyRef, qcDatastream } = vi.hoisted(
  () => {
    const { ref: r } = require('vue') as typeof import('vue')
    return {
      graphSeriesArray: r<any[]>([]),
      lockedAxisIds: r(new Set<string>()),
      plotlyRef: r<any>(null),
      qcDatastream: r<any>(null),
    }
  }
)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () =>
    reactive({ graphSeriesArray, lockedAxisIds, plotlyRef }),
}))
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () =>
    reactive({ qcDatastream, sourceContextDatastream: ref(null) }),
}))

import {
  canLockAxis,
  installAxisLock,
  sharesPrimaryVariable,
  toggleAxisLock,
} from '../axisLock'

// qc and flow2 measure discharge in cfs; ph is another variable.
const series = [
  { id: 'qc', variable: 'discharge:cfs' },
  { id: 'flow2', variable: 'discharge:cfs' },
  { id: 'ph', variable: 'ph:none' },
]

/** A plot with the edit target on `y`, flow2 on `y2` and ph on `y3`. */
const makePlot = () => {
  const gd = document.createElement('div') as any
  gd.innerHTML = `<svg><g class="draglayer">
    <g class="xy"><rect class="nsdrag"></rect></g>
    <g class="xy2"><rect class="nsdrag"></rect></g>
    <g class="xy3"><rect class="nsdrag"></rect></g>
  </g></svg>`
  gd.data = [
    { id: 'qc', yaxis: 'y' },
    { id: 'flow2', yaxis: 'y2' },
    { id: 'ph', yaxis: 'y3' },
  ]
  gd.layout = {
    yaxis: { range: [0, 10] },
    yaxis2: { range: [100, 200] },
    yaxis3: { range: [7, 8] },
  }
  gd._fullLayout = {
    yaxis: { range: [0, 10] },
    yaxis2: { range: [100, 200] },
    yaxis3: { range: [7, 8] },
    _axisConstraintGroups: [],
  }
  const handlers: Record<string, (evt: unknown) => void> = {}
  gd.on = (name: string, fn: (evt: unknown) => void) => (handlers[name] = fn)
  document.body.appendChild(gd)
  plotlyRef.value = gd
  installAxisLock(gd)
  return { gd, handlers }
}

const strip = (gd: HTMLElement, subplot: string) =>
  gd.querySelector(`g.${subplot} > rect.nsdrag`)!

beforeEach(() => {
  document.body.innerHTML = ''
  relayout.mockClear()
  graphSeriesArray.value = series
  lockedAxisIds.value = new Set()
  qcDatastream.value = { id: 'qc' }
})

describe('axis lock', () => {
  it('lets any other axis lock, and same-variable axes match', () => {
    expect(canLockAxis('qc')).toBe(false)
    expect(canLockAxis('flow2')).toBe(true)
    expect(canLockAxis('ph')).toBe(true)
    expect(sharesPrimaryVariable('flow2')).toBe(true)
    expect(sharesPrimaryVariable('ph')).toBe(false)
  })

  it('moves a locked axis with the primary axis at its own scale', () => {
    const { handlers } = makePlot()
    toggleAxisLock('flow2')
    handlers.plotly_relayout!({ 'yaxis.range': [5, 15] })
    expect(relayout).toHaveBeenCalledWith(expect.anything(), {
      'yaxis2.range': [150, 250],
      'yaxis2.autorange': false,
    })
  })

  it('leaves a locked axis the same change already sets', () => {
    const { handlers } = makePlot()
    toggleAxisLock('flow2')
    handlers.plotly_relayout!({
      'yaxis.range': [5, 15],
      'yaxis2.range': [0, 1],
    })
    expect(relayout).not.toHaveBeenCalled()
  })

  it('moves locked axes in the same step as a drag of the primary axis', () => {
    const { gd } = makePlot()
    toggleAxisLock('ph')
    strip(gd, 'xy').dispatchEvent(
      new MouseEvent('mousedown', { bubbles: true })
    )
    gd._fullLayout.yaxis.range = [5, 15]
    expect(gd._fullLayout.yaxis3.range).toEqual([7.5, 8.5])

    document.dispatchEvent(new MouseEvent('mouseup'))
    expect(gd._fullLayout._axisConstraintGroups).toEqual([])
    gd._fullLayout.yaxis.range = [0, 10]
    expect(gd._fullLayout.yaxis3.range).toEqual([7.5, 8.5])
  })

  it('double-clicking a same-variable axis gives it the primary range', () => {
    const { gd } = makePlot()
    strip(gd, 'xy3').dispatchEvent(
      new MouseEvent('click', { bubbles: true, detail: 2 })
    )
    expect(relayout).not.toHaveBeenCalled()

    strip(gd, 'xy2').dispatchEvent(
      new MouseEvent('click', { bubbles: true, detail: 2 })
    )
    expect(relayout).toHaveBeenCalledWith(gd, {
      'yaxis2.range': [0, 10],
      'yaxis2.autorange': false,
    })
  })

  it('uses the first series as the primary one outside the editor', () => {
    qcDatastream.value = null
    expect(canLockAxis('qc')).toBe(false)
    expect(sharesPrimaryVariable('flow2')).toBe(true)
    graphSeriesArray.value = [series[0], { id: 'flow2' }]
    expect(sharesPrimaryVariable('flow2')).toBe(false)
  })

  it('unlocks on a second toggle, with or without a plot', () => {
    toggleAxisLock('flow2')
    expect(lockedAxisIds.value.has('flow2')).toBe(true)
    const { handlers } = makePlot()
    toggleAxisLock('flow2')
    expect(lockedAxisIds.value.has('flow2')).toBe(false)
    handlers.plotly_relayout!({ 'yaxis.range': [5, 15] })
    expect(relayout).not.toHaveBeenCalled()
  })

  it('reads a range set one end at a time', () => {
    const { handlers } = makePlot()
    toggleAxisLock('flow2')
    handlers.plotly_relayout!({ 'yaxis.range[0]': 5, 'yaxis.range[1]': 15 })
    expect(relayout).toHaveBeenCalledWith(expect.anything(), {
      'yaxis2.range': [150, 250],
      'yaxis2.autorange': false,
    })
  })

  it('ignores changes that leave the primary axis alone', () => {
    const { handlers } = makePlot()
    toggleAxisLock('flow2')
    handlers.plotly_relayout!({ 'xaxis.range': [0, 1] })
    handlers.plotly_relayout!({ 'yaxis.range': [5, 'x'] })
    handlers.plotly_relayouting!({ 'xaxis.range': [0, 1] })
    handlers.plotly_relayouting!({ 'yaxis.range': [5, 15] })
    expect(relayout).not.toHaveBeenCalled()
  })

  it('skips locks it cannot place', () => {
    const { gd, handlers } = makePlot()
    lockedAxisIds.value = new Set(['qc', 'gone', 'flow2'])
    gd.layout.yaxis2 = {}
    gd.layout.yaxis3.range = [7, NaN]
    toggleAxisLock('ph')
    handlers.plotly_relayout!({ 'yaxis.range': [5, 15] })
    expect(relayout).not.toHaveBeenCalled()

    gd.layout.yaxis = { range: [3, 3] }
    handlers.plotly_relayout!({ 'yaxis.range': [5, 15] })
    expect(relayout).not.toHaveBeenCalled()
  })

  it('settles a drag from where it began', () => {
    const { gd, handlers } = makePlot()
    toggleAxisLock('flow2')
    strip(gd, 'xy').dispatchEvent(
      new MouseEvent('mousedown', { bubbles: true })
    )
    // Zooming from an end of the axis changes the range in place.
    handlers.plotly_relayouting!({ 'yaxis.range': [5, 15] })
    expect(gd._fullLayout.yaxis2.range).toEqual([150, 250])
    document.dispatchEvent(new MouseEvent('mouseup'))
    handlers.plotly_relayout!({
      'yaxis.range[0]': 5,
      'yaxis.range[1]': 15,
      'yaxis2.range[0]': 140,
      'yaxis2.range[1]': 240,
    })
    expect(relayout).toHaveBeenCalledWith(expect.anything(), {
      'yaxis2.range': [150, 250],
      'yaxis2.autorange': false,
    })
  })

  it('only links drags that start on the primary axis', () => {
    const { gd } = makePlot()
    toggleAxisLock('flow2')
    strip(gd, 'xy2').dispatchEvent(
      new MouseEvent('mousedown', { bubbles: true })
    )
    expect(gd._fullLayout._axisConstraintGroups).toEqual([])

    toggleAxisLock('flow2')
    strip(gd, 'xy').dispatchEvent(
      new MouseEvent('mousedown', { bubbles: true })
    )
    expect(gd._fullLayout._axisConstraintGroups).toEqual([])

    plotlyRef.value = null
    strip(gd, 'xy').dispatchEvent(
      new MouseEvent('mousedown', { bubbles: true })
    )
    expect(gd._fullLayout._axisConstraintGroups).toEqual([])
  })

  it('matches only on a double-click of another axis strip', () => {
    const { gd } = makePlot()
    const click = (el: Element, detail: number) =>
      el.dispatchEvent(new MouseEvent('click', { bubbles: true, detail }))
    click(strip(gd, 'xy2'), 1)
    click(gd.querySelector('g.draglayer')!, 2)
    click(strip(gd, 'xy'), 2)
    plotlyRef.value = null
    click(strip(gd, 'xy2'), 2)
    expect(relayout).not.toHaveBeenCalled()
  })
})
