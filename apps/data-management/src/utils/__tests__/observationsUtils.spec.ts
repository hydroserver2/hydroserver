import { describe, it, expect, vi, beforeEach } from 'vitest'

const { getObservationsMock } = vi.hoisted(() => ({
  getObservationsMock: vi.fn(),
}))

vi.mock('@hydroserver/client', () => {
  class Datastream {
    id = '123'
    phenomenonBeginTime: string | null = '2023-01-01T00:00:00Z'
    phenomenonEndTime: string | null = '2023-01-02T00:00:00Z'
    noDataValue?: number | null
    intendedTimeSpacing?: number
    intendedTimeSpacingUnit?: string
  }

  return {
    default: {
      datastreams: {
        getObservations: getObservationsMock,
      },
    },
    Datastream,
    TimeSpacingUnit: {
      seconds: 'seconds',
      minutes: 'minutes',
      hours: 'hours',
      days: 'days',
    },
  }
})

import {
  addNaNForGaps,
  convertTimeSpacingToMilliseconds,
  fetchObservations,
  preProcessData,
  replaceNoDataValues,
  subtractHours,
} from '@/utils/observationsUtils'
import { DataArray, Datastream, DataPoint } from '@hydroserver/client'

const createDatastream = (overrides: Partial<Datastream> = {}) =>
  Object.assign(new Datastream(), {
    id: '123',
    phenomenonBeginTime: '2023-01-01T00:00:00Z',
    phenomenonEndTime: '2023-01-02T00:00:00Z',
    ...overrides,
  })

beforeEach(() => {
  getObservationsMock.mockReset()
})

describe('subtractHours', () => {
  it('correctly subtracts hours from a timestamp', () => {
    expect(subtractHours('2022-01-01T10:00:00Z', 5)).toBe(
      '2022-01-01T05:00:00.000Z'
    )
  })
})

describe('preProcessData', () => {
  it('properly pre-processes data', () => {
    const input = [
      ['2023-01-01T00:00:00Z', 10],
      ['2023-01-01T02:00:00Z', 20],
      ['2023-01-01T02:05:00Z', -9999],
      ['2023-01-01T02:10:00Z', 30],
      ['2023-01-01T02:15:00Z', 40],
      ['2023-01-01T02:20:00Z', -9999],
      ['2023-01-01T02:30:00Z', 50],
      ['2023-01-01T02:35:00Z', 60],
    ]

    const datastream = createDatastream({
      noDataValue: -9999,
      intendedTimeSpacing: 5,
      intendedTimeSpacingUnit: 'minutes',
    })

    expect(preProcessData(input as DataArray, datastream)).toStrictEqual([
      { date: new Date('2023-01-01T00:00:00.000Z'), value: 10 },
      { date: new Date('2023-01-01T00:00:00.001Z'), value: NaN },
      { date: new Date('2023-01-01T02:00:00.000Z'), value: 20 },
      { date: new Date('2023-01-01T02:05:00.000Z'), value: NaN },
      { date: new Date('2023-01-01T02:10:00.000Z'), value: 30 },
      { date: new Date('2023-01-01T02:15:00.000Z'), value: 40 },
      { date: new Date('2023-01-01T02:20:00.000Z'), value: NaN },
      { date: new Date('2023-01-01T02:20:00.001Z'), value: NaN },
      { date: new Date('2023-01-01T02:30:00.000Z'), value: 50 },
      { date: new Date('2023-01-01T02:35:00.000Z'), value: 60 },
    ])
  })
})

describe('fetchObservations', () => {
  it('returns empty when datastream has missing time bounds', async () => {
    const data = await fetchObservations(
      createDatastream({ phenomenonBeginTime: null })
    )
    expect(data).toEqual([])
    expect(getObservationsMock).not.toHaveBeenCalled()
  })

  it('maps valid camelCase columnar responses', async () => {
    getObservationsMock.mockResolvedValue({
      ok: true,
      data: {
        phenomenonTime: ['2023-01-01T00:00:00Z', '2023-01-01T01:00:00Z'],
        result: [1, 2],
      },
    })

    const data = await fetchObservations(createDatastream())
    expect(data).toEqual([
      ['2023-01-01T00:00:00Z', 1],
      ['2023-01-01T01:00:00Z', 2],
    ])
  })

  it('maps valid snake_case responses and forwards custom bounds', async () => {
    getObservationsMock.mockResolvedValue({
      ok: true,
      data: {
        phenomenon_time: ['2023-01-01T00:00:00Z'],
        result: [5],
      },
    })

    const start = '2023-01-01T00:00:00Z'
    const end = '2023-01-01T12:00:00Z'
    const data = await fetchObservations(createDatastream(), start, end)

    expect(data).toEqual([['2023-01-01T00:00:00Z', 5]])
    expect(getObservationsMock).toHaveBeenCalledWith(
      '123',
      expect.objectContaining({
        phenomenon_time_min: start,
        phenomenon_time_max: end,
      })
    )
  })

  it('returns empty for non-ok or invalid payloads', async () => {
    getObservationsMock.mockResolvedValueOnce({ ok: false })
    expect(await fetchObservations(createDatastream())).toEqual([])

    getObservationsMock.mockResolvedValueOnce({ ok: true, data: null })
    expect(await fetchObservations(createDatastream())).toEqual([])

    getObservationsMock.mockResolvedValueOnce({
      ok: true,
      data: { phenomenonTime: 'bad', result: [] },
    })
    expect(await fetchObservations(createDatastream())).toEqual([])
  })
})

describe('replaceNoDataValues', () => {
  it('returns original data if noDataValue is null/undefined', () => {
    const points: DataPoint[] = [{ date: new Date('2023-01-01T00:00:00Z'), value: 1 }]
    expect(replaceNoDataValues(points, null)).toBe(points)
    expect(replaceNoDataValues(points, undefined)).toBe(points)
  })

  it('replaces null/undefined, NaN strings, and noData numeric matches', () => {
    const points: DataPoint[] = [
      { date: new Date('2023-01-01T00:00:00Z'), value: null as any },
      { date: new Date('2023-01-01T01:00:00Z'), value: undefined as any },
      { date: new Date('2023-01-01T02:00:00Z'), value: 'NaN' as any },
      { date: new Date('2023-01-01T03:00:00Z'), value: '-9999' as any },
      { date: new Date('2023-01-01T04:00:00Z'), value: 4 },
    ]

    const normalized = replaceNoDataValues(points, -9999)
    expect(Number.isNaN(normalized[0].value as number)).toBe(true)
    expect(Number.isNaN(normalized[1].value as number)).toBe(true)
    expect(Number.isNaN(normalized[2].value as number)).toBe(true)
    expect(Number.isNaN(normalized[3].value as number)).toBe(true)
    expect(normalized[4].value).toBe(4)
  })
})

describe('time spacing helpers', () => {
  it('converts units and falls back to zero for unknown units', () => {
    expect(convertTimeSpacingToMilliseconds(2, 'seconds')).toBe(2000)
    expect(convertTimeSpacingToMilliseconds(3, 'minutes')).toBe(180000)
    expect(convertTimeSpacingToMilliseconds(1, 'hours')).toBe(3600000)
    expect(convertTimeSpacingToMilliseconds(2, 'days')).toBe(172800000)
    expect(convertTimeSpacingToMilliseconds(2, 'weeks' as any)).toBe(0)
  })

  it('adds NaN markers for gaps over threshold', () => {
    const points: DataPoint[] = [
      { date: new Date('2023-01-01T00:00:00Z'), value: 1 },
      { date: new Date('2023-01-01T00:00:05Z'), value: 2 },
      { date: new Date('2023-01-01T00:00:25Z'), value: 3 },
    ]

    const withGaps = addNaNForGaps(points, 10_000)
    expect(withGaps).toHaveLength(4)
    expect(Number.isNaN(withGaps[2].value as number)).toBe(true)
  })
})
