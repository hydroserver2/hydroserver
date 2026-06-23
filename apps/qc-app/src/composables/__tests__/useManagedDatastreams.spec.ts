import { describe, it, expect, vi, beforeEach } from 'vitest'

const datastreams = [
  { id: 'mgd-1', name: 'Temp (QC)' },
  { id: 'mgd-2', name: 'Temp (QC v2)' },
]
const historiesBySource = new Map<string, any[]>()
const listAllItems = vi.fn()
const deleteHistory = vi.fn()
const deleteDatastream = vi.fn()

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ datastreams, historiesBySource }),
}))
vi.mock('@/store/hydroserver', () => ({
  useHydroServer: () => ({
    hs: {
      qualityControlSessions: { listAllItems },
      qualityControlHistories: { delete: deleteHistory },
      datastreams: { delete: deleteDatastream },
    },
  }),
}))

import { useManagedDatastreams } from '../useManagedDatastreams'

beforeEach(() => {
  vi.clearAllMocks()
  historiesBySource.clear()
})

describe('useManagedDatastreams.loadForSource', () => {
  it('resolves managed datastreams and their sessions for a source', async () => {
    historiesBySource.set('src-1', [
      { id: 'h-1', managedDatastreamId: 'mgd-1', sourceDatastreamId: 'src-1' },
      { id: 'h-2', managedDatastreamId: 'mgd-2', sourceDatastreamId: 'src-1' },
    ])
    listAllItems.mockImplementation(async (historyId: string) =>
      historyId === 'h-1'
        ? [{ id: 's-1', status: 'in_progress' }]
        : [{ id: 's-2', status: 'committed' }]
    )

    const { loadForSource } = useManagedDatastreams()
    const options = await loadForSource('src-1')

    expect(options).toHaveLength(2)
    expect(options[0]).toMatchObject({
      historyId: 'h-1',
      managed: { id: 'mgd-1', name: 'Temp (QC)' },
    })
    expect(options[0].sessions).toEqual([{ id: 's-1', status: 'in_progress' }])
    expect(options[1].managed.id).toBe('mgd-2')
    expect(options[1].sessions[0].status).toBe('committed')
  })

  it('returns an empty list when the source has no managed datastreams', async () => {
    const { loadForSource } = useManagedDatastreams()
    expect(await loadForSource('unknown')).toEqual([])
    expect(listAllItems).not.toHaveBeenCalled()
  })

  it('falls back to a stub when the managed datastream is not in the catalog', async () => {
    historiesBySource.set('src-2', [
      {
        id: 'h-9',
        managedDatastreamId: 'mgd-missing',
        managedDatastream: { name: 'Orphan (QC)' },
        sourceDatastreamId: 'src-2',
      },
    ])
    listAllItems.mockResolvedValue([])
    const { loadForSource } = useManagedDatastreams()
    const options = await loadForSource('src-2')
    expect(options[0].managed).toEqual({ id: 'mgd-missing', name: 'Orphan (QC)' })
  })

  it('deleteManaged removes the history then the datastream', async () => {
    deleteHistory.mockResolvedValue({ ok: true })
    deleteDatastream.mockResolvedValue({ ok: true })
    const { deleteManaged } = useManagedDatastreams()
    await deleteManaged('h-1', 'mgd-1')
    expect(deleteHistory).toHaveBeenCalledWith('h-1')
    expect(deleteDatastream).toHaveBeenCalledWith('mgd-1')
  })

  it('deleteManaged throws and skips the datastream when the history delete fails', async () => {
    deleteHistory.mockResolvedValue({ ok: false, message: 'history busy' })
    const { deleteManaged } = useManagedDatastreams()
    await expect(deleteManaged('h-1', 'mgd-1')).rejects.toThrow('history busy')
    expect(deleteDatastream).not.toHaveBeenCalled()
  })
})
