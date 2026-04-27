import { usePlotlyStore } from '@/store/plotly'
import Plotly from 'plotly.js-dist'
import type {
  LayoutAxis,
  PlotData,
  PlotlyHTMLElement,
  PlotMouseEvent,
} from 'plotly.js-dist'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { debounce } from 'lodash-es'
import { handleSelected } from './selected'
import { captureCurrentZoomState, installZoomTracking } from './zoom'
import { handleRelayout } from './relayout'
import {
  handleMouseMove,
  handleMouseOut,
  handleWheel,
  widenYAxisDragRects,
  suppressHiddenAxisDragRects,
  updateAxisChips,
} from './interaction'
import type { AppPlotlyTrace } from './options'

const handleClick = async (eventData: PlotMouseEvent) => {
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
        ? [...(pointData.selectedpoints as number[])]
        : [pointData.selectedpoints as number]
    }

    const index = alreadySelected.indexOf(point.pointIndex)
    index >= 0
      ? alreadySelected.splice(index, 1)
      : alreadySelected.push(point.pointIndex)
    alreadySelected.sort()

    await Plotly.update(plotlyRef.value as Plotly.Root, {}, { selections: [] }, [0])
    await Plotly.restyle(plotlyRef.value as Plotly.Root, {
      selectedpoints: [[...alreadySelected]],
    })
    handleSelected(eventData)
  }
}

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
  installZoomTracking(plotlyRef.value)
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
  plotlyRef.value?.on('plotly_selected', () => {
    storeToRefs(useDataVisStore()).hasSelectionShape.value = true
  })
  plotlyRef.value?.on('plotly_deselect', () => {
    storeToRefs(useDataVisStore()).hasSelectionShape.value = false
  })

  plotlyRef.value?.on('plotly_click', handleClick)

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
