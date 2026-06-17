/**
 * Encode / decode the QC app's share URL.
 *
 * The URL keeps every plot-relevant piece of state the sender sees so
 * a recipient lands on an identical view: plotted datastreams, QC
 * target, time range, current view (Select / Edit), Plot/Table tab,
 * per-trace visibility, per-Y-axis visibility, X/Y zoom, and the data-
 * points (markers) mode and threshold. Sidebar filters are kept only
 * on the Select view, since they drive the datastreams table — not
 * the plot.
 *
 * Compaction tactics used (none of them lossy):
 *   - Short query keys (`ds`, `b`, `e`, `r`, …) instead of verbose
 *     ones.
 *   - QC target is implicit (first id in `ds`); no separate `qc` key.
 *   - When a date preset is active (`r=0..5`), the begin/end pair is
 *     elided — recipients recompute it from "now" on load, matching
 *     the preset semantics the sender chose.
 *   - Timestamps go through `tsToBase36Seconds` (≈ 7 chars instead
 *     of 24).
 *   - Visibility state is a hex bitmask over the `ds` order rather
 *     than a list of ids.
 *   - Zoom Y axes are indexed by position in `ds`; axes at their
 *     default fit are omitted entirely.
 *   - Optional bits (tab, data-points mode/threshold, zoom) are
 *     emitted only when they differ from the default.
 */

export interface ShareableZoom {
  /** X range as [minMs, maxMs], or `null` when the X axis is at its
   *  default extent. */
  xRange: [number, number] | null
  /** Per-Y-axis ranges, keyed by the Plotly axis name (`y`, `y2`, …).
   *  Axes at default fit can be omitted from this map. */
  yRanges: Record<string, [number, number]>
}

export interface ShareState {
  /** Workspace UUID (drives the router workspace guard). */
  workspaceId?: string | null
  /** Edit view active when true. Select view is the default. */
  editView?: boolean
  /** Table tab active when true. Plot tab is the default. */
  tableTab?: boolean
  /** Ordered list of plotted datastream ids. The first id is the QC
   *  target. */
  datastreamIds?: string[]
  /** Date range preset id (`0..5`). When set, `begin`/`end` are
   *  omitted from the URL and the receiver recomputes the window
   *  from "now". */
  datePresetId?: number | null
  /** Custom-window begin (epoch ms). Only emitted when no preset is
   *  active. */
  beginMs?: number | null
  /** Custom-window end (epoch ms). Only emitted when no preset is
   *  active. */
  endMs?: number | null
  /** Sidebar filters — only emitted when the recipient lands on the
   *  Select view (they don't affect the plot). */
  thingIds?: string[]
  observedPropertyNames?: string[]
  processingLevelNames?: string[]
  /** Eye-toggle state: `true` means visible, `false` means hidden.
   *  Indexed by position in `datastreamIds`. */
  traceVisibility?: boolean[]
  /** Y-axis-toggle state for non-QC datastreams (`true` means the
   *  axis is shown). Indexed by position in `datastreamIds` starting
   *  at 1 (the QC stream's primary axis can't be hidden). */
  axisVisibility?: boolean[]
  /** Plot zoom — both x and per-axis y. */
  zoom?: ShareableZoom
  /** Data-points marker mode. Default is `auto`. */
  dataPointsMode?: 'auto' | 'manualOn' | 'manualOff'
  /** Auto-mode threshold (visible-points cutoff). Omitted when at the
   *  app default (10 000). */
  dataPointsThreshold?: number | null
}

const DEFAULT_DATA_POINTS_THRESHOLD = 10_000

/** Convert an epoch-ms timestamp to a base36 second string. */
export function tsToBase36Seconds(ms: number): string {
  return Math.floor(ms / 1000).toString(36)
}

/** Inverse of `tsToBase36Seconds`. Returns `null` for unparseable input. */
export function base36SecondsToMs(s: string): number | null {
  if (!s) return null
  const n = parseInt(s, 36)
  if (!Number.isFinite(n)) return null
  return n * 1000
}

/** Encode a boolean list as a hex bitmask. Bit 0 = first element. */
export function bitmaskFromBoolList(bits: boolean[]): string {
  let n = 0n
  for (let i = 0; i < bits.length; i++) {
    if (bits[i]) n |= 1n << BigInt(i)
  }
  return n.toString(16)
}

/** Decode a hex bitmask back into a boolean list of `len` items. */
export function boolListFromBitmask(hex: string, len: number): boolean[] {
  const n = BigInt('0x' + (hex || '0'))
  const out: boolean[] = new Array(len)
  for (let i = 0; i < len; i++) {
    out[i] = (n & (1n << BigInt(i))) !== 0n
  }
  return out
}

/** Render a float with at most 5 significant digits, trimming trailing zeros. */
export function compactFloat(n: number): string {
  if (!Number.isFinite(n)) return '0'
  return Number(n.toPrecision(5)).toString()
}

/**
 * Encode `state` into a flat query record. Keys absent from the
 * record represent app defaults; the URL stays as short as possible.
 */
export function encodeShareState(state: ShareState): Record<string, string> {
  const q: Record<string, string> = {}

  if (state.workspaceId) q.ws = state.workspaceId
  if (state.editView) q.m = 'e'
  if (state.tableTab) q.tab = 't'

  if (state.datastreamIds?.length) {
    q.ds = state.datastreamIds.join(',')
  }

  // Preset wins over begin/end. If a preset is active, dropping the
  // explicit dates lets the recipient pick up the same preset window
  // anchored to *their* "now" — which is the sender's intent when
  // they clicked the preset.
  if (
    state.datePresetId != null &&
    Number.isFinite(state.datePresetId) &&
    state.datePresetId >= 0
  ) {
    q.r = String(state.datePresetId)
  } else {
    if (Number.isFinite(state.beginMs as number)) {
      q.from = tsToBase36Seconds(state.beginMs as number)
    }
    if (Number.isFinite(state.endMs as number)) {
      q.to = tsToBase36Seconds(state.endMs as number)
    }
  }

  // Filters: serialize only when there's content. They're a Select-
  // view concern; callers that want the Edit-view rule pass empty
  // arrays.
  if (state.thingIds?.length) q.t = state.thingIds.join(',')
  if (state.observedPropertyNames?.length) {
    q.op = state.observedPropertyNames.join(',')
  }
  if (state.processingLevelNames?.length) {
    q.pl = state.processingLevelNames.join(',')
  }

  // Visibility — only serialise when at least one trace is hidden
  // (false). Empty/all-visible → omit.
  if (state.traceVisibility?.some((v) => v === false)) {
    const hidden = state.traceVisibility.map((v) => v === false)
    const mask = bitmaskFromBoolList(hidden)
    if (mask !== '0') q.h = mask
  }
  if (state.axisVisibility?.some((v) => v === false)) {
    const hidden = state.axisVisibility.map((v) => v === false)
    const mask = bitmaskFromBoolList(hidden)
    if (mask !== '0') q.ya = mask
  }

  if (state.zoom) {
    if (state.zoom.xRange) {
      const [lo, hi] = state.zoom.xRange
      q.z = `${tsToBase36Seconds(lo)}.${tsToBase36Seconds(hi)}`
    }
    const yEntries: string[] = []
    const ids = state.datastreamIds ?? []
    for (const [axisName, range] of Object.entries(state.zoom.yRanges)) {
      const idx = axisIndexFromName(axisName, ids.length)
      if (idx < 0 || idx >= ids.length) continue
      yEntries.push(`${idx}:${compactFloat(range[0])}~${compactFloat(range[1])}`)
    }
    if (yEntries.length) q.yz = yEntries.join(';')
  }

  if (state.dataPointsMode && state.dataPointsMode !== 'auto') {
    q.dp = state.dataPointsMode === 'manualOn' ? 'm' : '0'
  }
  if (
    state.dataPointsThreshold != null &&
    Number.isFinite(state.dataPointsThreshold) &&
    state.dataPointsThreshold !== DEFAULT_DATA_POINTS_THRESHOLD
  ) {
    q.th = String(state.dataPointsThreshold)
  }

  return q
}

/** Inverse of `encodeShareState`. Tolerant of missing / malformed values. */
export function decodeShareState(query: Record<string, unknown>): ShareState {
  const out: ShareState = {}
  const str = (k: string) =>
    typeof query[k] === 'string' ? (query[k] as string) : ''

  const ws = str('ws')
  if (ws) out.workspaceId = ws

  if (str('m') === 'e') out.editView = true
  if (str('tab') === 't') out.tableTab = true

  const ds = splitCsv(str('ds'))
  if (ds.length) out.datastreamIds = ds

  const rRaw = str('r')
  if (rRaw) {
    const n = Number(rRaw)
    if (Number.isFinite(n) && n >= 0) out.datePresetId = n
  } else {
    const fromMs = base36SecondsToMs(str('from'))
    if (fromMs != null) out.beginMs = fromMs
    const toMs = base36SecondsToMs(str('to'))
    if (toMs != null) out.endMs = toMs
    if (fromMs != null || toMs != null) out.datePresetId = -1
  }

  const t = splitCsv(str('t'))
  if (t.length) out.thingIds = t
  const op = splitCsv(str('op'))
  if (op.length) out.observedPropertyNames = op
  const pl = splitCsv(str('pl'))
  if (pl.length) out.processingLevelNames = pl

  const h = str('h')
  if (h && ds.length) {
    const hidden = boolListFromBitmask(h, ds.length)
    out.traceVisibility = hidden.map((bit) => !bit)
  }
  const ya = str('ya')
  if (ya && ds.length) {
    const hidden = boolListFromBitmask(ya, ds.length)
    out.axisVisibility = hidden.map((bit) => !bit)
  }

  const zoom: ShareableZoom = { xRange: null, yRanges: {} }
  const z = str('z')
  if (z) {
    const [lo, hi] = z.split('.')
    const loMs = base36SecondsToMs(lo ?? '')
    const hiMs = base36SecondsToMs(hi ?? '')
    if (loMs != null && hiMs != null) zoom.xRange = [loMs, hiMs]
  }
  const yz = str('yz')
  if (yz) {
    for (const piece of yz.split(';')) {
      const [idxRaw, rangeRaw] = piece.split(':')
      if (idxRaw == null || rangeRaw == null) continue
      const idx = Number(idxRaw)
      if (!Number.isFinite(idx)) continue
      const [loRaw, hiRaw] = rangeRaw.split('~')
      const lo = Number(loRaw)
      const hi = Number(hiRaw)
      if (!Number.isFinite(lo) || !Number.isFinite(hi)) continue
      zoom.yRanges[axisNameFromIndex(idx)] = [lo, hi]
    }
  }
  if (zoom.xRange || Object.keys(zoom.yRanges).length) out.zoom = zoom

  const dp = str('dp')
  if (dp === 'm') out.dataPointsMode = 'manualOn'
  else if (dp === '0') out.dataPointsMode = 'manualOff'
  // No `dp` key → `auto` (default), leave undefined.

  const th = str('th')
  if (th) {
    const n = Number(th)
    if (Number.isFinite(n) && n > 0) out.dataPointsThreshold = n
  }

  return out
}

/** Position-in-`ds` → Plotly axis name (`0` → `y`, `1` → `y2`, …). */
export function axisNameFromIndex(idx: number): string {
  return idx === 0 ? 'y' : `y${idx + 1}`
}

/** Plotly axis name → position-in-`ds`. `-1` for unrecognised inputs. */
export function axisIndexFromName(name: string, _datastreamCount: number): number {
  if (name === 'y') return 0
  const m = name.match(/^y(\d+)$/)
  if (!m) return -1
  const n = Number(m[1])
  if (!Number.isFinite(n)) return -1
  return n - 1
}

function splitCsv(v: string): string[] {
  return v ? v.split(',').filter(Boolean) : []
}
