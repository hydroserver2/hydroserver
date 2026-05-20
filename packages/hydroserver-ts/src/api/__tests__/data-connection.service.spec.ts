import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { DataConnection } from '../Models/data-connection.model'

const jsonResponse = (data: unknown) =>
  new Response(JSON.stringify(data), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
    },
  })

describe('DataConnectionService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends auth header fields when creating a data connection', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'data-connection-1',
        name: 'Authenticated source',
        sourceUrl: 'https://httpbin.org/bearer',
        authHeaderName: 'Authorization',
        authHeaderValue: 'Bearer abc123',
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.dataConnections.create(
      new DataConnection({
        id: '',
        name: 'Authenticated source',
        sourceUrl: 'https://httpbin.org/bearer',
        authHeaderName: 'Authorization',
        authHeaderValue: 'Bearer abc123',
      })
    )

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/etl/data-connections'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({
      name: 'Authenticated source',
      sourceUrl: 'https://httpbin.org/bearer',
      authHeaderName: 'Authorization',
      authHeaderValue: 'Bearer abc123',
    })
  })

  it('sends auth header fields when updating a data connection', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'data-connection-1',
        authHeaderName: 'X-API-Key',
        authHeaderValue: 'abc123',
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.dataConnections.update({
      id: 'data-connection-1',
      authHeaderName: 'X-API-Key',
      authHeaderValue: 'abc123',
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/etl/data-connections/data-connection-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({
      authHeaderName: 'X-API-Key',
      authHeaderValue: 'abc123',
    })
  })
})
