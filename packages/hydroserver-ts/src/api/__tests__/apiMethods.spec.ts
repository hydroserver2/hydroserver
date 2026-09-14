import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiMethods } from '../apiMethods'

describe('paginatedFetch', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('merges the `included` buckets across every fetched page', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
      const offset = new URL(String(input)).searchParams.get('offset')
      const body =
        offset === '0'
          ? {
              data: [{ id: '1', ownerEmail: 'a@example.com' }],
              meta: { offset: 0, limit: 1, totalCount: 2 },
              included: { owners: [{ email: 'a@example.com' }] },
            }
          : {
              data: [{ id: '2', ownerEmail: 'b@example.com' }],
              meta: { offset: 1, limit: 1, totalCount: 2 },
              included: { owners: [{ email: 'b@example.com' }] },
            }

      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
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
      const body =
        offset === '0'
          ? {
              data: {
                fields: ['phenomenonTime', 'result'],
                rows: [['2026-01-01T00:00:00Z', 1]],
              },
              meta: { offset: 0, limit: 1, totalCount: 2 },
            }
          : {
              data: {
                fields: ['phenomenonTime', 'result'],
                rows: [['2026-01-01T00:01:00Z', 2]],
              },
              meta: { offset: 1, limit: 1, totalCount: 2 },
            }

      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
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
      new Response(
        JSON.stringify({
          data: [{ id: '1', ownerEmail: 'a@example.com' }],
          meta: { offset: 0, limit: 200, totalCount: 1 },
          included: { owners: [{ email: 'a@example.com' }] },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
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
  })
})
