import type { PlotlyOptions } from './plotly'

export const escapePlotText = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** Wrap plain text, including unbroken identifiers, without dropping content. */
export function wrapPlotLabel(
  text: string,
  width: number,
  measure: (text: string) => number
): string[] {
  return text.split(/\r?\n/).flatMap((paragraph) => {
    const lines: string[] = []
    let line = ''
    for (const word of paragraph.trim().split(/\s+/)) {
      if (line && measure(`${line} ${word}`) > width) {
        lines.push(line)
        line = ''
      }
      // A single long word must also fit (site codes often have no spaces).
      for (const character of `${line ? ' ' : ''}${word}`) {
        if (line && measure(line + character) > width) {
          lines.push(line)
          line = ''
        }
        line += character
      }
    }
    lines.push(line)
    return lines
  })
}

/** Keep the same fully expanded legend in the live chart and Plotly exports. */
export function applyPlotLabels(
  options: PlotlyOptions,
  labels: { id: string; label: string }[],
  width: number,
  fontFamily: string,
  measure: (text: string) => number,
  {
    title = '',
    fontSize = 12,
    legendPosition = 'above',
  }: {
    title?: string
    fontSize?: number
    legendPosition?: 'above' | 'below'
  } = {}
): { options: PlotlyOptions; minHeight: number } {
  const availableWidth = Math.max(
    80,
    width -
      (options.layout.margin?.l ?? 0) -
      (options.layout.margin?.r ?? 0) -
      32
  )
  const textWidth = Math.min((230 * fontSize) / 12, availableWidth - 56)
  const lineHeight = fontSize * 1.5
  const labelsById = new Map(labels.map((item) => [item.id, item.label]))
  const lines = options.traces.map((trace) =>
    wrapPlotLabel(labelsById.get(trace.id) ?? trace.name, textWidth, measure)
  )
  const entryWidth = Math.max(1, ...lines.flat().map(measure)) + 56
  const columns = Math.max(1, Math.floor(availableWidth / entryWidth))
  const shownLines = lines.filter(
    (_, index) => options.traces[index].visible !== false
  )
  let legendHeight = options.layout.showlegend === false ? 0 : 8
  for (
    let i = 0;
    options.layout.showlegend !== false && i < shownLines.length;
    i += columns
  ) {
    legendHeight +=
      Math.max(...shownLines.slice(i, i + columns).map((row) => row.length)) *
        lineHeight +
      8
  }
  const xDomain = options.layout.xaxis?.domain ?? [0, 1]
  const titleGap = options.layout.xaxis?.title?.standoff ?? 24
  const titleLines = title
    ? wrapPlotLabel(title, availableWidth * (xDomain[1] - xDomain[0]), measure)
    : []
  const titleHeight = titleLines.length
    ? titleLines.length * lineHeight + titleGap
    : 0
  const aboveLegendHeight = legendPosition === 'above' ? legendHeight : 0
  const topMargin = 32 + aboveLegendHeight + titleHeight
  const bottomMargin =
    (options.layout.margin?.b ?? 80) +
    (legendPosition === 'below' && legendHeight ? legendHeight + 16 : 0)
  // A rotated axis title must also fit below the legend. Plotly does not
  // reserve vertical space for it and otherwise lets it run into the header.
  const axisTitleHeight = Math.max(
    0,
    ...Object.entries(options.layout)
      .filter(([key]) => /^yaxis\d*$/.test(key))
      .map(([, axis]) => {
        const axisTitle = (
          axis as { title?: { text?: string; font?: { size?: number } } }
        ).title
        const longestLine = Math.max(
          0,
          ...(axisTitle?.text ?? '').split(/<br\s*\/?>|\r?\n/i).map(measure)
        )
        return (
          longestLine *
            (axisTitle?.font?.size
              ? (axisTitle.font.size / fontSize) * 1.1
              : 1.4) +
          48
        )
      })
  )
  const minHeight = Math.ceil(
    topMargin + bottomMargin + Math.max(220, axisTitleHeight)
  )
  const plotHeight = Math.max(
    1,
    (options.layout.height ?? minHeight) - topMargin - bottomMargin
  )
  const layout = {
    ...options.layout,
    margin: {
      ...options.layout.margin,
      t: topMargin,
      b: bottomMargin,
    },
    legend: {
      ...options.layout.legend,
      orientation: 'h',
      x: 0,
      xanchor: 'left',
      y: legendPosition === 'above' ? 1 + titleHeight / plotHeight : 0,
      yanchor: legendPosition === 'above' ? 'bottom' : 'top',
      font: { family: fontFamily, size: fontSize },
      entrywidth: 1 / columns,
      entrywidthmode: 'fraction',
      // Plotly otherwise limits horizontal legends to half the chart height
      // and introduces a scrollbar, hiding entries in downloaded images.
      maxheight: legendHeight + 20,
    },
    annotations: [
      ...(options.layout.annotations ?? []),
      ...(titleLines.length
        ? [
            {
              name: 'figure-title',
              text: titleLines.map(escapePlotText).join('<br>'),
              xref: 'paper',
              yref: 'paper',
              x: (xDomain[0] + xDomain[1]) / 2,
              y: 1,
              xanchor: 'center',
              yanchor: 'bottom',
              yshift: titleGap,
              align: 'center',
              showarrow: false,
              font: { family: fontFamily, size: fontSize },
            },
          ]
        : []),
    ],
  }
  return {
    options: {
      ...options,
      layout,
      traces: options.traces.map((trace, index) => ({
        ...trace,
        name: lines[index].map(escapePlotText).join('<br>'),
      })),
    },
    // Let the page grow to fit the legend while retaining a usable plot area.
    minHeight,
  }
}
