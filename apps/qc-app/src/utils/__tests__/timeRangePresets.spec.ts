import { describe, it, expect } from 'vitest'
import {
  ALL_PRESET_ID,
  DEFAULT_PRESET_ID,
  EDITOR_PRESETS,
  TIME_RANGE_PRESETS,
  dataExtent,
  presetAroundWindow,
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

describe('EDITOR_PRESETS', () => {
  it('offers every preset but YTD, with the same ids', () => {
    expect(EDITOR_PRESETS.map((p) => [p.id, p.label])).toEqual([
      [0, '1w'],
      [1, '1m'],
      [2, '6m'],
      [4, '1y'],
      [5, 'All'],
    ])
  })
})

describe('presetAroundWindow', () => {
  const extent = { begin: new Date(2019, 0, 1), end: new Date(2022, 0, 1) }
  const window = {
    begin: new Date(2020, 7, 31, 6),
    end: new Date(2020, 9, 15, 18),
  }

  it('1w adds seven days on each side of the window', () => {
    const w = presetAroundWindow(0, window, extent)
    expect(w?.begin.getTime()).toBe(new Date(2020, 7, 24, 6).getTime())
    expect(w?.end.getTime()).toBe(new Date(2020, 9, 22, 18).getTime())
  })

  it('1m clamps to the end of a shorter month on each side', () => {
    const w = presetAroundWindow(1, window, extent)
    expect(w?.begin.getTime()).toBe(new Date(2020, 6, 31, 6).getTime())
    expect(w?.end.getTime()).toBe(new Date(2020, 10, 15, 18).getTime())
    const endOfJan = { begin: new Date(2021, 0, 31), end: new Date(2021, 0, 31, 12) }
    expect(presetAroundWindow(1, endOfJan, extent)?.end.getTime()).toBe(
      new Date(2021, 1, 28, 12).getTime()
    )
  })

  it('6m and 1y extend the window by their span', () => {
    const six = presetAroundWindow(2, window, extent)
    expect(six?.begin.getTime()).toBe(new Date(2020, 1, 29, 6).getTime())
    expect(six?.end.getTime()).toBe(new Date(2021, 3, 15, 18).getTime())
    const year = presetAroundWindow(4, window, extent)
    expect(year?.begin.getTime()).toBe(new Date(2019, 7, 31, 6).getTime())
    expect(year?.end.getTime()).toBe(new Date(2021, 9, 15, 18).getTime())
  })

  it('does not clip a span to the data at the extent edges', () => {
    const atEdges = { begin: extent.begin, end: extent.end }
    const w = presetAroundWindow(0, atEdges, extent)
    expect(w?.begin.getTime()).toBe(new Date(2018, 11, 25).getTime())
    expect(w?.end.getTime()).toBe(new Date(2022, 0, 8).getTime())
  })

  it('All is the data extent', () => {
    const w = presetAroundWindow(ALL_PRESET_ID, window, extent)
    expect(w?.begin.getTime()).toBe(extent.begin.getTime())
    expect(w?.end.getTime()).toBe(extent.end.getTime())
  })

  it('All still covers a window wider than the extent', () => {
    const narrow = { begin: new Date(2020, 8, 1), end: new Date(2020, 9, 1) }
    const w = presetAroundWindow(ALL_PRESET_ID, window, narrow)
    expect(w?.begin.getTime()).toBe(window.begin.getTime())
    expect(w?.end.getTime()).toBe(window.end.getTime())
  })

  it('All is the window when there is no data extent', () => {
    const w = presetAroundWindow(ALL_PRESET_ID, window, null)
    expect(w?.begin.getTime()).toBe(window.begin.getTime())
    expect(w?.end.getTime()).toBe(window.end.getTime())
  })

  it('YTD resolves like All around a window', () => {
    expect(presetAroundWindow(3, window, extent)).toEqual(
      presetAroundWindow(ALL_PRESET_ID, window, extent)
    )
  })

  it('never returns the caller its own dates', () => {
    const w = presetAroundWindow(ALL_PRESET_ID, window, null)
    expect(w?.begin).not.toBe(window.begin)
    expect(w?.end).not.toBe(window.end)
  })

  it('is null for an unknown id', () => {
    expect(presetAroundWindow(999, window, extent)).toBeNull()
    expect(presetAroundWindow(-1, window, extent)).toBeNull()
  })
})
