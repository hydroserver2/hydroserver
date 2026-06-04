import { describe, expect, it } from 'vitest'
import {
  datastreamThingId,
  datastreamsForThing,
} from '../orchestration/datastreams'

describe('datastream orchestration helpers', () => {
  it('resolves thing ids from lean or expanded datastreams', () => {
    expect(datastreamThingId({ thingId: 'thing-1' } as any)).toBe('thing-1')
    expect(datastreamThingId({ thing: { id: 'thing-2' } } as any)).toBe(
      'thing-2'
    )
    expect(datastreamThingId({} as any)).toBe('')
  })

  it('filters datastreams for the selected thing', () => {
    const datastreams = [
      { id: 'ds-1', thingId: 'thing-1' },
      { id: 'ds-2', thing: { id: 'thing-1' } },
      { id: 'ds-3', thingId: 'thing-2' },
    ] as any[]

    expect(datastreamsForThing(datastreams, null)).toEqual([])
    expect(datastreamsForThing(datastreams, 'thing-1').map((d) => d.id)).toEqual([
      'ds-1',
      'ds-2',
    ])
  })
})
