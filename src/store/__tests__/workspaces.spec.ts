import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { useWorkspaceStore } from '@/store/workspaces'

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
  createTestPinia()
})

describe('useWorkspaceStore.canEditSelected', () => {
  it('returns false when no workspace is selected', () => {
    const store = useWorkspaceStore()
    expect(store.canEditSelected).toBe(false)
  })

  it('returns true for owner (collaboratorRole is null)', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws() as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with edit on Observation', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: 'edit' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with edit on "*" resource', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: '*', action: 'edit' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with "*" action on Observation', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: '*' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns true for collaborator with create on Observation', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: 'create' }])
    ) as any
    expect(store.canEditSelected).toBe(true)
  })

  it('returns false for collaborator with only view on Observation', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Observation', action: 'view' }])
    ) as any
    expect(store.canEditSelected).toBe(false)
  })

  it('returns false for collaborator with edit on unrelated resource', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(
      role([{ resource: 'Thing', action: 'edit' }])
    ) as any
    expect(store.canEditSelected).toBe(false)
  })

  it('returns false for collaborator with empty permissions list', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws(role([])) as any
    expect(store.canEditSelected).toBe(false)
  })
})

describe('useWorkspaceStore.selectWorkspace', () => {
  it('clears selection when id is null', () => {
    const store = useWorkspaceStore()
    store.selectedWorkspace = ws() as any
    expect(store.selectWorkspace(null)).toBeNull()
    expect(store.selectedWorkspace).toBeNull()
  })

  it('sets selection to null for unknown id', () => {
    const store = useWorkspaceStore()
    store.availableWorkspaces = [ws({ id: 'a' }), ws({ id: 'b' })] as any
    const result = store.selectWorkspace('missing')
    expect(result).toBeNull()
    expect(store.selectedWorkspace).toBeNull()
  })

  it('finds the matching workspace in availableWorkspaces', () => {
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
  it('returns null for empty id', () => {
    const store = useWorkspaceStore()
    expect(store.applyWorkspaceById('')).toBeNull()
  })

  it('returns the currently selected workspace without mutation when id matches', () => {
    const store = useWorkspaceStore()
    const current = ws({ id: 'ws-1' })
    store.selectedWorkspace = current as any
    const result = store.applyWorkspaceById('ws-1')
    expect(result).toStrictEqual(current)
    expect(store.selectedWorkspace).toStrictEqual(current)
  })

  it('sets selection to matching workspace from availableWorkspaces', () => {
    const store = useWorkspaceStore()
    const a = ws({ id: 'a' })
    const b = ws({ id: 'b' })
    store.availableWorkspaces = [a, b] as any
    const result = store.applyWorkspaceById('b')
    expect(result).toStrictEqual(b)
    expect(store.selectedWorkspace).toStrictEqual(b)
  })

  it('falls back to placeholder { id } when not in availableWorkspaces', () => {
    const store = useWorkspaceStore()
    store.availableWorkspaces = [ws({ id: 'a' })] as any
    const result = store.applyWorkspaceById('unknown')
    expect(result).toEqual({ id: 'unknown' })
    expect(store.selectedWorkspace).toEqual({ id: 'unknown' })
  })
})
