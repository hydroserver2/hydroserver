import Plotly from 'plotly.js-dist'
import type {
  Layout,
  LayoutAxis,
  PlotData,
  PlotlyHTMLElement,
} from 'plotly.js-dist'
import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { findFirstGreaterOrEqual } from '@uwrl/qc-utils'
import { handleNewPlot } from './events'
import { traceXAsNumbers } from './internal'
import { plotCoord, plotCoordToDate, toPlotDate } from './plotTime'
import type { AppPlotlyTrace } from './options'

/**
 * Zoom the x-axis to an explicit [start, end] window without touching
 * the data. Used by the editor's preset buttons, which should be a
 * visual-only zoom, unlike the Select-view sidebar presets, which
 * drive a fresh fetch + redraw via `useDataVisStore#onDateBtnClick`.
 */
export const zoomXaxisTo = async (
  gd: PlotlyHTMLElement | null,
  start: number,
  end: number
): Promise<void> => {
  if (!gd) return
  await Plotly.relayout(gd as Plotly.Root, {
    'xaxis.range': [toPlotDate(start), toPlotDate(end)],
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
 * We rebuild via `handleNewPlot(preserveZoom)` (the same replot path
 * used for QC swaps and trace reorders), which regenerates the layout
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
 * selection rectangles). Used by `useDataSelection#setPlotSelection`.
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
      selectedpoints: [indices],
    },
    { selections: [] } as Partial<Layout>,
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
      const layoutUpdates = plotlyOptions.value.layout
      const xAxis = layoutUpdates.xaxis as Partial<LayoutAxis> | undefined
      const xRange = (xAxis?.range as Array<string | number> | undefined)?.map(
        plotCoord
      )
      const liveRange = (
        plotlyRef.value?.layout.xaxis.range as
        | Array<string | number>
        | undefined
      )?.map(plotCoord)

      if (xAxis && xRange && liveRange) {
        xAxis.range = [
          plotCoordToDate(Math.max(liveRange[0]!, xRange[0]!)),
          plotCoordToDate(Math.min(liveRange[1]!, xRange[1]!)),
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
 * min/max x.
 * @param _eventData unused; preserved for the modebar click signature.
 */
export const fitXaxisToVisible = async (_eventData?: unknown) => {
  const { plotlyRef, isUpdating } = storeToRefs(usePlotlyStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())

  isUpdating.value = true

  try {
    const gd = plotlyRef.value
    if (!gd) return
    const qcId = qcDatastream.value?.id
    if (!qcId) return

    const traces = gd.data ?? []
    const qcIndex = traces.findIndex(
      (t) => (t as AppPlotlyTrace).id === qcId
    )
    if (qcIndex < 0) return
    const qcTrace = traces[qcIndex] as AppPlotlyTrace

    const liveLayout = gd.layout as unknown as
      | Record<string, Partial<LayoutAxis> | unknown>
      | undefined
    const liveXRange = (
      (liveLayout?.xaxis as Partial<LayoutAxis> | undefined)?.range as
      | Array<string | number>
      | undefined
    )?.map(plotCoord)

    const xs = traceXAsNumbers(gd, qcIndex)
    if (!xs.length) return
    // First/last value of liveXRange might be undefined under
    // noUncheckedIndexedAccess; default to +/- Infinity so the binary
    // search returns the full range when the live layout is missing
    // an axis range (fresh plot, before the user has touched zoom).
    const startIdx = findFirstGreaterOrEqual(xs, liveXRange?.[0] ?? -Infinity)
    const endIdx = findFirstGreaterOrEqual(xs, liveXRange?.[1] ?? Infinity)
    if (endIdx - startIdx <= 0) return

    // QC always lives on the primary `yaxis` (see `createPlotlyOption`).
    // Clamp by the live QC y-range so points outside the user's current
    // y-zoom (likely outliers) don't blow the fit open.
    const liveYAxis = liveLayout?.yaxis as Partial<LayoutAxis> | undefined
    const yRange = (liveYAxis?.range ?? []) as Array<number>
    const yRangeMin = Number(yRange[0])
    const yRangeMax = Number(yRange[1])
    const hasYClamp = Number.isFinite(yRangeMin) && Number.isFinite(yRangeMax)
    const yData = (qcTrace.y ?? []) as ArrayLike<number>

    let xMin = Infinity
    let xMax = -Infinity
    for (let j = startIdx; j < endIdx; j++) {
      if (hasYClamp) {
        const yv = Number(yData[j])
        if (yv < yRangeMin || yv > yRangeMax) continue
      }
      const x = xs[j]
      if (x === undefined) continue
      if (x < xMin) xMin = x
      if (x > xMax) xMax = x
    }

    if (!Number.isFinite(xMin) || !Number.isFinite(xMax) || xMin === xMax) return

    // Fit X means fit; no padding.
    await Plotly.relayout(gd as Plotly.Root, {
      'xaxis.range': [plotCoordToDate(xMin), plotCoordToDate(xMax)],
      'xaxis.autorange': false,
    } as unknown as Partial<Layout>)
  } finally {
    isUpdating.value = false
  }
}

/**
 * Crops the QC trace's y axis to the extent of its currently visible
 * points: those inside both the live x-range and the live y-range.
 * Only the primary `yaxis` (where QC always lives, per
 * `createPlotlyOption`) is rescaled; every non-QC overlay keeps the
 * range the user set on it.
 * @param _eventData unused; preserved for the modebar click signature.
 */
export const fitYaxisToVisible = async (_eventData?: unknown) => {
  const { plotlyRef, isUpdating } = storeToRefs(usePlotlyStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())

  isUpdating.value = true

  try {
    const gd = plotlyRef.value
    if (!gd) return
    const qcId = qcDatastream.value?.id
    if (!qcId) return

    const qcIndex = (gd.data ?? []).findIndex(
      (t) => (t as AppPlotlyTrace).id === qcId
    )
    if (qcIndex < 0) return
    const qcTrace = gd.data[qcIndex] as AppPlotlyTrace
    const visible = qcTrace.visible as unknown
    if (visible === false || visible === 'legendonly') return

    // Read the live layout, never `plotlyOptions`: the stored layout
    // stops tracking the plot once any update replaces an axis object.
    const liveLayout = gd.layout as unknown as
      | Record<string, Partial<LayoutAxis> | unknown>
      | undefined
    const liveXRange = (
      (liveLayout?.xaxis as Partial<LayoutAxis> | undefined)?.range as
      | Array<string | number>
      | undefined
    )?.map(plotCoord)

    const xs = traceXAsNumbers(gd, qcIndex)
    const startIdx = findFirstGreaterOrEqual(xs, liveXRange?.[0] ?? -Infinity)
    const endIdx = findFirstGreaterOrEqual(xs, liveXRange?.[1] ?? Infinity)
    if (endIdx - startIdx <= 0) return

    // Points above or below the current view are not visible, so they
    // don't count; this also keeps off-screen outliers out of the fit.
    const liveYAxis = liveLayout?.yaxis as Partial<LayoutAxis> | undefined
    const yRange = (liveYAxis?.range ?? []) as Array<number>
    const yRangeMin = Number(yRange[0])
    const yRangeMax = Number(yRange[1])
    const hasYClamp = Number.isFinite(yRangeMin) && Number.isFinite(yRangeMax)
    const yData = (qcTrace.y ?? []) as ArrayLike<number>

    let yMin = Infinity
    let yMax = -Infinity
    for (let j = startIdx; j < endIdx; j++) {
      const val = Number(yData[j])
      if (!Number.isFinite(val)) continue
      if (hasYClamp && (val < yRangeMin || val > yRangeMax)) continue
      if (val < yMin) yMin = val
      if (val > yMax) yMax = val
    }

    if (!Number.isFinite(yMin) || !Number.isFinite(yMax) || yMin === yMax) return

    // Fit Y means fit; no padding, same as `fitXaxisToVisible`.
    await Plotly.relayout(gd as Plotly.Root, {
      'yaxis.range': [yMin, yMax],
      'yaxis.autorange': false,
    } as unknown as Partial<Layout>)
  } finally {
    isUpdating.value = false
  }
}
