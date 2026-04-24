import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// --- Mocks --------------------------------------------------------------

vi.mock('plotly.js-dist', () => ({
  default: {
    relayout: vi.fn().mockResolvedValue(undefined),
    restyle: vi.fn().mockResolvedValue(undefined),
  },
}))

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

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    qcDatastream,
    selectedData: ref(null),
  }),
}))

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    plotlyRef: ref(null),
    isUpdating: ref(false),
    areTooltipsEnabled: ref(true),
    visiblePoints: ref(0),
    tooltipsMaxDataPoints: ref(10000),
    selectedSeries: ref(null),
    editHistory: ref([]),
  }),
}))

// --- Tests --------------------------------------------------------------

import {
  intendedSpacingMs,
  computeIntendedTickvals,
  tickvalsEqual,
} from '../relayout'

describe('intendedSpacingMs', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    qcDatastream.value = null
  })

  it('returns null when no qcDatastream', () => {
    qcDatastream.value = null
    expect(intendedSpacingMs()).toBeNull()
  })

  it('returns null when intendedTimeSpacing is missing', () => {
    qcDatastream.value = { intendedTimeSpacingUnit: 'minutes' }
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
})

describe('computeIntendedTickvals', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    qcDatastream.value = null
  })

  it('returns null when no qcDatastream', () => {
    qcDatastream.value = null
    expect(computeIntendedTickvals(0, 1000)).toBeNull()
  })

  it('returns null when span is too wide for any multiplier', () => {
    // 1-second spacing over a 10-day span: even 120x multiplier => 2-min ticks
    // over 10 days = 7200 ticks, way over MAX_TICKS.
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
    // 10-minute window: should give a reasonable tick count
    const ticks = computeIntendedTickvals(0, 10 * 60 * 1000)
    expect(ticks).not.toBeNull()
    expect(ticks!.length).toBeGreaterThan(0)
    expect(ticks!.length).toBeLessThanOrEqual(15)
  })

  it('respects MAX_TICKS cap (≤15 ticks)', () => {
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

  it('returns true when all elements differ by ≤1 (tolerance)', () => {
    expect(tickvalsEqual([1, 2, 3], [1, 2.5, 3])).toBe(true)
    expect(tickvalsEqual([100, 200], [100.9, 199.5])).toBe(true)
  })
})
