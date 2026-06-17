import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// --- Mocks --------------------------------------------------------------

vi.mock('plotly.js-dist', () => ({
  default: {
    relayout: vi.fn().mockResolvedValue(undefined),
  },
}))

// plotlyRef is accessed via `storeToRefs` (returns ref) in captureCurrentZoomState,
// and via raw property access (`store.plotlyRef`) in applyZoomState. Other fields
// like zoomUndoStack/zoomRedoStack/suppressZoomHistory are mutated directly on the
// store object (not via `.value`), so they must be plain properties — not refs.
const plotlyRefRef = ref<any>(null)

type ZoomSnap = { xRange: [number, number] | null; yRanges: Record<string, [number, number]>; source: 'user' | 'init' }

const storeState: {
  plotlyRef: any
  zoomUndoStack: ZoomSnap[]
  zoomRedoStack: ZoomSnap[]
  suppressZoomHistory: boolean
  graphSeriesArray: any[]
  canUndoZoom: boolean
  canRedoZoom: boolean
  pushZoomState: (s: ZoomSnap) => void
} = {
  get plotlyRef() {
    return plotlyRefRef.value
  },
  set plotlyRef(v: any) {
    plotlyRefRef.value = v
  },
  zoomUndoStack: [],
  zoomRedoStack: [],
  suppressZoomHistory: false,
  graphSeriesArray: [{}],
  get canUndoZoom() {
    return storeState.zoomUndoStack.length > 1
  },
  get canRedoZoom() {
    return storeState.zoomRedoStack.length > 0
  },
  pushZoomState(state: ZoomSnap) {
    storeState.zoomUndoStack.push(state)
    storeState.zoomRedoStack = []
  },
}

vi.mock('@/store/plotly', async () => {
  return {
    usePlotlyStore: () => storeState,
  }
})

// storeToRefs → returns refs for each key. captureCurrentZoomState calls
// `storeToRefs(usePlotlyStore()).plotlyRef` then reads `.value`. Pinia's
// real storeToRefs works with reactive state, but our mock store is plain.
// Override pinia's storeToRefs to produce a ref for plotlyRef.
vi.mock('pinia', async () => {
  const actual = await vi.importActual<typeof import('pinia')>('pinia')
  return {
    ...actual,
    storeToRefs: (store: any) => {
      // Proxy that returns `{ value }` refs for any property accessed.
      return new Proxy(
        {},
        {
          get: (_target, prop: string) => {
            if (prop === 'plotlyRef') return plotlyRefRef
            return {
              get value() {
                return store[prop]
              },
              set value(v) {
                store[prop] = v
              },
            }
          },
        }
      )
    },
  }
})

// --- Tests --------------------------------------------------------------

import {
  captureCurrentZoomState,
  recordZoomIfSettled,
  applyZoomState,
  undoZoom,
  redoZoom,
  installZoomTracking,
} from '../zoom'

const resetState = () => {
  plotlyRefRef.value = null
  storeState.zoomUndoStack = []
  storeState.zoomRedoStack = []
  storeState.suppressZoomHistory = false
  storeState.graphSeriesArray = [{}]
}

describe('captureCurrentZoomState', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetState()
  })

  it('returns null when plotlyRef is null', () => {
    plotlyRefRef.value = null
    expect(captureCurrentZoomState('user')).toBeNull()
  })

  it('returns ZoomState with xRange and yRanges from layout', () => {
    plotlyRefRef.value = {
      layout: {
        xaxis: { range: [100, 200] },
        yaxis: { range: [1, 10] },
        yaxis2: { range: [0, 5] },
      },
    }
    const snap = captureCurrentZoomState('user')
    expect(snap).not.toBeNull()
    expect(snap!.xRange).toEqual([100, 200])
    // Normalised to trace-axis-ref form (`yaxis` → `y`, `yaxis2` →
    // `y2`) so the share-URL encoder + decoder + applyZoomState all
    // speak the same dialect.
    expect(snap!.yRanges.y).toEqual([1, 10])
    expect(snap!.yRanges.y2).toEqual([0, 5])
    expect(snap!.source).toBe('user')
  })

  it('parses date-string ranges into numeric xRange', () => {
    const a = new Date('2024-01-01T00:00:00Z').toISOString()
    const b = new Date('2024-01-02T00:00:00Z').toISOString()
    plotlyRefRef.value = {
      layout: { xaxis: { range: [a, b] } },
    }
    const snap = captureCurrentZoomState('init')
    expect(snap).not.toBeNull()
    expect(Number.isFinite(snap!.xRange![0])).toBe(true)
    expect(Number.isFinite(snap!.xRange![1])).toBe(true)
    expect(snap!.source).toBe('init')
  })
})

describe('recordZoomIfSettled (exercises sameRange/sameZoomState)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetState()
    plotlyRefRef.value = {
      layout: {
        xaxis: { range: [0, 1000] },
        yaxis: { range: [0, 10] },
      },
    }
  })

  it('no-ops when suppressZoomHistory is true', () => {
    storeState.suppressZoomHistory = true
    recordZoomIfSettled('user')
    expect(storeState.zoomUndoStack.length).toBe(0)
  })

  it('no-ops when current snapshot matches top of undo stack (within 0.5%)', () => {
    storeState.zoomUndoStack.push({
      xRange: [0, 1000],
      yRanges: { y: [0, 10] },
      source: 'user',
    })
    recordZoomIfSettled('user')
    expect(storeState.zoomUndoStack.length).toBe(1)
  })

  it('pushes when snapshot is a new state (x differs beyond threshold)', () => {
    storeState.zoomUndoStack.push({
      xRange: [0, 1000],
      yRanges: { y: [0, 10] },
      source: 'user',
    })
    plotlyRefRef.value = {
      layout: {
        xaxis: { range: [500, 1500] },
        yaxis: { range: [0, 10] },
      },
    }
    recordZoomIfSettled('user')
    expect(storeState.zoomUndoStack.length).toBe(2)
  })

  it('pushes when a y-axis range differs beyond threshold', () => {
    storeState.zoomUndoStack.push({
      xRange: [0, 1000],
      yRanges: { y: [0, 10] },
      source: 'user',
    })
    plotlyRefRef.value = {
      layout: {
        xaxis: { range: [0, 1000] },
        yaxis: { range: [0, 100] }, // y changed
      },
    }
    recordZoomIfSettled('user')
    expect(storeState.zoomUndoStack.length).toBe(2)
  })

  it('treats ranges within 0.5% as same (no push)', () => {
    storeState.zoomUndoStack.push({
      xRange: [0, 1000],
      yRanges: { y: [0, 10] },
      source: 'user',
    })
    plotlyRefRef.value = {
      layout: {
        xaxis: { range: [1, 1001] }, // 0.1% drift
        yaxis: { range: [0, 10] },
      },
    }
    recordZoomIfSettled('user')
    expect(storeState.zoomUndoStack.length).toBe(1)
  })
})

describe('undoZoom', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetState()
  })

  it('no-ops when canUndoZoom is false', async () => {
    storeState.zoomUndoStack = []
    await undoZoom()
    expect(storeState.zoomUndoStack.length).toBe(0)
    expect(storeState.zoomRedoStack.length).toBe(0)
  })

  it('moves current to redo stack and applies previous', async () => {
    const s1 = { xRange: [0, 10] as [number, number], yRanges: {}, source: 'user' as const }
    const s2 = { xRange: [5, 15] as [number, number], yRanges: {}, source: 'user' as const }
    storeState.zoomUndoStack = [s1, s2]
    plotlyRefRef.value = { layout: {} }
    await undoZoom()
    expect(storeState.zoomUndoStack).toEqual([s1])
    expect(storeState.zoomRedoStack).toEqual([s2])
  })
})

describe('redoZoom', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetState()
  })

  it('no-ops when canRedoZoom is false', async () => {
    storeState.zoomRedoStack = []
    await redoZoom()
    expect(storeState.zoomUndoStack.length).toBe(0)
  })

  it('pops from redo, pushes to undo, and applies', async () => {
    const s1 = { xRange: [0, 10] as [number, number], yRanges: {}, source: 'user' as const }
    const s2 = { xRange: [5, 15] as [number, number], yRanges: {}, source: 'user' as const }
    storeState.zoomUndoStack = [s1]
    storeState.zoomRedoStack = [s2]
    plotlyRefRef.value = { layout: {} }
    await redoZoom()
    expect(storeState.zoomUndoStack).toEqual([s1, s2])
    expect(storeState.zoomRedoStack).toEqual([])
  })
})

describe('applyZoomState', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetState()
  })

  it('returns without effect when plotlyRef is null', async () => {
    plotlyRefRef.value = null
    await applyZoomState({
      xRange: [0, 10],
      yRanges: {},
      source: 'user',
    })
    expect(storeState.suppressZoomHistory).toBe(false)
  })

  it('sets suppressZoomHistory during relayout', async () => {
    plotlyRefRef.value = { layout: {} }
    await applyZoomState({
      xRange: [0, 10],
      // `y` (trace-axis ref) — applyZoomState converts to `yaxis`
      // before emitting the Plotly relayout payload.
      yRanges: { y: [0, 1] },
      source: 'user',
    })
    // suppressZoomHistory is cleared asynchronously via setTimeout(…, 450)
    expect(storeState.suppressZoomHistory).toBe(true)
  })

  it('falls back to xaxis.autorange:true when xRange is null', async () => {
    plotlyRefRef.value = { layout: {} }
    const Plotly = (await import('plotly.js-dist')).default as any
    Plotly.relayout.mockClear()
    await applyZoomState({ xRange: null, yRanges: {}, source: 'user' })
    expect(Plotly.relayout).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ 'xaxis.autorange': true })
    )
  })

  it('clears suppressZoomHistory after the post-relayout timeout', async () => {
    vi.useFakeTimers()
    try {
      plotlyRefRef.value = { layout: {} }
      await applyZoomState({
        xRange: [0, 10],
        yRanges: {},
        source: 'user',
      })
      expect(storeState.suppressZoomHistory).toBe(true)
      vi.advanceTimersByTime(500)
      expect(storeState.suppressZoomHistory).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('installZoomTracking', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetState()
  })

  it('subscribes to plotly_relayout when given a Plotly element', () => {
    const on = vi.fn()
    const gd = { on } as unknown as Parameters<typeof installZoomTracking>[0]
    installZoomTracking(gd)
    expect(on).toHaveBeenCalledWith('plotly_relayout', expect.any(Function))
  })

  it('no-ops on a null/undefined plotly element', () => {
    expect(() => installZoomTracking(null)).not.toThrow()
    expect(() => installZoomTracking(undefined)).not.toThrow()
  })
})
