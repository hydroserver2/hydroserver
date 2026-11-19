import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { useOrchestrationStore } from '../orchestration'
import { useWorkspaceStore } from '../workspaces'

const {
  listAllItemsMock,
  monitoringSitesListAllItemsMock,
  etlMappingsListAllItemsMock,
  dataProductTransformationsListAllItemsMock,
} = vi.hoisted(() => ({
  listAllItemsMock: vi.fn(),
  monitoringSitesListAllItemsMock: vi.fn(),
  etlMappingsListAllItemsMock: vi.fn(),
  dataProductTransformationsListAllItemsMock: vi.fn(),
}))

vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()

  return {
    ...actual,
    default: {
      ...actual.default,
      datastreams: {
        listAllItems: listAllItemsMock,
      },
      monitoringSites: {
        listAllItems: monitoringSitesListAllItemsMock,
      },
      etlMappings: {
        listAllItems: etlMappingsListAllItemsMock,
      },
      dataProductTransformations: {
        listAllItems: dataProductTransformationsListAllItemsMock,
      },
    },
  }
})

describe('orchestration store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    listAllItemsMock.mockReset()
    monitoringSitesListAllItemsMock.mockReset()
    etlMappingsListAllItemsMock.mockReset()
    dataProductTransformationsListAllItemsMock.mockReset()
  })

  it('does not derive linked datastream ids from workspaceTasks, since task list responses only carry a mapping count, not the mappings themselves', async () => {
    const workspaceStore = useWorkspaceStore()
    workspaceStore.selectedWorkspace = {
      id: 'workspace-1',
      name: 'Workspace 1',
      isPrivate: false,
    } as any

    const orchestrationStore = useOrchestrationStore()
    orchestrationStore.workspaceTasks = [
      { id: 'task-1', dataConnectionId: 'connection-1', mappingCount: 2 },
      { id: 'task-2', dataConnectionId: 'connection-1', mappingCount: 1 },
    ] as any
    orchestrationStore.workspaceDatastreams = [
      { id: 'ds-1', name: 'Datastream 1' },
      { id: 'ds-2', name: 'Datastream 2' },
      { id: 'ds-3', name: 'Datastream 3' },
      { id: 'ds-4', name: 'Datastream 4' },
    ] as any

    await nextTick()

    expect([...orchestrationStore.linkedDatastreamIds]).toEqual([])
    expect(orchestrationStore.linkedDatastreams.map((d) => d.id)).toEqual([])
  })

  it('loads linked destinations across ingestion and data product tasks in one call each', async () => {
    etlMappingsListAllItemsMock.mockResolvedValue([
      { targetDatastreamId: 'etl-1' },
      { targetDatastreamId: 'etl-2' },
    ])
    dataProductTransformationsListAllItemsMock.mockResolvedValue([
      { outputDatastreamId: 'aggregation-output' },
      { outputDatastreamId: 'rating-curve-output' },
    ])

    const orchestrationStore = useOrchestrationStore()
    await orchestrationStore.ensureWorkspaceLinkedDatastreams('workspace-1')

    expect([...orchestrationStore.linkedDatastreamIds]).toEqual([
      'etl-1',
      'etl-2',
      'aggregation-output',
      'rating-curve-output',
    ])
    expect(etlMappingsListAllItemsMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
    })
    expect(dataProductTransformationsListAllItemsMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
    })
    expect(etlMappingsListAllItemsMock).toHaveBeenCalledTimes(1)
    expect(dataProductTransformationsListAllItemsMock).toHaveBeenCalledTimes(1)
  })

  it('recovers from an empty failed load because every call fetches again', async () => {
    listAllItemsMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: 'ds-1', name: 'Datastream 1' }])
    monitoringSitesListAllItemsMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: 'site-1', name: 'Site 1' }])
    const orchestrationStore = useOrchestrationStore()

    await orchestrationStore.ensureWorkspaceDatastreams('workspace-1')
    await orchestrationStore.ensureWorkspaceMonitoringSites('workspace-1')
    expect(orchestrationStore.workspaceDatastreams).toEqual([])
    expect(orchestrationStore.workspaceMonitoringSites).toEqual([])

    await orchestrationStore.ensureWorkspaceDatastreams('workspace-1')
    await orchestrationStore.ensureWorkspaceMonitoringSites('workspace-1')

    expect(orchestrationStore.workspaceDatastreams.map((d) => d.id)).toEqual([
      'ds-1',
    ])
    expect(orchestrationStore.workspaceMonitoringSites.map((s) => s.id)).toEqual(
      ['site-1']
    )
    expect(listAllItemsMock).toHaveBeenCalledTimes(2)
    expect(monitoringSitesListAllItemsMock).toHaveBeenCalledTimes(2)
  })

  it('ignores stale datastream responses after switching workspaces', async () => {
    type Deferred<T> = {
      promise: Promise<T>
      resolve: (value: T) => void
    }

    const deferred = <T>(): Deferred<T> => {
      let resolve!: (value: T) => void
      const promise = new Promise<T>((res) => {
        resolve = res
      })
      return { promise, resolve }
    }

    const workspaceOneRequest = deferred<any[]>()
    const workspaceTwoRequest = deferred<any[]>()

    listAllItemsMock.mockImplementation(({ workspaceId: requested }: any) => {
      const workspaceId = Array.isArray(requested) ? requested[0] : requested
      if (workspaceId === 'workspace-1') return workspaceOneRequest.promise
      if (workspaceId === 'workspace-2') return workspaceTwoRequest.promise
      return Promise.resolve([])
    })

    const workspaceStore = useWorkspaceStore()
    workspaceStore.selectedWorkspace = {
      id: 'workspace-1',
      name: 'Workspace 1',
      isPrivate: false,
    } as any

    const orchestrationStore = useOrchestrationStore()

    const workspaceOneLoad =
      orchestrationStore.ensureWorkspaceDatastreams('workspace-1')

    workspaceStore.selectedWorkspace = {
      id: 'workspace-2',
      name: 'Workspace 2',
      isPrivate: false,
    } as any
    await nextTick()

    const workspaceTwoLoad =
      orchestrationStore.ensureWorkspaceDatastreams('workspace-2')

    workspaceTwoRequest.resolve([{ id: 'ds-2', name: 'Datastream 2' }])
    await workspaceTwoLoad

    expect(orchestrationStore.workspaceDatastreams.map((d) => d.id)).toEqual([
      'ds-2',
    ])
    expect(listAllItemsMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-2'],
      expand_related: true,
    })

    workspaceOneRequest.resolve([{ id: 'ds-1', name: 'Datastream 1' }])
    await workspaceOneLoad

    expect(orchestrationStore.workspaceDatastreams.map((d) => d.id)).toEqual([
      'ds-2',
    ])
  })
})
