import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

const jsonResponse = (data: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(data), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  })

describe('QualityControl services', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('lists histories with generated query parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        [
          {
            id: 'history-1',
            managedDatastreamId: 'managed-1',
            sourceDatastreamId: 'source-1',
            createdAt: '2026-06-18T12:00:00Z',
          },
        ],
        { 'X-Total-Pages': '1' }
      )
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.qualityControlHistories.list({
      managed_datastream_id: ['managed-1'],
      fetch_all: true,
    })

    const url = new URL(fetchMock.mock.calls[0][0])
    expect(url.href).toBe(
      'https://hydro.example.com/api/data/quality-control/histories?managed_datastream_id=managed-1&page=1&page_size=200'
    )
  })

  it('creates sessions under a QC history', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'session-1',
        historyId: 'history-1',
        phenomenonTimeStart: '2026-06-18T00:00:00Z',
        phenomenonTimeEnd: '2026-06-18T01:00:00Z',
        status: 'in_progress',
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.qualityControlSessions.create('history-1', {
      phenomenonTimeStart: '2026-06-18T00:00:00Z',
      phenomenonTimeEnd: '2026-06-18T01:00:00Z',
      description: null,
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/quality-control/histories/history-1/sessions'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      phenomenonTimeStart: '2026-06-18T00:00:00Z',
      phenomenonTimeEnd: '2026-06-18T01:00:00Z',
      description: null,
    })
  })

  it('appends operation batches under a QC session', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse([
        {
          id: 'operation-1',
          order: 1,
          operationType: 'CHANGE_VALUES',
          createdAt: '2026-06-18T12:00:00Z',
          createdBy: { id: 'user-1', email: 'user@example.com' },
        },
      ])
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.qualityControlOperations.create('history-1', 'session-1', [
      {
        operationType: 'CHANGE_VALUES',
        order: 1,
        comment: 'Adjusted spike',
        arguments: { indices: [4], value: 10 },
      },
    ])

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/quality-control/histories/history-1/sessions/session-1/operations'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual([
      {
        operationType: 'CHANGE_VALUES',
        order: 1,
        comment: 'Adjusted spike',
        arguments: { indices: [4], value: 10 },
      },
    ])
  })
})
