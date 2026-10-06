import { describe, it, expect } from 'vitest'
import type {
  QualityControlHistory,
  QualityControlSession,
} from '@hydroserver/client'
import {
  historyManagedId,
  historySourceId,
  sessionOperations,
} from '../qcHistory'

describe('qcHistory ids', () => {
  it('reads the ids of a summary history', () => {
    const h = { id: 'h', managedDatastreamId: 'm', sourceDatastreamId: 's' }
    expect(historyManagedId(h as QualityControlHistory)).toBe('m')
    expect(historySourceId(h as QualityControlHistory)).toBe('s')
  })

  it('reads the ids of a detail history', () => {
    const h = {
      id: 'h',
      managedDatastream: { id: 'm' },
      sourceDatastream: { id: 's' },
    }
    expect(historyManagedId(h as unknown as QualityControlHistory)).toBe('m')
    expect(historySourceId(h as unknown as QualityControlHistory)).toBe('s')
  })
})

describe('sessionOperations', () => {
  it('returns a detail session operations, and none for a summary', () => {
    const detail = { id: 's', operations: [{ id: 'o' }] }
    expect(sessionOperations(detail as unknown as QualityControlSession)).toEqual([
      { id: 'o' },
    ])
    expect(sessionOperations({ id: 's' } as QualityControlSession)).toEqual([])
  })
})
