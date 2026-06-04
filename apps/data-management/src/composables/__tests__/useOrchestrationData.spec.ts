import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useOrchestrationData } from '../orchestration/useOrchestrationData'

const {
  dataConnectionsListMock,
  tasksListMock,
  dataProductTasksListMock,
  monitoringTasksListMock,
  thingsTaskSummariesMock,
} = vi.hoisted(() => ({
  dataConnectionsListMock: vi.fn(),
  tasksListMock: vi.fn(),
  dataProductTasksListMock: vi.fn(),
  monitoringTasksListMock: vi.fn(),
  thingsTaskSummariesMock: vi.fn(),
}))

vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()

  return {
    ...actual,
    default: {
      ...actual.default,
      dataConnections: { listAllItems: dataConnectionsListMock },
      tasks: { listAllItems: tasksListMock },
      dataProductTasks: { listAllItems: dataProductTasksListMock },
      monitoringTasks: { listAllItems: monitoringTasksListMock },
      things: { listTaskSummaries: thingsTaskSummariesMock },
    },
  }
})

describe('useOrchestrationData', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads orchestration summaries for a workspace', async () => {
    dataConnectionsListMock.mockResolvedValue([{ id: 'dc-1', name: 'Source' }])
    thingsTaskSummariesMock.mockResolvedValue({
      ok: true,
      data: [{ id: 'thing-1', name: 'Site' }],
    })

    const data = useOrchestrationData()
    await data.fetchAll('workspace-1')

    expect(data.loading.value).toBe(false)
    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-1'])
    expect(data.workspaceTasks.value).toEqual([])
    expect(data.dataProductTasks.value).toEqual([])
    expect(data.monitoringTasks.value).toEqual([])
    expect(data.things.value.map((item) => item.id)).toEqual(['thing-1'])
    expect(data.datastreamThingByDatastreamId.value).toEqual({})
    expect(dataConnectionsListMock).toHaveBeenCalledWith({
      workspace_id: 'workspace-1',
      order_by: 'name',
    })
    expect(thingsTaskSummariesMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
    })
    expect(tasksListMock).not.toHaveBeenCalled()
    expect(dataProductTasksListMock).not.toHaveBeenCalled()
    expect(monitoringTasksListMock).not.toHaveBeenCalled()
  })

  it('ignores stale fetchAll responses', async () => {
    let resolveFirst!: (items: unknown[]) => void
    const firstRequest = new Promise((resolve) => {
      resolveFirst = resolve
    })

    dataConnectionsListMock
      .mockReturnValueOnce(firstRequest)
      .mockResolvedValueOnce([{ id: 'dc-2' }])
    thingsTaskSummariesMock.mockResolvedValue({ ok: true, data: [] })

    const data = useOrchestrationData()
    const staleLoad = data.fetchAll('workspace-1')
    await data.fetchAll('workspace-2')
    resolveFirst([{ id: 'dc-1' }])
    await staleLoad

    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-2'])
    expect(data.loading.value).toBe(false)
  })

  it('loads detailed tasks only for the selected group', async () => {
    tasksListMock.mockResolvedValue([{ id: 'etl-1' }])
    dataProductTasksListMock.mockResolvedValue([{ id: 'dp-1' }])
    monitoringTasksListMock.mockResolvedValue([{ id: 'mon-1' }])

    const data = useOrchestrationData()

    await data.fetchTasksForGroup('ingestion', 'dc-1', 'workspace-1')
    expect(data.workspaceTasks.value.map((item) => item.id)).toEqual(['etl-1'])
    expect(tasksListMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
      data_connection_id: ['dc-1'],
      order_by: ['name'],
    })

    await data.fetchTasksForGroup('aggregation', 'thing-1', 'workspace-1')
    expect(data.dataProductTasks.value.map((item) => item.id)).toEqual(['dp-1'])
    expect(dataProductTasksListMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
      thing_id: ['thing-1'],
      order_by: ['name'],
    })

    await data.fetchTasksForGroup('quality', 'thing-1', 'workspace-1')
    expect(data.monitoringTasks.value.map((item) => item.id)).toEqual(['mon-1'])
    expect(monitoringTasksListMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
      thing_id: ['thing-1'],
      order_by: ['name'],
    })
  })

  it('refreshes data connections without replacing other loaded data', async () => {
    dataConnectionsListMock.mockResolvedValue([{ id: 'dc-3' }])

    const data = useOrchestrationData()
    data.workspaceTasks.value = [{ id: 'etl-1' }] as any

    await data.refreshDataConnections('workspace-1')

    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-3'])
    expect(data.workspaceTasks.value.map((item) => item.id)).toEqual(['etl-1'])
  })
})
