import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { registerAccessTokenProvider } from '../requestInterceptor'
import { User, Workspace } from '../../types'

function makeClientWithCachedUser(user: User): HydroServer {
  const client = new HydroServer({ host: 'https://hydro.example.com' })
  // Bypass the DOM script-tag lookup resolveCachedUser() would otherwise do;
  // any defined value (not `undefined`) short-circuits straight to it.
  ;(client.user as any)._cachedUser = user
  return client
}

function makeStandardUser(email = 'collaborator@example.com'): User {
  const user = new User()
  user.email = email
  return user
}

function makeWorkspace(overrides: Partial<Workspace> = {}): Workspace {
  const workspace = new Workspace()
  workspace.owner = { name: 'Owner', email: 'owner@example.com' }
  Object.assign(workspace, overrides)
  return workspace
}

describe('UserService.can', () => {
  it('allows an admin regardless of role permissions', async () => {
    const admin = makeStandardUser('admin@example.com')
    admin.isSuperuser = true
    const client = makeClientWithCachedUser(admin)
    const workspace = makeWorkspace()

    await expect(
      client.user.can('delete', 'Datastream', workspace)
    ).resolves.toBe(true)
  })

  it('allows the workspace owner regardless of role permissions', async () => {
    const owner = makeStandardUser('owner@example.com')
    const client = makeClientWithCachedUser(owner)
    const workspace = makeWorkspace()

    await expect(
      client.user.can('delete', 'Datastream', workspace)
    ).resolves.toBe(true)
  })

  it('allows a collaborator whose role grants the exact action/resource', async () => {
    const user = makeStandardUser()
    const client = makeClientWithCachedUser(user)
    const workspace = makeWorkspace({
      collaboratorRole: {
        name: 'Editor',
        description: '',
        id: 'role-1',
        workspaceId: 'ws-1',
        permissions: [{ action: 'edit', resource: 'Datastream' }],
      },
    })

    await expect(
      client.user.can('edit', 'Datastream', workspace)
    ).resolves.toBe(true)
  })

  it('allows a collaborator whose role grants the action on all resources via "*"', async () => {
    const user = makeStandardUser()
    const client = makeClientWithCachedUser(user)
    const workspace = makeWorkspace({
      collaboratorRole: {
        name: 'Editor',
        description: '',
        id: 'role-1',
        workspaceId: 'ws-1',
        permissions: [{ action: 'edit', resource: '*' }],
      },
    })

    await expect(
      client.user.can('edit', 'MonitoringSite', workspace)
    ).resolves.toBe(true)
  })

  it('denies a collaborator whose role does not grant the requested action/resource', async () => {
    const user = makeStandardUser()
    const client = makeClientWithCachedUser(user)
    const workspace = makeWorkspace({
      collaboratorRole: {
        name: 'Viewer',
        description: '',
        id: 'role-1',
        workspaceId: 'ws-1',
        permissions: [{ action: 'view', resource: 'Datastream' }],
      },
    })

    await expect(
      client.user.can('delete', 'Datastream', workspace)
    ).resolves.toBe(false)
  })

  it('denies a collaborator with no role on the workspace', async () => {
    const user = makeStandardUser()
    const client = makeClientWithCachedUser(user)
    const workspace = makeWorkspace()

    await expect(
      client.user.can('view', 'Datastream', workspace)
    ).resolves.toBe(false)
  })
})

describe('UserService with an access token provider', () => {
  afterEach(() => {
    registerAccessTokenProvider(null)
    vi.unstubAllGlobals()
  })

  it('fetches the user from the OIDC UserInfo endpoint', async () => {
    const client = await HydroServer.initialize({
      host: 'https://hydro.example.com',
      accessTokenProvider: async () => 'token-123',
    })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ email: 'user@example.com' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await client.user.get()

    expect(response.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('https://hydro.example.com/identity/o/api/userinfo')
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer token-123')
  })

  const userInfoResponse = (email: string) =>
    new Response(JSON.stringify({ email }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })

  it('reuses the cached user while the token is unchanged', async () => {
    const client = await HydroServer.initialize({
      host: 'https://hydro.example.com',
      accessTokenProvider: async () => 'token-123',
    })
    const fetchMock = vi.fn().mockResolvedValue(userInfoResponse('user@example.com'))
    vi.stubGlobal('fetch', fetchMock)

    await client.user.get()
    const response = await client.user.get()

    expect(response.ok && response.data.email).toBe('user@example.com')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not return the cached user after the token is gone', async () => {
    let token: string | null = 'token-123'
    const client = await HydroServer.initialize({
      host: 'https://hydro.example.com',
      accessTokenProvider: async () => token,
    })
    const fetchMock = vi.fn().mockResolvedValue(userInfoResponse('user@example.com'))
    vi.stubGlobal('fetch', fetchMock)
    await client.user.get()

    token = null
    const response = await client.user.get()

    expect(response.ok).toBe(false)
    expect(response.status).toBe(401)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('fetches the user again when the token changes', async () => {
    let token = 'token-a'
    const client = await HydroServer.initialize({
      host: 'https://hydro.example.com',
      accessTokenProvider: async () => token,
    })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(userInfoResponse('a@example.com'))
      .mockResolvedValueOnce(userInfoResponse('b@example.com'))
    vi.stubGlobal('fetch', fetchMock)
    await client.user.get()

    token = 'token-b'
    const response = await client.user.get()

    expect(response.ok && response.data.email).toBe('b@example.com')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
