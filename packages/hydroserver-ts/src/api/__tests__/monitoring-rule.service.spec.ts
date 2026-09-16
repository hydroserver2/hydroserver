import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('MonitoringRuleService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates a rule at the flat route and refetches the canonical record', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 'rule-1' }, 201))
      .mockResolvedValueOnce(
        jsonResponse({
          data: {
            id: 'rule-1',
            taskId: 'task-1',
            datastreamId: 'datastream-1',
            ruleType: 'missing_data',
            windowInterval: 1,
            windowIntervalUnits: 'days',
          },
          included: {},
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.monitoringRules.create({
      id: '',
      taskId: 'task-1',
      datastreamId: 'datastream-1',
      ruleType: 'missing_data',
      windowInterval: 1,
      windowIntervalUnits: 'days',
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/monitoring-rules'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    const sentBody = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(sentBody.taskId).toBe('task-1')

    expect(fetchMock.mock.calls[1][0]).toBe(
      'https://hydro.example.com/api/data/monitoring-rules/rule-1'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.id).toBe('rule-1')
  })

  it('updates a rule at the flat route', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        jsonResponse({
          data: {
            id: 'rule-1',
            taskId: 'task-1',
            datastreamId: 'datastream-1',
            ruleType: 'missing_data',
            windowInterval: 2,
            windowIntervalUnits: 'days',
          },
          included: {},
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.monitoringRules.update({
      id: 'rule-1',
      windowInterval: 2,
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/monitoring-rules/rule-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(response.ok).toBe(true)
  })

  it('returns the error unchanged when the create request fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ detail: 'Duplicate rule type' }, 400))
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.monitoringRules.create({
      id: '',
      taskId: 'task-1',
      datastreamId: 'datastream-1',
      ruleType: 'missing_data',
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(response.ok).toBe(false)
  })
})
