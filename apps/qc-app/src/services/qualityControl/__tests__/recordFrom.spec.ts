import { describe, it, expect } from 'vitest'
import { recordFrom } from '../recordFrom'

describe('recordFrom', () => {
  it('holds its own copy of the data', async () => {
    const datetimes = [1, 2, 3]
    const dataValues = [10, 20, 30]

    const record = await recordFrom(datetimes, dataValues)

    expect(Array.from(record.dataX)).toEqual([1, 2, 3])
    expect(Array.from(record.dataY)).toEqual([10, 20, 30])
    expect(record.history).toHaveLength(0)
    record.dataY[0] = 99
    expect(dataValues[0]).toBe(10)
  })

  it('keeps values at full precision', async () => {
    const record = await recordFrom([1, 2], [12.34, 0.1])

    expect(Array.from(record.dataY)).toEqual([12.34, 0.1])
  })
})
