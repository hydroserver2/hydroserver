// Import the necessary libraries
import { describe, it, expect } from 'vitest'
import {
  SummaryStatistics,
  calculateSummaryStatistics,
} from '@/utils/plotting/summaryStatisticUtils'
import { DataPoint, GraphSeries } from '@hydroserver/client'

const createDataPoints = (values: number[]): DataPoint[] => {
  return values.map((value) => ({
    date: new Date(), // Date is not used in calculation, so any valid date will suffice
    value: value,
  }))
}

describe('SummaryStatistics', () => {
  const name = 'Sample Series'
  const data1 = [10, 20, 30, 40, 50]
  const data2 = [10, 2, 38, 23, 38, 23, 21]
  const data3 = [1, 2, 3, 4, 5, 6, 7, 8]
  const data4 = [1.123, NaN, -2.232, 3.5, 45, -56]
  const summary1 = new SummaryStatistics(name, data1)
  const summary2 = new SummaryStatistics(name, data2)
  const summary3 = new SummaryStatistics(name, data3)
  const summary4 = new SummaryStatistics(name, data4)

  it('properly constructs from raw data', () => {
    expect(summary1.name).toBe(name)
    expect(summary1.observations).toBe(data1.length)
  })

  it('handles empty array correctly', () => {
    const emptySummary = new SummaryStatistics('Empty Series', [])
    expect(emptySummary.observations).toBe(0)
    expect(emptySummary.arithmeticMean).toBeNaN()
  })

  it('calculates arithmetic mean correctly', () => {
    expect(summary1.arithmeticMean).toBeCloseTo(30)
    expect(summary2.arithmeticMean).toBeCloseTo(22.142857)
    expect(summary3.arithmeticMean).toBeCloseTo(4.5)
  })

  it('calculates standard deviation correctly', () => {
    expect(summary1.standardDeviation).toBeCloseTo(14.1421)
    expect(summary2.standardDeviation).toBeCloseTo(12.2989)
    expect(summary3.standardDeviation).toBeCloseTo(2.29128)
    expect(summary4.standardDeviation).toBeCloseTo(32.1393)
  })

  it('calculates quantiles correctly', () => {
    const summary = new SummaryStatistics('Quantile Test Series', data1)

    expect(summary.quantile10).toBe(14)
    expect(summary.quantile25).toBe(20)
    expect(summary.median).toBe(30)
    expect(summary.quantile75).toBe(40)
    expect(summary.quantile90).toBe(46)
  })

  it('handles edge cases for quantile calculations', () => {
    const emptySeries = new SummaryStatistics('Empty Series', [])
    const singleElementSeries = new SummaryStatistics('Single Element', [42])
    expect(emptySeries.quantile25).toBeNaN()
    expect(singleElementSeries.quantile25).toBe(42)
  })
})

describe('calculateSummaryStatistics', () => {
  const seriesArray: GraphSeries[] = [
    {
      id: '1',
      name: 'Series 1',
      data: createDataPoints([1, 2, 3]),
      yAxisLabel: 'Y1',
      lineColor: '#FF0000',
    },
    {
      id: '2',
      name: 'Series 2',
      data: createDataPoints([4, 5, 6]),
      yAxisLabel: 'Y2',
      lineColor: '#00FF00',
    },
  ]

  it('calculates statistics for multiple series correctly', () => {
    const summaries = calculateSummaryStatistics(seriesArray)
    expect(summaries).toHaveLength(seriesArray.length)
    expect(summaries[0].name).toBe('Series 1')
    expect(summaries[1].name).toBe('Series 2')
  })
})
