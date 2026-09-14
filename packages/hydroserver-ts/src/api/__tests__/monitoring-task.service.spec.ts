import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('MonitoringTaskService rules', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('createRule posts and returns the created id, with no follow-up fetch', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 'rule-1' }, 201))
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.monitoringTasks.createRule('task-1', {
      datastreamId: 'datastream-1',
      ruleType: 'missing_data',
      windowInterval: 1,
      windowIntervalUnits: 'days',
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/monitoring/tasks/task-1/rules'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.id).toBe('rule-1')
  })

  it('updateRule patches, with no follow-up fetch', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.monitoringTasks.updateRule('task-1', 'rule-1', {
      windowInterval: 2,
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/monitoring/tasks/task-1/rules/rule-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(response.ok).toBe(true)
  })

  it('createRule returns the error unchanged when the create request fails', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ detail: 'Duplicate rule type' }, 400)
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.monitoringTasks.createRule('task-1', {
      datastreamId: 'datastream-1',
      ruleType: 'missing_data',
      windowInterval: 1,
      windowIntervalUnits: 'days',
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(response.ok).toBe(false)
  })
})
