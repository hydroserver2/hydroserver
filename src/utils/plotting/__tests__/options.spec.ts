import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// --- Mocks --------------------------------------------------------------

// Avoid real @uwrl/qc-utils (worker-heavy). Re-export just what options.ts touches.
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

const qcDatastream = ref<{ id: string; phenomenonBeginTime?: string } | null>(null)
const beginDate = ref<Date | null>(null)
const endDate = ref<Date | null>(null)
const selectedData = ref<number[] | null>(null)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    qcDatastream,
    beginDate,
    endDate,
    selectedData,
  }),
}))

const previewMode = ref(false)
const hiddenAxisIds = ref<Set<string>>(new Set())
const plotlyRef = ref<unknown>(null)
const editHistory = ref<unknown[]>([])

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    previewMode,
    hiddenAxisIds,
    plotlyRef,
    editHistory,
  }),
}))

const applications: Array<{ qualifierId: string; index: number; appliedAt: string; appliedBy: string }> = []
const qualifierById: Record<string, { code: string; description: string }> = {}

vi.mock('@/store/qualifiers', () => ({
  useQualifierStore: () => ({
    getApplicationsForDatastream: (_id: string) => applications,
    qualifierById,
  }),
}))

// operations.ts does not exist in wave 1. Stub it so options.ts can
// import fitXaxisToVisible/fitYaxisToVisible at test time.
vi.mock('@/utils/plotting/operations', () => ({
  fitXaxisToVisible: vi.fn(),
  fitYaxisToVisible: vi.fn(),
}))
vi.mock('../operations', () => ({
  fitXaxisToVisible: vi.fn(),
  fitYaxisToVisible: vi.fn(),
}))

// --- Tests --------------------------------------------------------------

import {
  COLORS,
  LABEL_COLORS,
  QUALIFIER_COLORS,
  labelColorFor,
  buildQualifierBand,
  createPlotlyOption,
  findGapIndices,
  insertGapBreaks,
} from '../options'

const makeSeries = (overrides: Partial<Record<string, unknown>> = {}) => {
  const x = new Float64Array([1, 2, 3, 4, 5])
  const y = new Float64Array([10, 20, 30, 40, 50])
  return {
    id: 'series-1',
    name: 'Series 1',
    color: COLORS[1],
    yAxisLabel: 'y',
    data: {
      dataX: x,
      dataY: y,
      history: [],
    },
    ...overrides,
  } as any
}

describe('labelColorFor', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('returns the paired LABEL_COLOR for a known color', () => {
    expect(labelColorFor(COLORS[1])).toBe(LABEL_COLORS[1])
    expect(labelColorFor(COLORS[3])).toBe(LABEL_COLORS[3])
  })

  it('falls back to LABEL_COLORS[0] for an unknown color', () => {
    expect(labelColorFor('#not-a-color')).toBe(LABEL_COLORS[0])
  })
})

describe('color constants', () => {
  it('COLORS has 9 entries and no duplicates', () => {
    expect(COLORS.length).toBe(9)
    expect(new Set(COLORS).size).toBe(COLORS.length)
  })

  it('LABEL_COLORS has 9 entries and no duplicates', () => {
    expect(LABEL_COLORS.length).toBe(9)
    expect(new Set(LABEL_COLORS).size).toBe(LABEL_COLORS.length)
  })

  it('QUALIFIER_COLORS has 8 entries and no duplicates', () => {
    expect(QUALIFIER_COLORS.length).toBe(8)
    expect(new Set(QUALIFIER_COLORS).size).toBe(QUALIFIER_COLORS.length)
  })
})

describe('buildQualifierBand', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    applications.length = 0
    for (const k of Object.keys(qualifierById)) delete qualifierById[k]
  })

  it('returns null when no qcDatastreamId', () => {
    const result = buildQualifierBand([makeSeries()], undefined, 0, '')
    expect(result).toBeNull()
  })

  it('returns null when the QC series is missing from seriesArray', () => {
    const result = buildQualifierBand([], 'missing', 0, '')
    expect(result).toBeNull()
  })

  it('returns null when there are no qualifier applications', () => {
    const result = buildQualifierBand([makeSeries({ id: 'qc' })], 'qc', 0, '')
    expect(result).toBeNull()
  })

  it('returns N traces for N distinct qualifier codes and uses yaxis{N} axisKey', () => {
    qualifierById['q1'] = { code: 'A', description: 'alpha' }
    qualifierById['q2'] = { code: 'B', description: 'beta' }
    applications.push(
      { qualifierId: 'q1', index: 0, appliedAt: new Date().toISOString(), appliedBy: 'user' },
      { qualifierId: 'q2', index: 1, appliedAt: new Date().toISOString(), appliedBy: 'user' }
    )
    const result = buildQualifierBand([makeSeries({ id: 'qc' })], 'qc', 0, '')
    expect(result).not.toBeNull()
    expect(result!.traces.length).toBe(2)
    expect(result!.mainAxisBottom).toBe(0.14)
    expect(result!.axisKey).toMatch(/^yaxis\d+$/)
  })
})

describe('createPlotlyOption', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    qcDatastream.value = null
    beginDate.value = null
    endDate.value = null
    previewMode.value = false
    hiddenAxisIds.value = new Set()
    plotlyRef.value = null
    applications.length = 0
    for (const k of Object.keys(qualifierById)) delete qualifierById[k]
  })

  it('returns a valid PlotlyChartOptions shape for an empty series array', () => {
    const opts = createPlotlyOption([])
    expect(Array.isArray(opts.traces)).toBe(true)
    expect(opts.traces.length).toBe(0)
    expect(opts.layout).toBeDefined()
    expect(opts.config).toBeDefined()
  })

  it('assigns QC series to primary y (yaxis) and non-QC to yaxis2+', () => {
    qcDatastream.value = { id: 'qc' }
    const qc = makeSeries({ id: 'qc' })
    const other = makeSeries({ id: 'other', color: COLORS[2] })
    const opts = createPlotlyOption([qc, other])
    // Traces are reversed on output; find by id.
    const qcTrace = opts.traces.find((t: any) => t.id === 'qc') as any
    const otherTrace = opts.traces.find((t: any) => t.id === 'other') as any
    expect(qcTrace.yaxis).toBe('y')
    expect(otherTrace.yaxis).toBe('y2')
  })

  it('reverses trace order (last in seriesArray becomes first in traces)', () => {
    const a = makeSeries({ id: 'a' })
    const b = makeSeries({ id: 'b', color: COLORS[2] })
    const opts = createPlotlyOption([a, b])
    expect((opts.traces[0] as any).id).toBe('b')
    expect((opts.traces[1] as any).id).toBe('a')
  })

  it('omits select/lasso modebar buttons when previewMode is true', () => {
    previewMode.value = true
    const opts = createPlotlyOption([])
    const cfg = opts.config as any
    const flat = cfg.modeBarButtons.flat()
    expect(flat).not.toContain('select2d')
    expect(flat).not.toContain('lasso2d')
  })

  it('hides non-QC axis when its id is in hiddenAxisIds', () => {
    qcDatastream.value = { id: 'qc' }
    hiddenAxisIds.value = new Set(['other'])
    const qc = makeSeries({ id: 'qc' })
    const other = makeSeries({ id: 'other', color: COLORS[2] })
    const opts = createPlotlyOption([qc, other])
    const layout = opts.layout as Record<string, any>
    expect(layout.yaxis2.visible).toBe(false)
  })

  it('emits a lines-only gap overlay when intendedSpacingMs is set', () => {
    // Spacing 1.5 → the [1,2,3,4,5] x grid (Δ=1) never exceeds, so the
    // overlay's x/y match the main trace verbatim — but the trace
    // pair is still emitted so the line-drawing path is exercised
    // regardless of whether real gaps are present.
    qcDatastream.value = { id: 'qc' }
    const qc = makeSeries({ id: 'qc', intendedSpacingMs: 1.5 })
    const opts = createPlotlyOption([qc])
    const main = opts.traces.find((t: any) => t.id === 'qc') as any
    const overlay = opts.traces.find(
      (t: any) => t._gapOverlayFor === 'qc'
    ) as any
    expect(main.mode).toBe('markers')
    expect(overlay).toBeDefined()
    expect(overlay.mode).toBe('lines')
    expect(overlay.id).toBeUndefined()
    expect(overlay._isGapOverlay).toBe(true)
    expect(overlay.yaxis).toBe(main.yaxis)
    // No gap > 1.5 in the grid, so the overlay arrays match the main
    // arrays element-for-element.
    expect(Array.from(overlay.x as Float64Array)).toEqual([1, 2, 3, 4, 5])
  })

  it('inserts NaN-y break points in the overlay where gaps exceed the spacing', () => {
    qcDatastream.value = { id: 'qc' }
    const x = new Float64Array([0, 10, 20, 200, 210])
    const y = new Float64Array([1, 2, 3, 4, 5])
    const qc = makeSeries({
      id: 'qc',
      intendedSpacingMs: 15,
      data: { dataX: x, dataY: y, history: [] },
    })
    const opts = createPlotlyOption([qc])
    const overlay = opts.traces.find(
      (t: any) => t._gapOverlayFor === 'qc'
    ) as any
    const oy = Array.from(overlay.y as Float64Array)
    // Exactly one gap (20 → 200), so exactly one NaN injected.
    expect(oy.filter((v) => Number.isNaN(v)).length).toBe(1)
    // Original samples preserved.
    expect(oy.filter((v) => !Number.isNaN(v))).toEqual([1, 2, 3, 4, 5])
  })

  it('omits the gap overlay when intendedSpacingMs is null/zero', () => {
    const a = makeSeries({ id: 'a', intendedSpacingMs: null })
    const b = makeSeries({ id: 'b', color: COLORS[2], intendedSpacingMs: 0 })
    const opts = createPlotlyOption([a, b])
    const overlays = opts.traces.filter((t: any) => t._isGapOverlay)
    expect(overlays.length).toBe(0)
    // Default mode for the series-without-cadence path is markers-only.
    const aTrace = opts.traces.find((t: any) => t.id === 'a') as any
    expect(aTrace.mode).toBe('markers')
  })
})

describe('findGapIndices', () => {
  it('returns an empty array when no consecutive points exceed the threshold', () => {
    expect(findGapIndices([0, 1, 2, 3], 1.5)).toEqual([])
  })

  it('returns an empty array for arrays with fewer than 2 points', () => {
    expect(findGapIndices([], 1)).toEqual([])
    expect(findGapIndices([42], 1)).toEqual([])
  })

  it('flags the index of each point that follows an oversized gap', () => {
    // Gap 100→200 is 100 > 50, gap 250→500 is 250 > 50.
    expect(findGapIndices([100, 200, 250, 500], 50)).toEqual([1, 3])
  })

  it('uses strict greater-than (gap exactly equal to threshold is not a break)', () => {
    expect(findGapIndices([0, 10, 20], 10)).toEqual([])
  })
})

describe('insertGapBreaks', () => {
  it('returns the originals unchanged when there are no gaps', () => {
    const x = new Float64Array([1, 2, 3])
    const y = new Float64Array([10, 20, 30])
    const out = insertGapBreaks(x, y, [])
    expect(out.x).toBe(x)
    expect(out.y).toBe(y)
  })

  it('inserts (midpoint, NaN) at each gap index', () => {
    const x = [0, 10, 100, 110]
    const y = [1, 2, 3, 4]
    const out = insertGapBreaks(x, y, [2])
    expect(Array.from(out.x as Float64Array)).toEqual([0, 10, 55, 100, 110])
    const ys = Array.from(out.y as Float64Array)
    expect(ys[0]).toBe(1)
    expect(ys[1]).toBe(2)
    expect(Number.isNaN(ys[2])).toBe(true)
    expect(ys[3]).toBe(3)
    expect(ys[4]).toBe(4)
  })

  it('handles multiple gaps in order', () => {
    const x = [0, 10, 100, 200, 1000]
    const y = [1, 2, 3, 4, 5]
    const out = insertGapBreaks(x, y, [2, 4])
    const xs = Array.from(out.x as Float64Array)
    expect(xs.length).toBe(x.length + 2)
    // Two NaN-y break points, one per gap.
    const ys = Array.from(out.y as Float64Array)
    expect(ys.filter((v) => Number.isNaN(v)).length).toBe(2)
  })
})
