import { describe, expect, it } from 'vitest'
import { HydroServer } from '../HydroServer'
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
  user.accountType = 'standard'
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
    admin.accountType = 'admin'
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
