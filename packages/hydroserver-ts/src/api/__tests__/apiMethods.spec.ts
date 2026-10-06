import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiMethods } from '../apiMethods'

const jsonResponse = (body: unknown) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })

describe('paginatedFetch', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('merges the `included` buckets across every fetched page', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
      const offset = new URL(String(input)).searchParams.get('offset')
      if (offset === '0') {
        return jsonResponse({
          data: [{ id: '1', ownerEmail: 'a@example.com' }],
          meta: { offset: 0, limit: 1, totalCount: 2 },
          included: { owners: [{ email: 'a@example.com' }] },
        })
      }
      if (offset === '1') {
        return jsonResponse({
          data: [{ id: '2', ownerEmail: 'b@example.com' }],
          meta: { offset: 1, limit: 1, totalCount: 2 },
          included: { owners: [{ email: 'b@example.com' }] },
        })
      }
      // A real server returns an empty page once past the true end of data -
      // this is what terminates the "keep going while the last page was
      // full" check for a totalCount that happens to be exact.
      return jsonResponse({
        data: [],
        meta: { offset: Number(offset), limit: 1, totalCount: 2 },
        included: {},
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<
      { id: string; ownerEmail: string }[]
    >('https://hydro.example.com/api/ogc/collections/workspaces/items?limit=1')

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data).toEqual([
      { id: '1', ownerEmail: 'a@example.com' },
      { id: '2', ownerEmail: 'b@example.com' },
    ])
    expect(response.included).toEqual({
      owners: [{ email: 'a@example.com' }, { email: 'b@example.com' }],
    })
  })

  it('keeps a single fields list (not duplicated) when merging row-format observation pages', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
      const offset = new URL(String(input)).searchParams.get('offset')
      if (offset === '0') {
        return jsonResponse({
          data: {
            fields: ['phenomenonTime', 'result'],
            rows: [['2026-01-01T00:00:00Z', 1]],
          },
          meta: { offset: 0, limit: 1, totalCount: 2 },
        })
      }
      if (offset === '1') {
        return jsonResponse({
          data: {
            fields: ['phenomenonTime', 'result'],
            rows: [['2026-01-01T00:01:00Z', 2]],
          },
          meta: { offset: 1, limit: 1, totalCount: 2 },
        })
      }
      return jsonResponse({
        data: { fields: ['phenomenonTime', 'result'], rows: [] },
        meta: { offset: Number(offset), limit: 1, totalCount: 2 },
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<{
      fields: string[]
      rows: unknown[][]
    }>('https://hydro.example.com/api/ogc/collections/observations/items?format=row&limit=1')

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.fields).toEqual(['phenomenonTime', 'result'])
    expect(response.data.rows).toEqual([
      ['2026-01-01T00:00:00Z', 1],
      ['2026-01-01T00:01:00Z', 2],
    ])
  })

  it('carries a single page’s `included` through unchanged when there is no second page', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [{ id: '1', ownerEmail: 'a@example.com' }],
        meta: { offset: 0, limit: 200, totalCount: 1 },
        included: { owners: [{ email: 'a@example.com' }] },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<
      { id: string; ownerEmail: string }[]
    >('https://hydro.example.com/api/ogc/collections/workspaces/items')

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.included).toEqual({
      owners: [{ email: 'a@example.com' }],
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('keeps fetching past an underestimated totalCount until a short page is seen', async () => {
    // totalCount reports 2 (e.g., a Postgres row-estimate for a large
    // filtered Observation query), but 5 rows actually exist across 3
    // pages of limit=2.
    const pages: Record<string, { id: string }[]> = {
      '0': [{ id: '1' }, { id: '2' }],
      '2': [{ id: '3' }, { id: '4' }],
      '4': [{ id: '5' }],
    }
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
      const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
      const data = pages[offset] ?? []
      return jsonResponse({
        data,
        meta: { offset: Number(offset), limit: 2, totalCount: 2 },
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<{ id: string }[]>(
      'https://hydro.example.com/api/ogc/collections/observations/items?limit=2'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.map((item) => item.id)).toEqual([
      '1',
      '2',
      '3',
      '4',
      '5',
    ])
    expect(response.meta?.totalCount).toBe(5)
  })

  it('still paginates past the first page when totalCount is missing entirely', async () => {
    const pages: Record<string, { id: string }[]> = {
      '0': [{ id: '1' }, { id: '2' }],
      '2': [{ id: '3' }],
    }
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
      const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
      const data = pages[offset] ?? []
      return jsonResponse({ data, meta: { offset: Number(offset), limit: 2 } })
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<{ id: string }[]>(
      'https://hydro.example.com/api/ogc/collections/observations/items?limit=2'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.map((item) => item.id)).toEqual(['1', '2', '3'])
  })

  describe('when the server clamps the requested limit', () => {
    // 5 records; the client asks for limit=4 but the server caps pages at 2.
    const mockClampedServer = (meta: (offset: number) => Record<string, unknown>) => {
      const records = ['1', '2', '3', '4', '5'].map((id) => ({ id }))
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
        const url = new URL(String(input))
        const offset = Number(url.searchParams.get('offset') ?? '0')
        const limit = Math.min(Number(url.searchParams.get('limit')), 2)
        return jsonResponse({
          data: records.slice(offset, offset + limit),
          meta: meta(offset),
        })
      })
      vi.stubGlobal('fetch', fetchMock)
      return fetchMock
    }

    const requestedOffsets = (fetchMock: ReturnType<typeof vi.fn>) =>
      fetchMock.mock.calls.map(([input]) =>
        Number(new URL(String(input)).searchParams.get('offset'))
      )

    it('pages by the returned meta.limit instead of the requested limit', async () => {
      const fetchMock = mockClampedServer((offset) => ({ offset, limit: 2, totalCount: 5 }))

      const response = await apiMethods.paginatedFetch<{ id: string }[]>(
        'https://hydro.example.com/api/ogc/collections/observations/items?limit=4'
      )

      expect(response.ok).toBe(true)
      if (!response.ok) return
      expect(requestedOffsets(fetchMock)).toEqual([0, 2, 4])
      expect(response.data.map((item) => item.id)).toEqual(['1', '2', '3', '4', '5'])
      expect(response.meta?.totalCount).toBe(5)
    })

    it('pages by the returned meta.limit when totalCount is missing', async () => {
      mockClampedServer((offset) => ({ offset, limit: 2 }))

      const response = await apiMethods.paginatedFetch<{ id: string }[]>(
        'https://hydro.example.com/api/ogc/collections/observations/items?limit=4'
      )

      expect(response.ok).toBe(true)
      if (!response.ok) return
      expect(response.data.map((item) => item.id)).toEqual(['1', '2', '3', '4', '5'])
    })
  })

  it('falls back to the requested limit when the response has no meta.limit', async () => {
    const pages: Record<string, { id: string }[]> = {
      '0': [{ id: '1' }, { id: '2' }],
      '2': [{ id: '3' }],
    }
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
      const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
      return jsonResponse({ data: pages[offset] ?? [], meta: { offset: Number(offset), totalCount: 3 } })
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<{ id: string }[]>(
      'https://hydro.example.com/api/ogc/collections/observations/items?limit=2'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.map((item) => item.id)).toEqual(['1', '2', '3'])
  })
})
