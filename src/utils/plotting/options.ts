import { usePlotlyStore } from '@/store/plotly'
import { GraphSeries } from '@/types'
import type {
  Config,
  Data,
  Layout,
  LayoutAxis,
  PlotData,
  PlotlyHTMLElement,
} from 'plotly.js-dist'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQualifierStore } from '@/store/qualifiers'
import { findFirstGreaterOrEqual } from '@uwrl/qc-utils'
import { DENSITY_HIDE_MARKERS } from './internal'
import { undoZoom, redoZoom } from './zoom'
import { fitXaxisToVisible, fitYaxisToVisible } from './operations'

/**
 * Return type of `createPlotlyOption`. Plan 03-03 will reuse this shape
 * via the store's `plotlyOptions` ref so the QC app's chart options carry
 * Plotly types end-to-end.
 */
export interface PlotlyChartOptions {
  traces: Data[]
  layout: Partial<Layout>
  config: Partial<Config>
}

/**
 * Application-level trace shape: `Plotly.PlotData` plus a few QC-app-specific
 * fields (`id`, `showLegend`, custom `selected`) that the seam attaches before
 * handing the trace to Plotly.
 */
export type AppPlotlyTrace = Partial<PlotData> & {
  id?: string
  showLegend?: boolean
  selected?: { marker: { color: string; opacity?: number } }
  unselected?: { marker: { opacity?: number } }
  /**
   * Index into the full `ObservationRecord` arrays where the windowed
   * trace slice starts.
   */
  _windowStartIdx?: number
}

/**
 * Re-export of `Plotly.PlotlyHTMLElement` so callers can type their
 * `plotlyRef` without importing `plotly.js-dist` directly.
 */
export type AppPlotlyHTMLElement = PlotlyHTMLElement

/**
 * One right-side y-axis's data for the chip overlay in `Plot.vue`.
 */
export type AxisChip = {
  id: string
  lineX: number
  graphWidth: number
  title: string
  color: string
  /** Which side of the plot the axis sits on. Plot.vue uses this to
   *  stack same-side chips vertically without left- and right-side
   *  chips offsetting each other (they don't overlap horizontally). */
  side: 'left' | 'right'
  /** Visual stacking index within the chip's side, used as
   *  `--chip-idx` in Plot.vue's CSS. */
  chipIdx: number
}

// Slot 0 is reserved for the QC datastream (dark grey so it stands out
// from the lighter non-QC companions). Slots 1..8 are the light half
// of d3's category20 with red and pink removed.
export const COLORS = [
  '#3f3f3f', // QC — medium grey
  '#aec7e8', // light blue
  '#ffbb78', // light orange
  '#98df8a', // light green
  '#c5b0d5', // light purple
  '#c49c94', // light brown
  '#c7c7c7', // light gray
  '#dbdb8d', // light olive
  '#9edae5', // light cyan
]

// Darkened companion palette used for tick labels and axis titles.
export const LABEL_COLORS = [
  '#3f3f3f', // QC — dark grey (unchanged)
  '#1f77b4', // blue
  '#c06a00', // orange
  '#208020', // green
  '#7a4da3', // purple
  '#8c564b', // brown
  '#707070', // grey
  '#8a8c14', // olive
  '#117a85', // cyan
]

/** Companion text colour for a `COLORS[i]` line; falls back to QC grey. */
export const labelColorFor = (lineColor: string): string => {
  const idx = COLORS.indexOf(lineColor)
  return idx >= 0 ? LABEL_COLORS[idx] : LABEL_COLORS[0]
}

// Colour palette for qualifier-flag markers along the bottom of the plot.
// Reds and pinks are deliberately excluded — red is reserved for point
// selection.
export const QUALIFIER_COLORS = [
  '#ff7f0e', // orange
  '#2ca02c', // green
  '#9467bd', // purple
  '#17becf', // teal
  '#bcbd22', // olive
  '#8c564b', // brown
  '#1f77b4', // blue
  '#7f7f7f', // grey
]

const iconRescaleY = {
  width: 500,
  height: 600,
  path: 'M182.6 9.4c-12.5-12.5-32.8-12.5-45.3 0l-96 96c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L128 109.3l0 293.5L86.6 361.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l96 96c12.5 12.5 32.8 12.5 45.3 0l96-96c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192 402.7l0-293.5 41.4 41.4c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-96-96z',
}
// Horizontal double-arrow — FontAwesome `arrows-alt-h`.
const iconRescaleX = {
  width: 512,
  height: 512,
  path: 'M502.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-96-96c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L402.7 224 109.3 224l41.4-41.4c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-96 96c-12.5 12.5-12.5 32.8 0 45.3l96 96c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L109.3 288l293.5 0-41.4 41.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l96-96z',
}

const iconUndoZoom = {
  width: 512,
  height: 512,
  path: 'M125.7 160l50.3 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L48 224c-17.7 0-32-14.3-32-32L16 64c0-17.7 14.3-32 32-32s32 14.3 32 32l0 51.2L97.6 97.6c87.5-87.5 229.3-87.5 316.8 0s87.5 229.3 0 316.8s-229.3 87.5-316.8 0c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0c62.5 62.5 163.8 62.5 226.3 0s62.5-163.8 0-226.3s-163.8-62.5-226.3 0L125.7 160z',
}
const iconRedoZoom = {
  width: 512,
  height: 512,
  path: 'M386.3 160L336 160c-17.7 0-32 14.3-32 32s14.3 32 32 32l128 0c17.7 0 32-14.3 32-32l0-128c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 51.2L414.4 97.6c-87.5-87.5-229.3-87.5-316.8 0s-87.5 229.3 0 316.8s229.3 87.5 316.8 0c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0c-62.5 62.5-163.8 62.5-226.3 0s-62.5-163.8 0-226.3s163.8-62.5 226.3 0L386.3 160z',
}

/**
 * Collects qualifier applications for the QC datastream and emits a dedicated
 * band of scatter traces (one per unique qualifier code) at the bottom of the
 * plot. Returns null when there is nothing to render.
 */
function buildQualifierBand(
  seriesArray: GraphSeries[],
  qcDatastreamId: string | undefined,
  nonQcCounter: number,
  qcAxisSuffix: string | number
): {
  traces: AppPlotlyTrace[]
  axis: Partial<LayoutAxis>
  axisKey: string
  mainAxisBottom: number
} | null {
  if (!qcDatastreamId) return null

  const qcSeries = seriesArray.find((s) => s.id === qcDatastreamId)
  if (!qcSeries) return null

  const xData = qcSeries.data?.dataX as ArrayLike<number> | undefined
  if (!xData || !xData.length) return null

  const qualifierStore = useQualifierStore()
  const applications = qualifierStore.getApplicationsForDatastream(qcDatastreamId)
  if (!applications.length) return null

  // Group applications by qualifier code.
  const byCode = new Map<
    string,
    Array<{ index: number; appliedAt: string; appliedBy: string; description: string }>
  >()
  for (const a of applications) {
    const q = qualifierStore.qualifierById[a.qualifierId]
    if (!q) continue
    const arr = byCode.get(q.code) ?? []
    arr.push({
      index: a.index,
      appliedAt: a.appliedAt,
      appliedBy: a.appliedBy,
      description: q.description,
    })
    byCode.set(q.code, arr)
  }
  if (!byCode.size) return null

  const codes = Array.from(byCode.keys()).sort()
  const qualAxisNum =
    typeof qcAxisSuffix === 'number'
      ? qcAxisSuffix + 1
      : nonQcCounter > 0
        ? nonQcCounter + 2
        : 2
  const qualAxisName = `y${qualAxisNum}`
  const qualAxisKey = `yaxis${qualAxisNum}`

  const bandTop = 0.1
  const mainAxisBottom = 0.14

  const traces: AppPlotlyTrace[] = codes.map((code, row) => {
    const entries = byCode.get(code)!
    const xs: number[] = []
    const ys: number[] = []
    const texts: string[] = []
    for (const e of entries) {
      const x = xData[e.index]
      if (x == null || Number.isNaN(x)) continue
      xs.push(x as number)
      ys.push(row)
      const ts = new Date(e.appliedAt)
      const when = isNaN(ts.getTime()) ? e.appliedAt : ts.toLocaleString()
      texts.push(
        `<b>${code}</b>${e.description ? ' — ' + e.description : ''}` +
        `<br>Applied: ${when}` +
        `<br>By: ${e.appliedBy}`
      )
    }
    const color = QUALIFIER_COLORS[row % QUALIFIER_COLORS.length]
    return {
      x: xs,
      y: ys,
      yaxis: qualAxisName,
      type: 'scatter',
      mode: 'markers',
      name: code,
      showLegend: false,
      marker: {
        color,
        symbol: 'square',
        size: 10,
      },
      text: texts,
      hovertemplate: '%{text}<extra></extra>',
    } as AppPlotlyTrace
  })

  const axis: Partial<LayoutAxis> = {
    domain: [0, bandTop],
    range: [-0.5, codes.length - 0.5],
    tickmode: 'array',
    tickvals: codes.map((_, i) => i),
    ticktext: codes,
    tickfont: { size: 10 },
    showgrid: false,
    zeroline: false,
    fixedrange: true,
    side: 'left',
    anchor: 'x',
  }

  return { traces, axis, axisKey: qualAxisKey, mainAxisBottom }
}

export { buildQualifierBand }

export const createPlotlyOption = (
  seriesArray: GraphSeries[]
): PlotlyChartOptions => {
  const { qcDatastream, beginDate, endDate } = storeToRefs(useDataVisStore())
  const { previewMode, hiddenAxisIds, plotlyRef } = storeToRefs(
    usePlotlyStore()
  )
  const isPreview = previewMode?.value ?? false
  const hiddenAxes = hiddenAxisIds?.value ?? new Set<string>()

  // Density range for pre-seeding marker opacity.
  const live = (plotlyRef?.value as unknown as { layout?: Partial<Layout> } | null)
    ?.layout?.xaxis?.range as Array<string | number> | undefined
  const parseCoord = (v: string | number): number =>
    typeof v === 'string' ? Date.parse(v) : Number(v)
  const densityStart = live
    ? parseCoord(live[0])
    : Number(beginDate?.value?.getTime?.())
  const densityEnd = live
    ? parseCoord(live[1])
    : Number(endDate?.value?.getTime?.())
  const densityRangeValid =
    Number.isFinite(densityStart) && Number.isFinite(densityEnd)

  const traces: AppPlotlyTrace[] = []
  const yaxis: Partial<Layout> = {}

  let maxDatetime = -Infinity
  let minDatetime = Infinity

  // Axis-naming scheme:
  //   yaxis       (no suffix, primary)        — QC series
  //   yaxis2, yaxis3, … (overlaying, right)   — every non-QC series
  let nonQcAxisCount = 0
  let visibleNonQcCount = 0

  const windowStartMs = beginDate?.value?.getTime() ?? -Infinity
  const windowEndMs = endDate?.value?.getTime() ?? Infinity

  seriesArray.forEach((s) => {
    const color = s.color ?? COLORS[1]
    const rawX = s.data?.dataX
    const rawY = s.data?.dataY

    // Slice to [beginDate, endDate].
    let xData = rawX
    let yData = rawY
    if (rawX?.length && rawY?.length &&
      Number.isFinite(windowStartMs) && Number.isFinite(windowEndMs)) {
      const startIdx = findFirstGreaterOrEqual(rawX as unknown as number[], windowStartMs)
      const endIdx = findFirstGreaterOrEqual(rawX as unknown as number[], windowEndMs + 1)
      xData = rawX.subarray(startIdx, endIdx)
      yData = rawY.subarray(startIdx, endIdx)
    }

    if (xData?.length) {
      const xDataStart = xData[0] as number
      const xDataEnd = xData[xData.length - 1] as number

      maxDatetime = Math.max(xDataEnd, maxDatetime)
      minDatetime = Math.min(xDataStart, minDatetime)
    }

    const isQc = s.id === qcDatastream.value?.id
    const axisSuffix: string | number = isQc ? '' : nonQcAxisCount + 2
    const axisKey = `yaxis${axisSuffix}`
    const axisRef = `y${axisSuffix}`

    // Pre-seed marker opacity from the current visible density.
    let markerOpacity = 1
    if (densityRangeValid && xData?.length) {
      const xs = xData as unknown as number[]
      const count =
        findFirstGreaterOrEqual(xs, densityEnd) -
        findFirstGreaterOrEqual(xs, densityStart)
      if (count > DENSITY_HIDE_MARKERS) markerOpacity = 0
    }

    const trace: AppPlotlyTrace = {
      id: s.id,
      x: xData,
      y: yData,
      yaxis: axisRef,
      type: 'scattergl',
      mode: 'lines+markers',
      // https://github.com/plotly/plotly.js/issues/5927
      hoverinfo: 'skip', // Fixes performance issues, but disables tooltips
      name: s.name,
      showLegend: false,
      marker: { color, opacity: markerOpacity },
      line: { color },
    }

    if (isQc) {
      trace.marker = { ...(trace.marker ?? {}), color: COLORS[0] }
      trace.line = { ...(trace.line ?? {}), color: COLORS[0] }
      trace.selected = { marker: { color: 'red', opacity: 1 } }

      trace._windowStartIdx = (rawX?.length && Number.isFinite(windowStartMs))
        ? findFirstGreaterOrEqual(rawX as unknown as number[], windowStartMs)
        : 0

      // Title omitted on purpose — the horizontal QC chip (rendered as
      // an HTML overlay in Plot.vue) replaces Plotly's vertical title.
      ;(yaxis as Record<string, Partial<LayoutAxis>>)[axisKey] = {
        title: undefined,
        tickfont: { color: COLORS[0] },
        side: 'left',
        showline: true,
        linecolor: COLORS[0],
        automargin: true,
        tickformat: '~s',
      } as Partial<LayoutAxis>

      const { editHistory } = storeToRefs(usePlotlyStore())
      editHistory.value = s.data.history
    } else {
      // Plotly applies a global selection-fade once any trace has
      // `selectedpoints` set: every other trace's "unselected" markers
      // drop to ~0.2 opacity by default. Non-QC traces are read-only
      // context and shouldn't fade alongside the QC trace's selection,
      // so pin `unselected.marker.opacity` to the density-driven value
      // we already chose.
      trace.unselected = { marker: { opacity: markerOpacity } }

      const labelColor = labelColorFor(color)
      const isAxisVisible = !(s.id && hiddenAxes.has(s.id))
      const yAxis: Partial<LayoutAxis> = {
        title: undefined,
        tickfont: { color: labelColor },
        side: 'right',
        anchor: 'free',
        overlaying: 'y',
        zeroline: false,
        showgrid: false,
        showline: true,
        linecolor: color,
        automargin: true,
        tickformat: '~s',
        visible: isAxisVisible,
        ...(isAxisVisible
          ? {
            ...(visibleNonQcCount === 0
              ? {}
              : ({ shift: 16 } as object)),
            ...({ autoshift: true } as object),
          }
          : ({ autoshift: false } as object)),
      }
        ; (yaxis as Record<string, Partial<LayoutAxis>>)[axisKey] = yAxis
      nonQcAxisCount++
      if (isAxisVisible) visibleNonQcCount++
    }

    traces.push(trace)
  })

  // Reverse so the top of the legend paints last.
  traces.reverse()

  const counter = nonQcAxisCount
  const axisSuffix: string | number = ''

  // Qualifier flag band at the bottom of the plot.
  const qualifierBand = !isPreview && seriesArray.length
    ? buildQualifierBand(
      seriesArray,
      qcDatastream?.value?.id,
      counter,
      axisSuffix
    )
    : null
  if (qualifierBand) {
    for (const key of Object.keys(yaxis)) {
      ; (yaxis as Record<string, Partial<LayoutAxis>>)[key].domain = [
        qualifierBand.mainAxisBottom,
        1,
      ]
    }
    ; (yaxis as Record<string, Partial<LayoutAxis>>)[qualifierBand.axisKey] =
      qualifierBand.axis
    for (const t of qualifierBand.traces) {
      traces.push(t)
    }
  }

  const storeBegin = beginDate?.value?.getTime?.()
  const storeEnd = endDate?.value?.getTime?.()
  const hasData = Number.isFinite(minDatetime) && Number.isFinite(maxDatetime)
  const xRangeStart = hasData
    ? minDatetime
    : (typeof storeBegin === 'number' && Number.isFinite(storeBegin) ? storeBegin : 0)
  const xRangeEnd = hasData
    ? maxDatetime
    : (typeof storeEnd === 'number' && Number.isFinite(storeEnd) ? storeEnd : Date.now())

  const xaxis: Partial<LayoutAxis> = {
    type: 'date',
    title: undefined,
    rangeselector: undefined,
    range: [xRangeStart, xRangeEnd],
    autorange: false,
    showline: true,
    automargin: true,
  }

  const layout: Partial<Layout> = {
    xaxis,
    ...yaxis,
    dragmode: 'pan',
    hovermode: 'closest',
    title: undefined,
    margin: isPreview
      ? { l: 24, r: 24, t: 28, b: 64, pad: 0 }
      : { l: 24, r: 24, t: 32, b: 64, pad: 0 },
    showlegend: false,
  }

  // Modebar buttons. `isPreview` drops select/lasso and the Fit buttons.
  const undoZoomButton = {
    name: 'Undo zoom',
    title: 'Undo zoom',
    icon: iconUndoZoom,
    click: () => {
      void undoZoom()
    },
  }
  const redoZoomButton = {
    name: 'Redo zoom',
    title: 'Redo zoom',
    icon: iconRedoZoom,
    click: () => {
      void redoZoom()
    },
  }
  const fitXButton = {
    name: 'Fit X to visible',
    icon: iconRescaleX,
    click: fitXaxisToVisible,
  }
  const fitYButton = {
    name: 'Fit Y to visible',
    icon: iconRescaleY,
    direction: 'up',
    click: fitYaxisToVisible,
  }

  const modebarGroups: unknown[][] = isPreview
    ? [
      [undoZoomButton, redoZoomButton],
      ['zoom2d', 'zoomIn2d', 'zoomOut2d'],
      ['pan2d'],
      ['resetScale2d'],
    ]
    : [
      [undoZoomButton, redoZoomButton],
      ['zoom2d', 'zoomIn2d', 'zoomOut2d'],
      ['pan2d', 'select2d', 'lasso2d'],
      ['resetScale2d'],
      [fitXButton, fitYButton],
    ]

  const config = {
    displayModeBar: true,
    showlegend: false,
    scrollZoom: false,
    responsive: true,
    doubleClick: false,
    modeBarButtons: modebarGroups,
    edits: { shapePosition: true },
  } as unknown as Partial<Config>

  return {
    traces,
    layout,
    config,
  }
}
