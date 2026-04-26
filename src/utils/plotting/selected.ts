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
 *
 * The SELECTION-dispatch branch is the source-of-truth for "user just
 * selected something on the plot". To distinguish a real user gesture
 * from the relayout echo of our own programmatic Plotly writes
 * (`setPlotSelection`, `clearSelected`), the writers arm a sentinel
 * (`suppressNextRelayoutEcho`) before their `Plotly.update`. The next
 * `plotly_relayout`-induced `handleSelected` call (i.e. `fromRelayout:
 * true`) consumes the sentinel and skips its dispatch. The
 * click-induced path (`fromRelayout` falsy, default) ignores the
 * sentinel — user clicks always dispatch.
 *
 * The sentinel approach replaces an earlier time-windowed guard that
 * broke at scale: Plotly's relayout debounce stretches past any
 * fixed window on large datasets. Tying the suppress to the actual
 * event firing makes it timing-independent.
 */
export const handleSelected = async (
  eventData?: PlotMouseEvent | PlotRelayoutEvent | PlotSelectionEvent | null,
  opts: { fromRelayout?: boolean } = {}
) => {
  const { plotlyRef, selectedSeries, isUpdating, suppressNextRelayoutEcho } =
    storeToRefs(usePlotlyStore())
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

  // Only dispatch the SELECTION filter on user gestures. Two
  // suppression signals layer here:
  //
  //  1. `isUpdating` — set by undo/redo and dispatch-helper composables
  //     so a programmatic re-render doesn't echo back as a SELECTION
  //     and clobber the redo stack.
  //  2. `suppressNextRelayoutEcho` — sentinel armed by
  //     `setPlotSelection` / `clearSelected`. Consumed (and cleared)
  //     here on the relayout path so the programmatic write's own
  //     relayout echo never reaches `dispatchFilter`. Click and
  //     direct-call paths bypass — they're real user gestures.
  if (opts.fromRelayout && suppressNextRelayoutEcho.value) {
    suppressNextRelayoutEcho.value = false
    return
  }
  if (eventData && !isUpdating.value) {
    await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.SELECTION,
      selectedData.value ?? []
    )
  }

  // TODO: prevent selection on other traces
}
