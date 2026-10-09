import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDatastreamMetadata } from '../useDatastreamMetadata'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'

const methodList = [{ id: 'method-1', name: 'Thermistor' }]
const statusList = [
  { id: 'st-1', name: 'ongoing', description: '' },
  { id: 'st-2', name: 'complete', description: '' },
]

function setHs(listMethods: any, listStatuses: any) {
  useHydroServer().hs = {
    methods: { list: listMethods },
    datastreamStatuses: { list: listStatuses },
  } as any
}

describe('useDatastreamMetadata', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useWorkspaceStore().selectedWorkspace = { id: 'ws-1' } as any
    vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  it('loads the workspace methods and the status vocabulary', async () => {
    const listMethods = vi.fn().mockResolvedValue({ ok: true, data: methodList })
    const listStatuses = vi.fn().mockResolvedValue({ ok: true, data: statusList })
    setHs(listMethods, listStatuses)

    const { methods, statuses, load } = useDatastreamMetadata()
    await load()

    // System-level methods (workspace null) are selectable too, and every
    // page is fetched so a long list is not truncated.
    expect(listMethods.mock.calls[0][0]).toMatchObject({
      workspaceId: ['ws-1', 'null'],
      fetch_all: true,
    })
    expect(methods.value).toEqual(methodList)
    expect(statuses.value).toEqual(['ongoing', 'complete'])
  })

  it('leaves a list empty when its request fails, without throwing', async () => {
    setHs(
      vi.fn().mockRejectedValue(new Error('offline')),
      vi.fn().mockResolvedValue({ ok: false, data: null })
    )

    const { methods, statuses, load } = useDatastreamMetadata()
    await expect(load()).resolves.toBeUndefined()
    expect(methods.value).toEqual([])
    expect(statuses.value).toEqual([])
    expect(console.warn).toHaveBeenCalledTimes(2)
  })

  it('keeps the list that loaded when the other one fails', async () => {
    setHs(
      vi.fn().mockResolvedValue({ ok: false, data: null }),
      vi.fn().mockResolvedValue({ ok: true, data: [statusList[0]] })
    )

    const { methods, statuses, load } = useDatastreamMetadata()
    await load()
    expect(methods.value).toEqual([])
    expect(statuses.value).toEqual(['ongoing'])
  })

  it('loads nothing when no workspace is selected', async () => {
    const listMethods = vi.fn()
    const listStatuses = vi.fn()
    setHs(listMethods, listStatuses)
    useWorkspaceStore().selectedWorkspace = undefined as any

    const { load } = useDatastreamMetadata()
    await load()
    expect(listMethods).not.toHaveBeenCalled()
    expect(listStatuses).not.toHaveBeenCalled()
  })
})
