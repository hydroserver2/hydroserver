import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useOrchestrationData } from '../orchestration/useOrchestrationData'

const {
  dataConnectionsListMock,
  tasksListMock,
  dataProductTasksListMock,
  monitoringTasksListMock,
  thingsListMock,
  datastreamsListMock,
} = vi.hoisted(() => ({
  dataConnectionsListMock: vi.fn(),
  tasksListMock: vi.fn(),
  dataProductTasksListMock: vi.fn(),
  monitoringTasksListMock: vi.fn(),
  thingsListMock: vi.fn(),
  datastreamsListMock: vi.fn(),
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
      things: { listAllItems: thingsListMock },
      datastreams: { listAllItems: datastreamsListMock },
    },
  }
})

describe('useOrchestrationData', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads all orchestration data for a workspace', async () => {
    dataConnectionsListMock.mockResolvedValue([{ id: 'dc-1', name: 'Source' }])
    tasksListMock.mockResolvedValue([{ id: 'etl-1', name: 'Ingest' }])
    dataProductTasksListMock.mockResolvedValue([{ id: 'dp-1', name: 'Aggregate' }])
    monitoringTasksListMock.mockResolvedValue([{ id: 'mon-1', name: 'Quality' }])
    thingsListMock.mockResolvedValue([{ id: 'thing-1', name: 'Site' }])
    datastreamsListMock.mockResolvedValue([
      { id: 'ds-1', thingId: 'thing-1' },
      { id: 'ds-2' },
    ])

    const data = useOrchestrationData()
    await data.fetchAll('workspace-1')

    expect(data.loading.value).toBe(false)
    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-1'])
    expect(data.workspaceTasks.value.map((item) => item.id)).toEqual(['etl-1'])
    expect(data.dataProductTasks.value.map((item) => item.id)).toEqual(['dp-1'])
    expect(data.monitoringTasks.value.map((item) => item.id)).toEqual(['mon-1'])
    expect(data.things.value.map((item) => item.id)).toEqual(['thing-1'])
    expect(data.datastreamThingByDatastreamId.value).toEqual({
      'ds-1': 'thing-1',
    })
    expect(dataConnectionsListMock).toHaveBeenCalledWith({
      workspace_id: 'workspace-1',
      order_by: 'name',
    })
  })

  it('ignores stale fetchAll responses', async () => {
    let resolveFirst!: (items: unknown[]) => void
    const firstRequest = new Promise((resolve) => {
      resolveFirst = resolve
    })

    dataConnectionsListMock
      .mockReturnValueOnce(firstRequest)
      .mockResolvedValueOnce([{ id: 'dc-2' }])
    tasksListMock.mockResolvedValue([])
    dataProductTasksListMock.mockResolvedValue([])
    monitoringTasksListMock.mockResolvedValue([])
    thingsListMock.mockResolvedValue([])
    datastreamsListMock.mockResolvedValue([])

    const data = useOrchestrationData()
    const staleLoad = data.fetchAll('workspace-1')
    await data.fetchAll('workspace-2')
    resolveFirst([{ id: 'dc-1' }])
    await staleLoad

    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-2'])
    expect(data.loading.value).toBe(false)
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
