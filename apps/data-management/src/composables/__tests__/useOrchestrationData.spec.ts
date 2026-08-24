import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useOrchestrationData } from '../orchestration/useOrchestrationData'

const {
  dataConnectionsListMock,
  tasksListMock,
  dataProductTasksListMock,
  monitoringTasksListMock,
  monitoringSitesTaskSummariesMock,
} = vi.hoisted(() => ({
  dataConnectionsListMock: vi.fn(),
  tasksListMock: vi.fn(),
  dataProductTasksListMock: vi.fn(),
  monitoringTasksListMock: vi.fn(),
  monitoringSitesTaskSummariesMock: vi.fn(),
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
      monitoringSites: { listTaskSummaries: monitoringSitesTaskSummariesMock },
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
    monitoringSitesTaskSummariesMock.mockResolvedValue({
      ok: true,
      data: [{ id: 'monitoringSite-1', name: 'Site' }],
    })

    const data = useOrchestrationData()
    await data.fetchAll('workspace-1')

    expect(data.loading.value).toBe(false)
    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-1'])
    expect(data.workspaceTasks.value).toEqual([])
    expect(data.dataProductTasks.value).toEqual([])
    expect(data.monitoringTasks.value).toEqual([])
    expect(data.monitoringSites.value.map((item) => item.id)).toEqual(['monitoringSite-1'])
    expect(data.datastreamMonitoringSiteByDatastreamId.value).toEqual({})
    expect(dataConnectionsListMock).toHaveBeenCalledWith({
      workspace_id: 'workspace-1',
      order_by: 'name',
    })
    expect(monitoringSitesTaskSummariesMock).toHaveBeenCalledWith({
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
    monitoringSitesTaskSummariesMock.mockResolvedValue({ ok: true, data: [] })

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

    await data.fetchTasksForGroup('aggregation', 'monitoringSite-1', 'workspace-1')
    expect(data.dataProductTasks.value.map((item) => item.id)).toEqual(['dp-1'])
    expect(dataProductTasksListMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
      monitoring_site_id: ['monitoringSite-1'],
      order_by: ['name'],
    })

    await data.fetchTasksForGroup('quality', 'monitoringSite-1', 'workspace-1')
    expect(data.monitoringTasks.value.map((item) => item.id)).toEqual(['mon-1'])
    expect(monitoringTasksListMock).toHaveBeenCalledWith({
      workspace_id: ['workspace-1'],
      monitoring_site_id: ['monitoringSite-1'],
      order_by: ['name'],
    })
  })

  it('does not restore tasks from a request after its group is cleared', async () => {
    let resolveTasks!: (items: unknown[]) => void
    tasksListMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveTasks = resolve
      })
    )

    const data = useOrchestrationData()
    const staleLoad = data.fetchTasksForGroup(
      'ingestion',
      'dc-old',
      'workspace-1'
    )

    await data.fetchTasksForGroup('ingestion', null, 'workspace-1')
    resolveTasks([{ id: 'etl-stale' }])
    await staleLoad

    expect(data.workspaceTasks.value).toEqual([])
    expect(data.loadedTaskGroup.value).toBeNull()
    expect(data.taskLoading.value).toBe(false)
  })

  it('invalidates a pending task request when workspace summaries reload', async () => {
    let resolveTasks!: (items: unknown[]) => void
    tasksListMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveTasks = resolve
      })
    )
    dataConnectionsListMock.mockResolvedValue([])
    monitoringSitesTaskSummariesMock.mockResolvedValue({ ok: true, data: [] })

    const data = useOrchestrationData()
    const staleLoad = data.fetchTasksForGroup(
      'ingestion',
      'dc-old',
      'workspace-old'
    )

    await data.fetchAll('workspace-new')
    resolveTasks([{ id: 'etl-stale' }])
    await staleLoad

    expect(data.workspaceTasks.value).toEqual([])
    expect(data.loadedTaskGroup.value).toBeNull()
    expect(data.taskLoading.value).toBe(false)
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
