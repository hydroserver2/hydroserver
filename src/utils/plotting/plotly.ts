import { usePlotlyStore } from '@/store/plotly'
import { GraphSeries } from '@/types'
import Plotly from 'plotly.js-dist'
import type {
  Config,
  Data,
  Layout,
  LayoutAxis,
  PlotData,
  PlotlyHTMLElement,
  PlotMouseEvent,
  PlotRelayoutEvent,
  PlotSelectionEvent,
  PrivatePlotlyHTMLElement,
  RangeSelector,
} from 'plotly.js-dist'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQualifierStore } from '@/store/qualifiers'
import { debounce, isEqual } from 'lodash-es'
import { EnumFilterOperations, findFirstGreaterOrEqual } from '@uwrl/qc-utils'

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
 * handing the trace to Plotly. Using an intersection avoids excess-property
 * errors on the literal trace objects below while still typing the standard
 * Plotly fields.
 *
 * Exported so call sites outside the seam (e.g. `PlottedDatastreams.vue` find
 * callbacks) can narrow `plotlyRef.value.data[i]` without re-introducing
 * `any` for the QC-app-attached `id` field.
 */
export type AppPlotlyTrace = Partial<PlotData> & {
  id?: string
  showLegend?: boolean
  selected?: { marker: { color: string } }
}

/**
 * Re-export of `Plotly.PlotlyHTMLElement` so callers (the Pinia store, the
 * `useDataSelection` composable, and components) can type their `plotlyRef`
 * against this alias instead of importing `plotly.js-dist` directly. Keeps
 * the runtime + type surface for Plotly localized to this seam (CONV-013).
 */
export type AppPlotlyHTMLElement = PlotlyHTMLElement

/**
 * Re-export of selected Plotly event types so callers (notably
 * `useDataSelection`) can pass typed event-shaped arguments to the
 * `handleSelected` wrapper without importing `plotly.js-dist` themselves.
 */
export type AppPlotMouseEvent = PlotMouseEvent
export type AppPlotRelayoutEvent = PlotRelayoutEvent
export type AppPlotSelectionEvent = PlotSelectionEvent

// DATA-CAST: Plotly.Data.x is typed broadly (Datum[] | Datum[][] | TypedArray
// | undefined) but every trace this app produces stores numeric epoch
// timestamps in `x`. Centralise the cast here so binary-search call sites
// (findFirstGreaterOrEqual in handleRelayout / fitYaxisToVisible) get number[]
// without scattering `as number[]` across the file. If we ever introduce
// non-numeric x data, this is the single place to reconsider.
const traceXAsNumbers = (
  gd: PlotlyHTMLElement | null | undefined,
  traceIndex: number
): number[] => {
  const x = gd?.data[traceIndex]?.x
  return (x ?? []) as number[]
}

// Slot 0 is reserved for the QC datastream (dark grey so it stands out
// from the lighter non-QC companions). Slots 1..8 are the light half
// of d3's category20 with red and pink removed — those reserved hues
// clash with the red highlight used on selected points.
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

// Darkened companion palette used for tick labels and axis titles. Each
// slot keeps the hue of its `COLORS[i]` pastel so readers still match
// text to its axis line, but the lightness drops enough to clear WCAG
// AA contrast on white — the pastels alone read as washed-out text.
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
// Assigned deterministically per qualifier code (by sorted order).
export const QUALIFIER_COLORS = [
  '#d62728',
  '#ff7f0e',
  '#2ca02c',
  '#9467bd',
  '#17becf',
  '#bcbd22',
  '#e377c2',
  '#8c564b',
]

const selectorOptions: Partial<RangeSelector> = {
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
    },
  ],
}
const iconRescaleY = {
  width: 500,
  height: 600,
  path: 'M182.6 9.4c-12.5-12.5-32.8-12.5-45.3 0l-96 96c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L128 109.3l0 293.5L86.6 361.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l96 96c12.5 12.5 32.8 12.5 45.3 0l96-96c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192 402.7l0-293.5 41.4 41.4c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-96-96z',
}
// Horizontal double-arrow — FontAwesome `arrows-alt-h`. Sibling of
// `iconRescaleY` used for the custom Autoscale-X modebar button.
const iconRescaleX = {
  width: 512,
  height: 512,
  path: 'M502.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-96-96c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L402.7 224 109.3 224l41.4-41.4c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-96 96c-12.5 12.5-12.5 32.8 0 45.3l96 96c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L109.3 288l293.5 0-41.4 41.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l96-96z',
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

export const createPlotlyOption = (
  seriesArray: GraphSeries[]
): PlotlyChartOptions => {
  const { qcDatastream, beginDate, endDate } = storeToRefs(useDataVisStore())
  const { previewMode } = storeToRefs(usePlotlyStore())
  const isPreview = previewMode?.value ?? false

  const traces: AppPlotlyTrace[] = []
  const yaxis: Partial<Layout> = {}

  let maxDatetime = -Infinity
  let minDatetime = Infinity

  // Axis-naming scheme:
  //   yaxis       (no suffix, primary)        — QC series
  //   yaxis2, yaxis3, … (overlaying, right)   — every non-QC series
  // Every non-QC axis gets `autoshift: true`, which requires `overlaying`
  // to take effect. When the first non-QC ran at the primary `y` slot
  // (old logic) it could not autoshift and collided with the first
  // shifted sibling — that's the "missing axis, overlapping neighbour"
  // bug.
  let nonQcAxisCount = 0

  seriesArray.forEach((s) => {
    // Colour is persisted on the GraphSeries at fetch time (see
    // `store/plotly.ts#assignFreeColor`), so dragging a row up or down
    // in PlottedDatastreams leaves its line colour intact. QC always
    // overrides with `COLORS[0]` (black) below.
    const color = s.color ?? COLORS[1]
    const xData = s.data?.dataX

    if (xData?.length) {
      const xDataStart = xData[0] as number
      const xDataEnd = xData[xData.length - 1] as number

      maxDatetime = Math.max(xDataEnd, maxDatetime)
      minDatetime = Math.min(xDataStart, minDatetime)
    }

    const isQc = s.id === qcDatastream.value?.id
    // QC goes on the primary `y`; each non-QC gets a fresh `yaxisN+2`.
    const axisSuffix: string | number = isQc ? '' : nonQcAxisCount + 2
    const axisKey = `yaxis${axisSuffix}`
    const axisRef = `y${axisSuffix}`

    const trace: AppPlotlyTrace = {
      id: s.id,
      x: s.data?.dataX,
      y: s.data?.dataY,
      yaxis: axisRef,
      type: 'scattergl',
      mode: 'lines+markers',
      // https://github.com/plotly/plotly.js/issues/5927
      hoverinfo: 'skip', // Fixes performance issues, but disables tooltips
      // hoverinfo: 'x+y',
      name: s.name,
      showLegend: false,
      marker: { color },
      line: { color },
    }

    if (isQc) {
      trace.marker = { ...(trace.marker ?? {}), color: COLORS[0] }
      trace.line = { ...(trace.line ?? {}), color: COLORS[0] }
      trace.selected = { marker: { color: 'red' } }

        ; (yaxis as Record<string, Partial<LayoutAxis>>)[axisKey] = {
          title: {
            text: s.yAxisLabel,
            font: { color: COLORS[0], weight: 'bold' },
          },
          tickfont: { color: COLORS[0] },
          side: 'left',
          showline: true,
          linecolor: COLORS[0],
          // Let Plotly compute the margin needed for ticks + title so they
          // never get clipped, regardless of label length.
          automargin: true,
          // Force SI tick abbreviation ("2k" instead of "2000") and keep
          // it stable across pans. Plotly's default `exponentformat` can
          // flip between SI and decimal depending on the visible range;
          // pinning `tickformat` makes it consistent.
          tickformat: '~s',
        } as Partial<LayoutAxis>

      const { editHistory } = storeToRefs(usePlotlyStore())
      editHistory.value = s.data.history
    } else {
      // Every non-QC axis is an overlay on the primary `y` with
      // `autoshift`, so Plotly stacks them pixel-wise on the right side
      // without collisions, regardless of label widths. Label text uses
      // the paired darker shade of the pastel (see `LABEL_COLORS`) so
      // the title/ticks match the axis line but are legible on white.
      const labelColor = labelColorFor(color)
      const yAxis: Partial<LayoutAxis> = {
        title: {
          text: s.yAxisLabel,
          font: { color: labelColor, weight: 'bold' },
        },
        tickfont: { color: labelColor },
        side: 'right',
        anchor: 'free',
        overlaying: 'y',
        zeroline: false,
        showgrid: false,
        showline: true,
        linecolor: color,
        automargin: true,
        // Force SI tick abbreviation ("2k" instead of "2000") and keep
        // it stable across pans (see primary yaxis above).
        tickformat: '~s',
        // `autoshift` is not in the published @types/plotly.js surface
        // yet, but is supported at runtime.
        ...({ autoshift: true } as object),
      }
        ; (yaxis as Record<string, Partial<LayoutAxis>>)[axisKey] = yAxis
      nonQcAxisCount++
    }

    traces.push(trace)
  })

  // Plotly paints traces in array order, so later indices land on top.
  // Reverse so the top of the legend paints last — dragging a row up in
  // PlottedDatastreams brings it visually in front, which matches how
  // layer panels work in design tools. Axis numbering was already
  // resolved above via `nonQcAxisCount`, so flipping the trace order
  // here doesn't affect the axis assignments.
  traces.reverse()

  // Kept for the qualifier-band helper which reads these to pick its own
  // axis suffix.
  const counter = nonQcAxisCount
  const axisSuffix: string | number = ''

  // Qualifier flag band at the bottom of the plot.
  // One scatter trace per unique qualifier code; stacked by row in a dedicated y-axis.
  // `qcDatastream` may be undefined here during the pinia circular-init from
  // `plotlyStore` <-> `dataVisStore`; skip safely in that case.
  // Suppressed in preview mode — the qualifier band is an editing affordance.
  const qualifierBand = !isPreview && seriesArray.length
    ? buildQualifierBand(
      seriesArray,
      qcDatastream?.value?.id,
      counter,
      axisSuffix
    )
    : null
  if (qualifierBand) {
    // Shrink main y-axes so the qualifier band has room at the bottom.
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

  // Clip to the user's selected begin/end when available, so choosing a
  // preset or typing a custom range on the sidebar pins the x-axis to
  // that exact window regardless of whether the returned observations
  // reach both ends. Falls back to the data extent if the store hasn't
  // resolved a range yet (first render, no datastream plotted).
  const storeBegin = beginDate?.value?.getTime?.()
  const storeEnd = endDate?.value?.getTime?.()
  const xRangeStart =
    typeof storeBegin === 'number' && Number.isFinite(storeBegin)
      ? storeBegin
      : minDatetime
  const xRangeEnd =
    typeof storeEnd === 'number' && Number.isFinite(storeEnd)
      ? storeEnd
      : maxDatetime

  const xaxis: Partial<LayoutAxis> = {
    type: 'date',
    // Drop the "Datetime" axis title and the rangeselector buttons —
    // both live in the custom toolbar above the chart now, so keeping
    // them inside Plotly only wastes chart height.
    title: undefined,
    rangeselector: undefined,
    range: [xRangeStart, xRangeEnd],
    autorange: false,
    showline: true,
    // range slider compatibility for Scattergl: https://github.com/plotly/plotly.js/issues/2627
  }

  // Secondary right-side axes now rely on Plotly's `autoshift` +
  // `automargin` (see the non-QC yaxis block above) to stack themselves
  // outside the plot area without collisions, so the hand-rolled xaxis
  // domain shrink is no longer needed.

  const layout: Partial<Layout> = {
    spikedistance: 0, // https://github.com/plotly/plotly.js/issues/5927#issuecomment-1697679087
    // hoverdistance: 20,
    xaxis,
    ...yaxis,
    dragmode: 'pan',
    hovermode: 'closest', // Disable if hovering is too costly
    // Title is omitted everywhere — the custom toolbar above the chart
    // (both in Select preview and Edit) already names the series, and
    // Plotly's built-in title steals a whole row of chart height.
    title: undefined,
    // Tight margins reclaim the generous default whitespace around the
    // chart. Per-axis `automargin: true` lets Plotly grow l/r as needed
    // to fit stacked y-axes and their titles. The top margin leaves
    // headroom for Plotly's modebar (top-right) so it doesn't overlap
    // the first tick label — preview needs roughly the same budget as
    // edit because the modebar is the same height either way.
    margin: isPreview
      ? { l: 24, r: 24, t: 28, b: 32, pad: 0 }
      : { l: 16, r: 16, t: 24, b: 32, pad: 0 },
    showlegend: false,
  }

  const config = {
    displayModeBar: true,
    showlegend: false,
    // `select2d` / `lasso2d` are editing affordances — strip them from
    // the preview modebar along with the custom Autoscale-Y button.
    modeBarButtonsToRemove: isPreview
      ? ['toImage', 'autoScale', 'select2d', 'lasso2d']
      : ['toImage', 'autoScale'],
    scrollZoom: true,
    responsive: true,
    doubleClick: false,
    modeBarButtonsToAdd: isPreview
      ? []
      : [
        {
          name: 'Fit X to visible',
          icon: iconRescaleX,
          click: fitXaxisToVisible,
        },
        {
          name: 'Fit Y to visible',
          icon: iconRescaleY,
          direction: 'up',
          click: fitYaxisToVisible,
        },
      ],
    // plotGlPixelRatio: 1,
  } as unknown as Partial<Config>

  return {
    traces,
    layout,
    config,
  }
}

export const handleClick = async (eventData: PlotMouseEvent) => {
  const { plotlyRef } = storeToRefs(usePlotlyStore())

  const point = eventData.points[0]
  if (point) {
    // `PlotDatum.data` is `Partial<PlotData>`; `selectedpoints` is not in
    // the published type but Plotly attaches it at runtime.
    const pointData = point.data as Partial<PlotData> & {
      selectedpoints?: number | number[]
    }
    let alreadySelected: number[] = []

    if (pointData.selectedpoints != null) {
      alreadySelected = Array.isArray(pointData.selectedpoints)
        ? [...pointData.selectedpoints as number[]]
        : [pointData.selectedpoints]
    }

    const index = alreadySelected.indexOf(point.pointIndex)
    // Toggle the point
    index >= 0
      ? alreadySelected.splice(index, 1)
      : alreadySelected.push(point.pointIndex)

    alreadySelected.sort()

    // Removes selected areas
    await Plotly.update(plotlyRef.value as Plotly.Root, {}, { selections: [] }, [0])

    // Colors selected points
    await Plotly.restyle(plotlyRef.value as Plotly.Root, {
      selectedpoints: [[...alreadySelected]],
    })

    handleSelected(eventData)
  }
}

/**
 * `handleSelected` is called from `handleClick` (with a `PlotMouseEvent`),
 * from `handleRelayout` (with a `PlotRelayoutEvent`-shaped object), and
 * occasionally with `null`/`undefined` to mean "re-sync the QC selection
 * without dispatching a filter". We accept the union explicitly so
 * call-site keys (`dragmode`, `'xaxis.range[0]'`) typecheck against
 * `PlotRelayoutEvent`.
 */
export const handleSelected = async (
  eventData?: PlotMouseEvent | PlotRelayoutEvent | PlotSelectionEvent | null
) => {
  const { plotlyRef, selectedSeries } = storeToRefs(usePlotlyStore())
  const { selectedData } = storeToRefs(useDataVisStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())

  // Plotly attaches the QC trace's app-level `id` and runtime `selectedpoints`
  // to each entry in `data`; neither is on the published `PlotData` shape, so
  // narrow with the app trace augmentation defined at module scope.
  const trace = plotlyRef.value?.data.find(
    (t) => (t as AppPlotlyTrace).id == qcDatastream.value?.id
  ) as (AppPlotlyTrace & { selectedpoints?: number[] }) | undefined

  selectedData.value = trace?.selectedpoints || null

  // PlotRelayoutEvent extends Partial<Layout>; `dragmode` is in Layout.
  // PlotMouseEvent has no `dragmode` so the property access narrows to
  // optional via the union.
  const relayout = eventData as Partial<PlotRelayoutEvent> | null | undefined
  if (
    relayout?.dragmode || // Changing selected tool
    relayout?.['xaxis.range[0]'] // Zooming
  ) {
    return
  }

  if (eventData) {
    await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.SELECTION,
      trace?.selectedpoints
    )

    // Sync Vue's reactive editHistory with the raw history array
    // (dispatchFilter mutates the array outside Vue's proxy)
    const { editHistory } = storeToRefs(usePlotlyStore())
    editHistory.value = selectedSeries.value?.data.history ?? []
  }

  // TODO: prevent selection on other traces
}

// export const handlePlotlySelected = async (eventData?: any) => {
//   console.log('handlePlotlySelected')
//   const { plotlyRef } = storeToRefs(usePlotlyStore())
//   const { qcDatastream } = storeToRefs(useDataVisStore())

//   const trace = plotlyRef.value?.data.find(
//     (trace: any) => trace.id == qcDatastream.value?.id
//   )

//   // Dispatch selection to qc-utils
//   // console.log(eventData)
//   if (eventData) {
//     const { selectedSeries } = storeToRefs(usePlotlyStore())
//     await selectedSeries.value?.data.dispatchFilter(
//       EnumFilterOperations.SELECTION,
//       trace?.selectedpoints
//     )
//   }

//   // TODO: prevent selection on other traces
// }

export const handleNewPlot = async (
  element?: HTMLElement,
  opts?: { preserveZoom?: boolean }
) => {
  const { plotlyOptions, plotlyRef } = storeToRefs(usePlotlyStore())

  // Rebuild cases like reordering the legend or changing the QC target
  // re-run `Plotly.newPlot`, which otherwise reverts every axis to the
  // defaults baked into `createPlotlyOption`. When asked to preserve
  // zoom, copy the live ranges off the outgoing figure: x is shared so
  // it goes straight across; per-series y ranges are keyed by series id
  // so they follow the series to whatever yaxis slot it lands on after
  // the reshuffle (e.g. `yaxis2` → `yaxis3` when a non-QC trace moves
  // past the QC target).
  if (
    opts?.preserveZoom &&
    !element &&
    plotlyRef.value?.layout &&
    plotlyRef.value?.data
  ) {
    const oldLayout = plotlyRef.value.layout as Record<string, unknown>
    const newLayout = plotlyOptions.value.layout as Record<string, unknown>

    const oldXRange = (oldLayout.xaxis as Partial<LayoutAxis> | undefined)
      ?.range as Array<string | number> | undefined
    const newXAxis = newLayout.xaxis as Partial<LayoutAxis> | undefined
    if (oldXRange && newXAxis) {
      newXAxis.range = [...oldXRange]
      newXAxis.autorange = false
    }

    const yAxisKey = (yref: string | undefined) =>
      `yaxis${(yref ?? 'y').slice(1)}`

    const yRangesBySeriesId: Record<string, Array<string | number>> = {}
    for (const trace of plotlyRef.value.data) {
      const t = trace as AppPlotlyTrace
      if (!t.id) continue
      const key = yAxisKey(t.yaxis as string | undefined)
      const range = (oldLayout[key] as Partial<LayoutAxis> | undefined)
        ?.range as Array<string | number> | undefined
      if (range) yRangesBySeriesId[t.id] = range
    }

    for (const trace of plotlyOptions.value.traces) {
      const t = trace as AppPlotlyTrace
      if (!t.id) continue
      const oldRange = yRangesBySeriesId[t.id]
      if (!oldRange) continue
      const key = yAxisKey(t.yaxis as string | undefined)
      const nextAxis = newLayout[key] as Partial<LayoutAxis> | undefined
      if (nextAxis) {
        nextAxis.range = [...oldRange]
        nextAxis.autorange = false
      }
    }
  }

  // `Plotly.newPlot` returns `Promise<PlotlyHTMLElement>`. The store's
  // `plotlyRef` is now typed as `PlotlyHTMLElement | null`
  const newElement = await Plotly.newPlot(
    element || plotlyRef.value as Plotly.Root,
    plotlyOptions.value.traces,
    plotlyOptions.value.layout,
    plotlyOptions.value.config
  )
  plotlyRef.value = newElement as unknown as typeof plotlyRef.value

  const debounceDelay = 250

  handleRelayout(null)

  // `.on('plotly_redraw', cb)` expects `() => void` per the published types,
  // but we reuse the same debounced relayout handler (which accepts an
  // optional event). Wrap to satisfy the no-arg overload.
  plotlyRef.value?.on(
    'plotly_redraw',
    debounce(() => handleRelayout(null), debounceDelay)
  )
  plotlyRef.value?.on(
    'plotly_relayout',
    debounce(handleRelayout, debounceDelay)
  )
  // plotlyRef.value?.on(
  //   'plotly_selected',
  //   debounce(handleSelected, debounceDelay)
  // )
  // plotlyRef.value?.on('plotly_deselec', debounce(handleSelected, debounceDelay))

  plotlyRef.value?.on('plotly_click', handleClick)
  // plotlyRef.value?.on('plotly_doubleclick', handleDoubleClick)

  plotlyRef.value?.removeEventListener('mousemove', handleMouseMove);
  plotlyRef.value?.addEventListener('mousemove', handleMouseMove);
  plotlyRef.value?.addEventListener('mouseout', handleMouseOut);
}

export const handleRelayout = async (
  eventData: PlotRelayoutEvent | null
) => {
  const {
    plotlyOptions,
    plotlyRef,
    isUpdating,
    areTooltipsEnabled,
    visiblePoints,
    tooltipsMaxDataPoints,
  } = storeToRefs(usePlotlyStore())

  handleSelected(eventData)

  // Plotly fires the relayout event for practically everything.
  // We only need to handle it when panning or zooming.
  // `selections` and `'selections[0].x0'` aren't on `PlotRelayoutEvent`'s
  // public surface but Plotly attaches them at runtime; widen narrowly.
  const evt = eventData as
    | (PlotRelayoutEvent & {
      selections?: unknown
      'selections[0].x0'?: unknown
    })
    | null
  if (
    isUpdating.value ||
    evt?.dragmode || // Changing selected tool
    evt?.selections || // Selecting points
    evt?.['selections[0].x0'] || // Moving a selected area
    isEqual(eventData, {}) // Double click using pan tool
  ) {
    return
  }

  isUpdating.value = true

  setTimeout(async () => {
    try {
      const layoutUpdates: Partial<Layout> = { ...plotlyOptions.value.layout }
      // `Layout.xaxis.range` is `any[]` in @types/plotly.js; the runtime
      // values are string|number for date axes. Treat the working copy as
      // an array we can rewrite in-place without losing precision.
      const xRange = (layoutUpdates.xaxis as Partial<LayoutAxis> | undefined)
        ?.range as Array<string | number> | undefined

      // Plotly will rewrite timestamps as datestrings. We need to convert them back to timestamps.
      if (xRange && typeof xRange[0] == 'string') {
        xRange[0] = Date.parse(xRange[0])
        xRange[1] = Date.parse(xRange[1] as string)
      }

      visiblePoints.value = 0

      // Find number of visible points
      const traceCount = plotlyRef.value?.data.length ?? 0
      for (let i = 0; i < traceCount; i++) {
        // Plotly does not return the indexes of current x-axis extent. We must find them using binary search.
        const xs = traceXAsNumbers(plotlyRef.value, i)
        const startIdx = findFirstGreaterOrEqual(xs, xRange?.[0])
        const endIdx = findFirstGreaterOrEqual(xs, xRange?.[1])
        visiblePoints.value += endIdx - startIdx
      }

      // Threshold check
      let newHoverState = 'x+y'
      let newHoverTemplate: string = '<b>%{y}</b><br>%{x}<extra></extra>'

      if (
        visiblePoints.value > tooltipsMaxDataPoints.value ||
        !areTooltipsEnabled.value
      ) {
        newHoverState = 'skip'
        newHoverTemplate = ''
      }

      // Only update if state changed
      if (plotlyRef.value?.data[0].hoverinfo !== newHoverState) {
        if (newHoverState === 'x+y' && !areTooltipsEnabled.value) {
          return
        }

        await Plotly.restyle(plotlyRef.value, {
          hoverinfo: newHoverState,
          hovertemplate: newHoverTemplate,
        } as Partial<PlotData>)
      }
    } finally {
      isUpdating.value = false
    }
  })
}

// export const handleDoubleClick = async (_event: MouseEvent) => {
//   const { plotlyRef } = storeToRefs(usePlotlyStore())

//   // Removes selected areas
//   await Plotly.update(
//     plotlyRef.value,
//     {},
//     { selections: [], selectedpoints: [[]] },
//     [0]
//   )

//   // Updates the color
//   await Plotly.restyle(plotlyRef.value, {
//     selectedpoints: [[]],
//   })

//   const { selectedData } = storeToRefs(useDataVisStore())
//   selectedData.value = []
// }

// TODO: work in progress
export const handleMouseMove = async (event: MouseEvent) => {
  const { plotlyRef, hover, showCoordinates } = storeToRefs(usePlotlyStore())

  // PRIVATE-API: `_fullLayout` (and the `xaxis.p2c` / `yaxis.p2c` pixel-to-data
  // converters it exposes) are undocumented Plotly internals used here for
  // mouse-move coordinate conversion. They have no public type — see
  // `src/types/plotly-dist.d.ts` for the local `PrivatePlotlyHTMLElement`
  // augmentation. If these break in a future Plotly version, switch to a
  // published gestures API or recompute coordinates from `layout.range`.
  const gd = plotlyRef.value as unknown as PrivatePlotlyHTMLElement | null
  const fullLayout = gd?._fullLayout
  if (!fullLayout) return

  const xaxis = fullLayout.xaxis
  const yaxis = fullLayout.yaxis
  const marginleft = fullLayout.margin.l
  const marginTop = fullLayout.margin.t

  const bounds = plotlyRef.value?.getBoundingClientRect()
  if (bounds) {
    const xInDataCoord = xaxis.p2c(event.x - marginleft - bounds.x);
    const yInDataCoord = yaxis.p2c(event.y - marginTop - bounds.y);
    hover.value.x = xInDataCoord
    hover.value.y = yInDataCoord.toFixed(4)
    showCoordinates.value = true
  }
}

export const handleMouseOut = () => {
  const { showCoordinates } = storeToRefs(usePlotlyStore())
  showCoordinates.value = false
}

/**
 * Toggle the `visible` attribute of a single trace via `Plotly.restyle`.
 * Replaces the direct `Plotly.restyle(...)` call in
 * `PlottedDatastreams.vue#toggleVisibility`.
 */
export const toggleTraceVisibility = async (
  gd: PlotlyHTMLElement | null,
  traceIndex: number,
  visible: boolean | 'legendonly'
): Promise<void> => {
  if (!gd) return
  await Plotly.restyle(gd, { visible }, [traceIndex])
}

/**
 * Set the selected point indices on a single trace (clearing any active
 * selection rectangles). Replaces the `Plotly.update(...)` call in
 * `useDataSelection#dispatchSelection`.
 *
 * Plotly expects one inner array per trace even when targeting a single
 * trace, so the caller-facing API takes a flat `number[]` and this wrapper
 * wraps it appropriately.
 */
export const setSelectedPoints = async (
  gd: PlotlyHTMLElement | null,
  traceIndex: number,
  indices: number[]
): Promise<void> => {
  if (!gd) return
  await Plotly.update(
    gd,
    {
      // Plotly attaches `selectedpoints` at runtime; the published typings
      // accept it on `Partial<PlotData>` via the same widening used in
      // `handleClick`/`handleRelayout` above.
      selections: [],
      selectedpoints: [indices],
    },
    {},
    [traceIndex]
  )
}

/**
 * Clear the active selection (both the highlighted points and any active
 * selection rectangles) on a single trace. Replaces the
 * `Plotly.update(...)` + `Plotly.restyle(...)` pair in
 * `useDataSelection#clearSelected`.
 */
export const clearSelection = async (
  gd: PlotlyHTMLElement | null,
  traceIndex: number
): Promise<void> => {
  if (!gd) return

  // Removes selected areas on the targeted trace.
  await Plotly.update(
    gd,
    {},
    { selections: [], selectedpoints: [[]] } as Partial<Layout>,
    [traceIndex]
  )

  // Resets the selected-point colouring across all traces (matches the
  // pre-plan behaviour of the second call in `clearSelected`, which
  // restyled without a trace-index argument).
  await Plotly.restyle(gd, {
    selectedpoints: [[]],
  })
}

/**
 * Apply a `(data, layout)` update to the entire figure. Replaces the
 * direct `Plotly.update(plotlyRef.value, { x, y }, layout)` call inside
 * `store/plotly.ts#redraw()`.
 */
export const applyTraceUpdate = async (
  gd: PlotlyHTMLElement | null,
  dataUpdate: Partial<PlotData>,
  layoutUpdate: Partial<Layout>
): Promise<void> => {
  if (!gd) return
  await Plotly.update(gd, dataUpdate, layoutUpdate)
}


export const cropXaxisRange = async () => {
  const { plotlyOptions, plotlyRef, isUpdating } = storeToRefs(usePlotlyStore())

  isUpdating.value = true

  setTimeout(async () => {
    try {
      const layoutUpdates: Partial<Layout> = { ...plotlyOptions.value.layout }
      const xAxis = layoutUpdates.xaxis as Partial<LayoutAxis> | undefined
      const xRange = xAxis?.range as Array<string | number> | undefined
      // Plotly will rewrite timestamps as datestrings. We need to convert them back to timestamps.
      if (xRange && typeof xRange[0] == 'string') {
        xRange[0] = Date.parse(xRange[0])
        xRange[1] = Date.parse(xRange[1] as string)
      }

      const liveRange = (
        plotlyRef.value?.layout.xaxis.range as
        | Array<string | number>
        | undefined
      )?.map((d) => (typeof d == 'string' ? Date.parse(d) : d))

      if (xAxis && xRange && liveRange) {
        xAxis.range = [
          Math.max(liveRange[0] as number, xRange[0] as number),
          Math.min(liveRange[1] as number, xRange[1] as number),
        ]
      }

      await Plotly.update(plotlyRef.value as Plotly.Root, {}, layoutUpdates)
    } finally {
      isUpdating.value = false
    }
  })
}

/**
 * Crops the x axis to only contain the extent of currently visible
 * points. Mirror of `fitYaxisToVisible`: for each trace we consider the
 * points already within the live x-range, keep those whose y also falls
 * inside the trace's live y-range, and shrink the x-axis to span their
 * min/max x (with 10% padding — same amount as the Y variant).
 * @param _eventData unused; preserved for the modebar click signature.
 */
export const fitXaxisToVisible = async (_eventData?: unknown) => {
  const { plotlyRef, isUpdating, graphSeriesArray } = storeToRefs(usePlotlyStore())

  isUpdating.value = true

  try {
    const liveLayout = plotlyRef.value?.layout as
      | Record<string, Partial<LayoutAxis> | unknown>
      | undefined
    const liveXRange = (
      (liveLayout?.xaxis as Partial<LayoutAxis> | undefined)?.range as
      | Array<string | number>
      | undefined
    )?.map((d) => (typeof d == 'string' ? Date.parse(d) : d))

    let xMin = Infinity
    let xMax = -Infinity

    for (let i = 0; i < graphSeriesArray.value.length; i++) {
      const xs = traceXAsNumbers(plotlyRef.value, i)
      if (!xs.length) continue
      const startIdx = findFirstGreaterOrEqual(xs, liveXRange?.[0])
      const endIdx = findFirstGreaterOrEqual(xs, liveXRange?.[1])
      if (endIdx - startIdx <= 0) continue

      const axisKey = i == 0 ? 'yaxis' : `yaxis${i + 1}`
      const liveYAxis = liveLayout?.[axisKey] as
        | Partial<LayoutAxis>
        | undefined
      const yRange = (liveYAxis?.range ?? []) as Array<number>
      const yRangeMin = Number(yRange[0])
      const yRangeMax = Number(yRange[1])
      const hasYClamp = Number.isFinite(yRangeMin) && Number.isFinite(yRangeMax)

      const traceData = plotlyRef.value?.data[i]
      const yData = (traceData?.y ?? []) as ArrayLike<number>

      for (let j = startIdx; j < endIdx; j++) {
        if (hasYClamp) {
          const v = Number(yData[j])
          if (v < yRangeMin || v > yRangeMax) continue
        }
        const x = xs[j]
        if (x < xMin) xMin = x
        if (x > xMax) xMax = x
      }
    }

    if (!Number.isFinite(xMin) || !Number.isFinite(xMax) || xMin === xMax) return

    const padding = (xMax - xMin) * 0.1
    await Plotly.relayout(plotlyRef.value as Plotly.Root, {
      'xaxis.range': [xMin - padding, xMax + padding],
      'xaxis.autorange': false,
    } as unknown as Partial<Layout>)
  } finally {
    isUpdating.value = false
  }
}

/**
 * Crops the QC trace's y axis to the extent of its currently visible
 * points. Only the primary `yaxis` (where QC always lives, per
 * `createPlotlyOption`) is rescaled — every non-QC overlay keeps the
 * range the user set on it, so clicking this button never reshuffles
 * the companion axes. The data considered is exclusively the QC
 * trace's y-values within the current live x-range.
 * @param _eventData unused; preserved for the original modebar click signature.
 */
export const fitYaxisToVisible = async (_eventData?: unknown) => {
  const { plotlyOptions, plotlyRef, isUpdating } = storeToRefs(usePlotlyStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())

  isUpdating.value = true

  try {
    const qcId = qcDatastream.value?.id
    if (!qcId) return

    const qcTraceIndex =
      plotlyRef.value?.data.findIndex(
        (t) => (t as AppPlotlyTrace).id === qcId
      ) ?? -1
    if (qcTraceIndex < 0) return

    const yAxis = (plotlyOptions.value.layout as Record<string, Partial<LayoutAxis>>)
      .yaxis
    if (!yAxis) return

    const liveXRange = (
      plotlyRef.value?.layout.xaxis.range as Array<string | number> | undefined
    )?.map((d) => (typeof d == 'string' ? Date.parse(d) : d))

    const xs = traceXAsNumbers(plotlyRef.value, qcTraceIndex)
    const startIdx = findFirstGreaterOrEqual(xs, liveXRange?.[0])
    const endIdx = findFirstGreaterOrEqual(xs, liveXRange?.[1])
    if (endIdx - startIdx <= 0) return

    const yData = (plotlyRef.value?.data[qcTraceIndex].y ?? []) as ArrayLike<number>

    // Clamp to the QC axis's stored range to keep edge outliers
    // (Infinity / sentinel values) from blowing the crop open. Strict
    // inequalities match the original seam so a finite point exactly
    // at the stored bound is still excluded as a likely sentinel.
    const yRange = yAxis.range ?? []
    const yRangeMin = Number(yRange[0])
    const yRangeMax = Number(yRange[1])

    let yMin = Infinity
    let yMax = -Infinity
    for (let j = startIdx; j < endIdx; j++) {
      const val = Number(yData[j])
      if (yMin > val && val > yRangeMin) yMin = val
      if (yMax < val && val < yRangeMax) yMax = val
    }

    if (yMax === yMin || !Number.isFinite(yMin) || !Number.isFinite(yMax)) return

    const padding = (yMax - yMin) * 0.1

    // Reuse the Plotly.update layout-object form (same shape the old
    // loop-over-all-axes seam used) — a previous attempt with
    // Plotly.relayout + dot-path keys silently no-op'd in some cases
    // and left the y-axis showing the whole extent.
    const layoutUpdates: Partial<Layout> & Record<string, Partial<LayoutAxis>> = {
      yaxis: {
        ...yAxis,
        range: [yMin - padding, yMax + padding],
        autorange: false,
      },
    }
    await Plotly.update(plotlyRef.value as Plotly.Root, {}, layoutUpdates)
  } finally {
    isUpdating.value = false
  }
}
