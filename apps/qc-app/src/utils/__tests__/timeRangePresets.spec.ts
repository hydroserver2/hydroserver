import { describe, it, expect } from 'vitest'
import {
  ALL_PRESET_ID,
  DEFAULT_PRESET_ID,
  TIME_RANGE_PRESETS,
  dataExtent,
  presetWindow,
} from '@/utils/timeRangePresets'

const DAY = 24 * 60 * 60 * 1000

describe('TIME_RANGE_PRESETS', () => {
  it('keeps the stable preset ids and defaults to 1m', () => {
    expect(TIME_RANGE_PRESETS.map((p) => [p.id, p.label])).toEqual([
      [0, '1w'],
      [1, '1m'],
      [2, '6m'],
      [4, '1y'],
      [3, 'YTD'],
      [5, 'All'],
    ])
    expect(DEFAULT_PRESET_ID).toBe(1)
    expect(ALL_PRESET_ID).toBe(5)
  })
})

describe('dataExtent', () => {
  it('spans the earliest begin to the latest end', () => {
    const extent = dataExtent([
      {
        phenomenonBeginTime: '2020-01-01T00:00:00Z',
        phenomenonEndTime: '2021-06-30T12:00:00Z',
      },
      {
        phenomenonBeginTime: '2019-05-01T00:00:00Z',
        phenomenonEndTime: '2020-02-01T00:00:00Z',
      },
    ])
    expect(extent?.begin.toISOString()).toBe('2019-05-01T00:00:00.000Z')
    expect(extent?.end.toISOString()).toBe('2021-06-30T12:00:00.000Z')
  })

  it('skips datastreams without observations', () => {
    const extent = dataExtent([
      { phenomenonBeginTime: null, phenomenonEndTime: null },
      {},
      {
        phenomenonBeginTime: '2020-01-01T00:00:00Z',
        phenomenonEndTime: '2020-02-01T00:00:00Z',
      },
    ])
    expect(extent?.end.toISOString()).toBe('2020-02-01T00:00:00.000Z')
  })

  it('is null when nothing has observations', () => {
    expect(dataExtent([])).toBeNull()
    expect(dataExtent([{ phenomenonEndTime: null }])).toBeNull()
  })
})

describe('presetWindow', () => {
  const extent = {
    begin: new Date(2019, 4, 1),
    end: new Date(2021, 2, 31, 12),
  }

  it('1w counts back seven days from the data end', () => {
    const w = presetWindow(0, { begin: extent.begin, end: new Date(2021, 5, 30, 12) })
    expect(w?.end.getTime()).toBe(new Date(2021, 5, 30, 12).getTime())
    expect(w!.end.getTime() - w!.begin.getTime()).toBe(7 * DAY)
  })

  it('1m clamps to the end of a shorter month', () => {
    const w = presetWindow(1, extent)
    expect(w?.begin.getTime()).toBe(new Date(2021, 1, 28, 12).getTime())
    expect(w?.end.getTime()).toBe(extent.end.getTime())
  })

  it('6m and 1y count back from the data end', () => {
    expect(presetWindow(2, extent)?.begin.getTime()).toBe(
      new Date(2020, 8, 30, 12).getTime()
    )
    expect(presetWindow(4, extent)?.begin.getTime()).toBe(
      new Date(2020, 2, 31, 12).getTime()
    )
  })

  it('YTD starts on Jan 1 of the data end year', () => {
    expect(presetWindow(3, extent)?.begin.getTime()).toBe(
      new Date(2021, 0, 1).getTime()
    )
  })

  it('All spans the whole extent', () => {
    const w = presetWindow(5, extent)
    expect(w?.begin.getTime()).toBe(extent.begin.getTime())
    expect(w?.end.getTime()).toBe(extent.end.getTime())
  })

  it('is null for an unknown id', () => {
    expect(presetWindow(999, extent)).toBeNull()
    expect(presetWindow(-1, extent)).toBeNull()
  })
})
