<template>
  <div class="plot-context" ref="rootEl">
    <div ref="plotEl" class="plot-context__plot"></div>
    <div
      v-show="hasBrush"
      class="plot-context__overlay"
      ref="overlayEl"
      @pointerdown="onBackgroundPointerDown"
    >
      <div
        class="plot-context__shade"
        :style="{ left: '0px', width: brushPixL + 'px' }"
      />
      <div
        class="plot-context__shade"
        :style="{ left: brushPixR + 'px', right: '0px' }"
      />
      <div
        class="plot-context__brush"
        :style="{ left: brushPixL + 'px', width: brushPixW + 'px' }"
        @pointerdown.stop="onBrushPointerDown"
      >
        <div
          class="plot-context__handle plot-context__handle--l"
          @pointerdown.stop="(e) => onHandlePointerDown('l', e)"
        />
        <div
          class="plot-context__handle plot-context__handle--r"
          @pointerdown.stop="(e) => onHandlePointerDown('r', e)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import Plotly from 'plotly.js-dist'
import type { Layout, LayoutAxis, PlotlyHTMLElement } from 'plotly.js-dist'
import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import { COLORS, type AppPlotlyTrace } from '@/utils/plotting/plotly'
import type { GraphSeries } from '@/types'

const TARGET_POINTS = 2000
const MIN_BRUSH_PX = 8

// Plotly's PlotlyHTMLElement extends EventEmitter at runtime, but the
// published types only surface `.on` / `.removeAllListeners`. We use the
// node-style `.removeListener(event, handler)` form to unsubscribe a
// specific handler — declare the shape here so the call sites don't
// need scattered `as any` casts.
type PlotlyEventEmitter = {
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void
}

const { plotlyRef, graphSeriesArray, mainPlotEpoch } =
  storeToRefs(usePlotlyStore())
const { qcDatastream } = storeToRefs(useDataVisStore())

const rootEl = ref<HTMLDivElement>()
const plotEl = ref<HTMLDivElement>()
const overlayEl = ref<HTMLDivElement>()

// Pixel-space brush window, computed from the main plot's xaxis range
// projected onto the context plot area. Updated on main-plot relayout
// and on resize.
const brushPixL = ref(0)
const brushPixW = ref(0)
const brushPixR = computed(() => brushPixL.value + brushPixW.value)
const hasBrush = ref(false)

let ctxGd: PlotlyHTMLElement | null = null
let dataExtent: [number, number] | null = null
let resizeObs: ResizeObserver | null = null
let mainRelayoutHandler: (() => void) | null = null
let mainRestyleHandler: (() => void) | null = null
let pendingMainUpdate: number | null = null
let pendingTargetRange: [number, number] | null = null

// Datastream ids whose trace is hidden in the main plot (via the eye toggle
// in PlottedDatastreams). Mirrored from `plotlyRef.value.data[*].visible`
// because that state lives on the live Plotly trace, not in the store.
const hiddenIds = ref<Set<string>>(new Set())

// --- Downsampling -----------------------------------------------------------
// Stride sample, always preserving the last point so the line reaches the
// right edge. Lines-only context view: visual fidelity is fine without LTTB.
function strideSample(
  xs: ArrayLike<number>,
  ys: ArrayLike<number>,
  target: number
): { x: number[]; y: number[] } {
  const n = xs.length
  if (n === 0) return { x: [], y: [] }
  const stride = Math.max(1, Math.floor(n / target))
  const outX: number[] = []
  const outY: number[] = []
  for (let i = 0; i < n; i += stride) {
    outX.push(xs[i] as number)
    outY.push(ys[i] as number)
  }
  const lastX = xs[n - 1] as number
  if (outX[outX.length - 1] !== lastX) {
    outX.push(lastX)
    outY.push(ys[n - 1] as number)
  }
  return { x: outX, y: outY }
}

function normalize(ys: number[]): number[] {
  let lo = Infinity
  let hi = -Infinity
  for (const v of ys) {
    if (Number.isFinite(v)) {
      if (v < lo) lo = v
      if (v > hi) hi = v
    }
  }
  const span = hi - lo
  if (!Number.isFinite(span) || span <= 0) return ys.map(() => 0.5)
  return ys.map((v) => (Number.isFinite(v) ? (v - lo) / span : 0.5))
}

function buildContextTraces(series: GraphSeries[]): {
  traces: AppPlotlyTrace[]
  extent: [number, number] | null
} {
  const qcId = qcDatastream.value?.id
  const traces: AppPlotlyTrace[] = []
  let xMin = Infinity
  let xMax = -Infinity

  for (const s of series) {
    if (hiddenIds.value.has(s.id)) continue
    const xs = s.data?.dataX as ArrayLike<number> | undefined
    const ys = s.data?.dataY as ArrayLike<number> | undefined
    if (!xs?.length || !ys?.length) continue
    if ((xs[0] as number) < xMin) xMin = xs[0] as number
    if ((xs[xs.length - 1] as number) > xMax) xMax = xs[xs.length - 1] as number
    const sampled = strideSample(xs, ys, TARGET_POINTS)
    const yNorm = normalize(sampled.y)
    const isQc = !!qcId && s.id === qcId
    const color = isQc ? COLORS[0] : (s.color ?? COLORS[1])
    traces.push({
      x: sampled.x,
      y: yNorm,
      type: 'scattergl',
      mode: 'lines',
      line: { color, width: 1 },
      hoverinfo: 'skip',
      showlegend: false,
    })
  }

  // Mirror main plot draw order: seriesArray[0] paints on top.
  traces.reverse()
  const extent: [number, number] | null =
    Number.isFinite(xMin) && Number.isFinite(xMax) ? [xMin, xMax] : null
  return { traces, extent }
}

// --- Main-plot live xaxis range read ---------------------------------------
function readMainXRange(): [number, number] | null {
  const gd = plotlyRef.value as
    | (PlotlyHTMLElement & {
        _fullLayout?: { xaxis?: Partial<LayoutAxis> }
        layout?: Partial<Layout>
      })
    | null
  const r =
    (gd?._fullLayout?.xaxis?.range as Array<string | number> | undefined) ??
    ((gd?.layout?.xaxis as Partial<LayoutAxis> | undefined)?.range as
      | Array<string | number>
      | undefined)
  if (!r) return null
  const a = typeof r[0] === 'string' ? Date.parse(r[0]) : Number(r[0])
  const b = typeof r[1] === 'string' ? Date.parse(r[1]) : Number(r[1])
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null
  return [a, b]
}

// --- Pixel/data conversion against the context plot ------------------------
function getCtxPlotMetrics(): {
  offset: number
  length: number
  range: [number, number]
} | null {
  const gd = ctxGd as
    | (PlotlyHTMLElement & {
        _fullLayout?: {
          xaxis?: Partial<LayoutAxis> & { _offset?: number; _length?: number }
        }
      })
    | null
  const xa = gd?._fullLayout?.xaxis
  if (!xa || xa._offset == null || xa._length == null) return null
  const r = xa.range as Array<string | number> | undefined
  if (!r) return null
  const a = typeof r[0] === 'string' ? Date.parse(r[0]) : Number(r[0])
  const b = typeof r[1] === 'string' ? Date.parse(r[1]) : Number(r[1])
  if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return null
  return { offset: xa._offset, length: xa._length, range: [a, b] }
}

function dataToPixel(dataValue: number): number | null {
  const m = getCtxPlotMetrics()
  if (!m) return null
  return (
    m.offset + ((dataValue - m.range[0]) / (m.range[1] - m.range[0])) * m.length
  )
}

function pixelToData(px: number): number | null {
  const m = getCtxPlotMetrics()
  if (!m) return null
  return m.range[0] + ((px - m.offset) / m.length) * (m.range[1] - m.range[0])
}

// --- Sync brush <- main plot -----------------------------------------------
function syncBrushFromMain() {
  const range = readMainXRange()
  const m = getCtxPlotMetrics()
  if (!range || !m) {
    hasBrush.value = false
    return
  }
  const a = dataToPixel(range[0])
  const b = dataToPixel(range[1])
  if (a == null || b == null) {
    hasBrush.value = false
    return
  }
  const minPx = m.offset
  const maxPx = m.offset + m.length
  const left = Math.max(minPx, Math.min(maxPx, Math.min(a, b)))
  const right = Math.max(minPx, Math.min(maxPx, Math.max(a, b)))
  brushPixL.value = left
  brushPixW.value = Math.max(0, right - left)
  hasBrush.value = true
}

// --- Brush -> main plot (RAF throttled) ------------------------------------
function scheduleMainUpdate(target: [number, number]) {
  pendingTargetRange = target
  if (pendingMainUpdate != null) return
  pendingMainUpdate = requestAnimationFrame(() => {
    pendingMainUpdate = null
    const range = pendingTargetRange
    pendingTargetRange = null
    if (!range) return
    const gd = plotlyRef.value as PlotlyHTMLElement | null
    if (!gd) return
    void Plotly.relayout(
      gd as unknown as HTMLElement,
      {
        'xaxis.range': [range[0], range[1]],
        'xaxis.autorange': false,
      } as unknown as Partial<Layout>
    )
  })
}

function pushBrushPixelsToMain() {
  const left = brushPixL.value
  const right = brushPixL.value + brushPixW.value
  const a = pixelToData(left)
  const b = pixelToData(right)
  if (a == null || b == null) return
  scheduleMainUpdate([a, b])
}

// --- Pointer interaction ----------------------------------------------------
type DragKind = 'move' | 'l' | 'r' | 'create'
let drag: {
  kind: DragKind
  startX: number
  origLeft: number
  origWidth: number
} | null = null

function clamp(px: number): number {
  const m = getCtxPlotMetrics()
  if (!m) return px
  return Math.max(m.offset, Math.min(m.offset + m.length, px))
}

function pointerXInOverlay(e: PointerEvent): number {
  // Return pixel x in the same coordinate space as `_offset` / `_length`,
  // i.e. relative to the gd element. The overlay covers the gd, so we
  // measure from the plotEl (which IS the gd) bounding rect.
  const rect = plotEl.value?.getBoundingClientRect()
  if (!rect) return 0
  return e.clientX - rect.left
}

function onBrushPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  drag = {
    kind: 'move',
    startX: pointerXInOverlay(e),
    origLeft: brushPixL.value,
    origWidth: brushPixW.value,
  }
  ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
}

function onHandlePointerDown(side: 'l' | 'r', e: PointerEvent) {
  if (e.button !== 0) return
  drag = {
    kind: side,
    startX: pointerXInOverlay(e),
    origLeft: brushPixL.value,
    origWidth: brushPixW.value,
  }
  ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
}

function onBackgroundPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  // Click on empty area starts a new brush window from that point.
  const x = clamp(pointerXInOverlay(e))
  brushPixL.value = x
  brushPixW.value = 0
  drag = { kind: 'create', startX: x, origLeft: x, origWidth: 0 }
  ;(overlayEl.value as Element | undefined)?.setPointerCapture?.(e.pointerId)
}

function onPointerMove(e: PointerEvent) {
  if (!drag) return
  const m = getCtxPlotMetrics()
  if (!m) return
  const x = pointerXInOverlay(e)
  const dx = x - drag.startX
  const minPx = m.offset
  const maxPx = m.offset + m.length

  if (drag.kind === 'move') {
    let nl = drag.origLeft + dx
    if (nl < minPx) nl = minPx
    if (nl + drag.origWidth > maxPx) nl = maxPx - drag.origWidth
    brushPixL.value = nl
    brushPixW.value = drag.origWidth
  } else if (drag.kind === 'l') {
    const right = drag.origLeft + drag.origWidth
    let nl = Math.min(right - MIN_BRUSH_PX, drag.origLeft + dx)
    if (nl < minPx) nl = minPx
    brushPixL.value = nl
    brushPixW.value = right - nl
  } else if (drag.kind === 'r') {
    let nr = Math.max(
      drag.origLeft + MIN_BRUSH_PX,
      drag.origLeft + drag.origWidth + dx
    )
    if (nr > maxPx) nr = maxPx
    brushPixL.value = drag.origLeft
    brushPixW.value = nr - drag.origLeft
  } else if (drag.kind === 'create') {
    const cx = clamp(x)
    const left = Math.min(drag.startX, cx)
    const right = Math.max(drag.startX, cx)
    brushPixL.value = left
    brushPixW.value = Math.max(MIN_BRUSH_PX, right - left)
  }
  pushBrushPixelsToMain()
}

function onPointerUp(e: PointerEvent) {
  if (!drag) return
  drag = null
  ;(e.target as Element | null)?.releasePointerCapture?.(e.pointerId)
}

// --- Lifecycle / wiring -----------------------------------------------------
async function buildOrUpdate() {
  const el = plotEl.value
  if (!el) return
  const { traces, extent } = buildContextTraces(
    graphSeriesArray.value as GraphSeries[]
  )
  dataExtent = extent

  if (!extent || !traces.length) {
    if (ctxGd) {
      try {
        Plotly.purge(ctxGd as unknown as HTMLElement)
      } catch {
        /* ignore */
      }
      ctxGd = null
    }
    hasBrush.value = false
    return
  }

  const layout: Partial<Layout> = {
    xaxis: {
      type: 'date',
      visible: false,
      range: [extent[0], extent[1]],
      fixedrange: true,
      autorange: false,
    } as Partial<LayoutAxis>,
    yaxis: {
      visible: false,
      range: [-0.05, 1.05],
      fixedrange: true,
      autorange: false,
    } as Partial<LayoutAxis>,
    margin: { l: 0, r: 0, t: 0, b: 0 },
    showlegend: false,
    hovermode: false,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
  }

  const config = {
    displayModeBar: false,
    staticPlot: true,
    responsive: true,
  } as unknown as Partial<Plotly.Config>

  ctxGd = (await Plotly.newPlot(
    el,
    traces as unknown as Plotly.Data[],
    layout,
    config
  )) as unknown as PlotlyHTMLElement

  syncBrushFromMain()
}

// Rebuild signature: changes only when series identity / length / color /
// QC target shifts. Per-cell y-edits don't refresh the context view (cheap
// and the overall shape barely changes anyway).
const rebuildSignature = computed(() => {
  const qid = qcDatastream.value?.id ?? ''
  const parts = graphSeriesArray.value.map(
    (s) => `${s.id}:${s.data?.dataX?.length ?? 0}:${s.color}`
  )
  const hidden = [...hiddenIds.value].sort().join(',')
  return parts.join('|') + '#' + qid + '!' + hidden
})

watch(rebuildSignature, () => {
  void buildOrUpdate()
})

function syncHiddenFromMain() {
  const gd = plotlyRef.value as PlotlyHTMLElement | null
  if (!gd) return
  const next = new Set<string>()
  for (const t of gd.data ?? []) {
    const tt = t as AppPlotlyTrace
    const v = tt.visible as unknown
    if (tt.id && (v === false || v === 'legendonly')) next.add(tt.id)
  }
  const cur = hiddenIds.value
  if (next.size !== cur.size || [...next].some((id) => !cur.has(id))) {
    hiddenIds.value = next
  }
}

function attachMainListener() {
  const gd = plotlyRef.value as PlotlyHTMLElement | null
  if (!gd) return
  if (mainRelayoutHandler) {
    ;(gd as unknown as PlotlyEventEmitter).removeListener?.(
      'plotly_relayout',
      mainRelayoutHandler as never
    )
  }
  mainRelayoutHandler = () => syncBrushFromMain()
  gd.on('plotly_relayout', mainRelayoutHandler as never)

  if (mainRestyleHandler) {
    ;(gd as unknown as PlotlyEventEmitter).removeListener?.(
      'plotly_restyle',
      mainRestyleHandler as never
    )
  }
  mainRestyleHandler = () => syncHiddenFromMain()
  gd.on('plotly_restyle', mainRestyleHandler as never)
  // Seed initial hidden state too — ensures rebuild picks it up if a trace
  // was already hidden when the context mounted.
  syncHiddenFromMain()
}

// `plotlyRef` only changes identity on first mount — `handleNewPlot`
// reuses the same DOM node on every replot. `mainPlotEpoch` bumps on
// every `Plotly.newPlot` run (which purges externally-attached event
// listeners), so we watch it too and re-bind the relayout/restyle
// handlers that drive the context brush.
watch(
  [plotlyRef, mainPlotEpoch],
  () => {
    attachMainListener()
    syncBrushFromMain()
  },
  { immediate: true, flush: 'post' }
)

onMounted(async () => {
  await buildOrUpdate()
  attachMainListener()
  syncBrushFromMain()

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)

  if (rootEl.value && typeof ResizeObserver !== 'undefined') {
    let initial = false
    resizeObs = new ResizeObserver(() => {
      if (!initial) {
        initial = true
        return
      }
      if (!ctxGd) return
      const anyGd = ctxGd as unknown as { _fullLayout?: unknown }
      if (!anyGd._fullLayout) return
      // `Plotly.Plots.resize` is typed as returning `void` in
      // plotly.js-dist's public surface but actually returns a Promise
      // at runtime. Cast through `unknown` to chain the brush sync
      // after layout settles.
      void (
        Plotly.Plots.resize(ctxGd as unknown as Plotly.Root) as unknown as Promise<void>
      ).then(() => syncBrushFromMain())
    })
    resizeObs.observe(rootEl.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  if (resizeObs) {
    resizeObs.disconnect()
    resizeObs = null
  }
  const gd = plotlyRef.value as PlotlyHTMLElement | null
  if (mainRelayoutHandler) {
    ;(gd as unknown as PlotlyEventEmitter | null)?.removeListener?.(
      'plotly_relayout',
      mainRelayoutHandler as never
    )
    mainRelayoutHandler = null
  }
  if (mainRestyleHandler) {
    ;(gd as unknown as PlotlyEventEmitter | null)?.removeListener?.(
      'plotly_restyle',
      mainRestyleHandler as never
    )
    mainRestyleHandler = null
  }
  if (pendingMainUpdate != null) {
    cancelAnimationFrame(pendingMainUpdate)
    pendingMainUpdate = null
  }
  if (ctxGd) {
    try {
      Plotly.purge(ctxGd as unknown as HTMLElement)
    } catch {
      /* ignore */
    }
    ctxGd = null
  }
})

// Expose for tests / external callers if needed
defineExpose({ syncBrushFromMain })
// Reference suppress to keep TS quiet about unused.
void dataExtent
</script>

<style scoped>
.plot-context {
  position: relative;
  height: 64px;
  flex: 0 0 auto;
  background-color: rgba(var(--v-theme-on-surface), 0.02);
  user-select: none;
  touch-action: none;
}

.plot-context__plot {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.plot-context__overlay {
  position: absolute;
  inset: 0;
  cursor: crosshair;
}

.plot-context__shade {
  position: absolute;
  top: 0;
  bottom: 0;
  background-color: rgba(var(--v-theme-on-surface), 0.18);
  pointer-events: none;
}

.plot-context__brush {
  position: absolute;
  top: 0;
  bottom: 0;
  background-color: rgba(var(--v-theme-primary), 0.08);
  border-left: 1px solid rgba(var(--v-theme-primary), 0.65);
  border-right: 1px solid rgba(var(--v-theme-primary), 0.65);
  cursor: grab;
}

.plot-context__brush:active {
  cursor: grabbing;
}

.plot-context__handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  background-color: rgba(var(--v-theme-primary), 0.55);
}

.plot-context__handle:hover {
  background-color: rgba(var(--v-theme-primary), 0.85);
}

.plot-context__handle--l {
  left: -4px;
  cursor: ew-resize;
}

.plot-context__handle--r {
  right: -4px;
  cursor: ew-resize;
}
</style>
