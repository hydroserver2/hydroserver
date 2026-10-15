import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'
import { createTestPinia } from '@/utils/test/pinia'
import { useQcSessionStore } from '@/store/qcSession'
import { useEditLock } from '@/composables/useEditLock'

const previewIndex = ref<number | null>(null)
vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ previewIndex }),
}))

const session = (id: string, status: 'committed' | 'in_progress') =>
  ({
    id,
    status,
    phenomenonTimeStart: '2025-01-01T00:00:00Z',
    phenomenonTimeEnd: '2025-02-01T00:00:00Z',
    createdAt: '2025-01-01T00:00:00Z',
    committedAt: status === 'committed' ? '2025-02-01T00:00:00Z' : null,
  }) as any

beforeEach(() => {
  createTestPinia()
  previewIndex.value = null
})

describe('useEditLock', () => {
  it('is unlocked on the in-progress session', () => {
    useQcSessionStore().applySessions('h', [session('a', 'in_progress')])
    expect(useEditLock().editLock.value).toBeNull()
  })

  it('is unlocked outside the session workflow', () => {
    expect(useEditLock().editLock.value).toBeNull()
  })

  it('locks as preview while an earlier step is shown', () => {
    previewIndex.value = 0
    expect(useEditLock().editLock.value).toBe('preview')
  })

  it('locks as read-only once the only session is committed', () => {
    useQcSessionStore().applySessions('h', [session('a', 'committed')])
    expect(useEditLock().editLock.value).toBe('readOnly')
  })

  it('locks as read-only when viewing a committed session, even mid-preview', () => {
    const store = useQcSessionStore()
    store.applySessions('h', [
      session('a', 'committed'),
      session('b', 'in_progress'),
    ])
    store.viewSession('a')
    previewIndex.value = 0
    expect(useEditLock().editLock.value).toBe('readOnly')
  })
})
