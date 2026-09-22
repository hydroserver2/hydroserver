import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDatastreamMetadata } from '../useDatastreamMetadata'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'

const sensorList = [{ id: 'sn-1', name: 'Thermistor' }]

function setHs(listAllItems: any, getStatuses: any) {
  useHydroServer().hs = {
    sensors: { listAllItems },
    datastreams: { getStatuses },
  } as any
}

describe('useDatastreamMetadata', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useWorkspaceStore().selectedWorkspace = { id: 'ws-1' } as any
    vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  it('loads the workspace sensors and the status vocabulary', async () => {
    const listAllItems = vi.fn().mockResolvedValue(sensorList)
    const getStatuses = vi
      .fn()
      .mockResolvedValue({ ok: true, data: ['ongoing', 'complete'] })
    setHs(listAllItems, getStatuses)

    const { sensors, statuses, load } = useDatastreamMetadata()
    await load()

    // System-level sensors (workspace null) are selectable too, and every
    // page is fetched so a long list is not truncated.
    expect(listAllItems.mock.calls[0][0]).toMatchObject({
      workspace_id: ['ws-1', 'null'],
    })
    expect(sensors.value).toEqual(sensorList)
    expect(statuses.value).toEqual(['ongoing', 'complete'])
  })

  it('leaves a list empty when its request fails, without throwing', async () => {
    setHs(
      vi.fn().mockRejectedValue(new Error('offline')),
      vi.fn().mockResolvedValue({ ok: false, data: null })
    )

    const { sensors, statuses, load } = useDatastreamMetadata()
    await expect(load()).resolves.toBeUndefined()
    expect(sensors.value).toEqual([])
    expect(statuses.value).toEqual([])
    expect(console.warn).toHaveBeenCalledTimes(2)
  })

  it('keeps the list that loaded when the other one fails', async () => {
    setHs(
      vi.fn().mockRejectedValue(new Error('offline')),
      vi.fn().mockResolvedValue({ ok: true, data: ['ongoing'] })
    )

    const { sensors, statuses, load } = useDatastreamMetadata()
    await load()
    expect(sensors.value).toEqual([])
    expect(statuses.value).toEqual(['ongoing'])
  })

  it('loads nothing when no workspace is selected', async () => {
    const listAllItems = vi.fn()
    const getStatuses = vi.fn()
    setHs(listAllItems, getStatuses)
    useWorkspaceStore().selectedWorkspace = undefined as any

    const { load } = useDatastreamMetadata()
    await load()
    expect(listAllItems).not.toHaveBeenCalled()
    expect(getStatuses).not.toHaveBeenCalled()
  })
})
