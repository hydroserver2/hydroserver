import { describe, expect, it } from 'vitest'
import type { Datastream } from '@hydroserver/client'
import {
  datastreamTypeLabel,
  profilePoints,
  selectPlotDatastream,
  type ProfileData,
} from '../profile'
import {
  parseDatastreamQuery,
  serializeDatastreamQuery,
} from '@/utils/datastreamSearch'

const stream = (id: string, type = 'timeSeriesCoverage') =>
  ({ id, type }) as Datastream

describe('profile datastreams', () => {
  it('replaces time series with one primary profile, and replaces that profile when choosing another type', () => {
    const first = stream('oxygen', 'profileCoverage'),
      second = stream('temperature', 'profileCoverage')
    expect(selectPlotDatastream([stream('level')], first, true)).toEqual([
      first,
    ])
    expect(selectPlotDatastream([first], second, true)).toEqual([second])
    expect(selectPlotDatastream([first], stream('level'), true)).toEqual([
      stream('level'),
    ])
    expect(selectPlotDatastream([first], first, false)).toEqual([])
    const five = Array.from({ length: 5 }, (_, i) => stream(String(i)))
    expect(selectPlotDatastream(five, stream('six'), true)).toEqual(five)
  })
  it('round trips the type filter alongside search and sorting', () => {
    const parsed = parseDatastreamQuery(
      'type:"Time Series" type:Profile reservoir sort:updated-desc'
    )
    expect(parsed.filters.type).toEqual(['Time Series', 'Profile'])
    expect(parsed.text).toBe('reservoir')
    expect(
      serializeDatastreamQuery(parsed.filters, parsed.text, parsed.sort)
    ).toBe('type:"Time Series" type:Profile sort:updated-desc reservoir')
    expect(datastreamTypeLabel(stream('old'))).toBe('Time Series')
    expect(datastreamTypeLabel(stream('sample', 'discreteCoverage'))).toBe(
      'Discrete'
    )
  })
  it('keeps measurement gaps and separates the same timestamp at different depths and analytes', () => {
    const data = {
      observations: [
        { datastreamId: 'oxygen', phenomenonTime: 'visit', z: 8, result: null },
        { datastreamId: 'oxygen', phenomenonTime: 'visit', z: 0, result: 9 },
        {
          datastreamId: 'temperature',
          phenomenonTime: 'visit',
          z: 0,
          result: 23,
        },
        { datastreamId: 'oxygen', phenomenonTime: 'older', z: 0, result: 8 },
        { datastreamId: 'oxygen', phenomenonTime: 'visit', z: 10, result: NaN },
      ],
    } as ProfileData
    expect(
      profilePoints(data, 'oxygen', 'visit').map((point) => [
        point.z,
        point.result,
      ])
    ).toEqual([
      [0, 9],
      [8, null],
      [10, null],
    ])
  })
})
