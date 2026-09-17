import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { ServiceAccount } from '../../types'

describe('WorkspaceService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses the service-account endpoint for the workspace management table', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: [], meta: { offset: 0, limit: 200, totalCount: 0 } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.workspaces.getServiceAccounts('workspace-1')

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      'https://hydro.example.com/api/data/workspaces/workspace-1/service-accounts?offset=0&limit=200'
    )
  })

  it('fetches every page of workspace collaborators and merges in the sideloaded role/user/serviceAccount', async () => {
    const role = {
      id: 'role-1',
      name: 'Editor',
      description: '',
      workspaceId: 'workspace-1',
      permissions: [],
    }
    const users = [
      { name: 'First', email: 'first@example.com', organizationName: null },
      { name: 'Second', email: 'second@example.com', organizationName: null },
    ]
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = new URL(String(input)).searchParams.get('offset')
        const data =
          offset === '0'
            ? [{ userEmail: 'first@example.com', serviceAccountEmail: null, roleId: 'role-1' }]
            : [{ userEmail: 'second@example.com', serviceAccountEmail: null, roleId: 'role-1' }]

        return new Response(
          JSON.stringify({
            data,
            included: { roles: [role], users },
            meta: { offset: Number(offset), limit: 200, totalCount: 201 },
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }
        )
      })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.getCollaborators('workspace-1')

    expect(response.data.map((c) => c.user?.email)).toEqual([
      'first@example.com',
      'second@example.com',
    ])
    expect(response.data.every((c) => c.role?.id === 'role-1')).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      'https://hydro.example.com/api/data/workspaces/workspace-1/collaborators?include=role%2Cuser%2CserviceAccount&offset=0&limit=200',
      'https://hydro.example.com/api/data/workspaces/workspace-1/collaborators?include=role%2Cuser%2CserviceAccount&offset=200&limit=200',
    ])
  })

  it('reports a later collaborator page failure instead of returning partial data', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async (input: string | URL) => {
        const offset = new URL(String(input)).searchParams.get('offset')

        if (offset === '0') {
          return new Response(
            JSON.stringify({
              data: [{ email: 'first@example.com' }],
              meta: { offset: 0, limit: 200, totalCount: 201 },
            }),
            {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
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
        const offset = new URL(String(input)).searchParams.get('offset')
        const data =
          offset === '0' ? [{ id: 'account-1' }] : [{ id: 'account-2' }]

        return new Response(
          JSON.stringify({
            data,
            meta: { offset: Number(offset), limit: 200, totalCount: 201 },
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }
        )
      })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.getServiceAccounts('workspace-1')

    expect(response.data).toEqual([{ id: 'account-1' }, { id: 'account-2' }])
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      'https://hydro.example.com/api/data/workspaces/workspace-1/service-accounts?offset=0&limit=200',
      'https://hydro.example.com/api/data/workspaces/workspace-1/service-accounts?offset=200&limit=200',
    ])
  })

  it('get() always requests all three includes and merges them back inline', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            id: 'workspace-1',
            name: 'Acme',
            isPrivate: false,
            ownerEmail: 'owner@example.com',
            pendingTransferToEmail: 'recipient@example.com',
            collaboratorRoleId: 'role-1',
          },
          included: {
            owners: [{ email: 'owner@example.com', name: 'Owner' }],
            pendingTransferRecipients: [
              { email: 'recipient@example.com', name: 'Recipient' },
            ],
            collaboratorRoles: [
              { id: 'role-1', name: 'Editor', workspaceId: 'workspace-1', description: '', permissions: [] },
            ],
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.get('workspace-1')

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      'https://hydro.example.com/api/data/workspaces/workspace-1?include=owner%2CpendingTransferTo%2CcollaboratorRole'
    )
    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.owner).toEqual({ email: 'owner@example.com', name: 'Owner' })
    expect(response.data.pendingTransferTo).toEqual({
      email: 'recipient@example.com',
      name: 'Recipient',
    })
    expect(response.data.collaboratorRole).toEqual({
      id: 'role-1',
      name: 'Editor',
      workspaceId: 'workspace-1',
      description: '',
      permissions: [],
    })
  })

  it('get() leaves pendingTransferTo/collaboratorRole null when the workspace has neither', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            id: 'workspace-1',
            name: 'Acme',
            isPrivate: false,
            ownerEmail: 'owner@example.com',
            pendingTransferToEmail: null,
            collaboratorRoleId: null,
          },
          included: { owners: [{ email: 'owner@example.com', name: 'Owner' }] },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.get('workspace-1')

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.owner).toEqual({ email: 'owner@example.com', name: 'Owner' })
    expect(response.data.pendingTransferTo).toBeNull()
    expect(response.data.collaboratorRole).toBeNull()
  })

  it('createServiceAccount merges the POST key onto the fetched full row', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL) => {
      const url = String(input)
      if (url.endsWith('/service-accounts')) {
        return new Response(
          JSON.stringify({ id: 'account-1', key: 'raw-key-123' }),
          { status: 201, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return new Response(
        JSON.stringify({
          data: {
            id: 'account-1',
            name: 'CI Bot',
            description: '',
            isActive: true,
            keyExpiresAt: null,
            email: 'account-1@service-accounts.example.com',
            createdAt: '2026-01-01T00:00:00Z',
            lastUsedAt: null,
            workspaceId: 'workspace-1',
          },
          included: {},
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.createServiceAccount(
      new ServiceAccount({ workspaceId: 'workspace-1', name: 'CI Bot' }),
      'role-1'
    )

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.id).toBe('account-1')
    expect(response.data.name).toBe('CI Bot')
    expect(response.data.key).toBe('raw-key-123')
  })

  it('addCollaborator posts the new collaborator and returns the merged row from the refetched list', async () => {
    const role = {
      id: 'role-1',
      name: 'Editor',
      description: '',
      workspaceId: 'workspace-1',
      permissions: [],
    }
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
      if (init?.method === 'POST') {
        return new Response(JSON.stringify({ id: 42 }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(
        JSON.stringify({
          data: [{ userEmail: 'new@example.com', serviceAccountEmail: null, roleId: 'role-1' }],
          included: {
            roles: [role],
            users: [{ name: 'New', email: 'new@example.com', organizationName: null }],
          },
          meta: { offset: 0, limit: 200, totalCount: 1 },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.addCollaborator(
      'workspace-1',
      'new@example.com',
      'role-1'
    )

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.user?.email).toBe('new@example.com')
    expect(response.data.role?.id).toBe('role-1')
  })

  it('addCollaborator returns ok:false when the new collaborator is missing from the refetched list', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
      if (init?.method === 'POST') {
        return new Response(JSON.stringify({ id: 42 }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(
        JSON.stringify({ data: [], meta: { offset: 0, limit: 200, totalCount: 0 } }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const response = await client.workspaces.addCollaborator(
      'workspace-1',
      'missing@example.com',
      'role-1'
    )

    expect(response.ok).toBe(false)
  })

  it('regenerateServiceAccountKey merges the new key onto the passed-in account without an extra fetch', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ key: 'new-raw-key' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const account = new ServiceAccount({
      id: 'account-1',
      name: 'CI Bot',
      workspaceId: 'workspace-1',
      key: 'old-raw-key',
    })
    const response = await client.workspaces.regenerateServiceAccountKey(
      'workspace-1',
      account
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0][0])).toBe(
      'https://hydro.example.com/api/data/workspaces/workspace-1/service-accounts/account-1/regenerate'
    )
    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data).toEqual({ ...account, key: 'new-raw-key' })
  })

  it('updateServiceAccount does PATCH then re-fetches the full row', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init) => {
      const url = String(input)
      if (init?.method === 'PATCH') {
        return new Response(null, { status: 204 })
      }
      return new Response(
        JSON.stringify({
          data: {
            id: 'account-1',
            name: 'Renamed Bot',
            description: '',
            isActive: true,
            keyExpiresAt: null,
            email: 'account-1@service-accounts.example.com',
            createdAt: '2026-01-01T00:00:00Z',
            lastUsedAt: null,
            workspaceId: 'workspace-1',
          },
          included: {},
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const account = new ServiceAccount({
      id: 'account-1',
      name: 'Renamed Bot',
      workspaceId: 'workspace-1',
    })
    const response = await client.workspaces.updateServiceAccount(account)

    expect(response.ok).toBe(true)
    if (!response.ok) return
    expect(response.data.name).toBe('Renamed Bot')
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(
      true
    )
  })
})
