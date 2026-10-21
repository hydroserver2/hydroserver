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
        PermissionResource.ServiceAccount,
        PermissionAction.View,
        workspace
      )
    ).toBe(true)
    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ServiceAccount,
        PermissionAction.Create,
        workspace
      )
    ).toBe(false)
  })

  it('matches the ServiceAccount resource value returned by the API', () => {
    const workspace = workspaceWithPermissions([
      {
        action: PermissionAction.View,
        resource: 'ServiceAccount' as PermissionResource,
      },
    ])

    expect(PermissionResource.ServiceAccount).toBe('ServiceAccount')
    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ServiceAccount,
        PermissionAction.View,
        workspace
      )
    ).toBe(true)
  })

  it.each([PermissionResource.Global, PermissionResource.Workspace])(
    'reserves workspace management for owners and admins despite %s grants',
    (resource) => {
      const workspace = workspaceWithPermissions(
        Object.values(PermissionAction).map((action) => ({ resource, action }))
      )
      const { hasPermission } = useWorkspacePermissions()

      expect(
        hasPermission(
          PermissionResource.Workspace,
          PermissionAction.View,
          workspace
        )
      ).toBe(true)
      for (const action of [PermissionAction.Edit, PermissionAction.Delete]) {
        expect(
          hasPermission(PermissionResource.Workspace, action, workspace)
        ).toBe(false)

        useUserStore().user.email = 'owner@example.com'
        expect(
          hasPermission(PermissionResource.Workspace, action, workspace)
        ).toBe(true)

        useUserStore().user.email = 'admin@example.com'
        useUserStore().user.isSuperuser = true
        expect(
          hasPermission(PermissionResource.Workspace, action, workspace)
        ).toBe(true)

        useUserStore().user.isSuperuser = false
        useUserStore().user.email = 'viewer@example.com'
      }
    }
  )

  it('applies a resource wildcard only to the explicitly granted action', () => {
    const workspace = workspaceWithPermissions([
      {
        action: PermissionAction.Edit,
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
    expect(
      useWorkspacePermissions().hasPermission(
        PermissionResource.ResultQualifier,
        PermissionAction.Delete,
        workspace
      )
    ).toBe(false)
  })

  it('exposes every permission resource returned by the API contract', () => {
    expect(Object.values(PermissionResource)).toEqual(
      expect.arrayContaining([
        'Role',
        'DataConnection',
        'EtlTask',
        'RatingCurve',
        'DataProductTask',
        'MonitoringTask',
      ])
    )
  })
})
