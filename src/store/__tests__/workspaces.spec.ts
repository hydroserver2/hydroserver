import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

const { hsRef, mockList } = vi.hoisted(() => {
  const { ref } = require('vue') as typeof import('vue')
  const mockList = { fn: (..._: any[]) => Promise.resolve({ data: [] as any[] }) }
  const hsRef = ref<any>({
    workspaces: {
      list: (...args: any[]) => mockList.fn(...args),
    },
  })
  return { hsRef, mockList }
})

vi.mock('@/store/hydroserver', () => ({
  useHydroServer: () => ({ hs: hsRef }),
}))

vi.mock('@uwrl/qc-utils', () => ({}))

const ws = (overrides: Record<string, any> = {}) => ({
  id: 'ws-1',
  name: 'Workspace 1',
  collaboratorRole: null,
  ...overrides,
})

const role = (permissions: Array<{ resource: string; action: string }>) => ({
  collaboratorRole: { permissions },
})

beforeEach(() => {
  setActivePinia(createPinia())
  mockList.fn = () => Promise.resolve({ data: [] })
})

describe('useWorkspaceStore.canEditSelected', () => {
  it('returns false when no workspace is selected', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    expect(store.canEditSelected).toBe(false)
  })

  it('returns true for owner (collaboratorRole is null)', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws() as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with edit on Observation', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: 'edit' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with edit on "*" resource', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: '*', action: 'edit' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with "*" action on Observation', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: '*' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with create on Observation', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: 'create' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns false for collaborator with only view on Observation', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: 'view' }])
    ) as any
    expect(store.canEditSelected).toBe(false)
  })

  it('returns false for collaborator with edit on unrelated resource', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Thing', action: 'edit' }])
    ) as any
    expect(store.canEditSelected).toBe(false)
  })

  it('returns false for collaborator with empty permissions list', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(role([])) as any
    expect(store.canEditSelected).toBe(false)
  })
})

describe('useWorkspaceStore.selectWorkspace', () => {
  it('clears selection when id is null', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws() as any
    expect(store.selectWorkspace(null)).toBeNull()
    expect(store.selectedWorkspace).toBeNull()
  })

  it('sets selection to null for unknown id', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.availableWorkspaces = [ws({ id: 'a' }), ws({ id: 'b' })] as any
    const result = store.selectWorkspace('missing')
    expect(result).toBeNull()
    expect(store.selectedWorkspace).toBeNull()
  })

  it('finds the matching workspace in availableWorkspaces', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    const a = ws({ id: 'a', name: 'A' })
    const b = ws({ id: 'b', name: 'B' })
    store.availableWorkspaces = [a, b] as any
    const result = store.selectWorkspace('b')
    expect(result).toStrictEqual(b)
    expect(store.selectedWorkspace).toStrictEqual(b)
  })
})

describe('useWorkspaceStore.applyWorkspaceById', () => {
  it('returns null for empty id', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    expect(store.applyWorkspaceById('')).toBeNull()
  })

  it('returns the currently selected workspace when id matches', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    const current = ws({ id: 'ws-1' })
    store.selectedWorkspace = current as any
    const result = store.applyWorkspaceById('ws-1')
    expect(result).toStrictEqual(current)
    expect(store.selectedWorkspace).toStrictEqual(current)
  })

  it('sets selection to matching workspace from availableWorkspaces', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    const a = ws({ id: 'a' })
    const b = ws({ id: 'b' })
    store.availableWorkspaces = [a, b] as any
    const result = store.applyWorkspaceById('b')
    expect(result).toStrictEqual(b)
    expect(store.selectedWorkspace).toStrictEqual(b)
  })

  it('falls back to placeholder { id } when not in availableWorkspaces', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.availableWorkspaces = [ws({ id: 'a' })] as any
    const result = store.applyWorkspaceById('unknown')
    expect(result).toEqual({ id: 'unknown' })
    expect(store.selectedWorkspace).toEqual({ id: 'unknown' })
  })
})

describe('useWorkspaceStore.loadWorkspaces', () => {
  it('populates availableWorkspaces from hs.workspaces.list', async () => {
    mockList.fn = () =>
      Promise.resolve({
        data: [ws({ id: 'a' }), ws({ id: 'b' })],
      })
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    const result = await store.loadWorkspaces()
    expect(result.map((w: any) => w.id)).toEqual(['a', 'b'])
    expect(store.availableWorkspaces.map((w: any) => w.id)).toEqual(['a', 'b'])
  })

  it('promotes placeholder selection to full workspace on match', async () => {
    const fullA = ws({ id: 'a', name: 'Workspace A' })
    mockList.fn = () => Promise.resolve({ data: [fullA] })
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = { id: 'a' } as any
    await store.loadWorkspaces()
    expect(store.selectedWorkspace?.name).toBe('Workspace A')
  })

  it('clears selection when stored id is not in non-empty list', async () => {
    mockList.fn = () => Promise.resolve({ data: [ws({ id: 'a' })] })
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = { id: 'gone' } as any
    await store.loadWorkspaces()
    expect(store.selectedWorkspace).toBeNull()
  })

  it('preserves placeholder when list comes back empty', async () => {
    mockList.fn = () => Promise.resolve({ data: [] })
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = { id: 'a' } as any
    await store.loadWorkspaces()
    expect(store.selectedWorkspace?.id).toBe('a')
  })
})

describe('useWorkspaceStore.clearSelection', () => {
  it('resets selectedWorkspace to null', async () => {
    const { useWorkspaceStore } = await import('@/store/workspaces')
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws() as any
    store.clearSelection()
    expect(store.selectedWorkspace).toBeNull()
  })
})
