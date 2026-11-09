import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkspaceCatalog } from '../useWorkspaceCatalog'
import { useHydroServer } from '@/store/hydroserver'
import { useDataVisStore } from '@/store/dataVisualization'

const { snackbarError } = vi.hoisted(() => ({ snackbarError: vi.fn() }))
vi.mock('@uwrl/qc-utils', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@uwrl/qc-utils')>()),
  Snackbar: { error: snackbarError },
}))

const ok = (data: unknown[]) => vi.fn().mockResolvedValue({ ok: true, data })

function setHs(overrides: Record<string, any> = {}) {
  const hs = {
    monitoringSites: { list: ok([{ id: 'site-1' }]) },
    datastreams: { list: ok([{ id: 'ds-1' }]) },
    processingLevels: { list: ok([{ id: 'pl-1' }]) },
    observedProperties: { list: ok([{ id: 'op-1' }]) },
    qualityControlHistories: { list: ok([{ id: 'h-1' }]) },
    ...overrides,
  }
  useHydroServer().hs = hs as any
  return hs
}

describe('useWorkspaceCatalog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    snackbarError.mockClear()
  })

  it('requests every page of each workspace list', async () => {
    const hs = setHs()
    await useWorkspaceCatalog().load('ws-1')

    for (const service of [
      hs.monitoringSites,
      hs.datastreams,
      hs.processingLevels,
      hs.observedProperties,
    ]) {
      expect(service.list.mock.calls[0][0]).toMatchObject({
        workspaceId: 'ws-1',
        fetch_all: true,
      })
    }
    expect(hs.datastreams.list.mock.calls[0][0]).toMatchObject({
      expand_related: true,
    })
    expect(hs.qualityControlHistories.list.mock.calls[0][0]).toEqual({
      fetch_all: true,
    })

    const store = useDataVisStore()
    expect(store.monitoringSites).toEqual([{ id: 'site-1' }])
    expect(store.datastreams).toEqual([{ id: 'ds-1' }])
    expect(store.processingLevels).toEqual([{ id: 'pl-1' }])
    expect(store.observedProperties).toEqual([{ id: 'op-1' }])
    expect(store.qcHistories).toEqual([{ id: 'h-1' }])
    expect(snackbarError).not.toHaveBeenCalled()
  })

  it('says which lists failed to load instead of showing them empty', async () => {
    setHs({
      datastreams: {
        list: vi.fn().mockResolvedValue({ ok: false, status: 500, message: 'boom' }),
      },
      observedProperties: { list: vi.fn().mockRejectedValue(new Error('offline')) },
    })
    await useWorkspaceCatalog().load('ws-1')

    expect(snackbarError).toHaveBeenCalledTimes(1)
    expect(snackbarError.mock.calls[0][0]).toBe(
      "Couldn't load datastreams and observed properties. Reload the page to try again."
    )
    const store = useDataVisStore()
    expect(store.monitoringSites).toEqual([{ id: 'site-1' }])
    expect(store.datastreams).toEqual([])
  })

  it('reports QC histories that fail to load', async () => {
    setHs({
      qualityControlHistories: {
        list: vi.fn().mockResolvedValue({ ok: false, status: 500, message: 'boom' }),
      },
    })
    await useWorkspaceCatalog().load('ws-1')

    expect(snackbarError.mock.calls[0][0]).toBe(
      "Couldn't load QC histories. Reload the page to try again."
    )
    expect(useDataVisStore().qcHistories).toEqual([])
  })

  it('clears the lists', () => {
    setHs()
    const store = useDataVisStore()
    store.datastreams = [{ id: 'old' }] as any
    useWorkspaceCatalog().clear()
    expect(store.datastreams).toEqual([])
    expect(store.monitoringSites).toEqual([])
  })
})
