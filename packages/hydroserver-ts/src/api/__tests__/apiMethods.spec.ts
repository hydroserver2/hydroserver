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
    >('https://hydro.example.com/api/data/workspaces?limit=1')

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
    }>('https://hydro.example.com/api/data/observations?format=row&limit=1')

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
    >('https://hydro.example.com/api/data/workspaces')

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
      'https://hydro.example.com/api/data/observations?limit=2'
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
      'https://hydro.example.com/api/data/observations?limit=2'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.map((item) => item.id)).toEqual(['1', '2', '3'])
  })
})
