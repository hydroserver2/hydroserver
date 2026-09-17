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

  it('lists rating curves for a monitoringSite with product query parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [
          {
            id: 'rating-curve-1',
            name: 'Stage to discharge',
            fittingMethod: 'linear',
            monitoringSite: { id: 'monitoringSite-1', name: 'Site 1' },
            points: [
              [1, 2],
              [2, 4],
            ],
          },
        ],
        meta: { offset: 0, limit: 200, totalCount: 1 },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.ratingCurves.listItemsForMonitoringSite('monitoringSite-1', {
      sortby: ['name'],
    })

    expect(response).toHaveLength(1)
    const url = new URL(fetchMock.mock.calls[0][0])
    expect(url.href).toBe(
      'https://hydro.example.com/api/data/data-product-rating-curves?sortby=name&monitoring_site_id=monitoringSite-1&offset=0&limit=200'
    )
  })

  it('creates rating curves with database points instead of a file upload, then fetches the full row', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init) => {
      if (init?.method === 'POST') {
        return jsonResponse({ id: 'rating-curve-1' }, {})
      }
      return jsonResponse({
        data: {
          id: 'rating-curve-1',
          name: 'Curve',
          description: null,
          fittingMethod: 'power_law',
          monitoringSiteId: 'monitoringSite-1',
          points: [[1, 2]],
        },
        included: {},
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.ratingCurves.create({
      id: '',
      name: 'Curve',
      description: null,
      fittingMethod: 'power_law',
      monitoringSiteId: 'monitoringSite-1',
      points: [[1, 2]],
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/data-product-rating-curves'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: 'Curve',
      description: null,
      fittingMethod: 'power_law',
      monitoringSiteId: 'monitoringSite-1',
      points: [[1, 2]],
    })
    expect(String(fetchMock.mock.calls[1][0])).toBe(
      'https://hydro.example.com/api/data/data-product-rating-curves/rating-curve-1'
    )
    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.name).toBe('Curve')
    expect(response.data.points).toEqual([[1, 2]])
  })

  it('updates rating curve metadata and points without sending read-only fields, then fetches the full row', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init) => {
      if (init?.method === 'PATCH') {
        return new Response(null, { status: 204 })
      }
      return jsonResponse({
        data: {
          id: 'rating-curve-1',
          name: 'Updated',
          description: 'New notes',
          fittingMethod: 'linear',
          monitoringSiteId: 'monitoringSite-1',
          points: [[2, 3]],
        },
        included: {},
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.ratingCurves.update({
      id: 'rating-curve-1',
      name: 'Updated',
      description: 'New notes',
      fittingMethod: 'linear',
      points: [[2, 3]],
      monitoringSiteId: 'monitoringSite-1',
      monitoringSite: { id: 'monitoringSite-1', name: 'Site 1' },
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/data-product-rating-curves/rating-curve-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: 'Updated',
      description: 'New notes',
      fittingMethod: 'linear',
      points: [[2, 3]],
    })
    expect(String(fetchMock.mock.calls[1][0])).toBe(
      'https://hydro.example.com/api/data/data-product-rating-curves/rating-curve-1'
    )
    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.name).toBe('Updated')
    expect(response.data.points).toEqual([[2, 3]])
  })

  it('deletes rating curves by id', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 204, statusText: 'No Content' })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.ratingCurves.delete('rating-curve-1')

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/data-product-rating-curves/rating-curve-1'
    )
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE')
  })
})
