import { describe, it, expect } from 'vitest'
import type {
  QualityControlHistory,
  QualityControlSession,
} from '@hydroserver/client'
import {
  historyManagedId,
  historySourceId,
  sessionOperations,
  type QcSession,
} from '../qcHistory'

describe('qcHistory ids', () => {
  it('reads the ids of a history', () => {
    const h = { id: 'h', managedDatastreamId: 'm', sourceDatastreamId: 's' }
    expect(historyManagedId(h as QualityControlHistory)).toBe('m')
    expect(historySourceId(h as QualityControlHistory)).toBe('s')
  })
})

describe('sessionOperations', () => {
  it('returns a loaded session operations, and none for a bare session', () => {
    const loaded = { id: 's', operations: [{ id: 'o' }] }
    expect(sessionOperations(loaded as unknown as QcSession)).toEqual([
      { id: 'o' },
    ])
    expect(sessionOperations({ id: 's' } as QualityControlSession)).toEqual([])
  })
})
