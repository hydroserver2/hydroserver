import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'

const getObservations = vi.fn()
const hs = ref<any>({ datastreams: { getObservations } })
vi.mock('@/store/hydroserver', () => ({ useHydroServer: () => ({ hs }) }))

import { fetchObservationsSync } from '@/utils/observations'

const PAGE_SIZE = 50_000

const page = (count: number, from = 0) => ({
  ok: true,
  status: 200,
  data: {
    phenomenonTime: Array.from({ length: count }, (_, i) =>
      new Date(from + i).toISOString()
    ),
    result: Array.from({ length: count }, (_, i) => from + i),
  },
})

const datastream = (valueCount: number) =>
  ({
    id: 'ds-1',
    phenomenonBeginTime: '1970-01-01T00:00:00Z',
    phenomenonEndTime: '2000-01-01T00:00:00Z',
    valueCount,
  }) as any

beforeEach(() => {
  vi.clearAllMocks()
})

describe('fetchObservationsSync', () => {
  it('fails when a page fails, rather than returning what it has', async () => {
    getObservations.mockResolvedValue({ ok: false, status: 500, message: 'Server error' })

    await expect(fetchObservationsSync(datastream(10))).rejects.toThrow('Server error')
  })

  it('keeps paging past a stale value count until a short page', async () => {
    getObservations
      .mockResolvedValueOnce(page(PAGE_SIZE))
      .mockResolvedValueOnce(page(2, PAGE_SIZE))

    const { datetimes } = await fetchObservationsSync(datastream(0))

    expect(getObservations).toHaveBeenCalledTimes(2)
    expect(datetimes).toHaveLength(PAGE_SIZE + 2)
  })

  it('makes no request for a datastream with no observations', async () => {
    const result = await fetchObservationsSync({
      ...datastream(0),
      phenomenonBeginTime: null,
    })

    expect(result).toEqual({ datetimes: [], dataValues: [] })
    expect(getObservations).not.toHaveBeenCalled()
  })
})
