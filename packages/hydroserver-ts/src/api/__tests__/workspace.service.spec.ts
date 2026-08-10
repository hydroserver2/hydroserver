import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

describe('WorkspaceService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses the service-account endpoint for the workspace management table', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.workspaces.getServiceAccounts('workspace-1')

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      'https://hydro.example.com/api/data/workspaces/workspace-1/service-accounts?page=1&page_size=200'
    )
  })

  it('fetches every page of workspace collaborators', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const page = new URL(String(input)).searchParams.get('page')
        const data =
          page === '1'
            ? [{ email: 'first@example.com' }]
            : [{ email: 'second@example.com' }]

        return new Response(JSON.stringify(data), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'X-Total-Pages': '2',
          },
        })
      })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.getCollaborators('workspace-1')

    expect(response.data).toEqual([
      { email: 'first@example.com' },
      { email: 'second@example.com' },
    ])
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      'https://hydro.example.com/api/data/workspaces/workspace-1/collaborators?page=1&page_size=200',
      'https://hydro.example.com/api/data/workspaces/workspace-1/collaborators?page=2&page_size=200',
    ])
  })

  it('reports a later collaborator page failure instead of returning partial data', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const page = new URL(String(input)).searchParams.get('page')

        if (page === '1') {
          return new Response(
            JSON.stringify([{ email: 'first@example.com' }]),
            {
              status: 200,
              headers: {
                'Content-Type': 'application/json',
                'X-Total-Pages': '2',
              },
            }
          )
        }

        return new Response(JSON.stringify({ detail: 'Page unavailable' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        })
      })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.getCollaborators('workspace-1')

    expect(response).toEqual({
      ok: false,
      status: 503,
      message: 'Page unavailable',
      data: { detail: 'Page unavailable' },
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('fetches every page of service accounts', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const page = new URL(String(input)).searchParams.get('page')
        const data =
          page === '1' ? [{ id: 'account-1' }] : [{ id: 'account-2' }]

        return new Response(JSON.stringify(data), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'X-Total-Pages': '2',
          },
        })
      })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.getServiceAccounts('workspace-1')

    expect(response.data).toEqual([{ id: 'account-1' }, { id: 'account-2' }])
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      'https://hydro.example.com/api/data/workspaces/workspace-1/service-accounts?page=1&page_size=200',
      'https://hydro.example.com/api/data/workspaces/workspace-1/service-accounts?page=2&page_size=200',
    ])
  })
})
