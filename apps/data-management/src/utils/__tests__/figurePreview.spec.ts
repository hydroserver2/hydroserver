import { describe, expect, it } from 'vitest'
import {
  buildFigurePreview,
  type FigureSettings,
} from '../plotting/figurePreview'
import type { PlotlyOptions } from '../plotting/plotly'
import { PlotlyColors } from '../materialColors'

const source: PlotlyOptions = {
  traces: [
    {
      id: 'flow',
      name: 'Discharge',
      x: [1, 2],
      y: [3, 4],
      type: 'scattergl',
      marker: { symbol: 'square' },
    },
  ],
  layout: {
    margin: { l: 4, r: 0, t: 88, b: 80 },
    xaxis: { range: [1, 2], title: { text: 'Datetime' } },
    yaxis: { range: [3, 4], title: { text: 'Discharge (m³/s)' } },
  },
  config: { displayModeBar: true },
  xRange: { min: 1, max: 2 },
}
const defaults = (): FigureSettings => ({
  title: 'Study reach',
  fontSize: 18,
  width: 1200,
  height: 900,
  showLegend: true,
  showSiteNames: true,
  legendPosition: 'above',
  traces: [
    {
      id: 'flow',
      name: 'Upstream flow',
      siteName: 'Logan River',
      color: PlotlyColors[0],
    },
  ],
  axes: [
    { key: 'xaxis', label: 'Date (UTC)' },
    { key: 'yaxis', label: 'Flow (m³ s⁻¹)' },
  ],
})
const measure = (text: string) => text.length * 9

describe('figure preview', () => {
  it('applies edited colors to lines, markers and their axis without changing source colors', () => {
    const settings = defaults()
    settings.traces[0].color = PlotlyColors[3]
    const before = JSON.stringify(source)
    const result = buildFigurePreview(source, settings, 'Arial', measure)
    expect(result.traces[0].line.color).toBe(PlotlyColors[3])
    expect(result.traces[0].marker.color).toBe(PlotlyColors[3])
    expect(result.traces[0].marker.symbol).toBe('square')
    expect(result.layout.yaxis.title.font.color).toBe(PlotlyColors[3])
    expect(result.layout.yaxis.tickfont.color).toBe(PlotlyColors[3])
    expect(result.layout.yaxis.linecolor).toBe(PlotlyColors[3])
    expect(JSON.stringify(source)).toBe(before)
  })

  it('keeps edited titles, traces, axes and site names separate from the live chart', () => {
    const before = JSON.stringify(source)
    const result = buildFigurePreview(source, defaults(), 'Arial', measure)
    expect(result.traces[0].name).toBe('Upstream flow<br>@ Logan River')
    expect(
      result.layout.annotations.find((a: any) => a.name === 'figure-title').text
    ).toBe('Study reach')
    expect(result.layout.xaxis.title.text).toBe('Date (UTC)')
    expect(result.layout.yaxis.title.text).toBe('Flow (m³ s⁻¹)')
    expect(result.layout.xaxis.range).toEqual([1, 2])
    expect(result.layout.yaxis.range).toEqual([3, 4])
    expect(result.config.staticPlot).toBe(true)
    expect(result.config.displayModeBar).toBe(false)
    expect(result.layout.width / result.layout.height).toBe(4 / 3)
    expect(JSON.stringify(source)).toBe(before)
  })

  it('can hide site names and the legend while preserving labels and symbols', () => {
    const settings = defaults()
    settings.showSiteNames = false
    settings.showLegend = false
    const result = buildFigurePreview(source, settings, 'Arial', measure)
    expect(result.traces[0].name).toBe('Upstream flow')
    expect(result.traces[0].marker.symbol).toBe('square')
    expect(result.layout.showlegend).toBe(false)
  })

  it('moves the legend below the axis labels without moving the figure title', () => {
    const settings = defaults()
    const above = buildFigurePreview(source, settings, 'Arial', measure)
    settings.legendPosition = 'below'
    const below = buildFigurePreview(source, settings, 'Arial', measure)
    expect(below.layout.legend.yanchor).toBe('top')
    expect(below.layout.legend.y).toBeLessThan(0)
    expect(below.layout.margin.b).toBeGreaterThan(above.layout.margin.b)
    expect(below.layout.margin.t).toBeLessThan(above.layout.margin.t)
    expect(below.layout.annotations[0].y).toBe(1)
    const plotHeight =
      below.layout.height - below.layout.margin.t - below.layout.margin.b
    expect(-below.layout.legend.y * plotHeight).toBeCloseTo(above.layout.margin.b)
    settings.showLegend = false
    const hidden = buildFigurePreview(source, settings, 'Arial', measure)
    expect(hidden.layout.margin.b).toBe(above.layout.margin.b)
  })

  it('centers the image title on the X-axis domain with matching typography and spacing', () => {
    const settings = defaults()
    const shifted = {
      ...source,
      layout: {
        ...source.layout,
        xaxis: {
          ...source.layout.xaxis,
          domain: [0.1, 0.8],
          title: { text: 'Datetime', standoff: 24 },
        },
      },
    }
    const result = buildFigurePreview(shifted, settings, 'Arial', measure)
    const title = result.layout.annotations[0]
    expect(title.x).toBe(0.45)
    expect(title.xanchor).toBe('center')
    expect(title.align).toBe('center')
    expect(title.font).toEqual(result.layout.xaxis.title.font)
    expect(title.yshift).toBe(result.layout.xaxis.title.standoff)
    expect(result.layout.legend.y).toBeGreaterThan(1)
  })

  it('shows or hides site names for every trace together', () => {
    const settings = defaults()
    settings.traces.push({
      ...settings.traces[0],
      id: 'second',
      siteName: 'Lower reach',
    })
    const multiple = {
      ...source,
      traces: [...source.traces, { ...source.traces[0], id: 'second' }],
    }
    expect(
      buildFigurePreview(multiple, settings, 'Arial', measure).traces.every(
        (trace) => trace.name.includes('@ ')
      )
    ).toBe(true)
    settings.showSiteNames = false
    expect(
      buildFigurePreview(multiple, settings, 'Arial', measure).traces.every(
        (trace) => !trace.name.includes('@ ')
      )
    ).toBe(true)
  })

  it('respects exact dimensions and reports space needed instead of growing the image', () => {
    const settings = defaults()
    settings.width = 800
    settings.height = 300
    settings.title = 'Long image title '.repeat(10)
    const result = buildFigurePreview(source, settings, 'Arial', measure)
    expect(result.layout.width).toBe(800)
    expect(result.layout.height).toBe(300)
    expect(result.minHeight).toBeGreaterThan(300)
    settings.height = result.minHeight
    const fitted = buildFigurePreview(source, settings, 'Arial', measure)
    expect(fitted.layout.height).toBeGreaterThanOrEqual(fitted.minHeight)
    expect(fitted.layout.width).toBe(800)
  })

  it('escapes user text and wraps long axis labels to fit the requested page shape', () => {
    const settings = defaults()
    settings.title = '<b>Study</b>'
    settings.axes[0].label = '<i>Date</i>'
    settings.axes[1].label = 'A very long axis label with units '.repeat(6)
    const result = buildFigurePreview(source, settings, 'Arial', measure)
    expect(result.layout.annotations[0].text).toBe('&lt;b&gt;Study&lt;/b&gt;')
    expect(result.layout.xaxis.title.text).toBe('&lt;i&gt;Date&lt;/i&gt;')
    expect(result.layout.yaxis.title.text).toContain('<br>')
    expect(result.layout.height).toBe(900)
  })
})
