import Plotly from 'plotly.js-dist'
import type { Layout, PlotlyHTMLElement } from 'plotly.js-dist'
import { storeToRefs } from 'pinia'
import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import type { AppPlotlyTrace } from './options'

type Range = [number, number]

const primarySeriesId = (): string | undefined => {
  const { graphSeriesArray } = storeToRefs(usePlotlyStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())
  return qcDatastream.value?.id ?? graphSeriesArray.value[0]?.id
}

/**
 * Whether a series has a y axis of its own that can lock to the primary
 * axis. The primary series and the raw source, which shares its axis,
 * don't.
 */
export const canLockAxis = (id: string): boolean => {
  const { graphSeriesArray } = storeToRefs(usePlotlyStore())
  const { sourceContextDatastream } = storeToRefs(useDataVisStore())
  const primaryId = primarySeriesId()
  return (
    !!primaryId &&
    id !== primaryId &&
    id !== sourceContextDatastream.value?.id &&
    graphSeriesArray.value.some((s) => s.id === id)
  )
}

/** Whether a series measures the primary series' observed property in the
 *  same unit, so its axis can take the primary axis's scale. */
export const sharesPrimaryVariable = (id: string): boolean => {
  if (!canLockAxis(id)) return false
  const { graphSeriesArray } = storeToRefs(usePlotlyStore())
  const variableOf = (sid?: string) =>
    graphSeriesArray.value.find((s) => s.id === sid)?.variable
  const variable = variableOf(id)
  return !!variable && variable === variableOf(primarySeriesId())
}

export const toggleAxisLock = (id: string) => {
  const { lockedAxisIds } = storeToRefs(usePlotlyStore())
  const ids = new Set(lockedAxisIds.value)
  if (ids.has(id)) ids.delete(id)
  else ids.add(id)
  lockedAxisIds.value = ids
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const gd = plotlyRef.value as unknown as PlotlyHTMLElement | null
  if (gd) settled = snapshot(gd)
}

/** `y2` → `yaxis2` */
const layoutKeyOf = (axisRef: string) => `yaxis${axisRef.slice(1)}`

/** Axis refs (`y2`, …) of the locked series on the plot. */
const lockedAxisRefs = (gd: PlotlyHTMLElement): string[] => {
  const { lockedAxisIds } = storeToRefs(usePlotlyStore())
  const refs: string[] = []
  for (const id of lockedAxisIds.value) {
    if (!canLockAxis(id)) continue
    const trace = gd.data.find((t) => (t as AppPlotlyTrace).id === id) as
      | AppPlotlyTrace
      | undefined
    const ref = trace?.yaxis as string | undefined
    if (ref && ref !== 'y') refs.push(ref)
  }
  return refs
}

const layoutRange = (gd: PlotlyHTMLElement, key: string): Range | null => {
  const range = (gd.layout as unknown as Record<string, { range?: unknown[] }>)[
    key
  ]?.range
  if (!range || range.length !== 2) return null
  const r: Range = [Number(range[0]), Number(range[1])]
  return r.every(Number.isFinite) ? r : null
}

/** The range a relayout event sets on `key`, if it sets one. */
const eventRange = (
  evt: Record<string, unknown>,
  key: string
): Range | null => {
  const whole = evt[`${key}.range`]
  const pair = Array.isArray(whole)
    ? whole
    : [evt[`${key}.range[0]`], evt[`${key}.range[1]`]]
  const r: Range = [Number(pair[0]), Number(pair[1])]
  return pair[0] != null && pair[1] != null && r.every(Number.isFinite)
    ? r
    : null
}

const sets = (evt: Record<string, unknown>, key: string) =>
  Object.keys(evt).some((k) => k.startsWith(`${key}.`))

/**
 * Where a locked axis goes when the primary axis moves from `from` to `to`.
 * It keeps its own scale and moves by the same share of its range, as if
 * the two were dragged together.
 */
const follow = (own: Range, from: Range, to: Range): Range => {
  const scale = (own[1] - own[0]) / (from[1] - from[0])
  return [
    own[0] + (to[0] - from[0]) * scale,
    own[0] + (to[1] - from[0]) * scale,
  ]
}

type Ranges = { primary: Range; own: Record<string, Range> }

const snapshot = (gd: PlotlyHTMLElement): Ranges | null => {
  const primary = layoutRange(gd, 'yaxis')
  if (!primary || primary[0] === primary[1]) return null
  const own: Record<string, Range> = {}
  for (const ref of lockedAxisRefs(gd)) {
    const key = layoutKeyOf(ref)
    const range = layoutRange(gd, key)
    if (range) own[key] = range
  }
  return { primary, own }
}

/** Ranges before the latest change, and before the current drag. */
let settled: Ranges | null = null
let dragStart: Ranges | null = null
let dragged = false
/** Undoes what `linkForDrag` changed in Plotly's state. */
let unlink: (() => void) | null = null

type FullLayout = Record<string, { range: Range }> & {
  _axisConstraintGroups?: Record<string, number>[]
}
const fullLayoutOf = (gd: PlotlyHTMLElement) =>
  (gd as unknown as { _fullLayout?: FullLayout })._fullLayout

/** Put each locked axis where the primary axis's move from the drag's
 *  start to `next` takes it. */
const moveLockedAxes = (gd: PlotlyHTMLElement, next: Range) => {
  const fullLayout = fullLayoutOf(gd)
  if (!dragStart || !fullLayout || !next.every(Number.isFinite)) return
  dragged = true
  for (const [key, own] of Object.entries(dragStart.own)) {
    const axis = fullLayout[key]
    if (axis) axis.range = follow(own, dragStart.primary, next)
  }
}

/**
 * PRIVATE-API: ready Plotly's drag state for a drag of the primary axis.
 *
 * Plotly's drag only redraws axes it moves itself or that share a
 * constraint group with them, so the locked axes join the primary axis in
 * a group, at the ratio they already have. Plotly would hold later changes
 * to that ratio too, so the group lasts only for this drag.
 *
 * Each step, the drag sets the primary axis's range and then draws. Its
 * `plotly_relayouting` event comes after the draw, a frame late, so the
 * locked axes move in a setter on that range instead, before the draw.
 */
const linkForDrag = (gd: PlotlyHTMLElement) => {
  dragStart = snapshot(gd)
  dragged = false
  const fullLayout = fullLayoutOf(gd)
  const groups = fullLayout?._axisConstraintGroups
  const primaryAxis = fullLayout?.yaxis
  const keys = Object.keys(dragStart?.own ?? {})
  if (!dragStart || !groups || !primaryAxis || !keys.length) return

  const span = dragStart.primary[1] - dragStart.primary[0]
  const group: Record<string, number> = { y: 1 }
  for (const key of keys) {
    const own = dragStart.own[key]!
    group[`y${key.slice('yaxis'.length)}`] = span / (own[1] - own[0])
  }
  groups.push(group)

  let range = primaryAxis.range
  Object.defineProperty(primaryAxis, 'range', {
    configurable: true,
    enumerable: true,
    get: () => range,
    set: (value: Range) => {
      range = value
      moveLockedAxes(gd, [Number(value[0]), Number(value[1])])
    },
  })

  unlink = () => {
    const index = groups.indexOf(group)
    if (index >= 0) groups.splice(index, 1)
    delete (primaryAxis as { range?: Range }).range
    primaryAxis.range = range
  }
}

const endDrag = () => {
  unlink?.()
  unlink = null
}

/** Steps that change the primary range in place (zooming from an end of
 *  the axis) skip the setter, so they follow here, a frame late. */
const followDuringDrag = (
  gd: PlotlyHTMLElement,
  evt: Record<string, unknown>
) => {
  const next = eventRange(evt, 'yaxis')
  if (next) moveLockedAxes(gd, next)
}

/** After any change to the primary axis, settle the locked axes. */
const followAfterRelayout = (
  gd: PlotlyHTMLElement,
  evt: Record<string, unknown> | null
) => {
  const fromDrag = dragged ? dragStart : null
  const before = fromDrag ?? settled
  dragStart = null
  dragged = false
  const next = evt && eventRange(evt, 'yaxis')
  const update: Record<string, unknown> = {}
  if (evt && before && next) {
    for (const [key, own] of Object.entries(before.own)) {
      // An axis the same change sets itself (a pan of the plot area, zoom
      // undo) keeps that range. After a drag, every locked axis is set
      // from where it began, which the drag's own range update may not be.
      if (!fromDrag && sets(evt, key)) continue
      update[`${key}.range`] = follow(own, before.primary, next)
      update[`${key}.autorange`] = false
    }
  }
  if (Object.keys(update).length) {
    void Plotly.relayout(gd, update as Partial<Layout>)
  }
  settled = snapshot(gd)
}

/**
 * Double-clicking an axis that measures the same variable as the primary
 * axis gives it the primary axis's range. Plotly's drag cover takes the
 * mouseup, so the browser never fires `dblclick`; the second `click`
 * (detail 2) still lands on the axis strip.
 */
const matchOnDoubleClick = (event: MouseEvent) => {
  if (event.detail !== 2) return
  const strip = event.target as Element | null
  if (!strip?.matches('rect.nsdrag, rect.ndrag, rect.sdrag')) return
  const subplot = strip.parentElement?.getAttribute('class')
  const axisRef = subplot?.match(/^x\d*(y\d*)$/)?.[1]
  if (!axisRef || axisRef === 'y') return

  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const gd = plotlyRef.value as unknown as PlotlyHTMLElement | null
  if (!gd) return
  const id = gd.data
    .map((t) => t as AppPlotlyTrace)
    .find((t) => t.id && t.yaxis === axisRef)?.id
  const range = layoutRange(gd, 'yaxis')
  if (!id || !range || !sharesPrimaryVariable(id)) return
  const key = layoutKeyOf(axisRef)
  void Plotly.relayout(gd, {
    [`${key}.range`]: range,
    [`${key}.autorange`]: false,
  } as Partial<Layout>)
}

/** Only drags of the primary subplot move locked axes. */
const onMouseDown = (event: MouseEvent) => {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const gd = plotlyRef.value as unknown as PlotlyHTMLElement | null
  if (!gd) return
  const onPrimary = !!(event.target as Element | null)?.closest(
    'g.draglayer > g.xy'
  )
  endDrag()
  if (onPrimary) linkForDrag(gd)
  else dragStart = null
}

/** Wire axis locking and matching to a freshly drawn plot. */
export const installAxisLock = (gd: PlotlyHTMLElement) => {
  unlink = null
  settled = snapshot(gd)
  dragStart = null
  dragged = false
  gd.on('plotly_relayouting', (evt) =>
    followDuringDrag(gd, evt as Record<string, unknown>)
  )
  gd.on('plotly_relayout', (evt) =>
    followAfterRelayout(gd, evt as Record<string, unknown>)
  )
  const el = gd as unknown as HTMLElement
  // Capture runs before Plotly's own mousedown, which reads the groups.
  el.removeEventListener('mousedown', onMouseDown, true)
  el.addEventListener('mousedown', onMouseDown, true)
  // Plotly's drag cover, not the plot, takes the mouseup.
  document.removeEventListener('mouseup', endDrag, true)
  document.addEventListener('mouseup', endDrag, true)
  el.removeEventListener('click', matchOnDoubleClick)
  el.addEventListener('click', matchOnDoubleClick)
}
