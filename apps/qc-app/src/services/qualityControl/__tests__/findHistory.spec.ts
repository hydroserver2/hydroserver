import { describe, it, expect } from 'vitest'
import { makeQcFake } from './qcServiceFake'
import { findHistoryForDatastream } from '../findHistory'
import { unwrap } from '../unwrap'

describe('findHistoryForDatastream', () => {
  it('returns the expanded history for a managed datastream', async () => {
    const qc = makeQcFake()
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    const found = await findHistoryForDatastream(qc.histories, 'm-1')
    expect(found?.id).toBe(h.id)
    expect(found?.managedDatastream.id).toBe('m-1')
    expect(found?.sourceDatastream.id).toBe('s-1')
  })

  it('returns null when the datastream has no history', async () => {
    const qc = makeQcFake()
    expect(await findHistoryForDatastream(qc.histories, 'nope')).toBeNull()
  })
})
