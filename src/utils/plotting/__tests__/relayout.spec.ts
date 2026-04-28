import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// --- Mocks --------------------------------------------------------------

const plotlyMock = vi.hoisted(() => ({
  relayout: vi.fn().mockResolvedValue(undefined),
  restyle: vi.fn().mockResolvedValue(undefined),
}))
vi.mock('plotly.js-dist', () => ({ default: plotlyMock }))

vi.mock('@uwrl/qc-utils', () => ({
  findFirstGreaterOrEqual: (arr: number[], target: number) => {
    let lo = 0
    let hi = arr.length
    while (lo < hi) {
      const mid = (lo + hi) >>> 1
      if (arr[mid] < target) lo = mid + 1
      else hi = mid
    }
    return lo
  },
  EnumFilterOperations: { SELECTION: 'SELECTION' },
}))

const qcDatastream = ref<any>(null)
const selectedData = ref<any>(null)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    qcDatastream,
    selectedData,
  }),
}))

const plotlyRef = ref<any>(null)
const isUpdating = ref(false)
const areTooltipsEnabled = ref(true)
const visiblePoints = ref(0)
const tooltipsMaxDataPoints = ref(10000)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    plotlyRef,
    isUpdating,
    areTooltipsEnabled,
    visiblePoints,
    tooltipsMaxDataPoints,
    selectedSeries: ref(null),
    editHistory: ref([]),
    suppressedEchoSelection: ref<number[] | null>(null),
  }),
}))

// --- Tests --------------------------------------------------------------

import {
  intendedSpacingMs,
  computeIntendedTickvals,
  tickvalsEqual,
  handleRelayout,
  invalidateVisibleRangeCache,
} from '../relayout'

// flushMicro + a macrotask tick so the `setTimeout(..., 0)` body inside
// handleRelayout finishes before assertions run.
const flush = () =>
  new Promise<void>((resolve) => setTimeout(resolve, 0))

const resetStoreState = () => {
  plotlyRef.value = null
  isUpdating.value = false
  areTooltipsEnabled.value = true
  visiblePoints.value = 0
  tooltipsMaxDataPoints.value = 10000
  qcDatastream.value = null
  selectedData.value = null
  plotlyMock.relayout.mockClear()
  plotlyMock.restyle.mockClear()
  invalidateVisibleRangeCache()
}

describe('intendedSpacingMs', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetStoreState()
  })

  it('returns null when no qcDatastream', () => {
    qcDatastream.value = null
    expect(intendedSpacingMs()).toBeNull()
  })

  it('returns null when intendedTimeSpacing is missing', () => {
    qcDatastream.value = { intendedTimeSpacingUnit: 'minutes' }
    expect(intendedSpacingMs()).toBeNull()
  })

  it('returns null when intendedTimeSpacing is zero or negative', () => {
    qcDatastream.value = { intendedTimeSpacing: 0, intendedTimeSpacingUnit: 'minutes' }
    expect(intendedSpacingMs()).toBeNull()
    qcDatastream.value = { intendedTimeSpacing: -1, intendedTimeSpacingUnit: 'minutes' }
    expect(intendedSpacingMs()).toBeNull()
  })

  it('returns null when intendedTimeSpacing is NaN', () => {
    qcDatastream.value = { intendedTimeSpacing: 'bogus', intendedTimeSpacingUnit: 'minutes' }
    expect(intendedSpacingMs()).toBeNull()
  })

  it('returns correct ms for seconds', () => {
    qcDatastream.value = { intendedTimeSpacing: 15, intendedTimeSpacingUnit: 'seconds' }
    expect(intendedSpacingMs()).toBe(15 * 1000)
  })

  it('returns correct ms for minutes', () => {
    qcDatastream.value = { intendedTimeSpacing: 5, intendedTimeSpacingUnit: 'minutes' }
    expect(intendedSpacingMs()).toBe(5 * 60 * 1000)
  })

  it('returns correct ms for hours', () => {
    qcDatastream.value = { intendedTimeSpacing: 2, intendedTimeSpacingUnit: 'hours' }
    expect(intendedSpacingMs()).toBe(2 * 60 * 60 * 1000)
  })

  it('returns correct ms for days', () => {
    qcDatastream.value = { intendedTimeSpacing: 1, intendedTimeSpacingUnit: 'days' }
    expect(intendedSpacingMs()).toBe(24 * 60 * 60 * 1000)
  })

  it('returns null for unknown unit', () => {
    qcDatastream.value = { intendedTimeSpacing: 1, intendedTimeSpacingUnit: 'weeks' }
    expect(intendedSpacingMs()).toBeNull()
  })

  it('returns null when unit is null', () => {
    qcDatastream.value = { intendedTimeSpacing: 1, intendedTimeSpacingUnit: null }
    expect(intendedSpacingMs()).toBeNull()
  })
})

describe('computeIntendedTickvals', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetStoreState()
  })

  it('returns null when no qcDatastream', () => {
    qcDatastream.value = null
    expect(computeIntendedTickvals(0, 1000)).toBeNull()
  })

  it('returns null when xStart or xEnd is NaN', () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'minutes',
    }
    expect(computeIntendedTickvals(NaN, 1000)).toBeNull()
    expect(computeIntendedTickvals(0, NaN)).toBeNull()
  })

  it('returns null when span is zero or negative', () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'minutes',
    }
    expect(computeIntendedTickvals(1000, 1000)).toBeNull()
    expect(computeIntendedTickvals(2000, 1000)).toBeNull()
  })

  it('returns null when span is too wide for any multiplier', () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'seconds',
      phenomenonBeginTime: new Date(0).toISOString(),
    }
    const span = 10 * 24 * 60 * 60 * 1000
    expect(computeIntendedTickvals(0, span)).toBeNull()
  })

  it('returns aligned ticks anchored to phenomenonBeginTime', () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'minutes',
      phenomenonBeginTime: new Date(0).toISOString(),
    }
    const ticks = computeIntendedTickvals(0, 10 * 60 * 1000)
    expect(ticks).not.toBeNull()
    expect(ticks!.length).toBeGreaterThan(0)
    expect(ticks!.length).toBeLessThanOrEqual(15)
    // All ticks should be multiples of the chosen step from the anchor.
    for (const t of ticks!) {
      expect(t % (60 * 1000)).toBe(0)
    }
  })

  it('falls back to xStart as anchor when phenomenonBeginTime is missing', () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'minutes',
    }
    const ticks = computeIntendedTickvals(0, 10 * 60 * 1000)
    expect(ticks).not.toBeNull()
    expect(ticks!.length).toBeGreaterThan(0)
  })

  it('respects MAX_TICKS cap (<=15 ticks)', () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'minutes',
      phenomenonBeginTime: new Date(0).toISOString(),
    }
    const ticks = computeIntendedTickvals(0, 60 * 60 * 1000)
    expect(ticks).not.toBeNull()
    expect(ticks!.length).toBeLessThanOrEqual(15)
  })
})

describe('tickvalsEqual', () => {
  it('returns true for the same reference', () => {
    const a = [1, 2, 3]
    expect(tickvalsEqual(a, a)).toBe(true)
  })

  it('returns true when both are null', () => {
    expect(tickvalsEqual(null, null)).toBe(true)
  })

  it('returns false when only one is null', () => {
    expect(tickvalsEqual([1, 2], null)).toBe(false)
    expect(tickvalsEqual(null, [1, 2])).toBe(false)
  })

  it('returns false for different lengths', () => {
    expect(tickvalsEqual([1, 2], [1, 2, 3])).toBe(false)
  })

  it('returns false when any element differs by >1', () => {
    expect(tickvalsEqual([1, 2, 3], [1, 2, 5])).toBe(false)
  })

  it('returns true when all elements differ by <=1 (tolerance)', () => {
    expect(tickvalsEqual([1, 2, 3], [1, 2.5, 3])).toBe(true)
    expect(tickvalsEqual([100, 200], [100.9, 199.5])).toBe(true)
  })

  it('returns true for two empty arrays', () => {
    expect(tickvalsEqual([], [])).toBe(true)
  })
})

// --- handleRelayout branch coverage -------------------------------------

// Build a minimal stub graph-div that satisfies handleRelayout's reads.
const makeStub = (overrides?: {
  xRange?: Array<number | string>
  tickmode?: string
  tickvals?: number[] | null
  traces?: Array<Partial<{ id: string; x: number[]; marker: { opacity: number }; hoverinfo: string }>>
}) => ({
  layout: {
    xaxis: {
      range: overrides?.xRange ?? [0, 1000],
      tickmode: overrides?.tickmode,
      tickvals: overrides?.tickvals,
    },
  },
  data: overrides?.traces ?? [
    { x: [0, 100, 200, 500, 900], marker: { opacity: 1 }, hoverinfo: 'x+y' },
  ],
})

describe('handleRelayout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetStoreState()
  })

  it('early-returns when isUpdating is already true', async () => {
    isUpdating.value = true
    plotlyRef.value = makeStub()
    await handleRelayout({} as any)
    await flush()
    expect(plotlyMock.relayout).not.toHaveBeenCalled()
    expect(plotlyMock.restyle).not.toHaveBeenCalled()
    // isUpdating stays true: early return never flips it back.
    expect(isUpdating.value).toBe(true)
  })

  it('early-returns on dragmode event', async () => {
    plotlyRef.value = makeStub()
    await handleRelayout({ dragmode: 'zoom' } as any)
    await flush()
    expect(isUpdating.value).toBe(false)
    expect(plotlyMock.relayout).not.toHaveBeenCalled()
  })

  it('early-returns on selection-bearing event', async () => {
    plotlyRef.value = makeStub()
    await handleRelayout({ selections: [{}] } as any)
    await flush()
    expect(isUpdating.value).toBe(false)
  })

  it('early-returns on active-selection drag event', async () => {
    plotlyRef.value = makeStub()
    await handleRelayout({ 'selections[0].x0': 100 } as any)
    await flush()
    expect(isUpdating.value).toBe(false)
  })

  it('early-returns on empty event object', async () => {
    plotlyRef.value = makeStub()
    await handleRelayout({} as any)
    await flush()
    expect(isUpdating.value).toBe(false)
  })

  it('resets tick grid on xaxis.autorange=true', async () => {
    plotlyRef.value = makeStub()
    await handleRelayout({ 'xaxis.autorange': true } as any)
    await flush()
    // First relayout call: tickmode/tickvals reset.
    expect(plotlyMock.relayout).toHaveBeenCalled()
    const firstCallArg = plotlyMock.relayout.mock.calls[0][1]
    expect(firstCallArg['xaxis.tickmode']).toBe('auto')
    expect(firstCallArg['xaxis.tickvals']).toBeNull()
  })

  it('swallows errors thrown by Plotly.relayout on autorange reset', async () => {
    plotlyMock.relayout.mockRejectedValueOnce(new Error('boom'))
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    plotlyRef.value = makeStub()
    await handleRelayout({ 'xaxis.autorange': true } as any)
    await flush()
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })

  it('counts visible points across traces with numeric x data', async () => {
    plotlyRef.value = makeStub({
      xRange: [100, 500],
      traces: [
        { x: [0, 100, 200, 500, 900], marker: { opacity: 1 }, hoverinfo: 'x+y' },
        { x: [50, 150, 250, 450, 600], marker: { opacity: 1 }, hoverinfo: 'x+y' },
      ],
    })
    await handleRelayout({ foo: 'bar' } as any)
    await flush()
    // Trace 0: indices [1..3) => 2 points (100, 200). Trace 1: [1..4) => 3 points.
    expect(visiblePoints.value).toBe(5)
    expect(isUpdating.value).toBe(false)
  })

  it('hides markers when trace point count exceeds DENSITY_HIDE_MARKERS and data-points hover is off', async () => {
    areTooltipsEnabled.value = false
    const dense = Array.from({ length: 3000 }, (_, i) => i)
    plotlyRef.value = makeStub({
      xRange: [0, 3000],
      traces: [{ x: dense, marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    await handleRelayout({ some: 'evt' } as any)
    await flush()
    // Should have called restyle to set marker.opacity to 0 for the dense trace.
    const restyleCalls = plotlyMock.restyle.mock.calls
    const markerOpacityCall = restyleCalls.find(
      (c) => c[1] && (c[1] as any)['marker.opacity']
    )
    expect(markerOpacityCall).toBeDefined()
    expect((markerOpacityCall![1] as any)['marker.opacity']).toEqual([0])
  })

  it('keeps every trace\'s markers when data-points hover will run, even past the density threshold', async () => {
    qcDatastream.value = { id: 'qc-target' }
    const dense = Array.from({ length: 3000 }, (_, i) => i)
    tooltipsMaxDataPoints.value = 10_000
    plotlyRef.value = makeStub({
      xRange: [0, 3000],
      traces: [
        { id: 'qc-target', x: dense, marker: { opacity: 0 }, hoverinfo: 'skip' },
        { id: 'other', x: dense, marker: { opacity: 0 }, hoverinfo: 'skip' },
      ],
    })
    await handleRelayout({ evt: 'q' } as any)
    await flush()
    const restyleCalls = plotlyMock.restyle.mock.calls
    const markerOpacityCall = restyleCalls.find(
      (c) => c[1] && (c[1] as any)['marker.opacity']
    )
    expect(markerOpacityCall).toBeDefined()
    expect((markerOpacityCall![1] as any)['marker.opacity']).toEqual([1, 1])
  })

  it('still hides QC trace markers when data-points hover is disabled', async () => {
    qcDatastream.value = { id: 'qc-target' }
    areTooltipsEnabled.value = false
    const dense = Array.from({ length: 3000 }, (_, i) => i)
    plotlyRef.value = makeStub({
      xRange: [0, 3000],
      traces: [{ id: 'qc-target', x: dense, marker: { opacity: 1 }, hoverinfo: 'skip' }],
    })
    await handleRelayout({ evt: 'q' } as any)
    await flush()
    const restyleCalls = plotlyMock.restyle.mock.calls
    const markerOpacityCall = restyleCalls.find(
      (c) => c[1] && (c[1] as any)['marker.opacity']
    )
    expect(markerOpacityCall).toBeDefined()
    expect((markerOpacityCall![1] as any)['marker.opacity']).toEqual([0])
  })

  it('skips marker restyle when opacities unchanged', async () => {
    plotlyRef.value = makeStub({
      xRange: [0, 1000],
      traces: [{ x: [100, 200], marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    await handleRelayout({ evt: 1 } as any)
    await flush()
    const restyleCalls = plotlyMock.restyle.mock.calls
    const markerOpacityCall = restyleCalls.find(
      (c) => c[1] && (c[1] as any)['marker.opacity']
    )
    expect(markerOpacityCall).toBeUndefined()
  })

  it('switches hover to skip when areTooltipsEnabled resolves false (e.g. auto over threshold)', async () => {
    // The store's `areTooltipsEnabled` is a computed that already
    // factors in mode + threshold; relayout just trusts it. Simulate
    // the auto-over-threshold case by setting the mock directly.
    areTooltipsEnabled.value = false
    tooltipsMaxDataPoints.value = 2
    plotlyRef.value = makeStub({
      xRange: [0, 1000],
      traces: [
        { x: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], marker: { opacity: 0 }, hoverinfo: 'x+y' },
      ],
    })
    await handleRelayout({ evt: 'z' } as any)
    await flush()
    const hoverCall = plotlyMock.restyle.mock.calls.find(
      (c) => c[1] && (c[1] as any).hoverinfo === 'skip'
    )
    expect(hoverCall).toBeDefined()
  })

  it('switches hover to skip when data-points hover is disabled', async () => {
    areTooltipsEnabled.value = false
    plotlyRef.value = makeStub({
      xRange: [0, 1000],
      traces: [{ x: [1, 2], marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    await handleRelayout({ evt: 'z' } as any)
    await flush()
    const hoverCall = plotlyMock.restyle.mock.calls.find(
      (c) => c[1] && (c[1] as any).hoverinfo === 'skip'
    )
    expect(hoverCall).toBeDefined()
  })

  it('re-enables hover when under cap and tooltips on, and current is skip', async () => {
    plotlyRef.value = makeStub({
      xRange: [0, 1000],
      traces: [{ x: [1, 2], marker: { opacity: 1 }, hoverinfo: 'skip' }],
    })
    await handleRelayout({ evt: 'z' } as any)
    await flush()
    const hoverCall = plotlyMock.restyle.mock.calls.find(
      (c) => c[1] && (c[1] as any).hoverinfo === 'x+y'
    )
    expect(hoverCall).toBeDefined()
  })

  it('parses string xRange values via Date.parse', async () => {
    plotlyRef.value = makeStub({
      xRange: ['1970-01-01T00:00:00Z', '1970-01-01T00:00:01Z'],
      traces: [{ x: [0, 500, 1500], marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    await handleRelayout({ evt: 'drag' } as any)
    await flush()
    // Range parsed to [0, 1000]. Binary search: findFirstGreaterOrEqual
    // returns the first index >= target, so start=0, end=2 => 2 points
    // counted (indices 0 and 1: values 0 and 500).
    expect(visiblePoints.value).toBe(2)
  })

  it('applies intended tickvals when they differ from current', async () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'minutes',
      phenomenonBeginTime: new Date(0).toISOString(),
    }
    plotlyRef.value = makeStub({
      xRange: [0, 10 * 60 * 1000],
      tickmode: 'auto',
      tickvals: null,
      traces: [{ x: [0, 60000, 120000], marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    await handleRelayout({ evt: 'drag' } as any)
    await flush()
    const tickCall = plotlyMock.relayout.mock.calls.find(
      (c) => c[1] && (c[1] as any)['xaxis.tickmode'] === 'array'
    )
    expect(tickCall).toBeDefined()
  })

  it('skips tickvals relayout when already equal', async () => {
    qcDatastream.value = {
      intendedTimeSpacing: 1,
      intendedTimeSpacingUnit: 'minutes',
      phenomenonBeginTime: new Date(0).toISOString(),
    }
    // Pre-seed with what computeIntendedTickvals actually produces for
    // this 10-minute window: with TARGET_TICKS=8 and step of 120s
    // aligned to anchor=0, the ticks are [0, 120k, 240k, 360k, 480k, 600k].
    const existing = [0, 120000, 240000, 360000, 480000, 600000]
    plotlyRef.value = makeStub({
      xRange: [0, 10 * 60 * 1000],
      tickmode: 'array',
      tickvals: existing,
      traces: [{ x: [0, 60000, 120000], marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    await handleRelayout({ evt: 'drag' } as any)
    await flush()
    const tickmodeCall = plotlyMock.relayout.mock.calls.find(
      (c) => c[1] && (c[1] as any)['xaxis.tickmode'] !== undefined
    )
    // No mismatch => no tickvals relayout call.
    expect(tickmodeCall).toBeUndefined()
  })

  it('skips rescan when visible x-range has not moved (cache hit)', async () => {
    plotlyRef.value = makeStub({
      xRange: [0, 1000],
      traces: [{ x: [100, 200, 300], marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    // First pass seeds the cache.
    await handleRelayout({ evt: 'first' } as any)
    await flush()
    const initialVisible = visiblePoints.value
    visiblePoints.value = 999 // sentinel to detect skip
    // Second pass with same range should short-circuit (visiblePoints stays at sentinel).
    await handleRelayout({ evt: 'second' } as any)
    await flush()
    expect(visiblePoints.value).toBe(999)
    // But a null event forces a recompute.
    await handleRelayout(null)
    await flush()
    expect(visiblePoints.value).toBe(initialVisible)
  })

  it('invalidateVisibleRangeCache clears the memoised range', async () => {
    plotlyRef.value = makeStub({
      xRange: [0, 1000],
      traces: [{ x: [100, 200], marker: { opacity: 1 }, hoverinfo: 'x+y' }],
    })
    await handleRelayout({ evt: 'seed' } as any)
    await flush()
    invalidateVisibleRangeCache()
    visiblePoints.value = 0
    await handleRelayout({ evt: 'again' } as any)
    await flush()
    expect(visiblePoints.value).toBe(2)
  })
})
