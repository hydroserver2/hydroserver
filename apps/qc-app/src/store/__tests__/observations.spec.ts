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
    // same instance, so edits/history would survive.
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

describe('useObservationStore.fetchObservationsInRange overlapping requests', () => {
  const deferred = <T>() => {
    let resolve!: (v: T) => void
    const promise = new Promise<T>((r) => (resolve = r))
    return { promise, resolve }
  }
  const rangeOf = (begin: number, end: number) => {
    const datetimes = ALL_TIMES.filter((t) => t >= begin && t <= end)
    return { datetimes, dataValues: datetimes.map((t) => t * 10) }
  }

  it('applies the latest requested window and keeps the cache free of duplicates when responses land out of order', async () => {
    const slow = deferred<ReturnType<typeof rangeOf>>()
    ;(fetchObservationsSync as any)
      .mockImplementationOnce(() => slow.promise)
      .mockImplementationOnce(async () => rangeOf(5, 10))
    const store = useObservationStore()

    const first = store.fetchObservationsInRange(datastream, new Date(0), new Date(10))
    const second = store.fetchObservationsInRange(datastream, new Date(5), new Date(10))
    await Promise.resolve()
    slow.resolve(rangeOf(0, 10))
    const [, rec] = await Promise.all([first, second])

    expect(rec.dataX.length).toBe(6)
    expect(Array.from(store.observationsRaw['ds-1'].datetimes)).toEqual(ALL_TIMES)
  })

  it('shares one request for an identical range already in flight', async () => {
    const store = useObservationStore()

    const [a, b] = await Promise.all([
      store.fetchObservationsInRange(datastream, new Date(2), new Date(8)),
      store.fetchObservationsInRange(datastream, new Date(2), new Date(8)),
    ])

    expect(a).toBe(b)
    expect(fetchObservationsSync).toHaveBeenCalledTimes(1)
  })

  it('still serves later requests after a failed one', async () => {
    ;(fetchObservationsSync as any).mockRejectedValueOnce(new Error('offline'))
    const store = useObservationStore()

    const failed = store.fetchObservationsInRange(datastream, new Date(0), new Date(10))
    const next = store.fetchObservationsInRange(datastream, new Date(0), new Date(4))

    await expect(failed).rejects.toThrow('offline')
    expect((await next).dataX.length).toBe(5)
  })
})

describe('useObservationStore.fetchObservationsInRange coverage', () => {
  const requested = () =>
    (fetchObservationsSync as any).mock.calls.map(
      ([, b, e]: [unknown, Date, Date]) => [b.getTime(), e.getTime()]
    )

  it('skips the excluded stretch and leaves a gap in the record', async () => {
    const store = useObservationStore()
    const rec = await store.fetchObservationsInRange(
      datastream,
      new Date(0),
      new Date(10),
      { begin: new Date(3), end: new Date(6) }
    )
    expect(requested()).toEqual([
      [0, 2],
      [7, 10],
    ])
    expect(Array.from(rec.dataX)).toEqual([0, 1, 2, 7, 8, 9, 10])
  })

  it('fetches only the gap once it is asked for', async () => {
    const store = useObservationStore()
    await store.fetchObservationsInRange(datastream, new Date(0), new Date(10), {
      begin: new Date(3),
      end: new Date(6),
    })
    ;(fetchObservationsSync as any).mockClear()
    const rec = await store.fetchObservationsInRange(
      datastream,
      new Date(0),
      new Date(10)
    )
    expect(requested()).toEqual([[3, 6]])
    expect(Array.from(rec.dataX)).toEqual(ALL_TIMES)
  })

  it('does not ask again for a range that held no data', async () => {
    const store = useObservationStore()
    await store.fetchObservationsInRange(datastream, new Date(100), new Date(200))
    ;(fetchObservationsSync as any).mockClear()
    await store.fetchObservationsInRange(datastream, new Date(100), new Date(200))
    expect(fetchObservationsSync).not.toHaveBeenCalled()
  })

  it('keeps one copy of a timestamp two ranges both returned', async () => {
    ;(fetchObservationsSync as any)
      .mockImplementationOnce(async () => ({ datetimes: [0, 1, 2], dataValues: [0, 10, 20] }))
      .mockImplementationOnce(async () => ({ datetimes: [2, 3], dataValues: [99, 30] }))
    const store = useObservationStore()
    await store.fetchObservationsInRange(datastream, new Date(0), new Date(2))
    const rec = await store.fetchObservationsInRange(datastream, new Date(0), new Date(3))
    expect(Array.from(rec.dataX)).toEqual([0, 1, 2, 3])
    expect(Array.from(rec.dataY)).toEqual([0, 10, 20, 30])
  })

  it('asks again for a range whose fetch failed', async () => {
    ;(fetchObservationsSync as any).mockRejectedValueOnce(new Error('offline'))
    const store = useObservationStore()
    await expect(
      store.fetchObservationsInRange(datastream, new Date(0), new Date(10))
    ).rejects.toThrow('offline')
    const rec = await store.fetchObservationsInRange(datastream, new Date(0), new Date(10))
    expect(rec.dataX.length).toBe(11)
  })
})
