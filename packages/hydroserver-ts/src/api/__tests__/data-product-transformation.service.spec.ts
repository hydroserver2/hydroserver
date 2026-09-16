import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('DataProductTransformationService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates a transformation at the flat route with taskId in the body, then refetches', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 'transformation-1' }, 201))
      .mockResolvedValueOnce(
        jsonResponse({
          data: {
            id: 'transformation-1',
            taskId: 'task-1',
            transformationType: 'aggregation',
            outputDatastreamId: 'output-1',
            inputDatastreams: [{ datastreamId: 'input-1', variableName: null }],
            aggregationMethod: 'mean',
            outputInterval: 15,
            outputIntervalUnits: 'minutes',
            stopOnNoData: true,
            stopOnError: true,
          },
          included: {},
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.dataProductTransformations.create({
      id: '',
      taskId: 'task-1',
      transformationType: 'aggregation',
      outputDatastreamId: 'output-1',
      inputDatastreams: [{ datastreamId: 'input-1' }],
      aggregationMethod: 'mean',
      outputInterval: 15,
      outputIntervalUnits: 'minutes',
      stopOnNoData: true,
      stopOnError: true,
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/data-product-transformations'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    const sentBody = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(sentBody.taskId).toBe('task-1')

    expect(fetchMock.mock.calls[1][0]).toBe(
      'https://hydro.example.com/api/data/data-product-transformations/transformation-1'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.id).toBe('transformation-1')
  })

  it('updates a transformation at the flat route', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        jsonResponse({
          data: {
            id: 'transformation-1',
            taskId: 'task-1',
            transformationType: 'aggregation',
            outputDatastreamId: 'output-1',
            inputDatastreams: [{ datastreamId: 'input-1', variableName: null }],
            aggregationMethod: 'mean',
            outputInterval: 30,
            outputIntervalUnits: 'minutes',
            stopOnNoData: true,
            stopOnError: true,
          },
          included: {},
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.dataProductTransformations.update({
      id: 'transformation-1',
      outputInterval: 30,
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/data-product-transformations/transformation-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(response.ok).toBe(true)
  })
})
