import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Datastream } from '@hydroserver/client'
import { useObservationStore } from '../observations'
import { SummaryStatistics } from '@/utils/plotting/summaryStatisticUtils'

const { getObservationsMock } = vi.hoisted(() => ({
  getObservationsMock: vi.fn(),
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    datastreams: { getObservations: getObservationsMock },
  },
  ObservationProfile: {
    Column: 'https://hydroserver.org/profiles/observations/column',
  },
}))

const times = [
  '2023-01-01T00:00:00Z',
  '2023-01-01T01:00:00Z',
  '2023-01-01T02:00:00Z',
  '2023-01-01T03:00:00Z',
  '2023-01-01T04:00:00Z',
  '2023-01-01T05:00:00Z',
]

const datastream = {
  id: 'decimal-observations',
  phenomenonBeginTime: times[0],
  phenomenonEndTime: times[5],
  noDataValue: -9999.99,
} as Datastream

const mockObservations = (timestamps: string[], values: number[]) => {
  getObservationsMock.mockResolvedValueOnce({
    ok: true,
    data: [{ columns: { phenomenonTime: timestamps, result: values } }],
  })
}

describe('observation cache precision', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getObservationsMock.mockReset()
  })

  it.each([10, 10.123456789])(
    'preserves %s and normalizes decimal no-data values on cached reads',
    async (measurement) => {
      const store = useObservationStore()
      mockObservations(times.slice(0, 2), [measurement, datastream.noDataValue])

      const initial = await store.fetchGraphSeriesData(
        datastream,
        times[0],
        times[1]
      )
      const cached = await store.fetchGraphSeriesData(
        datastream,
        times[0],
        times[1]
      )
      const expected = [
        { date: new Date(times[0]), value: measurement },
        { date: new Date(times[1]), value: NaN },
      ]

      expect(initial).toEqual(expected)
      expect(cached).toEqual(expected)
      expect(getObservationsMock).toHaveBeenCalledTimes(1)
      const summary = new SummaryStatistics(
        'Cached data',
        cached!.map((d) => d.value)
      )
      expect(summary.observations).toBe(1)
      expect(summary.arithmeticMean).toBe(measurement)
    }
  )

  it.each([
    { direction: 'earlier', start: 0, end: 3, mean: 15.123456789, requests: 2 },
    { direction: 'later', start: 2, end: 5, mean: 25.123456789, requests: 2 },
    { direction: 'both', start: 0, end: 5, mean: 20.123456789, requests: 3 },
  ])(
    'preserves precision when extending the cache $direction',
    async ({ start, end, mean, requests }) => {
      const store = useObservationStore()
      const values = [
        10.123456789, -9999.99, 20.123456789, -9999.99, 30.123456789, -9999.99,
      ]
      mockObservations(times.slice(2, 4), values.slice(2, 4))
      await store.fetchGraphSeriesData(datastream, times[2], times[3])

      if (start === 0) mockObservations(times.slice(0, 2), values.slice(0, 2))
      if (end === 5) mockObservations(times.slice(4, 6), values.slice(4, 6))

      const merged = await store.fetchGraphSeriesData(
        datastream,
        times[start],
        times[end]
      )
      const cached = await store.fetchGraphSeriesData(
        datastream,
        times[start],
        times[end]
      )
      const expected = times.slice(start, end + 1).map((time, index) => ({
        date: new Date(time),
        value: index % 2 === 0 ? values[start + index] : NaN,
      }))

      expect(merged).toEqual(expected)
      expect(cached).toEqual(expected)
      expect(getObservationsMock).toHaveBeenCalledTimes(requests)

      const summary = new SummaryStatistics(
        'Merged data',
        cached!.map((d) => d.value)
      )
      expect(summary.observations).toBe(expected.length / 2)
      expect(summary.arithmeticMean).toBeCloseTo(mean, 9)
    }
  )
})
