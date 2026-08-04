import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  PermissionAction,
  PermissionResource,
  Workspace,
} from '@hydroserver/client'
import { useUserStore } from '@/store/user'
import { useWorkspacePermissions } from '../useWorkspacePermissions'

const workspaceWithPermissions = (
  permissions: { action: PermissionAction; resource: PermissionResource }[]
) =>
  ({
    id: 'workspace-id',
    name: 'Workspace',
    owner: { email: 'owner@example.com' },
    collaboratorRole: { permissions },
  }) as Workspace

describe('useWorkspacePermissions', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    useUserStore().user.email = 'viewer@example.com'
  })

  it('applies a resource wildcard to the requested resource', () => {
    const workspace = workspaceWithPermissions([
      {
        action: PermissionAction.View,
        resource: PermissionResource.Global,
      },
    ])

    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ApiKey,
        PermissionAction.View,
        workspace
      )
    ).toBe(true)
    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ApiKey,
        PermissionAction.Create,
        workspace
      )
    ).toBe(false)
  })

  it('matches the APIKey resource value returned by the API', () => {
    const workspace = workspaceWithPermissions([
      {
        action: PermissionAction.View,
        resource: 'APIKey' as PermissionResource,
      },
    ])

    expect(PermissionResource.ApiKey).toBe('APIKey')
    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ApiKey,
        PermissionAction.View,
        workspace
      )
    ).toBe(true)
  })

  it('applies an action wildcard to the requested action', () => {
    const workspace = workspaceWithPermissions([
      {
        action: PermissionAction.Global,
        resource: PermissionResource.Collaborator,
      },
    ])

    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.Collaborator,
        PermissionAction.Delete,
        workspace
      )
    ).toBe(true)
    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ApiKey,
        PermissionAction.Delete,
        workspace
      )
    ).toBe(false)
  })

  it('applies a global wildcard permission to every action and resource', () => {
    const workspace = workspaceWithPermissions([
      {
        action: PermissionAction.Global,
        resource: PermissionResource.Global,
      },
    ])

    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ResultQualifier,
        PermissionAction.Edit,
        workspace
      )
    ).toBe(true)
  })
})
