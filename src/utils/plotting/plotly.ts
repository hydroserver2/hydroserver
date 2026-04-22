import { usePlotlyStore, type ZoomState } from '@/store/plotly'
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
  selected?: { marker: { color: string; opacity?: number } }
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

/**
 * One right-side y-axis's data for the chip overlay in `Plot.vue`.
 * `lineX` is the pixel position of the axis line in container
 * coords; `graphWidth` is the current plot container width so the
 * overlay can decide, per chip, whether there's room to sit to the
 * right of the axis without running past the plot's right edge.
 * When the chip doesn't fit on the right, Plot.vue falls back to
 * anchoring its right edge at `lineX` so overflow into the right
 * gutter is impossible regardless of title length. Entries are
 * emitted in plotted-datastreams order so the stacked chips match
 * the sidebar.
 */
export type AxisChip = {
  id: string
  lineX: number
  graphWidth: number
  title: string
  color: string
}

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

// Marker-density threshold. Above this many visible points per trace,
// scattergl markers are rendered at `opacity: 0` (still hit-testable for
// select/lasso, just invisible) so the plot doesn't turn into ink soup.
// Consumed by `createPlotlyOption` (initial paint) and `handleRelayout`
// (zoom-driven updates).
const DENSITY_HIDE_MARKERS = 2000

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

// Colour palette for qualifier-flag markers along the bottom of the
// plot. Assigned deterministically per qualifier code (by sorted
// order). Reds and pinks are deliberately excluded — red is reserved
// for the point-selection highlight, so reusing it here confused
// "this point is selected" with "this point carries a qualifier".
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
// Horizontal double-arrow — FontAwesome `arrows-alt-h`. Sibling of
// `iconRescaleY` used for the custom Autoscale-X modebar button.
const iconRescaleX = {
  width: 512,
  height: 512,
  path: 'M502.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-96-96c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L402.7 224 109.3 224l41.4-41.4c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-96 96c-12.5 12.5-12.5 32.8 0 45.3l96 96c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L109.3 288l293.5 0-41.4 41.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l96-96z',
}

// FontAwesome `rotate-left` / `rotate-right` — curved arrows. Used for the
// zoom-history Undo / Redo modebar buttons.
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

export const createPlotlyOption = (
  seriesArray: GraphSeries[]
): PlotlyChartOptions => {
  const { qcDatastream, beginDate, endDate } = storeToRefs(useDataVisStore())
  const { previewMode, hiddenAxisIds, plotlyRef } = storeToRefs(
    usePlotlyStore()
  )
  const isPreview = previewMode?.value ?? false
  // `hiddenAxisIds` may be undefined during the pinia circular-init
  // that first calls `createPlotlyOption([])` before the store's own
  // refs are exposed (same pattern as `previewMode` above). The empty
  // set keeps the downstream `.has(id)` check happy.
  const hiddenAxes = hiddenAxisIds?.value ?? new Set<string>()

  // Density range for pre-seeding marker opacity. Prefer the live
  // plot's x-range so reorders / QC swaps keep dense traces hidden
  // across the replot (otherwise Plotly.newPlot renders markers at
  // full opacity and `handleRelayout` only kicks in 450 ms later).
  // Falls back to the store's begin/end dates when no plot exists.
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
  // Every non-QC axis gets `autoshift: true`, which requires `overlaying`
  // to take effect. When the first non-QC ran at the primary `y` slot
  // (old logic) it could not autoshift and collided with the first
  // shifted sibling — that's the "missing axis, overlapping neighbour"
  // bug.
  let nonQcAxisCount = 0
  // Counts only rendered overlays so toggled-off axes don't reserve
  // shift padding on the right.
  let visibleNonQcCount = 0

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

    // Pre-seed marker opacity from the current visible density so
    // Plotly.newPlot renders dense traces invisible from frame 0 —
    // `handleRelayout` would otherwise catch up 450 ms later, which
    // shows up as a flash on reorder / QC swap.
    let markerOpacity = 1
    if (densityRangeValid && xData?.length) {
      const xs = xData as number[]
      const count =
        findFirstGreaterOrEqual(xs, densityEnd) -
        findFirstGreaterOrEqual(xs, densityStart)
      if (count > DENSITY_HIDE_MARKERS) markerOpacity = 0
    }

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
      marker: { color, opacity: markerOpacity },
      line: { color },
    }

    if (isQc) {
      trace.marker = { ...(trace.marker ?? {}), color: COLORS[0] }
      trace.line = { ...(trace.line ?? {}), color: COLORS[0] }
      // Selected markers override both colour and opacity — the density
      // logic in `handleRelayout` drops base `marker.opacity` to 0 at
      // high density (keeps markers hit-testable for box-select without
      // the ink-soup), so without an explicit selected.marker.opacity
      // the highlighted points would inherit that zero and stay
      // invisible after a box-select.
      trace.selected = { marker: { color: 'red', opacity: 1 } }

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
          // Note: crosshair droplines live outside of Plotly. We render
          // two CSS lines driven by `processMouseMove` (see the
          // `crosshair` store field + `.plot-crosshair` in Plot.vue)
          // instead of Plotly's `showspikes`, because the built-in
          // spikes are gated on `hoverinfo !== 'skip'` and so vanish
          // together with tooltips at high point counts.
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
      const isAxisVisible = !(s.id && hiddenAxes.has(s.id))
      const yAxis: Partial<LayoutAxis> = {
        // Title rendered as a horizontal HTML chip overlay (see
        // `axisChips` in the store + `.plot-axis-chip` in Plot.vue)
        // instead of Plotly's rotated-text title — much easier to
        // read when multiple right-side axes stack up.
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
        // Force SI tick abbreviation ("2k" instead of "2000") and keep
        // it stable across pans (see primary yaxis above).
        tickformat: '~s',
        // `visible: false` hides the axis chrome; the trace keeps
        // rendering on it. Hidden axes also drop out of the
        // autoshift stack so they don't reserve empty space — Plotly's
        // shift accumulator runs before the `visible` check, so
        // `autoshift: true` on a hidden axis would still push the plot
        // right. `shift: 16` inter-axis padding applies only between
        // adjacent visible overlays.
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
    // Let Plotly grow the bottom margin to fit rotated tick labels.
    // Without this the fixed `margin.b` clips the last few pixels of
    // vertical date/time labels at zoom levels where Plotly rotates
    // them 90°.
    automargin: true,
    // Note: vertical crosshair dropline lives outside of Plotly — see
    // the companion note on the primary yaxis above.
    // range slider compatibility for Scattergl: https://github.com/plotly/plotly.js/issues/2627
  }

  // Secondary right-side axes now rely on Plotly's `autoshift` +
  // `automargin` (see the non-QC yaxis block above) to stack themselves
  // outside the plot area without collisions, so the hand-rolled xaxis
  // domain shrink is no longer needed.

  const layout: Partial<Layout> = {
    // hoverdistance: 20,
    xaxis,
    ...yaxis,
    dragmode: 'pan',
    hovermode: 'closest', // Disable if hovering is too costly
    // Title is omitted everywhere — the custom toolbar above the chart
    // (both in Select preview and Edit) already names the series, and
    // Plotly's built-in title steals a whole row of chart height.
    title: undefined,
    // `margin.b` pre-allocates headroom for rotated date-time tick
    // labels so the plot doesn't jump vertically every time zoom
    // flips label orientation. `automargin: true` on xaxis still
    // grows past this floor if a label really needs more.
    margin: isPreview
      ? { l: 24, r: 24, t: 28, b: 64, pad: 0 }
      : { l: 24, r: 24, t: 32, b: 64, pad: 0 },
    showlegend: false,
  }

  // Full modebar button list (`modeBarButtons`) — overrides Plotly's
  // defaults entirely so we control ordering. Undo/Redo zoom sit to the
  // left of the zoom tool; Fit X/Y stay at the far right. `isPreview`
  // drops select/lasso and the Fit buttons to keep the Select-view
  // chart uncluttered.
  const undoZoomButton = {
    name: 'Undo zoom',
    title: 'Undo zoom',
    icon: iconUndoZoom,
    click: () => {
      // Local import to avoid touching module-init ordering — the store
      // is already initialised by the time a user clicks a modebar button.
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

  // Modebar is split into functional groups so a visible gap appears
  // between each cluster. Related tools sit side by side; each cluster
  // is separated from the next by the inter-group padding applied to
  // `.modebar-group` in Plot.vue.
  //
  //   [ history ] [ zoom controls ] [ drag modes ] [ reset ] [ fit ]
  //
  //   history      — undo / redo zoom
  //   zoom         — box-zoom, step in, step out (all change the
  //                  viewport scale, grouped together instead of
  //                  scattered between drag modes)
  //   drag modes   — pan, box-select, lasso (each changes what a
  //                  primary drag gesture does)
  //   reset        — return to the default view
  //   fit          — autoscale X or Y to the data currently in view
  //
  // Preview charts drop select / lasso and fit to keep the toolbar
  // compact.
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
    // Plotly's built-in `scrollZoom` oscillates the x-range back and
    // forth during a wheel gesture — Plotly's pivot recomputation
    // desyncs against mid-gesture layout passes, producing a visible
    // "zoom in and out repeatedly" effect. We replace it with our own
    // wheel handler (`handleWheel`) that computes the pivot once per
    // event and applies a single coalesced relayout per animation
    // frame, avoiding the internal dragbox path entirely. Related
    // upstream: plotly/plotly.js#7449, plotly/plotly.py#4798.
    scrollZoom: false,
    responsive: true,
    doubleClick: false,
    modeBarButtons: modebarGroups,
    // Enables drag-to-resize on the staging band. `edits.shapePosition`
    // is a global baseline that Plotly uses to wire up shape-edit
    // hit-testers; without it per-shape `editable: true` is ignored
    // and the band can't be resized. The tradeoff is that every
    // shape on the plot becomes hit-testable for edits even with
    // `editable: false`, which is why `staging.ts` drops the stage
    // shape entirely in zoom / select / lasso modes instead of
    // rendering an inert visual clone.
    edits: { shapePosition: true },
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

  // Debounce long enough that a rapid scroll-wheel burst collapses
  // into a single post-gesture sweep. 250 ms used to cut it off
  // mid-burst, producing a visible "jump" when the downstream
  // opacity restyle + tickvals relayout landed between wheel ticks.
  const debounceDelay = 450

  handleRelayout(null)

  // Only listen to `plotly_relayout`. We used to also wire
  // `plotly_redraw`, which fires on every Plotly re-paint — so each
  // scroll tick routed through BOTH debouncers (one per event
  // type) and handleRelayout ran twice per gesture, each heavy pass
  // competing with the user's in-progress zoom. The relayout event
  // covers every case we care about (range changes, autorange
  // resets, modebar actions) without the duplicate work.
  plotlyRef.value?.on(
    'plotly_relayout',
    debounce(handleRelayout, debounceDelay)
  )
  // Zoom-history recorder — runs on its own 350 ms debouncer so a single
  // drag/scroll gesture collapses to one entry. Kept independent of the
  // relayout handler above, which does tooltip/visible-point work.
  plotlyRef.value?.on('plotly_relayout', () => recordZoomDebounced())
  // Seed the initial auto-fit state so the user can always undo back to
  // the plot's starting viewport. Runs after `handleRelayout(null)`
  // above so the layout ranges are populated.
  {
    const store = usePlotlyStore()
    if (!store.zoomUndoStack.length) {
      const initial = captureCurrentZoomState('init')
      if (initial) store.pushZoomState(initial)
    }
  }
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

  // Custom wheel handler replaces `scrollZoom` (disabled in config).
  // Non-passive because we preventDefault when the cursor is over the
  // plot area.
  plotlyRef.value?.removeEventListener('wheel', handleWheel as EventListener)
  plotlyRef.value?.addEventListener('wheel', handleWheel as EventListener, {
    passive: false,
  })

  // Widen each y-axis's drag column (primary QC on the left + every
  // right-side overlay) to span its full wheel-zoom zone, and
  // populate the horizontal axis-title chips. Both depend on
  // post-render layout state, so they run now and again after every
  // replot (Plotly rebuilds drag rects back to DRAGGERSIZE on
  // relayout; chip positions track axis lines that may have shifted).
  const gdEl = plotlyRef.value as unknown as HTMLElement
  widenYAxisDragRects(gdEl)
  suppressHiddenAxisDragRects(gdEl)
  updateAxisChips(plotlyRef.value as unknown as PlotlyHTMLElement)
  plotlyRef.value?.on('plotly_afterplot', () => {
    widenYAxisDragRects(gdEl)
    suppressHiddenAxisDragRects(gdEl)
    updateAxisChips(plotlyRef.value as unknown as PlotlyHTMLElement)
  })
}

// Perf cache for `handleRelayout`: when a relayout fires but the visible
// x-range hasn't appreciably moved (drag-state toggles, redraws that
// re-apply the same range), skip the O(traces) binary-search scan. The
// scan is cheap for a few traces but noticeable past ~5 on slower
// machines. A null event means "forced recompute" (fresh plot, data
// edit) and bypasses the cache.
let lastVisibleRange: [number, number] | null = null

export const invalidateVisibleRangeCache = () => {
  lastVisibleRange = null
}

// --- Zoom history -----------------------------------------------------------
//
// State lives on the plotly store (stacks + suppressZoomHistory flag). This
// seam owns the Plotly-specific pieces: reading the live layout into a
// ZoomState snapshot, applying a snapshot back onto the plot, and the
// debounced recorder that listens to `plotly_relayout` on its own timer so
// it's independent of the existing relayout handler (tooltip/visible-point
// work) in `handleRelayout`.

const Y_AXIS_KEY_RE = /^yaxis\d*$/

/**
 * Read the current xaxis + yaxisN ranges from the live plot into a
 * serialisable snapshot. Returns `null` if the plot hasn't mounted yet.
 */
export const captureCurrentZoomState = (
  source: ZoomState['source'] = 'user'
): ZoomState | null => {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const gd = plotlyRef.value as
    | (PrivatePlotlyHTMLElement & { layout?: Partial<Layout> })
    | null
  if (!gd?.layout) return null

  const layout = gd.layout as Partial<Layout> & Record<string, unknown>

  const xAxis = layout.xaxis as Partial<LayoutAxis> | undefined
  const xR = xAxis?.range as Array<number | string> | undefined
  const xStart = xR ? Number(typeof xR[0] === 'string' ? Date.parse(xR[0]) : xR[0]) : NaN
  const xEnd = xR ? Number(typeof xR[1] === 'string' ? Date.parse(xR[1]) : xR[1]) : NaN
  const xRange: [number, number] | null =
    Number.isFinite(xStart) && Number.isFinite(xEnd) ? [xStart, xEnd] : null

  const yRanges: Record<string, [number, number]> = {}
  for (const key of Object.keys(layout)) {
    if (!Y_AXIS_KEY_RE.test(key)) continue
    const axis = layout[key] as Partial<LayoutAxis> | undefined
    const r = axis?.range as Array<number> | undefined
    if (!r || !Number.isFinite(r[0]) || !Number.isFinite(r[1])) continue
    yRanges[key] = [Number(r[0]), Number(r[1])]
  }

  return { xRange, yRanges, source }
}

/**
 * Push a snapshot of the live plot onto the undo stack. No-ops when the
 * snapshot would be identical to (or an imperceptible move from) the
 * current top of the stack, which keeps drag-gesture churn from flooding
 * the history.
 */
const THRESHOLD = 0.005 // 0.5% of span
const sameRange = (
  a: [number, number] | null,
  b: [number, number] | null
): boolean => {
  if (!a || !b) return a === b
  const span = Math.max(Math.abs(a[1] - a[0]), Math.abs(b[1] - b[0]), 1)
  return (
    Math.abs(a[0] - b[0]) / span < THRESHOLD &&
    Math.abs(a[1] - b[1]) / span < THRESHOLD
  )
}
const sameZoomState = (a: ZoomState, b: ZoomState): boolean => {
  if (!sameRange(a.xRange, b.xRange)) return false
  const keys = new Set([...Object.keys(a.yRanges), ...Object.keys(b.yRanges)])
  for (const k of keys) {
    if (!sameRange(a.yRanges[k] ?? null, b.yRanges[k] ?? null)) return false
  }
  return true
}

export const recordZoomIfSettled = (
  source: ZoomState['source'] = 'user'
) => {
  const store = usePlotlyStore()
  if (store.suppressZoomHistory) return
  if (!store.graphSeriesArray.length) return
  const snap = captureCurrentZoomState(source)
  if (!snap) return
  const top = store.zoomUndoStack[store.zoomUndoStack.length - 1]
  if (top && sameZoomState(top, snap)) return
  store.pushZoomState(snap)
}

/** 350 ms debounce — slightly longer than the relayout handler so a single
 * drag gesture collapses to one entry even when the user pauses briefly
 * mid-gesture. */
const recordZoomDebounced = debounce(
  () => recordZoomIfSettled('user'),
  350
)

/**
 * Apply a ZoomState snapshot to the live plot. Gates with
 * `suppressZoomHistory` so the recorder doesn't re-capture what we just
 * set. Does nothing when the plot hasn't mounted.
 */
export const applyZoomState = async (state: ZoomState): Promise<void> => {
  const store = usePlotlyStore()
  const gd = store.plotlyRef as
    | (PrivatePlotlyHTMLElement & { layout?: Partial<Layout> })
    | null
  if (!gd) return

  const update: Record<string, unknown> = {}
  if (state.xRange) {
    update['xaxis.range'] = [state.xRange[0], state.xRange[1]]
    update['xaxis.autorange'] = false
  } else {
    update['xaxis.autorange'] = true
  }
  for (const [key, range] of Object.entries(state.yRanges)) {
    update[`${key}.range`] = [range[0], range[1]]
    update[`${key}.autorange`] = false
  }

  store.suppressZoomHistory = true
  try {
    await Plotly.relayout(gd as unknown as HTMLElement, update)
  } finally {
    // Let the debounced recorder tick past (350 ms + slack) before
    // re-arming. The recorder bails anyway via `suppressZoomHistory`,
    // but flushing here matches intuition and spares future-us from
    // chasing timing oddities.
    setTimeout(() => {
      store.suppressZoomHistory = false
    }, 450)
  }
}

/** Step one entry back in the zoom history. */
export const undoZoom = async (): Promise<void> => {
  const store = usePlotlyStore()
  if (!store.canUndoZoom) return
  // Top of undo stack is the CURRENT viewport. Pop it onto the redo
  // stack, then apply the new top (the previous viewport).
  const current = store.zoomUndoStack.pop()
  if (current) store.zoomRedoStack.push(current)
  const target = store.zoomUndoStack[store.zoomUndoStack.length - 1]
  if (target) await applyZoomState(target)
}

/** Step one entry forward in the zoom history. */
export const redoZoom = async (): Promise<void> => {
  const store = usePlotlyStore()
  if (!store.canRedoZoom) return
  const target = store.zoomRedoStack.pop()
  if (!target) return
  store.zoomUndoStack.push(target)
  await applyZoomState(target)
}

// ----------------------------------------------------------------------------

/**
 * Convert a datastream's `intendedTimeSpacing` + `intendedTimeSpacingUnit`
 * into milliseconds. Returns `null` when either field is missing — caller
 * falls back to Plotly's auto tick picker in that case.
 */
const intendedSpacingMs = (): number | null => {
  const { qcDatastream } = storeToRefs(useDataVisStore())
  const ds = qcDatastream.value as
    | { intendedTimeSpacing?: number; intendedTimeSpacingUnit?: string | null }
    | null
  if (!ds) return null
  const n = Number(ds.intendedTimeSpacing)
  if (!Number.isFinite(n) || n <= 0) return null
  switch (ds.intendedTimeSpacingUnit) {
    case 'seconds':
      return n * 1000
    case 'minutes':
      return n * 60 * 1000
    case 'hours':
      return n * 60 * 60 * 1000
    case 'days':
      return n * 24 * 60 * 60 * 1000
    default:
      return null
  }
}

/**
 * Compute an explicit tick-position array aligned to the datastream's
 * intended cadence, bounded to the visible x-range. Paired with
 * `tickmode: 'array'` + `tickvals` when returned non-null; returns
 * `null` when we should hand back to Plotly's auto tick picker (no QC
 * datastream, no cadence metadata, or span wide enough that even the
 * largest "nice" multiplier we'd consider still gives too many ticks).
 */
const computeIntendedTickvals = (
  xStart: number,
  xEnd: number
): number[] | null => {
  const unit = intendedSpacingMs()
  if (!unit) return null
  if (!Number.isFinite(xStart) || !Number.isFinite(xEnd)) return null
  const span = xEnd - xStart
  if (span <= 0) return null

  const TARGET_TICKS = 8
  // Cap tick count before rotated labels start colliding. The old
  // ceiling of 30 let awkward zoom levels emit enough custom ticks that
  // the 90°-rotated date/time labels overlapped each other; at 15 the
  // array path either produces comfortable spacing or hands back to
  // Plotly's auto picker, which thins labels on its own.
  const MAX_TICKS = 15
  const raw = span / (unit * TARGET_TICKS)

  // `niceMultipliers` preserves the rhythm of the intended spacing —
  // e.g. for a 15-minute series the ticks step by 15m, 30m, 1h, 2h, 4h,
  // 12h, 1d … rather than some arbitrary 13m or 47m.
  const niceMultipliers = [
    1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 45, 60, 90, 120,
  ]
  let chosen = niceMultipliers[niceMultipliers.length - 1]
  for (const m of niceMultipliers) {
    if (m >= raw) {
      chosen = m
      break
    }
  }

  const step = unit * chosen
  // Even the top end of our multiplier ladder would give too many ticks
  // — hand back to Plotly's auto algorithm.
  if (span / step > MAX_TICKS) return null

  // Anchor to the QC datastream's phenomenon start so ticks fall on
  // real observations. Fall back to xStart if no anchor is available —
  // ticks then just step from the left edge.
  const { qcDatastream } = storeToRefs(useDataVisStore())
  const anchorSource = qcDatastream.value?.phenomenonBeginTime
  const anchor = anchorSource
    ? new Date(anchorSource).getTime()
    : xStart

  const firstK = Math.ceil((xStart - anchor) / step)
  const ticks: number[] = []
  for (let k = firstK; ; k++) {
    const t = anchor + k * step
    if (t > xEnd) break
    ticks.push(t)
    if (ticks.length > MAX_TICKS) break
  }
  return ticks.length ? ticks : null
}

/** True when two numeric arrays match element-wise within a small
 *  tolerance. Used to skip no-op tickvals relayouts. */
const tickvalsEqual = (
  a: number[] | null,
  b: number[] | null
): boolean => {
  if (a === b) return true
  if (!a || !b) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (Math.abs(a[i] - b[i]) > 1) return false
  }
  return true
}

export const handleRelayout = async (
  eventData: PlotRelayoutEvent | null
) => {
  const {
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
      'xaxis.autorange'?: unknown
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

  // `resetScale2d` fires a relayout with `xaxis.autorange: true` — the
  // user just asked for "back to full view". Reset any imposed tick grid
  // synchronously before the debounced body runs so we never briefly
  // render the old zoomed-in `tickvals` against the wide post-reset
  // span (which was causing the dense unreadable tick mass).
  if (evt?.['xaxis.autorange'] === true && plotlyRef.value) {
    try {
      await Plotly.relayout(plotlyRef.value as unknown as HTMLElement, {
        'xaxis.tickmode': 'auto',
        'xaxis.tickvals': null,
      } as unknown as Partial<Layout>)
    } catch (err) {
      // Don't swallow the debounced body below on a transient relayout
      // error; just log and continue.
      console.warn('Failed to reset x-axis tick grid on autorange', err)
    }
  }

  isUpdating.value = true

  setTimeout(async () => {
    try {
      // Always read from the LIVE plotly layout, not from
      // `plotlyOptions.value.layout` — the stored options object isn't
      // kept in sync with modebar actions like `resetScale2d`, so after
      // an autorange reset the stored range still reflects the old
      // zoomed-in viewport. Downstream tick/density logic needs the
      // true post-reset range to avoid applying a fine-cadence grid to
      // a wide view.
      const liveLayout =
        (plotlyRef.value as unknown as { layout?: Partial<Layout> })?.layout
      const liveXaxis = liveLayout?.xaxis as Partial<LayoutAxis> | undefined
      const xRange = liveXaxis?.range as Array<string | number> | undefined

      // Plotly will rewrite timestamps as datestrings. We need to convert them back to timestamps.
      if (xRange && typeof xRange[0] == 'string') {
        xRange[0] = Date.parse(xRange[0])
        xRange[1] = Date.parse(xRange[1] as string)
      }

      const xStart = Number(xRange?.[0])
      const xEnd = Number(xRange?.[1])

      // Only rescan when the visible x-range actually moved. Threshold
      // is 0.1% of the span, so idle relayouts (drag-state toggles,
      // modebar noise) no-op. A null event forces a recompute.
      if (
        eventData !== null &&
        lastVisibleRange &&
        Number.isFinite(xStart) &&
        Number.isFinite(xEnd)
      ) {
        const span = xEnd - xStart
        const epsilon = Math.abs(span) * 0.001
        if (
          Math.abs(xStart - lastVisibleRange[0]) <= epsilon &&
          Math.abs(xEnd - lastVisibleRange[1]) <= epsilon
        ) {
          return
        }
      }

      visiblePoints.value = 0

      // Find number of visible points — per trace so we can adjust
      // density-dependent rendering (marker opacity) per series.
      const traceCount = plotlyRef.value?.data.length ?? 0
      const perTraceVisible: number[] = new Array(traceCount).fill(0)
      for (let i = 0; i < traceCount; i++) {
        // Plotly does not return the indexes of current x-axis extent. We must find them using binary search.
        const xs = traceXAsNumbers(plotlyRef.value, i)
        const startIdx = findFirstGreaterOrEqual(xs, xRange?.[0])
        const endIdx = findFirstGreaterOrEqual(xs, xRange?.[1])
        const count = endIdx - startIdx
        perTraceVisible[i] = count
        visiblePoints.value += count
      }

      if (Number.isFinite(xStart) && Number.isFinite(xEnd)) {
        lastVisibleRange = [xStart, xEnd]
      }

      // Density-responsive marker rendering — scattergl becomes ink soup
      // above a few thousand points per trace. Rather than stripping
      // markers (which breaks box-select / lasso, since Plotly's
      // selection hit-tests against marker glyphs, not line segments),
      // keep `mode: 'lines+markers'` throughout and drop marker opacity
      // to 0 past the threshold. At opacity 0 the markers are invisible
      // but still present and selectable, and scattergl short-circuits
      // their fragment shader so the perf cost is negligible. Below the
      // threshold markers render at full opacity — no partial fade, so
      // points either show normally or disappear cleanly.
      const perTraceOpacity = perTraceVisible.map((n) =>
        n > DENSITY_HIDE_MARKERS ? 0 : 1
      )

      // Only restyle when the opacity vector has actually changed —
      // Plotly.restyle on scattergl is cheap but not free, and pans
      // inside a single density band shouldn't trigger a redraw.
      const currentOpacities = (plotlyRef.value?.data ?? []).map((t) => {
        const m = (t as Partial<PlotData>).marker as
          | { opacity?: number }
          | undefined
        return m?.opacity ?? 1
      })
      const opacitiesChanged = perTraceOpacity.some(
        (o, i) => o !== (currentOpacities[i] ?? 1)
      )
      if (opacitiesChanged && plotlyRef.value) {
        // Per-trace restyle: Plotly maps an N-length array to each of
        // the N traces. The `@types/plotly.js` surface types marker
        // properties as scalars, but the runtime happily accepts the
        // array form, so the cast widens past the typed narrow.
        await Plotly.restyle(plotlyRef.value, {
          'marker.opacity': perTraceOpacity,
        } as unknown as Partial<PlotData>)
      }

      // Align x-axis ticks to the datastream's intended cadence when
      // the user has zoomed in enough that the cadence becomes legible.
      // At wider spans we hand back to Plotly's auto tick picker, which
      // does a better job of calendar-aware breakpoints than a rigid
      // cadence grid.
      if (Number.isFinite(xStart) && Number.isFinite(xEnd) && plotlyRef.value) {
        const wantedTickvals = computeIntendedTickvals(xStart, xEnd)
        const currentTickmode =
          (liveXaxis?.tickmode as string | undefined) ?? 'auto'
        const currentTickvals = Array.isArray(liveXaxis?.tickvals)
          ? (liveXaxis?.tickvals as number[])
          : null

        const wantedTickmode = wantedTickvals ? 'array' : 'auto'
        const tickmodeChanged = wantedTickmode !== currentTickmode
        const tickvalsChanged = !tickvalsEqual(
          wantedTickvals,
          currentTickvals
        )

        if (tickmodeChanged || tickvalsChanged) {
          await Plotly.relayout(plotlyRef.value as unknown as HTMLElement, {
            'xaxis.tickmode': wantedTickvals ? 'array' : 'auto',
            'xaxis.tickvals': wantedTickvals ?? null,
          } as unknown as Partial<Layout>)
        }
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

// Throttle the per-pixel mousemove work to one frame. DOM mousemove
// fires ~hundreds of events/sec on modern displays; each one used to
// re-run the private-API pixel → data conversion and write to the
// Pinia `hover` ref, which then triggered a Vue re-render of the
// hover chip in `Plot.vue`. Under scroll-zoom (where the pointer
// drifts while the wheel fires) that reactive churn was noticeable.
// Coalescing to requestAnimationFrame caps the work at ~60 Hz while
// still keeping the chip responsive.
let pendingMoveEvent: MouseEvent | null = null
let pendingMoveFrame: number | null = null

export const handleMouseMove = (event: MouseEvent) => {
  pendingMoveEvent = event
  if (pendingMoveFrame != null) return
  pendingMoveFrame = requestAnimationFrame(() => {
    pendingMoveFrame = null
    const ev = pendingMoveEvent
    pendingMoveEvent = null
    if (ev) processMouseMove(ev)
  })
}

const processMouseMove = (event: MouseEvent) => {
  const { plotlyRef, hover, showCoordinates, crosshair } = storeToRefs(
    usePlotlyStore()
  )

  // PRIVATE-API: `_fullLayout` (and the `xaxis.p2c` / `yaxis.p2c` pixel-to-data
  // converters it exposes) are undocumented Plotly internals used here for
  // mouse-move coordinate conversion. They have no public type — see
  // `src/types/plotly-dist.d.ts` for the local `PrivatePlotlyHTMLElement`
  // augmentation. If these break in a future Plotly version, switch to a
  // published gestures API or recompute coordinates from `layout.range`.
  const gd = plotlyRef.value as unknown as PrivatePlotlyHTMLElement | null
  const fullLayout = gd?._fullLayout
  if (!fullLayout) return

  // Use `_offset`/`_length` over plain `margin` because axes with a
  // `domain` less than [0,1] (e.g. the primary y when the qualifier
  // band compresses it to [0.14,1]) sit inside the margins. These are
  // the actual pixel bounds of the axis and line up with the crosshair
  // termination points we want.
  const xaxis = fullLayout.xaxis as (typeof fullLayout.xaxis) & {
    _offset?: number
    _length?: number
  }
  const yaxis = fullLayout.yaxis as (typeof fullLayout.yaxis) & {
    _offset?: number
    _length?: number
  }
  if (
    xaxis._offset == null ||
    xaxis._length == null ||
    yaxis._offset == null ||
    yaxis._length == null
  )
    return

  const bounds = plotlyRef.value?.getBoundingClientRect()
  if (!bounds) return

  const cursorX = event.clientX - bounds.x
  const cursorY = event.clientY - bounds.y

  const plotLeft = xaxis._offset
  const plotRight = xaxis._offset + xaxis._length
  const plotTop = yaxis._offset
  const plotBottom = yaxis._offset + yaxis._length

  const insidePlot =
    cursorX >= plotLeft &&
    cursorX <= plotRight &&
    cursorY >= plotTop &&
    cursorY <= plotBottom

  if (!insidePlot) {
    // Leaving the plot area while still over the root element (e.g.
    // cursor dropped onto the qualifier band or a tick gutter) should
    // hide the readout and crosshair — otherwise they freeze at the
    // last in-plot position.
    showCoordinates.value = false
    if (crosshair.value.visible) crosshair.value.visible = false
    return
  }

  hover.value.x = Number(xaxis.p2c(cursorX - plotLeft))
  hover.value.y = Number(yaxis.p2c(cursorY - plotTop)).toFixed(4)
  showCoordinates.value = true

  // Crosshair droplines: vertical line goes from cursor down to the
  // x-axis (plot bottom); horizontal line goes from the QC y-axis
  // (plot left) to the cursor. Plot.vue reads these to position the
  // two CSS line divs.
  crosshair.value = {
    visible: true,
    cursorX,
    cursorY,
    plotLeft,
    plotBottom,
  }
}

export const handleMouseOut = () => {
  const { showCoordinates, crosshair } = storeToRefs(usePlotlyStore())
  showCoordinates.value = false
  if (crosshair.value.visible) crosshair.value.visible = false
}

// --- Custom wheel-zoom ---------------------------------------------------
//
// Replaces Plotly's built-in `scrollZoom`. Plotly's implementation
// recomputes the zoom pivot against `_fullLayout` on every wheel tick,
// which desyncs when the layout shifts mid-gesture (automargin, tick
// label relayout, etc.) and produces a visible back-and-forth zoom
// oscillation (see plotly/plotly.js#7449). We pin the pivot to the
// cursor's data coord at event time and coalesce bursts to a single
// `Plotly.relayout` per animation frame.
//
// Zone-based targeting matches user expectations for a multi-axis
// layout:
//  - Over the plot area   → zoom x AND every non-fixed y-axis, each
//                           around the cursor's own data coord.
//  - Over the x gutter    → zoom x only.
//  - Over the left gutter → zoom the primary y-axis only.
//  - Over a right-side y  → zoom just the axis whose column contains
//                           the cursor (see `pickRightYAxisAtCursor`);
//                           falls back to zoom-all if we can't
//                           identify one.
//
// `handleRelayout`'s downstream work (marker opacity, tickvals, hover
// template) still fires because our `Plotly.relayout` emits
// `plotly_relayout`.

/** Per-tick zoom ratio applied to each target axis. 0.85 means each
 *  full wheel tick shrinks the span to 85% (zoom in) or grows it to
 *  ~118% (zoom out). Tuned to feel close to Plotly's default
 *  scrollZoom step. */
const WHEEL_ZOOM_IN_FACTOR = 0.85
const WHEEL_ZOOM_OUT_FACTOR = 1 / WHEEL_ZOOM_IN_FACTOR

/**
 * Compute the rendered x-pixel of each non-primary y-axis's line, in
 * gd-root coordinates. Uses Plotly's private `_mainLinePosition`
 * (pre-shift position against the counter-axis) plus `_shift` (the
 * autoshift offset that stacks overlays out to the right). Returns a
 * list sorted by `lineX` ascending, skipping fixed-range axes.
 * Caller uses this both for the zone picker and for widening the
 * visible drag columns.
 */
type RightAxisInfo = {
  key: string
  lineX: number
  subplotId: string
}
const collectRightAxes = (
  fullLayout: Record<string, unknown>
): RightAxisInfo[] => {
  const axes: RightAxisInfo[] = []
  for (const key of Object.keys(fullLayout)) {
    if (!Y_AXIS_KEY_RE.test(key) || key === 'yaxis') continue
    const ax = fullLayout[key] as
      | {
          fixedrange?: boolean
          visible?: boolean
          _mainLinePosition?: number
          _shift?: number
          _mainSubplot?: string
          _subplotsWith?: string[]
        }
      | undefined
    if (!ax || ax.fixedrange) continue
    // Skip axes the user has hidden via the sidebar. Their chrome
    // (`visible: false`) is gone but the trace keeps rendering, and
    // Plotly still lays out a `_mainLinePosition` + drag rects for
    // them. Including them here would make `widenYAxisDragRects`
    // stretch an orphaned hit-zone across part of the plot, so the
    // user sees the blue hover tint on top of the chart (from the
    // `.drag.cursor-*:hover` styling in Plot.vue) in a region that
    // isn't a visible axis column. The wheel-zoom picker has the
    // same concern — routing scroll to an axis with no visible
    // chrome is surprising.
    if (ax.visible === false) continue
    if (typeof ax._mainLinePosition !== 'number') continue
    const lineX = ax._mainLinePosition + (ax._shift ?? 0)
    if (!Number.isFinite(lineX)) continue
    const subplotId = ax._mainSubplot ?? ax._subplotsWith?.[0]
    if (!subplotId) continue
    axes.push({ key, lineX, subplotId })
  }
  axes.sort((a, b) => a.lineX - b.lineX)
  return axes
}

/**
 * Widen each y-axis's drag rects so the blue hover / drag-rescale
 * column spans the full zone the wheel-zoom picker uses:
 *   - Primary (QC) y on the left: zone is `[0, primaryLineX]`.
 *   - Each right-side overlay: zone is `[lineX, nextLineX]`, with
 *     the rightmost axis extending to `gd.clientWidth`.
 * Plotly normally sizes these rects to `DRAGGERSIZE` (20 px), which
 * leaves narrow slivers of un-highlighted space between columns and
 * makes the hit target for drag-to-rescale feel small.
 *
 * DOM structure we rely on (from plotly.js source, v3.x):
 *   g.draglayer > g.{subplotId} > rect.nsdrag   (main middle drag)
 *                               > rect.ndrag    (top edge drag)
 *                               > rect.sdrag    (bottom edge drag)
 * For the primary y-axis the rects' default `x` is
 * `_mainLinePosition - DRAGGERSIZE` (20 px left of the line); for
 * right-side overlays Plotly already adds `_shift` into `x` inside
 * `makeDragBox`, so the default `x` equals `lineX`. We set both `x`
 * and `width` explicitly to normalise both cases.
 *
 * Plotly rebuilds drag rects on every plot/relayout, so this needs
 * to re-run after each `plotly_afterplot` event to survive layout
 * changes.
 */
const widenYAxisDragRects = (gd: HTMLElement): void => {
  const fl = (gd as unknown as PrivatePlotlyHTMLElement)._fullLayout as
    | Record<string, unknown>
    | undefined
  if (!fl) return

  type Span = { subplotId: string; zoneLeft: number; zoneRight: number }
  const spans: Span[] = []

  // Primary y-axis (side: 'left'). No `_shift` — autoshift only
  // applies to overlays with `anchor: 'free'`. Zone is from the
  // graph's left edge out to the axis line.
  const primaryY = fl.yaxis as
    | {
        fixedrange?: boolean
        _mainLinePosition?: number
        _mainSubplot?: string
        _subplotsWith?: string[]
      }
    | undefined
  if (
    primaryY &&
    !primaryY.fixedrange &&
    typeof primaryY._mainLinePosition === 'number'
  ) {
    const subplotId = primaryY._mainSubplot ?? primaryY._subplotsWith?.[0]
    if (subplotId && primaryY._mainLinePosition > 0) {
      spans.push({
        subplotId,
        zoneLeft: 0,
        zoneRight: primaryY._mainLinePosition,
      })
    }
  }

  // Right-side overlays.
  const rightAxes = collectRightAxes(fl)
  const graphWidth = gd.clientWidth
  for (let i = 0; i < rightAxes.length; i++) {
    const current = rightAxes[i]
    const rightEdge =
      i + 1 < rightAxes.length ? rightAxes[i + 1].lineX : graphWidth
    spans.push({
      subplotId: current.subplotId,
      zoneLeft: current.lineX,
      zoneRight: rightEdge,
    })
  }

  const DRAG_CLASSES = ['rect.nsdrag', 'rect.ndrag', 'rect.sdrag']

  for (const span of spans) {
    const newWidth = span.zoneRight - span.zoneLeft
    if (newWidth <= 0) continue

    const subplotGroup = gd.querySelector(
      `g.draglayer > g.${CSS.escape(span.subplotId)}`
    ) as SVGGraphicsElement | null
    if (!subplotGroup) continue

    for (const sel of DRAG_CLASSES) {
      const rect = subplotGroup.querySelector(sel) as SVGRectElement | null
      if (!rect) continue
      rect.setAttribute('x', String(span.zoneLeft))
      rect.setAttribute('width', String(newWidth))
    }
  }
}

/**
 * Plotly still emits `nsdrag/ndrag/sdrag` rects for overlay y-axes
 * even when we pass `visible: false` + `autoshift: false`. Without
 * `autoshift`, an `anchor: 'free'` y-axis defaults its position to
 * the counter-axis origin (plot-left), so the hidden axis's drag
 * column lands right next to the primary QC axis. With the hover
 * tint from `.drag.cursor-*:hover` in Plot.vue, that renders as a
 * stray blue rectangle hugging the QC axis — even though the axis
 * chrome itself is gone. Reproduces with as few as two plotted
 * datastreams (one QC + one hidden overlay).
 *
 * `widenYAxisDragRects` already skips hidden axes, so it never
 * re-sizes those rects back to a usable zone. We finish the job
 * here by collapsing each hidden overlay's drag rects to zero width
 * and stripping their cursor classes so the `.drag.cursor-*:hover`
 * selectors in Plot.vue can't match. `pointer-events: none` is a
 * belt-and-braces in case any sibling CSS still widens them.
 *
 * Must re-run after every `plotly_afterplot` — Plotly rebuilds drag
 * rects on each relayout and our DOM edits don't survive a rebuild.
 */
const suppressHiddenAxisDragRects = (gd: HTMLElement): void => {
  const fl = (gd as unknown as PrivatePlotlyHTMLElement)._fullLayout as
    | Record<string, unknown>
    | undefined
  if (!fl) return

  const DRAG_CLASSES = ['rect.nsdrag', 'rect.ndrag', 'rect.sdrag']
  const CURSOR_CLASSES = [
    'cursor-ns-resize',
    'cursor-n-resize',
    'cursor-s-resize',
  ]

  for (const key of Object.keys(fl)) {
    // Guard the primary yaxis — it's always visible and owns the QC
    // axis's drag column; zeroing it would break rescale-drag on QC.
    if (!Y_AXIS_KEY_RE.test(key) || key === 'yaxis') continue
    const ax = fl[key] as
      | {
          visible?: boolean
          _mainSubplot?: string
          _subplotsWith?: string[]
        }
      | undefined
    if (!ax || ax.visible !== false) continue
    const subplotId = ax._mainSubplot ?? ax._subplotsWith?.[0]
    if (!subplotId) continue
    const group = gd.querySelector(
      `g.draglayer > g.${CSS.escape(subplotId)}`
    ) as SVGGraphicsElement | null
    if (!group) continue
    for (const sel of DRAG_CLASSES) {
      const rect = group.querySelector(sel) as SVGRectElement | null
      if (!rect) continue
      rect.setAttribute('x', '0')
      rect.setAttribute('width', '0')
      rect.setAttribute('pointer-events', 'none')
      for (const cls of CURSOR_CLASSES) rect.classList.remove(cls)
    }
  }
}

/**
 * Populate the `axisChips` store ref from the current layout. One
 * chip per non-QC right-side axis that's currently visible, emitted
 * in plotted-datastreams order so the stacked overlay matches the
 * sidebar reading order.
 *
 * Memoised on a string key so wheel-zoom relayouts (which fire
 * `plotly_afterplot` without adding or removing chips) don't churn
 * the store and trigger needless re-renders of the overlay.
 */
let lastAxisChipsKey = ''
const updateAxisChips = (gd: PlotlyHTMLElement | null): void => {
  const { axisChips, graphSeriesArray } = storeToRefs(usePlotlyStore())
  const { labelColorForDatastream } = usePlotlyStore()

  if (!gd) {
    if (lastAxisChipsKey !== '') {
      lastAxisChipsKey = ''
      axisChips.value = []
    }
    return
  }
  const fl = (gd as unknown as PrivatePlotlyHTMLElement)._fullLayout as
    | Record<string, unknown>
    | undefined
  if (!fl) return

  const chips: AxisChip[] = []
  const graphWidth = (gd as HTMLElement).clientWidth
  // Iterate `graphSeriesArray` — it's the authoritative sidebar
  // order; `gd.data` gets reversed so traces paint top-over-bottom
  // (see `createPlotlyOption`), which would flip the stacked chips.
  for (const series of graphSeriesArray.value) {
    const trace = gd.data.find(
      (t) => (t as AppPlotlyTrace).id === series.id
    ) as AppPlotlyTrace | undefined
    const axisRef = trace?.yaxis as string | undefined
    if (!axisRef || axisRef === 'y') continue
    const ax = fl[`yaxis${axisRef.slice(1)}`] as
      | { visible?: boolean; _mainLinePosition?: number; _shift?: number }
      | undefined
    if (!ax || ax.visible === false) continue
    if (typeof ax._mainLinePosition !== 'number') continue
    const lineX = ax._mainLinePosition + (ax._shift ?? 0)
    if (!Number.isFinite(lineX)) continue

    chips.push({
      id: series.id,
      lineX,
      graphWidth,
      title: series.yAxisLabel,
      color: labelColorForDatastream(series.id),
    })
  }

  const key = chips
    .map((c) => `${c.id}:${c.lineX}:${c.graphWidth}:${c.title}`)
    .join('|')
  if (key === lastAxisChipsKey) return
  lastAxisChipsKey = key
  axisChips.value = chips
}

/**
 * Pick the specific non-primary y-axis whose column contains the
 * cursor. Axis N owns `[N.lineX, (N+1).lineX)`; the rightmost axis
 * extends to the graph's right edge. Returns `null` when the cursor
 * is left of every axis line (shouldn't happen in the right gutter,
 * but caller falls back to zoom-all if so).
 */
const pickRightYAxisAtCursor = (
  gd: HTMLElement,
  fullLayout: Record<string, unknown>,
  event: WheelEvent
): string | null => {
  const axes = collectRightAxes(fullLayout)
  if (!axes.length) return null
  const cursorXGdRelative = event.clientX - gd.getBoundingClientRect().left
  // axes are sorted ascending; the owner is the last axis whose line
  // we've passed.
  let owner: RightAxisInfo | null = null
  for (const a of axes) {
    if (a.lineX > cursorXGdRelative) break
    owner = a
  }
  return owner ? owner.key : null
}

type WheelAxisTarget = { key: string; pivot: number; factor: number }
type WheelPending = { x?: WheelAxisTarget; y: Record<string, WheelAxisTarget> }

let pendingWheelFrame: number | null = null
let pendingWheelZoom: WheelPending | null = null

export const handleWheel = (event: WheelEvent) => {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const gd = plotlyRef.value as unknown as PrivatePlotlyHTMLElement | null
  const fullLayout = gd?._fullLayout
  if (!fullLayout) return

  // PRIVATE-API: `_offset` and `_length` are Plotly internals. They
  // give the pixel rectangle actually occupied by each axis and are
  // the only reliable way to tell whether the cursor is over the
  // plot, the x gutter, or a y gutter when axes use `domain` (e.g.
  // the qualifier band compresses the primary y to [0.14, 1]).
  const xaxis = fullLayout.xaxis as (typeof fullLayout.xaxis) & {
    _offset?: number
    _length?: number
    fixedrange?: boolean
  }
  const primaryY = fullLayout.yaxis as (typeof fullLayout.yaxis) & {
    _offset?: number
    _length?: number
    fixedrange?: boolean
  }
  if (
    xaxis?._offset == null ||
    xaxis._length == null ||
    primaryY?._offset == null ||
    primaryY._length == null
  )
    return

  const bounds = (gd as unknown as HTMLElement).getBoundingClientRect()
  const pxRel = event.clientX - bounds.x
  const pyRel = event.clientY - bounds.y

  const xLeft = xaxis._offset
  const xRight = xaxis._offset + xaxis._length
  const yTop = primaryY._offset
  const yBottom = primaryY._offset + primaryY._length

  const overX = pxRel >= xLeft && pxRel <= xRight
  const overY = pyRel >= yTop && pyRel <= yBottom
  const overPlot = overX && overY
  const overBottomGutter = overX && pyRel > yBottom
  const overLeftGutter = pxRel < xLeft && overY
  const overRightGutter = pxRel > xRight && overY

  if (!overPlot && !overBottomGutter && !overLeftGutter && !overRightGutter)
    return

  event.preventDefault()

  const zoomX = (overPlot || overBottomGutter) && !xaxis.fixedrange

  // Pick the y-axis targets for the active zone.
  const yAxisKeys: string[] = []
  const collectYAxes = (predicate: (key: string) => boolean) => {
    for (const key of Object.keys(fullLayout)) {
      if (!Y_AXIS_KEY_RE.test(key)) continue
      if (!predicate(key)) continue
      const ax = (fullLayout as unknown as Record<string, { fixedrange?: boolean }>)[key]
      if (ax?.fixedrange) continue
      yAxisKeys.push(key)
    }
  }
  if (overPlot) collectYAxes(() => true)
  else if (overLeftGutter) collectYAxes((key) => key === 'yaxis')
  else if (overRightGutter) {
    // Pick the single axis whose zone contains the cursor. Fall back
    // to zoom-all if Plotly's layout state isn't populated yet (e.g.
    // first frame after plot mount).
    const pickedKey = pickRightYAxisAtCursor(
      gd as unknown as HTMLElement,
      fullLayout as unknown as Record<string, unknown>,
      event
    )
    collectYAxes(
      pickedKey ? (key) => key === pickedKey : (key) => key !== 'yaxis'
    )
  }

  if (!zoomX && !yAxisKeys.length) return

  // Normalise across `deltaMode` (lines/pixels/pages) so trackpad
  // smooth-scrolls and discrete-click wheels both feel like roughly
  // one step per click after rAF coalescing. Positive deltaY = scroll
  // toward user = zoom out.
  const magnitude = Math.min(1, Math.abs(event.deltaY) / 100)
  const baseFactor = event.deltaY > 0
    ? WHEEL_ZOOM_OUT_FACTOR
    : WHEEL_ZOOM_IN_FACTOR
  const tickFactor = 1 + (baseFactor - 1) * magnitude

  if (!pendingWheelZoom) pendingWheelZoom = { y: {} }

  // Pin the pivot to the first event of the burst; subsequent events
  // in the same frame compose their factors against that pivot.
  if (zoomX) {
    const pivot = Number(xaxis.p2c(pxRel - xLeft))
    if (Number.isFinite(pivot)) {
      pendingWheelZoom.x ??= { key: 'xaxis', pivot, factor: 1 }
      pendingWheelZoom.x.factor *= tickFactor
    }
  }

  for (const key of yAxisKeys) {
    const ax = (fullLayout as unknown as Record<string, {
      _offset?: number
      p2c?: (px: number) => number
    }>)[key]
    if (ax?._offset == null || !ax.p2c) continue
    const pivot = Number(ax.p2c(pyRel - ax._offset))
    if (!Number.isFinite(pivot)) continue
    pendingWheelZoom.y[key] ??= { key, pivot, factor: 1 }
    pendingWheelZoom.y[key].factor *= tickFactor
  }

  if (pendingWheelFrame != null) return
  pendingWheelFrame = requestAnimationFrame(() => {
    pendingWheelFrame = null
    const zoom = pendingWheelZoom
    pendingWheelZoom = null
    if (zoom) void applyWheelZoom(zoom)
  })
}

const applyWheelZoom = async (zoom: WheelPending): Promise<void> => {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const gd = plotlyRef.value
  const liveLayout = gd?.layout as Record<string, Partial<LayoutAxis>> | undefined
  if (!gd || !liveLayout) return

  const update: Record<string, unknown> = {}

  // Plotly serialises date-axis range endpoints as ISO strings; convert
  // back to epoch ms so the pivot arithmetic matches `p2c`'s space.
  const toNumber = (v: string | number): number =>
    typeof v === 'string' ? Date.parse(v) : Number(v)

  const applyAxis = (key: string, pivot: number, factor: number): void => {
    const range = liveLayout[key]?.range as Array<string | number> | undefined
    if (!range) return
    const a = toNumber(range[0])
    const b = toNumber(range[1])
    if (!Number.isFinite(a) || !Number.isFinite(b)) return
    const newA = pivot - (pivot - a) * factor
    const newB = pivot + (b - pivot) * factor
    // Bail on degenerate ranges (excessive zoom past axis resolution).
    if (!Number.isFinite(newA) || !Number.isFinite(newB) || newA >= newB) return
    update[`${key}.range`] = [newA, newB]
    update[`${key}.autorange`] = false
  }

  if (zoom.x) {
    applyAxis(zoom.x.key, zoom.x.pivot, zoom.x.factor)
    // Hand tick placement back to Plotly's auto picker mid-gesture.
    // Cadence-aligned `tickvals` from `handleRelayout` are pinned to
    // the previous visible range and clump around the old centre as
    // the new range slides under them. `handleRelayout` restores the
    // cadence grid 450 ms after the gesture settles.
    update['xaxis.tickmode'] = 'auto'
    update['xaxis.tickvals'] = null
  }
  for (const target of Object.values(zoom.y)) {
    applyAxis(target.key, target.pivot, target.factor)
  }

  if (!Object.keys(update).length) return
  await Plotly.relayout(
    gd as unknown as HTMLElement,
    update as unknown as Partial<Layout>
  )
}

/**
 * Zoom the x-axis to an explicit [start, end] window without touching
 * the data. Used by the editor's preset buttons, which should be a
 * visual-only zoom — unlike the Select-view sidebar presets, which
 * drive a fresh fetch + redraw via `useDataVisStore#onDateBtnClick`.
 */
export const zoomXaxisTo = async (
  gd: PlotlyHTMLElement | null,
  start: number,
  end: number
): Promise<void> => {
  if (!gd) return
  await Plotly.relayout(gd as Plotly.Root, {
    'xaxis.range': [start, end],
    'xaxis.autorange': false,
  } as unknown as Partial<Layout>)
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
 * Toggle whether a non-QC datastream's right-side y-axis is rendered.
 * The trace keeps plotting on that axis; only the chrome (line, ticks,
 * labels, title) is hidden, and autoshift reclaims the horizontal
 * space so neighbouring axes pack in against the plot.
 *
 * A dot-path relayout (`{'yaxisN.visible': false}`) hides the chrome
 * but doesn't rerun the autoshift pass, so the column stays reserved.
 * We rebuild via `handleNewPlot(preserveZoom)` — the same replot path
 * used for QC swaps and trace reorders — which regenerates the layout
 * from `createPlotlyOption` with the updated `hiddenAxisIds` and
 * preserves the user's viewport.
 *
 * No-op for the QC datastream (lives on the primary yaxis) and for
 * datastreams that aren't currently plotted.
 */
export const toggleAxisVisibility = async (
  datastreamId: string
): Promise<void> => {
  const { plotlyRef, hiddenAxisIds } = storeToRefs(usePlotlyStore())
  const { updateOptions } = usePlotlyStore()
  const gd = plotlyRef.value as unknown as PlotlyHTMLElement | null
  if (!gd) return

  const trace = gd.data.find(
    (t) => (t as AppPlotlyTrace).id === datastreamId
  ) as AppPlotlyTrace | undefined
  if (!trace || trace.yaxis === 'y') return

  const ids = hiddenAxisIds.value
  if (ids.has(datastreamId)) ids.delete(datastreamId)
  else ids.add(datastreamId)

  // `handleNewPlot` reads `plotlyOptions` directly; without a fresh
  // `updateOptions` the flipped state never reaches the new layout.
  updateOptions()
  await handleNewPlot(undefined, { preserveZoom: true })
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
