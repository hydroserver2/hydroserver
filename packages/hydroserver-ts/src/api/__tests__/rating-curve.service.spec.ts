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

describe('RatingCurveService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('lists rating curves for a thing with product query parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        [
          {
            id: 'rating-curve-1',
            name: 'Stage to discharge',
            fittingMethod: 'linear',
            thing: { id: 'thing-1', name: 'Site 1' },
            points: [
              [1, 2],
              [2, 4],
            ],
          },
        ],
        { 'X-Total-Pages': '1' }
      )
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.ratingCurves.listItemsForThing('thing-1', {
      order_by: ['name'],
    })

    expect(response).toHaveLength(1)
    const url = new URL(fetchMock.mock.calls[0][0])
    expect(url.href).toBe(
      'https://hydro.example.com/api/data/products/rating-curves?order_by=name&thing_id=thing-1&page=1&page_size=200'
    )
  })

  it('creates rating curves with database points instead of a file upload', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'rating-curve-1',
        name: 'Curve',
        description: null,
        fittingMethod: 'power_law',
        thing: { id: 'thing-1', name: 'Site 1' },
        points: [[1, 2]],
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.ratingCurves.create({
      id: '',
      name: 'Curve',
      description: null,
      fittingMethod: 'power_law',
      thingId: 'thing-1',
      points: [[1, 2]],
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/products/rating-curves'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: 'Curve',
      description: null,
      fittingMethod: 'power_law',
      thingId: 'thing-1',
      points: [[1, 2]],
    })
  })

  it('updates rating curve metadata and points without sending read-only fields', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 'rating-curve-1',
        name: 'Updated',
        description: 'New notes',
        fittingMethod: 'linear',
        thing: { id: 'thing-1', name: 'Site 1' },
        points: [[2, 3]],
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.ratingCurves.update({
      id: 'rating-curve-1',
      name: 'Updated',
      description: 'New notes',
      fittingMethod: 'linear',
      points: [[2, 3]],
      thingId: 'thing-1',
      thing: { id: 'thing-1', name: 'Site 1' },
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/products/rating-curves/rating-curve-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: 'Updated',
      description: 'New notes',
      fittingMethod: 'linear',
      points: [[2, 3]],
    })
  })

  it('deletes rating curves by id', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 204, statusText: 'No Content' })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.ratingCurves.delete('rating-curve-1')

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/products/rating-curves/rating-curve-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE')
  })
})
