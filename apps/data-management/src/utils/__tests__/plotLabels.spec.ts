import { describe, expect, it } from 'vitest'
import { applyPlotLabels, wrapPlotLabel } from '../plotting/plotLabels'
import type { PlotlyOptions } from '../plotting/plotly'

const measure = (text: string) => Array.from(text).length * 8

describe('presentation plot labels', () => {
  it('wraps long identifiers and preserves explicit line breaks without truncation', () => {
    const identifier = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    const lines = wrapPlotLabel(`Discharge\n@ ${identifier}`, 80, measure)
    expect(lines[0]).toBe('Discharge')
    expect(lines.slice(1).join('').replace(/\s/g, '')).toBe(`@${identifier}`)
    expect(lines.every((line) => measure(line) <= 80)).toBe(true)
  })

  function baseOptions(): PlotlyOptions {
    return {
      traces: Array.from({ length: 5 }, (_, index) => ({
        id: `stream-${index}`,
        name: 'Discharge',
        x: [1, 2],
        y: [3, 4],
      })),
      layout: {
        margin: { l: 4, r: 0, t: 88, b: 80 },
        legend: {},
        xaxis: { range: [1, 2] },
        uirevision: 'selection',
      },
      config: { modeBarButtonsToAdd: [{ name: 'Download plot' }] },
      xRange: { min: 1, max: 2 },
    }
  }

  it('expands the header for narrow charts and leaves room for every legend row and subtitle', () => {
    const base = baseOptions()
    const labels = base.traces.map((trace) => ({
      id: trace.id,
      label:
        'Water temperature\n@ A very long monitoring site name with no ellipses',
    }))
    const wide = applyPlotLabels(
      base,
      labels,
      'Logan River',
      1200,
      'Arial',
      measure
    )
    const narrow = applyPlotLabels(
      base,
      labels,
      'Logan River',
      300,
      'Arial',
      measure
    )
    expect(narrow.minHeight).toBeGreaterThan(wide.minHeight)
    expect(narrow.options.layout.legend.entrywidth).toBe(1)
    expect(narrow.options.layout.legend.maxheight).toBeGreaterThan(200)
    const subtitle = narrow.options.layout.annotations[0]
    expect(subtitle.text).toBe('Logan River')
    expect(narrow.options.layout.margin.t).toBeGreaterThan(subtitle.yshift + 18)
    expect(narrow.minHeight - narrow.options.layout.margin.t - 80).toBe(220)
    expect(
      narrow.options.traces.every((trace) => trace.name.includes('ellipses'))
    ).toBe(true)
  })

  it('treats user labels as plain text and keeps export configuration and zoom intact', () => {
    const base = baseOptions()
    const result = applyPlotLabels(
      base,
      [{ id: 'stream-0', label: '<b>Upstream</b> & downstream' }],
      '<i>Site</i>',
      800,
      'Arial',
      measure
    )
    expect(result.options.traces[0].name).toContain(
      '&lt;b&gt;Upstream&lt;/b&gt;'
    )
    expect(result.options.layout.annotations[0].text).toBe(
      '&lt;i&gt;Site&lt;/i&gt;'
    )
    expect(result.options.config).toBe(base.config)
    expect(result.options.layout.xaxis.range).toEqual([1, 2])
    expect(result.options.layout.uirevision).toBe('selection')
    expect(base.traces[0].name).toBe('Discharge')
    expect(base.layout.margin.t).toBe(88)
  })
})
