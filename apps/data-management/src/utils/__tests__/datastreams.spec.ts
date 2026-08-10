import { describe, expect, it } from 'vitest'
import {
  datastreamMonitoringSiteId,
  datastreamsForMonitoringSite,
} from '../orchestration/datastreams'

describe('datastream orchestration helpers', () => {
  it('resolves monitoringSite ids from lean or expanded datastreams', () => {
    expect(datastreamMonitoringSiteId({ monitoringSiteId: 'monitoringSite-1' } as any)).toBe('monitoringSite-1')
    expect(datastreamMonitoringSiteId({ monitoring_site_id: 'monitoringSite-snake' } as any)).toBe(
      'monitoringSite-snake'
    )
    expect(datastreamMonitoringSiteId({ monitoringSite: { id: 'monitoringSite-2' } } as any)).toBe(
      'monitoringSite-2'
    )
    expect(datastreamMonitoringSiteId({} as any)).toBe('')
  })

  it('filters datastreams for the selected monitoringSite', () => {
    const datastreams = [
      { id: 'ds-1', monitoringSiteId: 'monitoringSite-1' },
      { id: 'ds-2', monitoringSite: { id: 'monitoringSite-1' } },
      { id: 'ds-snake', monitoring_site_id: 'monitoringSite-1' },
      { id: 'ds-3', monitoringSiteId: 'monitoringSite-2' },
    ] as any[]

    expect(datastreamsForMonitoringSite(datastreams, null)).toEqual([])
    expect(
      datastreamsForMonitoringSite(datastreams, 'monitoringSite-1').map((d) => d.id)
    ).toEqual(['ds-1', 'ds-2', 'ds-snake'])
  })
})
