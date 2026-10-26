import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiMethods } from '../apiMethods'
import {
  registerAccessTokenProvider,
  registerUnauthorizedHandler,
} from '../requestInterceptor'

const jsonResponse = (body: unknown) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })

describe('patch', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('merges nested objects consistently and preserves request headers', async () => {
    const original = {
      settings: { source: { station: 'A', parameter: 'temperature' } },
      organization: { name: 'OriginalOrg', code: '001' },
    }
    const updated = {
      settings: { source: { station: 'B', parameter: 'temperature' } },
      organization: { name: 'UpdatedOrg', code: '001' },
    }
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse(updated))
    vi.stubGlobal('fetch', fetchMock)

    await apiMethods.patch('https://hydro.example.com/resource', updated, original, {
      headers: { 'X-Example': 'preserved' },
    })

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      settings: { source: { station: 'B' } },
      organization: { name: 'UpdatedOrg' },
    })
    expect(fetchMock.mock.calls[0][1].headers.get('Content-Type')).toBe('application/merge-patch+json')
    expect(fetchMock.mock.calls[0][1].headers.get('X-Example')).toBe('preserved')
  })

  it('forwards an explicit patch without an original snapshot', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)
    const patch = { taskVariables: { parameter: null } }
    await apiMethods.patch('https://hydro.example.com/resource', patch)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(patch)
  })

  it('preserves multipart PATCH requests', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)
    const body = new FormData()
    body.set('name', 'Attachment')
    await apiMethods.patch('https://hydro.example.com/resource', body)
    expect(fetchMock.mock.calls[0][1].body).toBe(body)
    expect(fetchMock.mock.calls[0][1].headers.has('Content-Type')).toBe(false)
  })

  it.each([null, [], false])('does not silently skip a non-object patch: %j', async (patch) => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)
    await apiMethods.patch('https://hydro.example.com/resource', patch)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(patch)
  })
})

describe('paginatedFetch', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('merges the `included` buckets across every fetched page', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = new URL(String(input)).searchParams.get('offset')
        if (offset === '0') {
          return jsonResponse({
            data: [{ id: '1', ownerEmail: 'a@example.com' }],
            meta: { offset: 0, limit: 1, numberMatched: 2 },
            included: { owners: [{ email: 'a@example.com' }] },
          })
        }
        if (offset === '1') {
          return jsonResponse({
            data: [{ id: '2', ownerEmail: 'b@example.com' }],
            meta: { offset: 1, limit: 1, numberMatched: 2 },
            included: { owners: [{ email: 'b@example.com' }] },
          })
        }
        // A real server returns an empty page once past the true end of data -
        // this is what terminates the "keep going while the last page was
        // full" check for a numberMatched that happens to be exact.
        return jsonResponse({
          data: [],
          meta: { offset: Number(offset), limit: 1, numberMatched: 2 },
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

  it('merges row-profile groups by datastream across pages', async () => {
    const fields = ['phenomenonTime', 'result', 'resultQualifiers']
    const pages: Record<string, unknown[]> = {
      '0': [
        {
          datastreamId: 'a',
          fields,
          rows: [
            ['t0', 1, []],
            ['t1', 2, []],
          ],
        },
      ],
      '2': [
        { datastreamId: 'a', fields, rows: [['t2', 3, []]] },
        { datastreamId: 'b', fields, rows: [['t0', 9, []]] },
      ],
    }
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
        return jsonResponse({
          data: pages[offset] ?? [],
          meta: { offset: Number(offset), limit: 2, numberMatched: 4 },
        })
      })
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<
      { datastreamId: string; fields: string[]; rows: unknown[][] }[]
    >(
      'https://hydro.example.com/api/ogc/collections/observations/items?profile=https://hydroserver.org/profiles/observations/row&limit=2'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data).toEqual([
      {
        datastreamId: 'a',
        fields,
        rows: [
          ['t0', 1, []],
          ['t1', 2, []],
          ['t2', 3, []],
        ],
      },
      { datastreamId: 'b', fields, rows: [['t0', 9, []]] },
    ])
  })

  it('merges column-profile groups and keeps paging while pages are full', async () => {
    const group = (offset: number) => ({
      datastreamId: 'a',
      columns: {
        phenomenonTime: [`t${offset}`],
        result: [offset],
        resultQualifiers: [[]],
      },
    })
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = Number(new URL(String(input)).searchParams.get('offset'))
        // No numberMatched: paging continues while a page's rows fill the limit.
        return jsonResponse({
          data: offset < 2 ? [group(offset)] : [],
          meta: { offset, limit: 1 },
        })
      })
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.paginatedFetch<
      { datastreamId: string; columns: Record<string, unknown[]> }[]
    >(
      'https://hydro.example.com/api/ogc/collections/observations/items?profile=https://hydroserver.org/profiles/observations/column&limit=1'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data).toEqual([
      {
        datastreamId: 'a',
        columns: {
          phenomenonTime: ['t0', 't1'],
          result: [0, 1],
          resultQualifiers: [[], []],
        },
      },
    ])
  })

  it('carries a single page’s `included` through unchanged when there is no second page', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [{ id: '1', ownerEmail: 'a@example.com' }],
        meta: { offset: 0, limit: 200, numberMatched: 1 },
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

  it('keeps fetching past an underestimated numberMatched until a short page is seen', async () => {
    // numberMatched reports 2 (e.g., a Postgres row-estimate for a large
    // filtered Observation query), but 5 rows actually exist across 3
    // pages of limit=2.
    const pages: Record<string, { id: string }[]> = {
      '0': [{ id: '1' }, { id: '2' }],
      '2': [{ id: '3' }, { id: '4' }],
      '4': [{ id: '5' }],
    }
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
        const data = pages[offset] ?? []
        return jsonResponse({
          data,
          meta: { offset: Number(offset), limit: 2, numberMatched: 2 },
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
    expect(response.meta?.numberMatched).toBe(5)
    expect(response.meta?.numberReturned).toBe(5)
  })

  it('still paginates past the first page when numberMatched is missing entirely', async () => {
    const pages: Record<string, { id: string }[]> = {
      '0': [{ id: '1' }, { id: '2' }],
      '2': [{ id: '3' }],
    }
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
        const data = pages[offset] ?? []
        return jsonResponse({
          data,
          meta: { offset: Number(offset), limit: 2 },
        })
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
    const mockClampedServer = (
      meta: (offset: number) => Record<string, unknown>
    ) => {
      const records = ['1', '2', '3', '4', '5'].map((id) => ({ id }))
      const fetchMock = vi
        .fn()
        .mockImplementation(async (input: string | URL) => {
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
      const fetchMock = mockClampedServer((offset) => ({
        offset,
        limit: 2,
        numberMatched: 5,
      }))

      const response = await apiMethods.paginatedFetch<{ id: string }[]>(
        'https://hydro.example.com/api/ogc/collections/observations/items?limit=4'
      )

      expect(response.ok).toBe(true)
      if (!response.ok) return
      expect(requestedOffsets(fetchMock)).toEqual([0, 2, 4])
      expect(response.data.map((item) => item.id)).toEqual([
        '1',
        '2',
        '3',
        '4',
        '5',
      ])
      expect(response.meta?.numberMatched).toBe(5)
    })

    it('pages by the returned meta.limit when numberMatched is missing', async () => {
      mockClampedServer((offset) => ({ offset, limit: 2 }))

      const response = await apiMethods.paginatedFetch<{ id: string }[]>(
        'https://hydro.example.com/api/ogc/collections/observations/items?limit=4'
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
    })
  })

  it('falls back to the requested limit when the response has no meta.limit', async () => {
    const pages: Record<string, { id: string }[]> = {
      '0': [{ id: '1' }, { id: '2' }],
      '2': [{ id: '3' }],
    }
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = new URL(String(input)).searchParams.get('offset') ?? '0'
        return jsonResponse({
          data: pages[offset] ?? [],
          meta: { offset: Number(offset), numberMatched: 3 },
        })
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

describe('access token retries', () => {
  const endpoint = 'https://hydro.example.com/api/ogc/collections/workspaces/items/1'
  const unauthorized = () => new Response(null, { status: 401 })
  const authorizationOf = (init: RequestInit) =>
    new Headers(init.headers).get('Authorization')

  afterEach(() => {
    registerAccessTokenProvider(null)
    registerUnauthorizedHandler(null)
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('retries a 401 once with a token fetched again from the provider', async () => {
    const tokens = ['expired-token', 'fresh-token']
    registerAccessTokenProvider(async () => tokens.shift() ?? null)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(jsonResponse({ id: '1' }))
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.fetch(endpoint)

    expect(response.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(authorizationOf(fetchMock.mock.calls[0][1])).toBe('Bearer expired-token')
    expect(authorizationOf(fetchMock.mock.calls[1][1])).toBe('Bearer fresh-token')
  })

  it('notifies the unauthorized handler when the retry is also rejected', async () => {
    const onUnauthorized = vi.fn()
    registerAccessTokenProvider(async () => 'revoked-token')
    registerUnauthorizedHandler(onUnauthorized)
    const fetchMock = vi.fn().mockImplementation(async () => unauthorized())
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiMethods.fetch(endpoint)

    expect(response.ok).toBe(false)
    expect(response.status).toBe(401)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('does not retry a 401 for a request sent without a token', async () => {
    const onUnauthorized = vi.fn()
    registerUnauthorizedHandler(onUnauthorized)
    const fetchMock = vi.fn().mockImplementation(async () => unauthorized())
    vi.stubGlobal('fetch', fetchMock)

    await apiMethods.fetch(endpoint)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('does not retry a 401 when the provider has no token', async () => {
    const onUnauthorized = vi.fn()
    registerAccessTokenProvider(async () => null)
    registerUnauthorizedHandler(onUnauthorized)
    const fetchMock = vi.fn().mockImplementation(async () => unauthorized())
    vi.stubGlobal('fetch', fetchMock)

    await apiMethods.fetch(endpoint)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('does not resend a streamed body', async () => {
    const onUnauthorized = vi.fn()
    registerAccessTokenProvider(async () => 'token-123')
    registerUnauthorizedHandler(onUnauthorized)
    const fetchMock = vi.fn().mockImplementation(async () => unauthorized())
    vi.stubGlobal('fetch', fetchMock)

    await apiMethods.post(endpoint, new ReadableStream())

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })
})
