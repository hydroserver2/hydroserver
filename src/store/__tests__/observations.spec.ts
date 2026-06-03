/**
 * Unit tests for the observations store windowing. The full fetched history
 * stays in `observationsRaw` (the cache); the `ObservationRecord` is sliced
 * to the selected `[begin, end]` window via its `applyWindow`, so the plot,
 * table and counts reflect the current window.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// The store fetches through this helper; stub it so each test controls
// exactly which observations the "server" returns for a requested range.
vi.mock('@/utils/observations', () => ({
  fetchObservationsSync: vi.fn(),
}))

import { fetchObservationsSync } from '@/utils/observations'
import { useObservationStore } from '@/store/observations'

const datastream = { id: 'ds-1' } as any

// 11 points at epoch-ms 0..10.
const ALL_TIMES = Array.from({ length: 11 }, (_, i) => i)

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  // Return whatever falls inside the requested [begin, end] range, mirroring
  // a real range query so the store's cache-fill logic exercises normally.
  ;(fetchObservationsSync as any).mockImplementation(
    async (_ds: unknown, begin: Date, end: Date) => {
      const b = begin.getTime()
      const e = end.getTime()
      const datetimes = ALL_TIMES.filter((t) => t >= b && t <= e)
      return { datetimes, dataValues: datetimes.map((t) => t * 10) }
    }
  )
})

describe('useObservationStore.fetchObservationsInRange windowing', () => {
  it('materializes the full window on a first load', async () => {
    const store = useObservationStore()
    const rec = await store.fetchObservationsInRange(
      datastream,
      new Date(0),
      new Date(10)
    )
    expect(rec.dataX.length).toBe(11)
  })

  it('shrinks the record to the window after narrowing, even though the cache keeps everything', async () => {
    const store = useObservationStore()
    await store.fetchObservationsInRange(datastream, new Date(0), new Date(10))
    // Narrow to [5, 10]; no new fetch, the cache still holds 0..10.
    const rec = await store.fetchObservationsInRange(
      datastream,
      new Date(5),
      new Date(10)
    )
    // Points 5..10 inclusive → 6.
    expect(rec.dataX.length).toBe(6)
    // The cache (source of truth) is untouched.
    expect(store.observationsRaw['ds-1'].datetimes.length).toBe(11)
  })

  it('re-widens back to the full window from the cache without refetching', async () => {
    const store = useObservationStore()
    await store.fetchObservationsInRange(datastream, new Date(0), new Date(10))
    await store.fetchObservationsInRange(datastream, new Date(5), new Date(10))
    ;(fetchObservationsSync as any).mockClear()
    const rec = await store.fetchObservationsInRange(
      datastream,
      new Date(0),
      new Date(10)
    )
    expect(rec.dataX.length).toBe(11)
    expect(fetchObservationsSync).not.toHaveBeenCalled()
  })

  it('reuses the same record and leaves its data untouched when the window is unchanged', async () => {
    const store = useObservationStore()
    const first = await store.fetchObservationsInRange(
      datastream,
      new Date(2),
      new Date(8)
    )
    const beforeX = first.dataX
    const second = await store.fetchObservationsInRange(
      datastream,
      new Date(2),
      new Date(8)
    )
    expect(second).toBe(first)
    // applyWindow is a no-op for the same window, so the data buffer is the
    // same instance — edits/history would survive.
    expect(second.dataX).toBe(beforeX)
  })

  it('keeps the window empty when no points fall in the range', async () => {
    const store = useObservationStore()
    await store.fetchObservationsInRange(datastream, new Date(0), new Date(10))
    const rec = await store.fetchObservationsInRange(
      datastream,
      new Date(100),
      new Date(200)
    )
    expect(rec.dataX.length).toBe(0)
  })
})
