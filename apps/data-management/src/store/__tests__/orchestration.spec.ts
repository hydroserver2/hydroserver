import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { useOrchestrationStore } from '../orchestration'
import { useWorkspaceStore } from '../workspaces'

const {
  listAllItemsMock,
  taskListAllItemsMock,
  productTaskListAllItemsMock,
  listMappingsMock,
  listTransformationsMock,
} = vi.hoisted(() => ({
  listAllItemsMock: vi.fn(),
  taskListAllItemsMock: vi.fn(),
  productTaskListAllItemsMock: vi.fn(),
  listMappingsMock: vi.fn(),
  listTransformationsMock: vi.fn(),
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
      tasks: {
        listAllItems: taskListAllItemsMock,
        listMappings: listMappingsMock,
      },
      dataProductTasks: {
        listAllItems: productTaskListAllItemsMock,
        listTransformations: listTransformationsMock,
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
    taskListAllItemsMock.mockReset()
    productTaskListAllItemsMock.mockReset()
    listMappingsMock.mockReset()
    listTransformationsMock.mockReset()
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

  it('loads linked destinations across ingestion and data product tasks, fetching mappings/transformations only for tasks that have them', async () => {
    taskListAllItemsMock.mockResolvedValue([
      { id: 'etl-task-1', mappingCount: 2 },
      { id: 'etl-task-2', mappingCount: 0 },
    ])
    listMappingsMock.mockResolvedValue({
      ok: true,
      data: [
        { targetDatastreamId: 'etl-1' },
        { targetDatastreamId: 'etl-2' },
      ],
    })
    productTaskListAllItemsMock.mockResolvedValue([
      { id: 'product-task-1', transformationTypes: ['aggregation', 'rating_curve'] },
      { id: 'product-task-2', transformationTypes: [] },
    ])
    listTransformationsMock.mockResolvedValue({
      ok: true,
      data: [
        { outputDatastreamId: 'aggregation-output' },
        { outputDatastreamId: 'rating-curve-output' },
      ],
    })

    const orchestrationStore = useOrchestrationStore()
    await orchestrationStore.ensureWorkspaceLinkedDatastreams('workspace-1')

    expect([...orchestrationStore.linkedDatastreamIds]).toEqual([
      'etl-1',
      'etl-2',
      'aggregation-output',
      'rating-curve-output',
    ])
    expect(taskListAllItemsMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
    })
    expect(productTaskListAllItemsMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
    })
    expect(listMappingsMock).toHaveBeenCalledWith('etl-task-1')
    expect(listMappingsMock).not.toHaveBeenCalledWith('etl-task-2')
    expect(listTransformationsMock).toHaveBeenCalledWith('product-task-1')
    expect(listTransformationsMock).not.toHaveBeenCalledWith('product-task-2')
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

    listAllItemsMock.mockImplementation(({ workspace_id }: any) => {
      const workspaceId = Array.isArray(workspace_id)
        ? workspace_id[0]
        : workspace_id
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
      workspace_id: ['workspace-2'],
      expand_related: true,
    })

    workspaceOneRequest.resolve([{ id: 'ds-1', name: 'Datastream 1' }])
    await workspaceOneLoad

    expect(orchestrationStore.workspaceDatastreams.map((d) => d.id)).toEqual([
      'ds-2',
    ])
  })
})
