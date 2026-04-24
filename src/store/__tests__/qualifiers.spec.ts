import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref, computed } from 'vue'
import { setActivePinia, createPinia, defineStore } from 'pinia'

const { selectedWorkspaceId } = vi.hoisted(() => {
  const { ref } = require('vue') as typeof import('vue')
  return { selectedWorkspaceId: ref<string | null>(null) }
})

vi.mock('@/store/hydroserver', () => ({
  useHydroServer: () => ({ hs: ref(null) }),
}))

vi.mock('@/store/workspaces', () => {
  const useWorkspaceStore = defineStore('workspaces', () => {
    const selectedWorkspaceIdRef = computed(() => selectedWorkspaceId.value)
    return { selectedWorkspaceId: selectedWorkspaceIdRef }
  })
  return { useWorkspaceStore }
})

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    plotlyRef: null,
    updateOptions: vi.fn(),
  }),
}))

vi.mock('@/utils/plotting/plotly', () => ({
  handleNewPlot: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@uwrl/qc-utils', () => ({}))

beforeEach(() => {
  setActivePinia(createPinia())
  selectedWorkspaceId.value = null
  vi.clearAllMocks()
})

describe('useQualifierStore.applyQualifiers', () => {
  it('adds entries for a single index and qualifier', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1'], 'user@test')
    expect(store.applied['ds-1'][5]).toHaveLength(1)
    expect(store.applied['ds-1'][5][0].qualifierId).toBe('q-1')
    expect(store.applied['ds-1'][5][0].appliedBy).toBe('user@test')
  })

  it('is idempotent for the same (index, qualifierId) pair', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1'], 'u')
    store.applyQualifiers('ds-1', [5], ['q-1'], 'u')
    expect(store.applied['ds-1'][5]).toHaveLength(1)
  })

  it('creates cartesian entries for multiple indices and multiple qualifiers', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [1, 2], ['q-1', 'q-2'], 'u')
    expect(store.applied['ds-1'][1]).toHaveLength(2)
    expect(store.applied['ds-1'][2]).toHaveLength(2)
    expect(
      store.applied['ds-1'][1].map((a: any) => a.qualifierId).sort()
    ).toEqual(['q-1', 'q-2'])
  })

  it('no-ops when datastreamId, indices, or qualifierIds are empty', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('', [1], ['q-1'], 'u')
    store.applyQualifiers('ds', [], ['q-1'], 'u')
    store.applyQualifiers('ds', [1], [], 'u')
    expect(store.applied).toEqual({})
  })

  it('appends a new qualifier to an existing index without duplicating existing one', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1'], 'u')
    store.applyQualifiers('ds-1', [5], ['q-1', 'q-2'], 'u')
    expect(store.applied['ds-1'][5]).toHaveLength(2)
  })
})

describe('useQualifierStore.removeQualifier', () => {
  it('removes a specific qualifier from the index entry', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1', 'q-2'], 'u')
    store.removeQualifier('ds-1', 5, 'q-1')
    expect(store.applied['ds-1'][5]).toHaveLength(1)
    expect(store.applied['ds-1'][5][0].qualifierId).toBe('q-2')
  })

  it('deletes the index key when the last qualifier is removed', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1'], 'u')
    store.removeQualifier('ds-1', 5, 'q-1')
    expect(store.applied['ds-1'][5]).toBeUndefined()
  })

  it('is a no-op for unknown datastream or index', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1'], 'u')
    store.removeQualifier('other', 5, 'q-1')
    store.removeQualifier('ds-1', 99, 'q-1')
    expect(store.applied['ds-1'][5]).toHaveLength(1)
  })
})

describe('useQualifierStore.getApplicationsForDatastream', () => {
  it('returns an empty array for unknown datastream', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    expect(store.getApplicationsForDatastream('missing')).toEqual([])
  })

  it('flattens the nested structure into (index, qualifierId) rows', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [1, 2], ['q-1', 'q-2'], 'u')
    const out = store.getApplicationsForDatastream('ds-1')
    expect(out).toHaveLength(4)
    const keyed = out
      .map((o) => `${o.index}:${o.qualifierId}`)
      .sort()
    expect(keyed).toEqual(['1:q-1', '1:q-2', '2:q-1', '2:q-2'])
  })
})

describe('useQualifierStore.getApplicationsAtIndex', () => {
  it('returns the slice for the requested index', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1', 'q-2'], 'u')
    const apps = store.getApplicationsAtIndex('ds-1', 5)
    expect(apps).toHaveLength(2)
  })

  it('returns an empty array when nothing is applied at that index', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    expect(store.getApplicationsAtIndex('ds-1', 5)).toEqual([])
  })
})

describe('useQualifierStore.qualifierById', () => {
  it('returns a lookup keyed by id', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.qualifiers = [
      { id: 'q-1', code: 'A', description: 'a' },
      { id: 'q-2', code: 'B', description: 'b' },
    ]
    expect(store.qualifierById['q-1'].code).toBe('A')
    expect(store.qualifierById['q-2'].code).toBe('B')
  })

  it('returns undefined for unknown id', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    expect(store.qualifierById['missing']).toBeUndefined()
  })
})
