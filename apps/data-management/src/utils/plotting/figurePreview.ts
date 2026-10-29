import type { PlotlyOptions } from './plotly'
import { applyPlotLabels, escapePlotText, wrapPlotLabel } from './plotLabels'

export type FigureTraceLabel = {
  id: string
  name: string
  siteName: string
  color: string
}

export type FigureAxisLabel = { key: string; label: string }

export type FigureSettings = {
  title: string
  showSiteNames: boolean
  legendPosition: 'above' | 'below'
  showLegend: boolean
  fontSize: number
  aspectRatio: number
  traces: FigureTraceLabel[]
  axes: FigureAxisLabel[]
}

export const FIGURE_WIDTH = 1200

/** Build a separate figure; its labels and layout never mutate the live plot. */
export function buildFigurePreview(
  source: PlotlyOptions,
  settings: FigureSettings,
  fontFamily: string,
  measure: (text: string) => number
) {
  const { fontSize } = settings
  const colors = new Map(
    settings.traces.map((trace) => [trace.id, trace.color])
  )
  const traces = source.traces.map((trace) => {
    const color = colors.get(trace.id)
    return color
      ? {
          ...trace,
          line: { ...trace.line, color },
          marker: { ...trace.marker, color },
        }
      : trace
  })
  const layout = {
    ...source.layout,
    title: undefined,
    annotations: [],
    autosize: false,
    font: { ...source.layout.font, family: fontFamily, size: fontSize },
    margin: { l: 48, r: 48, b: Math.max(80, fontSize * 6), pad: 0 },
    showlegend: settings.showLegend,
    hovermode: false,
    dragmode: false,
  }
  for (const { key, label } of settings.axes) {
    const axis = source.layout[key]
    const axisId = key === 'yaxis' ? 'y' : key.replace('axis', '')
    const axisColors = new Set(
      traces
        .filter(
          (trace) =>
            (trace.yaxis ?? 'y') === axisId &&
            trace.visible !== false &&
            trace.visible !== 'legendonly'
        )
        .map((trace) => trace.line?.color)
    )
    const axisColor =
      key.startsWith('y') && axisColors.size === 1
        ? [...axisColors][0]
        : undefined
    layout[key] = {
      ...axis,
      automargin: false,
      fixedrange: true,
      ...(axisColor ? { linecolor: axisColor } : {}),
      tickfont: {
        ...axis.tickfont,
        family: fontFamily,
        size: fontSize * 0.85,
        ...(axisColor ? { color: axisColor } : {}),
      },
      title: {
        ...axis.title,
        text: escapePlotText(label).replace(/\r?\n/g, '<br>'),
        font: {
          ...axis.title?.font,
          family: fontFamily,
          size: fontSize,
          ...(axisColor ? { color: axisColor } : {}),
        },
      },
      ...(key.startsWith('x')
        ? { rangeselector: null, rangeslider: { visible: false } }
        : {}),
    }
  }
  const labels = settings.traces.map((trace) => ({
    id: trace.id,
    label:
      trace.name +
      (settings.showSiteNames && trace.siteName ? `\n@ ${trace.siteName}` : ''),
  }))
  const baseOptions = {
    ...source,
    traces,
    layout,
    config: {
      staticPlot: true,
      displayModeBar: false,
      responsive: false,
      displaylogo: false,
    },
  }
  let labeled = applyPlotLabels(
    baseOptions,
    labels,
    FIGURE_WIDTH,
    fontFamily,
    measure,
    { title: settings.title, fontSize, legendPosition: settings.legendPosition }
  )
  const desiredHeight = Math.round(FIGURE_WIDTH / settings.aspectRatio)
  for (const { key, label } of settings.axes) {
    const axisLength = key.startsWith('y')
      ? desiredHeight -
        labeled.options.layout.margin.t -
        labeled.options.layout.margin.b -
        48
      : FIGURE_WIDTH *
          ((layout[key].domain?.[1] ?? 1) - (layout[key].domain?.[0] ?? 0)) -
        120
    layout[key].title.text = wrapPlotLabel(
      label,
      Math.max(120, axisLength / 1.1),
      measure
    )
      .map(escapePlotText)
      .join('<br>')
  }
  labeled = applyPlotLabels(
    baseOptions,
    labels,
    FIGURE_WIDTH,
    fontFamily,
    measure,
    { title: settings.title, fontSize, legendPosition: settings.legendPosition }
  )
  const height = Math.max(desiredHeight, labeled.minHeight)
  if (settings.legendPosition === 'below') {
    // Place the legend after the space reserved for X-axis ticks and title.
    const plotHeight =
      height - labeled.options.layout.margin.t - labeled.options.layout.margin.b
    labeled.options.layout.legend.y = -layout.margin.b / plotHeight
  }
  return {
    ...labeled.options,
    layout: { ...labeled.options.layout, width: FIGURE_WIDTH, height },
  }
}
