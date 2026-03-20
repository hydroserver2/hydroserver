import { computed, Ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import { useUserStore } from '@/store/user'
import {
  PermissionResource,
  PermissionAction,
  Permission,
  Workspace,
} from '@hydroserver/client'

export function useWorkspacePermissions(
  localWorkspace?: Ref<Workspace | undefined>
) {
  const { selectedWorkspace: globalStoredWorkspace, workspaces } = storeToRefs(
    useWorkspaceStore()
  )
  const { user } = storeToRefs(useUserStore())

  /** Some pages need to be in the context of a specific workspace that isn't the globally
   * selected workspace. We want to preserve the state of the global workspace so we're still
   * in that context when we navigate away from a page that needs the localWorkspace to a
   * page that needs the global workspace context.
   */
  const selectedWorkspace = computed(() => {
    if (localWorkspace?.value) return localWorkspace.value
    return globalStoredWorkspace.value
  })

  const isWorkspaceOwner = computed<boolean>(() => {
    return isOwner(selectedWorkspace.value)
  })

  function isOwner(workspace: Workspace | null) {
    if (!workspace || !user.value?.email) return false
    return workspace.owner?.email === user.value.email
  }

  function isAdmin() {
    return user.value.accountType === 'admin'
  }
  const getUserRoleName = (workspace: Workspace): string => {
    if (isOwner(workspace)) return 'Owner'
    if (workspace.collaboratorRole?.name) return workspace.collaboratorRole.name
    if (isAdmin()) return 'None (Admin)'
    return ''
  }

  const hasPermission = (
    resource: PermissionResource,
    action: PermissionAction,
    workspace?: Workspace
  ) => {
    const w = workspace ?? selectedWorkspace.value
    if (!w) return false
    if (isOwner(w) || isAdmin()) return true

    const perms = w.collaboratorRole?.permissions ?? []
    return (
      hasGlobalPermissions(perms) ||
      perms.some((p) => p.action === action && p.resource === resource)
    )
  }

  const hasGlobalPermissions = (permissions: Permission[]) =>
    permissions.some(
      (p) =>
        p.resource === PermissionResource.Global &&
        p.action === PermissionAction.Global
    )

  function checkPermissionsByWorkspaceId(
    workspaceId: string,
    permissionType: PermissionResource,
    resourceType: PermissionAction
  ) {
    const workspace = workspaces.value.find((ws) => ws.id === workspaceId)
    if (!workspace) return false

    return hasPermission(permissionType, resourceType, workspace)
  }

  return {
    isWorkspaceOwner,
    isAdmin,
    isOwner,
    hasPermission,
    checkPermissionsByWorkspaceId,
    getUserRoleName,
  }
}
