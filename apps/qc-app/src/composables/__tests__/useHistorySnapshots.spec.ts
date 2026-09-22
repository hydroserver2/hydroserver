/**
 * Snapshots are built off a detached record and toggled on/off the plot.
 * The store actions are stubbed here; what matters is that the composable
 * resolves the right session, replays to the right index, and hands over
 * provenance metadata.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const {
  plottedDatastreams,
  qcDatastream,
  addSnapshotSeries,
  removeSnapshotSeries,
  sessions,
  historyId,
  sourceDatastream,
  viewedSessionId,
  selectedSeries,
  observationsRaw,
  fetchObservationsInRange,
  buildSnapshotRecord,
  hs,
  error,
} = vi.hoisted(() => {
  const { ref: r } = require('vue') as typeof import('vue')
  return {
    plottedDatastreams: r<any[]>([]),
    qcDatastream: r<any>({ id: 'mgd-1', name: 'Managed' }),
    addSnapshotSeries: vi.fn().mockResolvedValue(undefined),
    removeSnapshotSeries: vi.fn().mockResolvedValue(undefined),
    sessions: r<any[]>([]),
    historyId: r<string | null>('hist-1'),
    sourceDatastream: r<any>({ id: 'src-1', name: 'Source' }),
    viewedSessionId: r<string | null>(null),
    selectedSeries: r<any>({ data: { history: [] } }),
    observationsRaw: r<Record<string, any>>({}),
    fetchObservationsInRange: vi.fn().mockResolvedValue({}),
    buildSnapshotRecord: vi.fn(),
    hs: r<any>({
      qualityControlSessions: {},
      qualityControlOperations: {},
    }),
    error: vi.fn(),
  }
})

vi.mock('@/store/dataVisualization', async () => {
  const { defineStore } = await import('pinia')
  return {
    useDataVisStore: defineStore('dataVisualization', () => ({
      plottedDatastreams,
      qcDatastream,
      addSnapshotSeries,
      removeSnapshotSeries,
    })),
  }
})

vi.mock('@/store/qcSession', async () => {
  const { defineStore } = await import('pinia')
  return {
    useQcSessionStore: defineStore('qcSession', () => ({
      sessions,
      historyId,
      sourceDatastream,
      viewedSessionId,
    })),
  }
})

vi.mock('@/store/plotly', async () => {
  const { defineStore } = await import('pinia')
  return {
    usePlotlyStore: defineStore('Plotly', () => ({ selectedSeries })),
  }
})

vi.mock('@/store/observations', async () => {
  const { defineStore } = await import('pinia')
  return {
    useObservationStore: defineStore('observations', () => ({
      observationsRaw,
      fetchObservationsInRange,
    })),
  }
})

vi.mock('@/store/hydroserver', async () => {
  const { defineStore } = await import('pinia')
  return {
    useHydroServer: defineStore('hydroserver', () => ({ hs })),
  }
})

vi.mock('@/services/qualityControl/buildSnapshot', () => ({
  buildSnapshotRecord,
}))

vi.mock('@uwrl/qc-utils', () => ({
  Snackbar: { error, success: vi.fn(), warn: vi.fn() },
  applyHistory: vi.fn(),
  ObservationRecord: class {
    rawData: unknown
    constructor(raw: unknown) {
      this.rawData = raw
    }
    async applyWindow() {}
  },
}))

import { useHistorySnapshots } from '../useHistorySnapshots'

const committed = {
  id: 'sess-c',
  status: 'committed',
  description: 'March backfill',
  createdAt: '2026-03-14T00:00:00Z',
  phenomenonTimeStart: '2026-03-01T00:00:00Z',
  phenomenonTimeEnd: '2026-04-01T00:00:00Z',
  operations: [
    { operationType: 'FILL_GAPS', createdBy: { name: 'Alice' } },
    { operationType: 'DELETE_POINTS', createdBy: { name: 'Bob' } },
  ],
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  plottedDatastreams.value = []
  sessions.value = [committed]
  historyId.value = 'hist-1'
  sourceDatastream.value = { id: 'src-1', name: 'Source' }
  qcDatastream.value = { id: 'mgd-1', name: 'Managed' }
  viewedSessionId.value = null
  buildSnapshotRecord.mockResolvedValue({ history: [], isLoading: false })
})

describe('useHistorySnapshots', () => {
  it('adds a snapshot series with provenance metadata', async () => {
    const { toggleSnapshot } = useHistorySnapshots()

    await toggleSnapshot('sess-c', 1)

    expect(addSnapshotSeries).toHaveBeenCalledTimes(1)
    const [id, , meta] = addSnapshotSeries.mock.calls[0]!
    expect(id).toBe('snap:sess-c:1')
    expect(meta).toMatchObject({
      sessionId: 'sess-c',
      sessionLabel: 'March backfill',
      opIndex: 1,
      opCount: 2,
      opName: 'Delete Points',
      performedBy: 'Bob',
    })
  })

  it('labels the baseline snapshot with no operation name', async () => {
    const { toggleSnapshot } = useHistorySnapshots()

    await toggleSnapshot('sess-c', -1)

    const [, , meta] = addSnapshotSeries.mock.calls[0]!
    expect(meta.opIndex).toBe(-1)
    expect(meta.opName).toBe('')
  })

  it('removes an already-plotted snapshot instead of rebuilding it', async () => {
    plottedDatastreams.value = [{ id: 'snap:sess-c:1', name: 'x' }]
    const { toggleSnapshot } = useHistorySnapshots()

    await toggleSnapshot('sess-c', 1)

    expect(removeSnapshotSeries).toHaveBeenCalledWith('snap:sess-c:1')
    expect(buildSnapshotRecord).not.toHaveBeenCalled()
  })

  it('reports whether a snapshot is plotted', () => {
    plottedDatastreams.value = [{ id: 'snap:sess-c:1', name: 'x' }]
    const { isSnapshotPlotted } = useHistorySnapshots()

    expect(isSnapshotPlotted('sess-c', 1)).toBe(true)
    expect(isSnapshotPlotted('sess-c', 0)).toBe(false)
  })

  it('passes the live draft history for the session being viewed', async () => {
    viewedSessionId.value = 'sess-c'
    selectedSeries.value = {
      data: { history: [{ method: 'FILL_GAPS', args: [] }] },
    }
    const { toggleSnapshot } = useHistorySnapshots()

    await toggleSnapshot('sess-c', 0)

    const params = buildSnapshotRecord.mock.calls[0]![1]
    expect(params.liveHistory).toEqual([{ method: 'FILL_GAPS', args: [] }])
  })

  it('surfaces a build failure instead of plotting nothing silently', async () => {
    buildSnapshotRecord.mockRejectedValueOnce(new Error('boom'))
    const { toggleSnapshot } = useHistorySnapshots()

    await toggleSnapshot('sess-c', 0)

    expect(error).toHaveBeenCalledWith(expect.stringContaining('boom'))
    expect(addSnapshotSeries).not.toHaveBeenCalled()
  })

  it('refuses when the session is not loaded', async () => {
    sessions.value = []
    const { toggleSnapshot } = useHistorySnapshots()

    await toggleSnapshot('sess-c', 0)

    expect(error).toHaveBeenCalled()
    expect(buildSnapshotRecord).not.toHaveBeenCalled()
  })
})
