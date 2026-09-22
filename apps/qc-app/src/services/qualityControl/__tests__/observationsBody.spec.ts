import { describe, it, expect } from 'vitest'
import { observationsBulkBody } from '../observationsBody'

describe('observationsBulkBody', () => {
  it('serializes dataX/dataY into a replace-mode bulk body', () => {
    const body = observationsBulkBody({
      dataX: [Date.UTC(2025, 0, 1), Date.UTC(2025, 0, 1, 1)],
      dataY: [10, 20],
    })
    expect(body.fields).toEqual(['phenomenonTime', 'result'])
    expect(body.data).toEqual([
      ['2025-01-01T00:00:00.000Z', 10],
      ['2025-01-01T01:00:00.000Z', 20],
    ])
  })

  it('handles an empty record', () => {
    expect(observationsBulkBody({ dataX: [], dataY: [] }).data).toEqual([])
  })
})
