import type {
  Layout,
  LayoutAxis,
  PlotlyHTMLElement,
  PrivatePlotlyHTMLElement,
} from 'plotly.js-dist'
import Plotly from 'plotly.js-dist'
import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import { Y_AXIS_KEY_RE } from './internal'
import type { AppPlotlyTrace, AxisChip } from './options'

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
export const widenYAxisDragRects = (gd: HTMLElement): void => {
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
export const suppressHiddenAxisDragRects = (gd: HTMLElement): void => {
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
export const updateAxisChips = (gd: PlotlyHTMLElement | null): void => {
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
  let leftIdx = 0
  let rightIdx = 0
  // Iterate `graphSeriesArray` — it's the authoritative sidebar
  // order; `gd.data` gets reversed so traces paint top-over-bottom
  // (see `createPlotlyOption`), which would flip the stacked chips.
  for (const series of graphSeriesArray.value) {
    const trace = gd.data.find(
      (t) => (t as AppPlotlyTrace).id === series.id
    ) as AppPlotlyTrace | undefined
    const axisRef = trace?.yaxis as string | undefined
    if (!axisRef) continue
    // Primary (QC) y-axis lives on `y` / `yaxis`; right-side overlays
    // on `y2`/`y3`/...
    const isPrimary = axisRef === 'y'
    const axisKey = isPrimary ? 'yaxis' : `yaxis${axisRef.slice(1)}`
    const ax = fl[axisKey] as
      | { visible?: boolean; _mainLinePosition?: number; _shift?: number }
      | undefined
    if (!ax || ax.visible === false) continue
    if (typeof ax._mainLinePosition !== 'number') continue
    const lineX = ax._mainLinePosition + (ax._shift ?? 0)
    if (!Number.isFinite(lineX)) continue

    const side: 'left' | 'right' = isPrimary ? 'left' : 'right'
    chips.push({
      id: series.id,
      lineX,
      graphWidth,
      title: series.yAxisLabel,
      color: labelColorForDatastream(series.id),
      side,
      chipIdx: side === 'left' ? leftIdx++ : rightIdx++,
    })
  }

  const key = chips
    .map((c) => `${c.id}:${c.lineX}:${c.graphWidth}:${c.title}:${c.side}:${c.chipIdx}`)
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
