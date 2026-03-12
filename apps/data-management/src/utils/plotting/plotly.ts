import { GraphSeries } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'

type YAxisConfiguration = {
  index: number
  yAxisLabel: string
  color: string
}

type YAxisConfigurationMap = Map<string, YAxisConfiguration>

export type PlotlyOptions = {
  traces: any[]
  layout: any
  config: any
  xRange: { min: number; max: number } | null
}

type PlotlyBuildOptions = {
  dataZoomStart?: number
  dataZoomEnd?: number
  xAxisRange?: { start: number; end: number } | null
  yAxisRanges?: Record<string, [number, number]>
  addLegend?: boolean
  addSummaryButton?: boolean
  addScreenshotButton?: boolean
  showRangeSlider?: boolean
  showRangeSelector?: boolean
  activeRangeSelector?: number
  uirevision?: string | number
  title?: string
  titleWrapLength?: number
}

const AXIS_SPACING = 0.06
const AXIS_CHAR_SPACING = 0.006
const AXIS_MAX_SPACING = 0.14
const MIN_EXPORT_WIDTH = 3840
const MIN_EXPORT_HEIGHT = 2160

const rangeSelectorOptions = {
  xanchor: 'left',
  x: 0,
  yanchor: 'top',
  y: -0.15,
  buttons: [
    {
      step: 'month',
      stepmode: 'backward',
      count: 1,
      label: '1m',
    },
    {
      step: 'month',
      stepmode: 'backward',
      count: 6,
      label: '6m',
    },
    {
      step: 'year',
      stepmode: 'todate',
      count: 1,
      label: 'YTD',
    },
    {
      step: 'year',
      stepmode: 'backward',
      count: 1,
      label: '1y',
    },
    {
      step: 'all',
      label: 'all',
    },
  ],
}

export function createYAxisConfigurations(
  data: GraphSeries[]
): YAxisConfigurationMap {
  const yAxisConfigurations: YAxisConfigurationMap = new Map()

  data.forEach((series) => {
    if (!yAxisConfigurations.has(series.yAxisLabel)) {
      yAxisConfigurations.set(series.yAxisLabel, {
        index: yAxisConfigurations.size,
        yAxisLabel: series.yAxisLabel,
        color: series.lineColor,
      })
    } else {
      const existingEntry = yAxisConfigurations.get(series.yAxisLabel)
      if (existingEntry && existingEntry.color !== 'black') {
        yAxisConfigurations.set(series.yAxisLabel, {
          ...existingEntry,
          color: 'black',
        })
      }
    }
  })

  return yAxisConfigurations
}

export const getXRangeBounds = (
  seriesArray: GraphSeries[]
): { min: number; max: number } | null => {
  let min = Infinity
  let max = -Infinity

  seriesArray.forEach((series) => {
    series.data.forEach((point) => {
      const ts = point.date.getTime()
      if (ts < min) min = ts
      if (ts > max) max = ts
    })
  })

  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return null
  }

  return { min, max }
}

const clampPercent = (value: number) => Math.min(100, Math.max(0, value))

const buildSummaryButton = () => {
  const { showSummaryStatistics } = storeToRefs(useDataVisStore())

  return {
    name: 'Summary Statistics',
    icon: {
      width: 512,
      height: 512,
      path: 'M64 64h384v384H64z M128 176h64v224h-64z M224 256h64v144h-64z M320 128h64v272h-64z',
    },
    click: () => {
      showSummaryStatistics.value = true
    },
  }
}

const sanitizeFilename = (value: string) => {
  const withoutTags = value.replace(/<[^>]*>/g, ' ')
  const withoutIllegalChars = withoutTags.replace(/[\\/:*?"<>|]+/g, '-')
  const collapsedWhitespace = withoutIllegalChars.replace(/\s+/g, ' ').trim()
  return collapsedWhitespace.replace(/\s+/g, '_')
}

const getPlotFilename = (seriesArray: GraphSeries[], title?: string) => {
  const rawTitle = title ?? seriesArray[0]?.name ?? 'plot'
  const sanitized = sanitizeFilename(rawTitle)
  return sanitized || 'plot'
}

const getExportConfig = (gd: any) => {
  const width = gd?._fullLayout?.width ?? gd?.clientWidth ?? 0
  const height = gd?._fullLayout?.height ?? gd?.clientHeight ?? 0

  if (
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    !width ||
    !height
  ) {
    return { width: MIN_EXPORT_WIDTH, height: MIN_EXPORT_HEIGHT, scale: 1 }
  }

  const scale = Math.max(
    MIN_EXPORT_WIDTH / width,
    MIN_EXPORT_HEIGHT / height,
    1
  )

  return {
    width: Math.round(width),
    height: Math.round(height),
    scale,
  }
}

const buildScreenshotButton = (seriesArray: GraphSeries[], title?: string) => {
  const filename = getPlotFilename(seriesArray, title)

  return {
    name: 'Download plot',
    icon: {
      width: 24,
      height: 24,
      path: 'M4 7h3l1.5-2h7L17 7h3a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2m8 2a5 5 0 0 0-5 5a5 5 0 0 0 5 5a5 5 0 0 0 5-5a5 5 0 0 0-5-5m0 2a3 3 0 0 1 3 3a3 3 0 0 1-3 3a3 3 0 0 1-3-3a3 3 0 0 1 3-3Z',
    },
    click: async (gd: any) => {
      const { width, height, scale } = getExportConfig(gd)
      const PlotlyModule = await import('plotly.js-dist')
      const Plotly = (PlotlyModule as any).default ?? PlotlyModule
      Plotly.downloadImage(gd, {
        format: 'png',
        filename,
        width,
        height,
        scale,
      })
    },
  }
}

const wrapTitle = (title: string, maxLength: number) => {
  const words = title.trim().split(/\s+/)
  let line = ''
  const lines: string[] = []

  words.forEach((word) => {
    const next = line ? `${line} ${word}` : word
    if (next.length > maxLength && line) {
      lines.push(line)
      line = word
    } else {
      line = next
    }
  })

  if (line) lines.push(line)
  return lines.join('<br>')
}

export const createPlotlyOption = (
  seriesArray: GraphSeries[],
  opts: PlotlyBuildOptions = {}
): PlotlyOptions => {
  const {
    dataZoomStart = 0,
    dataZoomEnd = 100,
    xAxisRange,
    yAxisRanges,
    addLegend = true,
    addSummaryButton = true,
    addScreenshotButton = true,
    showRangeSlider = false,
    showRangeSelector = true,
    activeRangeSelector,
    uirevision,
    title,
    titleWrapLength = 48,
  } = opts

  const yAxisConfigurations = createYAxisConfigurations(seriesArray)
  const yAxisEntries = Array.from(yAxisConfigurations.values())
  const leftCount = Math.ceil(yAxisEntries.length / 2)
  const rightCount = yAxisEntries.length - leftCount
  const legendRows = seriesArray.length > 8 ? 3 : seriesArray.length > 4 ? 2 : 1
  const legendTopMargin = 70 + legendRows * 18
  const legendYOffset = 1 + legendRows * 0.02

  const estimateTickLabelLength = (value: number) => {
    if (!Number.isFinite(value)) return 0
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 4,
    }).format(value).length
  }

  const axisValueRanges = new Map<string, { min: number; max: number }>()
  seriesArray.forEach((series) => {
    if (!series.data.length) return
    const label = series.yAxisLabel
    series.data.forEach((point) => {
      const value = point.value
      if (!Number.isFinite(value)) return
      const existing = axisValueRanges.get(label)
      if (!existing) {
        axisValueRanges.set(label, { min: value, max: value })
      } else {
        existing.min = Math.min(existing.min, value)
        existing.max = Math.max(existing.max, value)
      }
    })
  })

  const estimateAxisSpacing = (label: string) => {
    const range = axisValueRanges.get(label)
    const tickLabelLength = range
      ? Math.max(
          estimateTickLabelLength(range.min),
          estimateTickLabelLength(range.max)
        )
      : 0
    const spacing = AXIS_SPACING + (tickLabelLength + 2) * AXIS_CHAR_SPACING
    return Math.min(AXIS_MAX_SPACING, Math.max(AXIS_SPACING, spacing))
  }

  const leftAxisEntries = yAxisEntries.slice(0, leftCount)
  const rightAxisEntries = yAxisEntries.slice(leftCount)

  const leftAxisSpacings = leftAxisEntries.map((entry) =>
    estimateAxisSpacing(entry.yAxisLabel)
  )
  const rightAxisSpacings = rightAxisEntries.map((entry) =>
    estimateAxisSpacing(entry.yAxisLabel)
  )

  const leftPad = leftAxisSpacings.reduce((sum, spacing) => sum + spacing, 0)
  const rightPad = rightAxisSpacings.reduce((sum, spacing) => sum + spacing, 0)

  const buildOffsets = (spacings: number[]) => {
    let total = 0
    return spacings.map((spacing) => {
      const offset = total
      total += spacing
      return offset
    })
  }

  const leftOffsets = buildOffsets(leftAxisSpacings)
  const rightOffsets = buildOffsets(rightAxisSpacings)

  const xRange = getXRangeBounds(seriesArray)
  const span = xRange ? xRange.max - xRange.min : 0
  const rangeStart = xRange
    ? xRange.min + (span * clampPercent(dataZoomStart)) / 100
    : undefined
  const rangeEnd = xRange
    ? xRange.min + (span * clampPercent(dataZoomEnd)) / 100
    : undefined
  const resolvedRangeStart =
    xAxisRange && Number.isFinite(xAxisRange.start)
      ? xAxisRange.start
      : rangeStart
  const resolvedRangeEnd =
    xAxisRange && Number.isFinite(xAxisRange.end) ? xAxisRange.end : rangeEnd

  const xDomainStart = leftCount ? leftPad : AXIS_SPACING
  const xDomainEnd = rightCount ? 1 - rightPad : 1 - AXIS_SPACING

  const titleText = title
  const titleColor = seriesArray[0]?.lineColor

  const layout: any = {
    margin: { l: 4, r: 0, t: legendTopMargin, b: 70, pad: 0 },
    showlegend: addLegend,
    legend: addLegend
      ? {
          orientation: 'h',
          x: 0,
          xanchor: 'left',
          y: legendYOffset,
          yanchor: 'bottom',
        }
      : undefined,
    hovermode: 'x',
    dragmode: 'pan',
    xaxis: {
      type: 'date',
      showline: true,
      showgrid: true,
      gridcolor: '#e6e6e6',
      gridwidth: 1,
      domain: [xDomainStart, xDomainEnd],
      title: { text: 'Datetime', standoff: 24 },
      automargin: true,
      range:
        resolvedRangeStart !== undefined && resolvedRangeEnd !== undefined
          ? [resolvedRangeStart, resolvedRangeEnd]
          : undefined,
      autorange:
        resolvedRangeStart === undefined || resolvedRangeEnd === undefined,
      rangeselector: showRangeSelector
        ? {
            ...rangeSelectorOptions,
            active: activeRangeSelector,
          }
        : null,
      rangeslider: showRangeSlider ? { visible: true } : { visible: false },
    },
    title: titleText
      ? {
          text: wrapTitle(titleText, titleWrapLength),
          font: titleColor ? { color: titleColor } : undefined,
          x: 0,
          xanchor: 'left',
          y: 0.98,
        }
      : undefined,
  }
  if (uirevision !== undefined) {
    layout.uirevision = uirevision
  }

  const markerSymbols = ['circle', 'square', 'triangle-up', 'x', 'diamond']

  const traces = seriesArray.map((series, index) => {
    const axisConfig = yAxisConfigurations.get(series.yAxisLabel)
    const axisIndex = axisConfig?.index ?? 0
    const axisId = axisIndex === 0 ? 'y' : `y${axisIndex + 1}`
    const symbol = markerSymbols[index % markerSymbols.length]

    return {
      id: series.id,
      name: wrapTitle(series.name, 28),
      x: series.data.map((dp) => dp.date.getTime()),
      y: series.data.map((dp) => dp.value),
      yaxis: axisId,
      type: 'scattergl',
      mode: 'lines+markers',
      line: { color: series.lineColor, width: 2 },
      marker: { color: series.lineColor, size: 6, symbol },
      hoverinfo: 'y',
      hovertemplate: '<b>%{y}</b><extra></extra>',
    }
  })

  yAxisEntries.forEach((axisConfig, index) => {
    const axisKey = index === 0 ? 'yaxis' : `yaxis${index + 1}`
    const side = index < leftCount ? 'left' : 'right'
    const sideIndex = side === 'left' ? index : index - leftCount
    const position =
      side === 'left'
        ? xDomainStart - leftOffsets[sideIndex]
        : xDomainEnd + rightOffsets[sideIndex]

    layout[axisKey] = {
      title: {
        text: axisConfig.yAxisLabel,
        font: { color: axisConfig.color },
        standoff: 12,
      },
      tickfont: { color: axisConfig.color },
      side,
      anchor: 'free',
      position,
      showline: true,
      linecolor: axisConfig.color,
      zeroline: false,
      showgrid: index === 0,
      gridcolor: '#e6e6e6',
      gridwidth: 1,
      overlaying: index === 0 ? undefined : 'y',
      autorange: true,
      automargin: false,
    }

    const axisRange = yAxisRanges?.[axisKey]
    if (
      axisRange &&
      Number.isFinite(axisRange[0]) &&
      Number.isFinite(axisRange[1])
    ) {
      layout[axisKey].range = axisRange
      layout[axisKey].autorange = false
    }
  })

  const config: any = {
    displayModeBar: true,
    displaylogo: false,
    scrollZoom: true,
    responsive: true,
    doubleClick: false,
    modeBarButtonsToRemove: ['toImage', 'autoScale', 'lasso2d', 'select2d'],
  }

  const extraButtons = []
  if (addScreenshotButton)
    extraButtons.push(buildScreenshotButton(seriesArray, titleText))
  if (addSummaryButton) extraButtons.push(buildSummaryButton())
  if (extraButtons.length) config.modeBarButtonsToAdd = extraButtons

  return { traces, layout, config, xRange }
}
