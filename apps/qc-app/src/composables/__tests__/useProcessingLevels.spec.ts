import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProcessingLevels } from '../useProcessingLevels'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'

function setHs(create: any) {
  useHydroServer().hs = { processingLevels: { create } } as any
}

describe('useProcessingLevels.createProcessingLevel', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('creates a workspace-scoped processing level and returns it', async () => {
    const created = {
      id: 'pl-new',
      workspaceId: 'ws-1',
      code: 'QC',
      name: 'Quality Controlled',
      description: 'Reviewed readings',
      definition: null,
    }
    const create = vi.fn().mockResolvedValue({ ok: true, data: created })
    setHs(create)
    useWorkspaceStore().selectedWorkspace = { id: 'ws-1' } as any

    const { createProcessingLevel } = useProcessingLevels()
    const res = await createProcessingLevel({
      name: 'Quality Controlled',
      description: 'Reviewed readings',
      code: 'QC',
    })

    expect(create).toHaveBeenCalledTimes(1)
    expect(create.mock.calls[0][0]).toMatchObject({
      workspaceId: 'ws-1',
      code: 'QC',
      name: 'Quality Controlled',
      description: 'Reviewed readings',
    })
    expect(res.id).toBe('pl-new')
  })

  it('throws when no workspace is selected', async () => {
    setHs(vi.fn())
    const { createProcessingLevel } = useProcessingLevels()
    await expect(createProcessingLevel({ name: 'QC', description: 'Reviewed' })).rejects.toThrow(
      /workspace/i
    )
  })

  it('throws the server message on failure', async () => {
    setHs(vi.fn().mockResolvedValue({ ok: false, message: 'Code already exists' }))
    useWorkspaceStore().selectedWorkspace = { id: 'ws-1' } as any
    const { createProcessingLevel } = useProcessingLevels()
    await expect(createProcessingLevel({ name: 'QC', description: 'Reviewed' })).rejects.toThrow(
      'Code already exists'
    )
  })
})
