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
  subtitle: '',
  showSubtitle: true,
  fontSize: 18,
  aspectRatio: 4 / 3,
  showLegend: true,
  traces: [
    {
      id: 'flow',
      name: 'Upstream flow',
      siteName: 'Logan River',
      includeSiteName: true,
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
    settings.traces[0].includeSiteName = false
    settings.showLegend = false
    settings.subtitle = 'Logan River'
    settings.showSubtitle = false
    const result = buildFigurePreview(source, settings, 'Arial', measure)
    expect(result.traces[0].name).toBe('Upstream flow')
    expect(result.traces[0].marker.symbol).toBe('square')
    expect(result.layout.showlegend).toBe(false)
    expect(
      result.layout.annotations.some((a: any) => a.name === 'site-subtitle')
    ).toBe(false)
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
