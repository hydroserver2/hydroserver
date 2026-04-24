import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import type {
  PlotData,
  PlotMouseEvent,
  PlotRelayoutEvent,
  PlotSelectionEvent,
} from 'plotly.js-dist'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import type { AppPlotlyTrace } from './options'

/**
 * `handleSelected` is called from `handleClick` (with a `PlotMouseEvent`),
 * from `handleRelayout` (with a `PlotRelayoutEvent`-shaped object), and
 * occasionally with `null`/`undefined` to mean "re-sync the QC selection
 * without dispatching a filter".
 */
export const handleSelected = async (
  eventData?: PlotMouseEvent | PlotRelayoutEvent | PlotSelectionEvent | null
) => {
  const { plotlyRef, selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
  const { selectedData } = storeToRefs(useDataVisStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())

  const trace = plotlyRef.value?.data.find(
    (t: Partial<PlotData>) => (t as AppPlotlyTrace).id == qcDatastream.value?.id
  ) as (AppPlotlyTrace & { selectedpoints?: number[] }) | undefined

  // Plotly's `selectedpoints` are indices into the *windowed* x/y
  // arrays; offset by the window's start position before storing.
  const windowOffset = (trace as AppPlotlyTrace)?._windowStartIdx ?? 0
  const rawSelected = trace?.selectedpoints
  selectedData.value = rawSelected?.length
    ? rawSelected.map((i) => i + windowOffset)
    : null

  const relayout = eventData as Partial<PlotRelayoutEvent> | null | undefined
  if (
    relayout?.dragmode || // Changing selected tool
    relayout?.['xaxis.range[0]'] // Zooming
  ) {
    return
  }

  // Only dispatch the SELECTION filter on user gestures. Suppressing it
  // when `isUpdating` is true prevents undo/redo from clearing the redo
  // stack via a programmatic selection echo.
  if (eventData && !isUpdating.value) {
    await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.SELECTION,
      selectedData.value ?? []
    )

    // Sync Vue's reactive editHistory with the raw history array
    // (dispatchFilter mutates the array outside Vue's proxy)
    const { editHistory } = storeToRefs(usePlotlyStore())
    editHistory.value = selectedSeries.value?.data.history ?? []
  }

  // TODO: prevent selection on other traces
}
