import { describe, it, expect } from 'vitest'
import { ObservationRecord } from '@uwrl/qc-utils'
import { cloneRecord } from '../cloneRecord'

describe('cloneRecord', () => {
  it('copies the data into an independent record', async () => {
    const original = new ObservationRecord({
      datetimes: [1, 2, 3],
      dataValues: [10, 20, 30],
    })
    await original.reload()

    const copy = await cloneRecord(original)

    expect(copy).not.toBe(original)
    expect(Array.from(copy.dataX)).toEqual([1, 2, 3])
    expect(Array.from(copy.dataY)).toEqual([10, 20, 30])
    expect(copy.history).toHaveLength(0)

    copy.dataY[0] = 99
    expect(original.dataY[0]).toBe(10)
  })
})
