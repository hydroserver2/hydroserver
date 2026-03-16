import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { useOrchestrationStore } from '../orchestration'
import { useWorkspaceStore } from '../workspaces'

const { listAllItemsMock } = vi.hoisted(() => ({
  listAllItemsMock: vi.fn(),
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
    },
  }
})

describe('orchestration store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    listAllItemsMock.mockReset()
  })

  it('derives linked datastream ids from lean task target identifiers', async () => {
    const workspaceStore = useWorkspaceStore()
    workspaceStore.selectedWorkspace = {
      id: 'workspace-1',
      name: 'Workspace 1',
      isPrivate: false,
    } as any

    const orchestrationStore = useOrchestrationStore()
    orchestrationStore.workspaceTasks = [
      {
        id: 'task-1',
        targetIdentifiers: ['ds-1', 'ds-2'],
        mappings: [],
      },
      {
        id: 'task-2',
        targetIdentifiers: [],
        mappings: [
          {
            sourceIdentifier: 'source-1',
            paths: [{ targetIdentifier: 'ds-3', dataTransformations: [] }],
          },
        ],
      },
      {
        id: 'task-3',
        targetIdentifiers: ['ds-1'],
        mappings: [],
      },
    ] as any
    orchestrationStore.workspaceDatastreams = [
      { id: 'ds-1', name: 'Datastream 1' },
      { id: 'ds-2', name: 'Datastream 2' },
      { id: 'ds-3', name: 'Datastream 3' },
      { id: 'ds-4', name: 'Datastream 4' },
    ] as any

    await nextTick()

    expect([...orchestrationStore.linkedDatastreamIds]).toEqual([
      'ds-1',
      'ds-2',
      'ds-3',
    ])
    expect(orchestrationStore.linkedDatastreams.map((d) => d.id)).toEqual([
      'ds-1',
      'ds-2',
      'ds-3',
    ])
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

    workspaceOneRequest.resolve([{ id: 'ds-1', name: 'Datastream 1' }])
    await workspaceOneLoad

    expect(orchestrationStore.workspaceDatastreams.map((d) => d.id)).toEqual([
      'ds-2',
    ])
  })
})
