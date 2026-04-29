import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import Plotly from 'plotly.js-dist'
import type {
  Layout,
  LayoutAxis,
  PlotData,
  PlotRelayoutEvent,
} from 'plotly.js-dist'
import { storeToRefs } from 'pinia'
import { isEqual } from 'lodash-es'
import { findFirstGreaterOrEqual } from '@uwrl/qc-utils'
import { traceXAsNumbers, DENSITY_HIDE_MARKERS } from './internal'
import type { AppPlotlyTrace } from './options'
import { handleSelected } from './selected'

// Perf cache for `handleRelayout`: when a relayout fires but the visible
// x-range hasn't appreciably moved, skip the O(traces) binary-search scan.
// A null event means "forced recompute" (fresh plot, data edit) and
// bypasses the cache.
let lastVisibleRange: [number, number] | null = null

export const invalidateVisibleRangeCache = () => {
  lastVisibleRange = null
}

/**
 * Convert a datastream's `intendedTimeSpacing` + `intendedTimeSpacingUnit`
 * into milliseconds. Returns `null` when either field is missing.
 */
export const intendedSpacingMs = (): number | null => {
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
 * intended cadence, bounded to the visible x-range. Returns `null` when
 * we should hand back to Plotly's auto tick picker.
 */
export const computeIntendedTickvals = (
  xStart: number,
  xEnd: number
): number[] | null => {
  const unit = intendedSpacingMs()
  if (!unit) return null
  if (!Number.isFinite(xStart) || !Number.isFinite(xEnd)) return null
  const span = xEnd - xStart
  if (span <= 0) return null

  const TARGET_TICKS = 8
  // Cap tick count before rotated labels start colliding.
  const MAX_TICKS = 15
  const raw = span / (unit * TARGET_TICKS)

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
  if (span / step > MAX_TICKS) return null

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
export const tickvalsEqual = (
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
    tooltipsMode,
  } = storeToRefs(usePlotlyStore())

  handleSelected(eventData, { fromRelayout: true })

  const evt = eventData as
    | (PlotRelayoutEvent & {
      selections?: unknown
      'selections[0].x0'?: unknown
      'xaxis.autorange'?: unknown
    })
    | null
  if (
    isUpdating.value ||
    evt?.dragmode ||
    evt?.selections ||
    evt?.['selections[0].x0'] ||
    isEqual(eventData, {})
  ) {
    return
  }

  // `resetScale2d` fires a relayout with `xaxis.autorange: true`. Reset
  // any imposed tick grid synchronously before the debounced body runs.
  if (evt?.['xaxis.autorange'] === true && plotlyRef.value) {
    try {
      await Plotly.relayout(plotlyRef.value as unknown as HTMLElement, {
        'xaxis.tickmode': 'auto',
        'xaxis.tickvals': null,
      } as unknown as Partial<Layout>)
    } catch (err) {
      console.warn('Failed to reset x-axis tick grid on autorange', err)
    }
  }

  isUpdating.value = true

  setTimeout(async () => {
    try {
      // Always read from the LIVE plotly layout.
      const liveLayout =
        (plotlyRef.value as unknown as { layout?: Partial<Layout> })?.layout
      const liveXaxis = liveLayout?.xaxis as Partial<LayoutAxis> | undefined
      const xRange = liveXaxis?.range as Array<string | number> | undefined

      if (xRange && typeof xRange[0] == 'string') {
        xRange[0] = Date.parse(xRange[0])
        xRange[1] = Date.parse(xRange[1] as string)
      }

      const xStart = Number(xRange?.[0])
      const xEnd = Number(xRange?.[1])

      // Only rescan when the visible x-range actually moved.
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

      // Find number of visible points per trace.
      const traceCount = plotlyRef.value?.data.length ?? 0
      const perTraceVisible: number[] = new Array(traceCount).fill(0)
      for (let i = 0; i < traceCount; i++) {
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

      // Density-responsive marker rendering. When the data-points
      // toggle is on every trace keeps its markers so hover
      // hit-testing lands on any series. When the toggle is off
      // markers fade past the density threshold so the lines stay
      // readable. `areTooltipsEnabled` already encodes the mode
      // policy (manual override vs. threshold-driven auto), so the
      // threshold isn't checked again here — doing so would make a
      // user's manual "on" silently flip off past the cap.
      const tooltipsWillRun = areTooltipsEnabled.value
      const { qcDatastream } = storeToRefs(useDataVisStore())
      const qcId = qcDatastream.value?.id
      const traces = (plotlyRef.value?.data ?? []) as AppPlotlyTrace[]
      const perTraceOpacity = perTraceVisible.map((n) => {
        if (tooltipsWillRun) return 1
        if (tooltipsMode.value === 'manual') return 0
        return n > DENSITY_HIDE_MARKERS ? 0 : 1
      })

      const currentOpacities = (plotlyRef.value?.data ?? []).map((t: Partial<PlotData>) => {
        const m = (t as Partial<PlotData>).marker as
          | { opacity?: number }
          | undefined
        return m?.opacity ?? 1
      })
      const opacitiesChanged = perTraceOpacity.some(
        (o, i) => o !== (currentOpacities[i] ?? 1)
      )
      if (opacitiesChanged && plotlyRef.value) {
        // Keep `unselected.marker.opacity` in lockstep with the
        // density-driven `marker.opacity` for non-QC traces so they
        // stay opted out of Plotly's global selection-fade no matter
        // what density bucket they land in. Pass `null` for the QC
        // trace to leave its `selected.marker` config untouched —
        // Plotly's restyle skips entries whose array slot is null.
        const perTraceUnselectedOpacity = perTraceOpacity.map((o, i) => {
          const isQc = qcId != null && traces[i]?.id === qcId
          return isQc ? null : o
        })
        await Plotly.restyle(plotlyRef.value, {
          'marker.opacity': perTraceOpacity,
          'unselected.marker.opacity': perTraceUnselectedOpacity,
        } as unknown as Partial<PlotData>)
      }

      // Align x-axis ticks to the datastream's intended cadence.
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

      if (!areTooltipsEnabled.value) {
        newHoverState = 'skip'
        newHoverTemplate = ''
      }

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
