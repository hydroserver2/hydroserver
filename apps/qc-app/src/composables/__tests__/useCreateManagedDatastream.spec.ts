import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { makeQcFake } from '@/services/qualityControl/__tests__/qcServiceFake'
import { unwrap } from '@/services/qualityControl/unwrap'

const hsCreate = vi.fn()
const createTag = vi.fn()
const hs = ref<any>({ datastreams: { create: hsCreate, createTag } })
vi.mock('@/store/hydroserver', () => ({
  useHydroServer: () => ({ hs }),
}))

const makeSource = (overrides: Record<string, unknown> = {}) =>
  ({
    id: 'source-1',
    name: 'Raw',
    processingLevelId: 'pl-raw',
    thingId: 't-1',
    unitId: 'u-1',
    observedPropertyId: 'op-1',
    sensorId: 'sn-1',
    ...overrides,
  }) as any

let qc: ReturnType<typeof makeQcFake>

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  qc = makeQcFake()
  hs.value = {
    datastreams: { create: hsCreate, createTag },
    qualityControlHistories: qc.histories,
    qualityControlSessions: qc.sessions,
    qualityControlOperations: qc.operations,
  }
  hsCreate.mockResolvedValue({
    data: { id: 'managed-1', name: 'Raw (QC)', processingLevelId: 'pl-qc' },
    ok: true,
    status: 201,
    message: '',
  })
  createTag.mockResolvedValue({})
})

describe('useCreateManagedDatastream', () => {
  it('creates the datastream, the history, and tags the source', async () => {
    const { useCreateManagedDatastream } = await import(
      '@/composables/useCreateManagedDatastream'
    )
    const { create } = useCreateManagedDatastream()
    const result = await create({
      source: makeSource(),
      processingLevelId: 'pl-qc',
      name: 'My QC',
    })

    const body = hsCreate.mock.calls[0][0]
    expect(body.processingLevelId).toBe('pl-qc')
    expect(body.name).toBe('My QC')
    expect(body.valueCount).toBe(0)

    expect(result.history.managedDatastream.id).toBe('managed-1')
    expect(unwrap(await qc.histories.list())).toHaveLength(1)

    expect(createTag).toHaveBeenCalledWith(
      'source-1',
      expect.objectContaining({ value: 'managed-1' })
    )
  })
})
