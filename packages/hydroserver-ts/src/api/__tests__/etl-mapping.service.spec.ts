import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('EtlMappingService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates a mapping at the flat route with etlTaskId in the body, then refetches', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 'mapping-1' }, 201))
      .mockResolvedValueOnce(
        jsonResponse({
          data: {
            id: 'mapping-1',
            etlTaskId: 'task-1',
            sourceIdentifier: 'sensor_1',
            targetDatastreamId: 'datastream-1',
          },
          included: {},
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.etlMappings.create({
      id: '',
      etlTaskId: 'task-1',
      sourceIdentifier: 'sensor_1',
      targetDatastreamId: 'datastream-1',
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/etl-mappings'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    const sentBody = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(sentBody.etlTaskId).toBe('task-1')

    expect(fetchMock.mock.calls[1][0]).toBe(
      'https://hydro.example.com/api/data/etl-mappings/mapping-1'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.id).toBe('mapping-1')
  })

  it('updates a mapping at the flat route', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        jsonResponse({
          data: {
            id: 'mapping-1',
            etlTaskId: 'task-1',
            sourceIdentifier: 'sensor_2',
            targetDatastreamId: 'datastream-1',
          },
          included: {},
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.etlMappings.update({
      id: 'mapping-1',
      sourceIdentifier: 'sensor_2',
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/etl-mappings/mapping-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(response.ok).toBe(true)
  })
})
