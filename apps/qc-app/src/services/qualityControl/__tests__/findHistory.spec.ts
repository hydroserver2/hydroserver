import { describe, it, expect } from 'vitest'
import { createHistory, makeQcFake } from './qcServiceFake'
import { findHistoryForDatastream } from '../findHistory'

describe('findHistoryForDatastream', () => {
  it('returns the history for a managed datastream', async () => {
    const qc = makeQcFake()
    const h = await createHistory(qc, {
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
    const found = await findHistoryForDatastream(qc.histories, 'm-1')
    expect(found?.id).toBe(h.id)
    expect(found?.managedDatastreamId).toBe('m-1')
    expect(found?.sourceDatastreamId).toBe('s-1')
  })

  it('returns null when the datastream has no history', async () => {
    const qc = makeQcFake()
    expect(await findHistoryForDatastream(qc.histories, 'nope')).toBeNull()
  })
})
