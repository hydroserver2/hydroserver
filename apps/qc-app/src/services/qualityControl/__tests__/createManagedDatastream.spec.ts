import { describe, it, expect, vi } from 'vitest'
import type { Datastream, HydroServer } from '@hydroserver/client'
import { makeQcFake } from './qcServiceFake'
import {
  SOURCE_TAG_KEY,
  buildManagedDatastreamBody,
  createManagedDatastream,
} from '../createManagedDatastream'
import { unwrap } from '../unwrap'

const makeSource = (overrides: Partial<Datastream> = {}): Datastream =>
  ({
    id: 'source-1',
    workspaceId: 'ws-1',
    name: 'Raw Temperature',
    description: 'raw sensor data',
    thingId: 'thing-1',
    observationType: 'OM_Measurement',
    sampledMedium: 'Air',
    noDataValue: -9999,
    aggregationStatistic: 'Continuous',
    unitId: 'unit-1',
    observedPropertyId: 'op-1',
    sensorId: 'sensor-1',
    processingLevelId: 'pl-raw',
    isPrivate: false,
    isVisible: true,
    timeAggregationInterval: null,
    valueCount: 1000,
    phenomenonBeginTime: '2024-01-01T00:00:00Z',
    phenomenonEndTime: '2024-02-01T00:00:00Z',
    ...overrides,
  }) as unknown as Datastream

const makeHs = (
  created: Datastream | null,
  { ok = true, status = 201, message = '' } = {}
) => {
  const create = vi.fn().mockResolvedValue({ data: created, ok, status, message })
  const createTag = vi.fn().mockResolvedValue({})
  const hs = { datastreams: { create, createTag } } as unknown as HydroServer
  return { hs, create, createTag }
}

describe('buildManagedDatastreamBody', () => {
  it('copies source metadata, starts empty, applies the new processing level', () => {
    const body = buildManagedDatastreamBody(makeSource(), 'pl-qc')
    expect(body.id).toBe('')
    expect(body.processingLevelId).toBe('pl-qc')
    expect(body.valueCount).toBe(0)
    expect(body.phenomenonBeginTime).toBeNull()
    expect(body.phenomenonEndTime).toBeNull()
    // metadata carried over from source
    expect(body.thingId).toBe('thing-1')
    expect(body.unitId).toBe('unit-1')
    expect(body.observedPropertyId).toBe('op-1')
    expect(body.sensorId).toBe('sensor-1')
  })

  it('applies overrides last', () => {
    const body = buildManagedDatastreamBody(makeSource(), 'pl-qc', {
      name: 'QC Temperature',
    })
    expect(body.name).toBe('QC Temperature')
  })

  it('extracts flat ids from an expand_related (nested) source', () => {
    const nested = {
      id: 's-1',
      name: 'Raw',
      thing: { id: 'thing-x' },
      unit: { id: 'unit-x' },
      observedProperty: { id: 'op-x' },
      sensor: { id: 'sensor-x' },
      processingLevel: { id: 'pl-raw' },
      workspace: { id: 'ws-x' },
    } as any
    const body = buildManagedDatastreamBody(nested, 'pl-qc')
    expect(body.thingId).toBe('thing-x')
    expect(body.unitId).toBe('unit-x')
    expect(body.observedPropertyId).toBe('op-x')
    expect(body.sensorId).toBe('sensor-x')
    expect(body.processingLevelId).toBe('pl-qc')
  })
})

describe('createManagedDatastream', () => {
  it('creates the datastream, the history, and tags the source', async () => {
    const source = makeSource()
    const created = makeSource({ id: 'managed-1', processingLevelId: 'pl-qc', valueCount: 0 })
    const { hs, create, createTag } = makeHs(created)
    const qc = makeQcFake()

    const result = await createManagedDatastream(hs, qc.histories, {
      source,
      processingLevelId: 'pl-qc',
    })

    // datastream created from source metadata, empty, new processing level
    const body = create.mock.calls[0][0] as Datastream
    expect(body.processingLevelId).toBe('pl-qc')
    expect(body.valueCount).toBe(0)
    expect(body.thingId).toBe('thing-1')

    // history links source and managed, and is persisted in the client
    expect(result.history.managedDatastream.id).toBe('managed-1')
    expect(result.history.sourceDatastream.id).toBe('source-1')
    expect(unwrap(await qc.histories.list())).toHaveLength(1)

    // source datastream tagged with the managed id
    expect(createTag).toHaveBeenCalledWith('source-1', {
      key: SOURCE_TAG_KEY,
      value: 'managed-1',
    })
  })

  it('requests the expanded datastream so the catalog keeps its nested relations', async () => {
    // The data-vis catalog is loaded with `expand_related`, and its consumers
    // read `ds.processingLevel.id` / `ds.thing.id`. A flat create response
    // appended to that list would blow up on the missing nested objects.
    const created = {
      id: 'managed-1',
      name: 'Raw Temperature (QC)',
      thing: { id: 'thing-1' },
      observedProperty: { id: 'op-1' },
      processingLevel: { id: 'pl-qc' },
    } as any
    const { hs, create } = makeHs(created)
    const qc = makeQcFake()

    const result = await createManagedDatastream(hs, qc.histories, {
      source: makeSource(),
      processingLevelId: 'pl-qc',
    })

    expect(create.mock.calls[0][1]).toEqual({ expand_related: true })
    expect(result.managedDatastream.processingLevel.id).toBe('pl-qc')
    expect(result.managedDatastream.thing.id).toBe('thing-1')
  })

  it('rejects a processing level equal to the source', async () => {
    const { hs } = makeHs(makeSource({ id: 'managed-1' }))
    const qc = makeQcFake()
    await expect(
      createManagedDatastream(hs, qc.histories, {
        source: makeSource(),
        processingLevelId: 'pl-raw',
      })
    ).rejects.toThrow(/different processing level/)
  })

  it('rejects a processing level equal to a nested source level', async () => {
    const { hs } = makeHs(makeSource({ id: 'managed-1' }))
    const qc = makeQcFake()
    const nestedSource = { id: 's-1', name: 'Raw', processingLevel: { id: 'pl-raw' } } as any
    await expect(
      createManagedDatastream(hs, qc.histories, {
        source: nestedSource,
        processingLevelId: 'pl-raw',
      })
    ).rejects.toThrow(/different processing level/)
  })

  it('rejects a missing processing level', async () => {
    const { hs } = makeHs(makeSource({ id: 'managed-1' }))
    const qc = makeQcFake()
    await expect(
      createManagedDatastream(hs, qc.histories, {
        source: makeSource(),
        processingLevelId: '',
      })
    ).rejects.toThrow(/processing level is required/)
  })

  it('surfaces the backend error when creation fails or returns no id', async () => {
    const qc = makeQcFake()
    await expect(
      createManagedDatastream(
        makeHs(null, { ok: false, status: 403, message: 'Forbidden' }).hs,
        qc.histories,
        { source: makeSource(), processingLevelId: 'pl-qc' }
      )
    ).rejects.toThrow(/HTTP 403.*Forbidden/)
    await expect(
      createManagedDatastream(makeHs({ name: 'no-id' } as any).hs, qc.histories, {
        source: makeSource(),
        processingLevelId: 'pl-qc',
      })
    ).rejects.toThrow(/Datastream creation failed/)
  })
})
