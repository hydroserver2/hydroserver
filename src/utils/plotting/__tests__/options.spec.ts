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
})
