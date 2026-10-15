import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'

const getObservations = vi.fn()
const hs = ref<any>({ datastreams: { getObservations } })
vi.mock('@/store/hydroserver', () => ({ useHydroServer: () => ({ hs }) }))

import { fetchObservationsSync } from '@/utils/observations'

// The client merges every page into one column group per datastream.
const columns = (count: number) => ({
  ok: true,
  status: 200,
  data: [
    {
      datastreamId: 'ds-1',
      columns: {
        phenomenonTime: Array.from({ length: count }, (_, i) =>
          new Date(i).toISOString()
        ),
        result: Array.from({ length: count }, (_, i) => i),
      },
    },
  ],
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

  it('reads the column group for the datastream window', async () => {
    getObservations.mockResolvedValue(columns(3))

    const { datetimes, dataValues } = await fetchObservationsSync(datastream(0))

    expect(getObservations).toHaveBeenCalledWith(
      'ds-1',
      expect.objectContaining({
        datetime: '1970-01-01T00:00:00Z/2000-01-01T00:00:00Z',
        sortby: ['phenomenonTime'],
        properties: ['phenomenonTime', 'result'],
      })
    )
    expect(datetimes).toEqual([0, 1, 2])
    expect(dataValues).toEqual([0, 1, 2])
  })

  it('returns no points when the window has no observations', async () => {
    getObservations.mockResolvedValue({ ok: true, status: 200, data: [] })

    expect(await fetchObservationsSync(datastream(0))).toEqual({
      datetimes: [],
      dataValues: [],
    })
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
