import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { computed } from 'vue'
import { setActivePinia, createPinia, getActivePinia, defineStore } from 'pinia'

const { selectedWorkspaceId, hsRef, mockList, mockCreate } = vi.hoisted(() => {
  const { ref } = require('vue') as typeof import('vue')
  const mockList = { fn: (..._: any[]) => Promise.resolve({ data: [] as any[] }) }
  const mockCreate = { fn: (..._: any[]) => Promise.resolve({ data: null as any }) }
  const hsRef = ref<any>({
    resultQualifiers: {
      list: (...args: any[]) => mockList.fn(...args),
      create: (...args: any[]) => mockCreate.fn(...args),
    },
  })
  return {
    selectedWorkspaceId: ref<string | null>(null),
    hsRef,
    mockList,
    mockCreate,
  }
})

vi.mock('@hydroserver/client', () => ({
  ResultQualifier: class {
    code = ''
    description = ''
    workspaceId = ''
  },
}))

vi.mock('@/store/hydroserver', () => ({
  useHydroServer: () => ({ hs: hsRef }),
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
  vi.resetModules()
  setActivePinia(createPinia())
  selectedWorkspaceId.value = null
  mockList.fn = () => Promise.resolve({ data: [] })
  mockCreate.fn = () => Promise.resolve({ data: null })
  vi.clearAllMocks()
})

afterEach(() => {
  // `_s` is Pinia's internal store-registry Map; the published `Pinia`
  // type doesn't expose it but it's stable across versions and is the
  // canonical way to tear down all stores between tests.
  ;(getActivePinia() as unknown as
    | { _s?: Map<string, { $dispose: () => void }> }
    | undefined
  )?._s?.forEach((store) => store.$dispose())
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

  it('is idempotent for the same pair', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1'], 'u')
    store.applyQualifiers('ds-1', [5], ['q-1'], 'u')
    expect(store.applied['ds-1'][5]).toHaveLength(1)
  })

  it('creates cartesian entries for multiple indices and qualifiers', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [1, 2], ['q-1', 'q-2'], 'u')
    expect(store.applied['ds-1'][1]).toHaveLength(2)
    expect(store.applied['ds-1'][2]).toHaveLength(2)
    expect(
      store.applied['ds-1'][1].map((a: any) => a.qualifierId).sort()
    ).toEqual(['q-1', 'q-2'])
  })

  it('no-ops on empty args', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('', [1], ['q-1'], 'u')
    store.applyQualifiers('ds', [], ['q-1'], 'u')
    store.applyQualifiers('ds', [1], [], 'u')
    expect(store.applied).toEqual({})
  })

  it('appends a new qualifier to an existing index', async () => {
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
  it('returns empty array for unknown datastream', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    expect(store.getApplicationsForDatastream('missing')).toEqual([])
  })

  it('flattens the nested structure into rows', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [1, 2], ['q-1', 'q-2'], 'u')
    const out = store.getApplicationsForDatastream('ds-1')
    expect(out).toHaveLength(4)
    const keyed = out.map((o) => String(o.index) + ':' + o.qualifierId).sort()
    expect(keyed).toEqual(['1:q-1', '1:q-2', '2:q-1', '2:q-2'])
  })
})

describe('useQualifierStore.getApplicationsAtIndex', () => {
  it('returns the slice for the requested index', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.applyQualifiers('ds-1', [5], ['q-1', 'q-2'], 'u')
    expect(store.getApplicationsAtIndex('ds-1', 5)).toHaveLength(2)
  })

  it('returns empty array when nothing applied at index', async () => {
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

describe('useQualifierStore.loadQualifiers', () => {
  let consoleErrSpy: ReturnType<typeof vi.spyOn>
  beforeEach(() => { consoleErrSpy = vi.spyOn(console, 'error').mockImplementation(() => {}) })
  afterEach(() => { consoleErrSpy.mockRestore() })

  it('clears qualifiers and returns early when no workspace selected', async () => {
    selectedWorkspaceId.value = null
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.qualifiers = [{ id: 'x', code: 'X', description: '' }]
    await store.loadQualifiers()
    expect(store.qualifiers).toEqual([])
  })

  it('populates qualifiers from hs.resultQualifiers.list', async () => {
    mockList.fn = () =>
      Promise.resolve({
        data: [
          { id: 'q-1', code: 'A', description: 'a', workspaceId: 'ws-1' },
          { id: 'q-2', code: 'B', description: 'b', workspaceId: 'ws-1' },
        ],
      })
    selectedWorkspaceId.value = 'ws-1'
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    await store.loadQualifiers()
    expect(store.qualifiers.map((q: any) => q.id).sort()).toEqual([
      'q-1',
      'q-2',
    ])
  })

  it('handles thrown errors gracefully and resets isLoading', async () => {
    mockList.fn = () => Promise.reject(new Error('network'))
    selectedWorkspaceId.value = 'ws-1'
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    await store.loadQualifiers()
    expect(store.isLoading).toBe(false)
  })
})

describe('useQualifierStore.createQualifier', () => {
  let consoleErrSpy: ReturnType<typeof vi.spyOn>
  beforeEach(() => { consoleErrSpy = vi.spyOn(console, 'error').mockImplementation(() => {}) })
  afterEach(() => { consoleErrSpy.mockRestore() })

  it('returns existing qualifier by case-insensitive code match', async () => {
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    store.qualifiers = [{ id: 'q-1', code: 'Foo', description: 'existing' }]
    const result = await store.createQualifier('FOO', 'new desc')
    expect(result.id).toBe('q-1')
    expect(store.qualifiers).toHaveLength(1)
  })

  it('creates via server and pushes the saved qualifier', async () => {
    mockCreate.fn = () =>
      Promise.resolve({
        data: {
          id: 'q-new',
          code: 'NEW',
          description: 'd',
          workspaceId: 'ws-1',
        },
      })
    selectedWorkspaceId.value = 'ws-1'
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    const result = await store.createQualifier('NEW', 'd')
    expect(result.id).toBe('q-new')
    expect(store.qualifiers.find((q: any) => q.id === 'q-new')).toBeTruthy()
  })

  it('falls back to local record when no workspace is selected', async () => {
    selectedWorkspaceId.value = null
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    const result = await store.createQualifier('LOCAL', 'desc')
    expect(result.code).toBe('LOCAL')
    expect(result.id).toMatch(/^local-/)
    expect(store.qualifiers.find((q: any) => q.code === 'LOCAL')).toBeTruthy()
  })

  it('falls back to local record when server throws', async () => {
    mockCreate.fn = () => Promise.reject(new Error('boom'))
    selectedWorkspaceId.value = 'ws-1'
    const { useQualifierStore } = await import('@/store/qualifiers')
    const store = useQualifierStore()
    const result = await store.createQualifier('LOCALERR', 'desc')
    expect(result.id).toMatch(/^local-/)
    expect(result.code).toBe('LOCALERR')
  })
})
