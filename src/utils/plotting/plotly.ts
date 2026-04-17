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
// (findFirstGreaterOrEqual in handleRelayout / cropYaxisRange) get number[]
// without scattering `as number[]` across the file. If we ever introduce
// non-numeric x data, this is the single place to reconsider.
const traceXAsNumbers = (
  gd: PlotlyHTMLElement | null | undefined,
  traceIndex: number
): number[] => {
  const x = gd?.data[traceIndex]?.x
  return (x ?? []) as number[]
}

// TODO: import these directly from Plotly
// https://github.com/plotly/plotly.js/blob/v2.14.0/src/components/color/attributes.js#L5-L16
export const COLORS = [
  '#1f77b4', // muted blue
  '#ff7f0e', // safety orange
  '#2ca02c', // cooked asparagus green
  '#d62728', // brick red
  '#9467bd', // muted purple
  '#8c564b', // chestnut brown
  '#e377c2', // raspberry yogurt pink
  '#7f7f7f', // middle gray
  '#bcbd22', // curry yellow-green
  '#17becf', // blue-teal
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

export const createPlotlyOption = (
  seriesArray: GraphSeries[]
): PlotlyChartOptions => {
  const { qcDatastream } = storeToRefs(useDataVisStore())

  const traces: AppPlotlyTrace[] = []
  const yaxis: Partial<Layout> = {}

  let maxDatetime = -Infinity
  let minDatetime = Infinity
  const axisPlotFraction = 0.075 // Between 0 and 1

  let qcTrace: AppPlotlyTrace | undefined
  let qcYaxis: Partial<LayoutAxis> | undefined
  let counter = 0
  let axisSuffix: string | number = counter > 0 ? counter + 1 : ''

  seriesArray.forEach((s, index) => {
    const color = COLORS[index + 1] // The first color is reserved for the QC datastream
    const xData = s.data?.dataX

    if (xData?.length) {
      const xDataStart = xData[0] as number
      const xDataEnd = xData[xData.length - 1] as number

      maxDatetime = Math.max(xDataEnd, maxDatetime)
      minDatetime = Math.min(xDataStart, minDatetime)
    }

    const trace: AppPlotlyTrace = {
      id: s.id,
      x: s.data?.dataX,
      y: s.data?.dataY,
      yaxis: `y${axisSuffix}`,
      type: 'scattergl',
      mode: 'lines+markers',
      // https://github.com/plotly/plotly.js/issues/5927
      hoverinfo: 'skip', // Fixes performance issues, but disables tooltips
      // hoverinfo: 'x+y',
      name: s.name,
      showLegend: false,
      marker: {
        color,
      },
      line: {
        color,
      },
    }

    if (s.id === qcDatastream.value?.id) {
      // The trace for the QC datastream needs to be added last so it's drawn on top.
      qcTrace = trace
      qcTrace.marker = { ...(qcTrace.marker ?? {}), color: COLORS[0] }
      qcTrace.line = { ...(qcTrace.line ?? {}), color: COLORS[0] }
      qcTrace.selected = {
        marker: {
          color: 'red',
        },
      }
      qcYaxis = {
        title: {
          text: s.yAxisLabel,
          font: { color: COLORS[0], weight: 'bold' },
        },
        tickfont: { color: COLORS[0] },
        side: 'left',
        anchor: 'free',
        position: 0,
        showline: true,
        linecolor: COLORS[0],
      }
      const { editHistory } = storeToRefs(usePlotlyStore())
      editHistory.value = s.data.history
    } else {
      traces.push(trace)

      const yAxis: Partial<LayoutAxis> = {
        title: {
          text: s.yAxisLabel,
          font: { color, weight: 'bold' }
        },
        tickfont: { color },
        side: 'right',
        anchor: 'free',
        position: 1 - axisPlotFraction * counter,
        zeroline: false,
        showgrid: false,
        showline: true,
        linecolor: color,
        // fixedrange: true,
        // autorange: true,
      }
      if (axisSuffix) {
        yAxis.overlaying = 'y'
      }

      // Plotly accepts dynamic axis keys (`yaxis`, `yaxis2`, …) on the
      // layout object; keep the assignment indexed off `Partial<Layout>`.
      ; (yaxis as Record<string, Partial<LayoutAxis>>)[`yaxis${axisSuffix}`] = yAxis
      counter++
      axisSuffix = counter > 0 ? counter + 1 : ''
    }
  })

  if (qcTrace) {
    qcTrace.yaxis = `y${axisSuffix}`
    traces.push(qcTrace)
  }
  if (qcYaxis && axisSuffix) {
    qcYaxis.overlaying = 'y'
  }
  if (qcYaxis) {
    ; (yaxis as Record<string, Partial<LayoutAxis>>)[`yaxis${axisSuffix}`] = qcYaxis
  }

  const xaxis: Partial<LayoutAxis> = {
    type: 'date',
    title: { text: 'Datetime' },
    rangeselector: selectorOptions,
    range: [minDatetime, maxDatetime],
    // minallowed: minDatetime,
    // maxallowed: maxDatetime,
    autorange: false,
    showline: true,
    // range slider compatibility for Scattergl: https://github.com/plotly/plotly.js/issues/2627
  }

  if (seriesArray.length > 2) {
    xaxis.domain = [0, 1 - axisPlotFraction * (seriesArray.length - 2)]
  }

  const layout: Partial<Layout> = {
    spikedistance: 0, // https://github.com/plotly/plotly.js/issues/5927#issuecomment-1697679087
    // hoverdistance: 20,
    xaxis,
    ...yaxis,
    dragmode: 'pan',
    hovermode: 'closest', // Disable if hovering is too costly
    title: {
      text: qcTrace?.name,
      font: { color: COLORS[0], weight: 'bold' },
    },
    showlegend: false,
  }

  const config = {
    displayModeBar: true,
    showlegend: false,
    modeBarButtonsToRemove: ['toImage', 'autoScale'],
    scrollZoom: true,
    responsive: true,
    doubleClick: false,
    modeBarButtonsToAdd: [
      {
        name: 'Autoscale Y axis',
        icon: iconRescaleY,
        direction: 'up',
        click: cropYaxisRange,
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
        ? [...pointData.selectedpoints]
        : [pointData.selectedpoints]
    }

    const index = alreadySelected.indexOf(point.pointIndex)
    // Toggle the point
    index >= 0
      ? alreadySelected.splice(index, 1)
      : alreadySelected.push(point.pointIndex)

    alreadySelected.sort()

    // Removes selected areas
    await Plotly.update(plotlyRef.value, {}, { selections: [] }, [0])

    // Colors selected points
    await Plotly.restyle(plotlyRef.value, {
      selectedpoints: [[...alreadySelected]],
    } as Partial<PlotData>)

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

export const handleNewPlot = async (element?: HTMLElement) => {
  const { plotlyOptions, plotlyRef } = storeToRefs(usePlotlyStore())

  // `Plotly.newPlot` returns `Promise<PlotlyHTMLElement>`. The store's
  // `plotlyRef` is now typed as `PlotlyHTMLElement | null` 
  const newElement = await Plotly.newPlot(
    element || plotlyRef.value,
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
    } as Partial<PlotData>,
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
  } as Partial<PlotData>)
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

      await Plotly.update(plotlyRef.value, {}, layoutUpdates)
    } finally {
      isUpdating.value = false
    }
  })
}

/**
 * Crops the y axis to only contain the extent of currently visible points.
 * @param _eventData unused; preserved for the original modebar click signature.
 */
export const cropYaxisRange = async (_eventData?: unknown) => {
  const { plotlyOptions, plotlyRef, isUpdating, graphSeriesArray } =
    storeToRefs(usePlotlyStore())

  isUpdating.value = true

  try {
    const layoutUpdates: Partial<Layout> & Record<string, Partial<LayoutAxis>> = {}

    const liveXRange = (
      plotlyRef.value?.layout.xaxis.range as Array<string | number> | undefined
    )?.map((d) => (typeof d == 'string' ? Date.parse(d) : d))

    // Find visible points count
    for (let i = 0; i < graphSeriesArray.value.length; i++) {
      // Plotly does not return the indexes of current axis range. We must find them using binary search.
      const xs = traceXAsNumbers(plotlyRef.value, i)
      const startIdx = findFirstGreaterOrEqual(xs, liveXRange?.[0])
      const endIdx = findFirstGreaterOrEqual(xs, liveXRange?.[1])

      const axisKey = i == 0 ? 'yaxis' : `yaxis${i + 1}`
      const yAxis = (plotlyOptions.value.layout as Record<string, Partial<LayoutAxis>>)[axisKey]
      if (!yAxis) continue

      const traceData = plotlyRef.value?.data[i]
      // `Plotly.PlotData.y` is `Datum[] | Datum[][] | TypedArray`; this app
      // populates it with numeric arrays only — narrow at the use site.
      const yData = (traceData?.y ?? []) as ArrayLike<number>

      // Find all y-values within the current x-axis range
      let yMin = Infinity
      let yMax = -Infinity

      // `LayoutAxis.range` is typed `any[]` in @types/plotly.js; for QC
      // axes the runtime values are numbers — read positions explicitly.
      const yRange = yAxis.range ?? []
      const yRangeMin = Number(yRange[0])
      const yRangeMax = Number(yRange[1])

      // Could use Math.max and Math.min and spread operator, but this is more memory efficient
      for (let j = startIdx; j < endIdx; j++) {
        const val = Number(yData[j])
        if (yMin > val && val > yRangeMin) {
          yMin = val
        }

        if (yMax < val && val < yRangeMax) {
          yMax = val
        }
      }

      // Calculate new y-axis range with padding
      if (endIdx - startIdx != 0 && yMax !== yMin) {
        const padding = (yMax - yMin) * 0.1 // 10% padding

        layoutUpdates[axisKey] = {
          ...yAxis,
          range: [yMin - padding, yMax + padding],
          autorange: false,
        }
      }
    }

    // Update axis range
    await Plotly.update(plotlyRef.value, {}, layoutUpdates)
  } finally {
    isUpdating.value = false
  }
}
