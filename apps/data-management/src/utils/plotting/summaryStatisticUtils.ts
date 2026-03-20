import { GraphSeries } from '@hydroserver/client'

// Math References:
//      Standard Deviation - https://stackoverflow.com/questions/7343890/standard-deviation-javascript
//      Quantile - https://www.geeksforgeeks.org/d3-js-d3-quantile-function/

export class SummaryStatistics {
  name: string
  maximum: number
  minimum: number
  arithmeticMean: number
  standardDeviation: number
  observations: number
  coefficientOfVariation: number
  quantile10: number
  quantile25: number
  median: number
  quantile75: number
  quantile90: number
  private sortedData: number[]

  constructor(name: string, rawData: number[]) {
    const data = rawData.filter((value) => !isNaN(value))

    this.name = name
    this.observations = data.length
    this.sortedData = [...data].sort((a, b) => a - b)
    this.maximum = this.sortedData[this.observations - 1]
    this.minimum = this.sortedData[0]
    this.arithmeticMean = this.computeArithmeticMean()
    this.standardDeviation = this.computeStandardDeviation()
    this.coefficientOfVariation = this.standardDeviation / this.arithmeticMean
    this.quantile10 = this.computeQuantile(0.1)
    this.quantile25 = this.computeQuantile(0.25)
    this.median = this.computeQuantile(0.5)
    this.quantile75 = this.computeQuantile(0.75)
    this.quantile90 = this.computeQuantile(0.9)
  }

  private computeArithmeticMean(): number {
    const sum = this.sortedData.reduce((a, b) => a + b, 0)
    return sum / this.observations
  }

  private computeStandardDeviation(): number {
    if (this.observations === 0) return NaN
    return Math.sqrt(
      this.sortedData
        .map((x) => Math.pow(x - this.arithmeticMean, 2))
        .reduce((a, b) => a + b) / this.observations
    )
  }

  private computeQuantile(quantile: number): number {
    const position = (this.sortedData.length - 1) * quantile
    const lowerIndex = Math.floor(position)
    const upperIndex = Math.ceil(position)

    // If the position is an integer, return the value at that position.
    // This will also handle array of length: 0 or 1.
    if (lowerIndex === upperIndex) return this.sortedData[lowerIndex]

    // Perform linear interpolation between the two surrounding values
    const lowerValue = this.sortedData[lowerIndex]
    const upperValue = this.sortedData[upperIndex]
    const t = position - lowerIndex
    return lowerValue + t * (upperValue - lowerValue)
  }
}

export const calculateSummaryStatistics = (seriesArray: GraphSeries[]) =>
  seriesArray.map(
    (series) =>
      new SummaryStatistics(
        series.name,
        series.data.map((dp) => dp.value)
      )
  )
