/**
 * Synchronous, reactive permission checks for gating UI. The user's role
 * comes with each `Workspace`: owners have a null `collaboratorRole`,
 * collaborators carry its `permissions`, and admins can do everything.
 */

import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import {
  PermissionAction,
  PermissionResource,
  type Permission,
  type Workspace,
} from '@hydroserver/client'
import { useWorkspaceStore } from '@/store/workspaces'
import { useUserStore } from '@/store/user'

export function useWorkspacePermissions() {
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
  const { user } = storeToRefs(useUserStore())

  const isAdmin = computed(
    () => (user.value?.accountType as string) === 'admin'
  )

  function isOwner(ws?: Workspace | null): boolean {
    if (!ws) return false
    if (ws.owner?.email && user.value?.email) {
      return ws.owner.email === user.value.email
    }
    // Owned workspaces carry a null collaboratorRole.
    return ws.collaboratorRole == null
  }

  function hasGlobal(perms: Permission[]): boolean {
    return perms.some(
      (p) =>
        p.resource === PermissionResource.Global &&
        p.action === PermissionAction.Global
    )
  }

  function can(
    action: PermissionAction,
    resource: PermissionResource,
    ws?: Workspace | null
  ): boolean {
    const w = ws ?? selectedWorkspace.value
    if (!w) return false
    if (isOwner(w) || isAdmin.value) return true
    const perms = w.collaboratorRole?.permissions ?? []
    return (
      hasGlobal(perms) ||
      perms.some((p) => p.action === action && p.resource === resource)
    )
  }

  /** Can work in QC sessions: the API checks datastream edit for sessions
   *  and their operations. Gates Edit, New session and Save. */
  function canEdit(ws?: Workspace | null): boolean {
    return can(PermissionAction.Edit, PermissionResource.Datastream, ws)
  }

  /** Commit also writes the managed datastream's observations. */
  function canCommit(ws?: Workspace | null): boolean {
    return (
      canEdit(ws) &&
      can(PermissionAction.Create, PermissionResource.Observation, ws)
    )
  }

  /** Creating a managed datastream also creates its QC history, which needs
   *  datastream edit. */
  function canCreateDatastream(ws?: Workspace | null): boolean {
    return (
      canEdit(ws) &&
      can(PermissionAction.Create, PermissionResource.Datastream, ws)
    )
  }

  /** Human-readable role label for display. */
  function roleName(ws?: Workspace | null): string {
    const w = ws ?? selectedWorkspace.value
    if (!w) return ''
    if (isOwner(w)) return 'Owner'
    if (w.collaboratorRole?.name) return w.collaboratorRole.name
    if (isAdmin.value) return 'Admin'
    return 'Read-only'
  }

  return {
    canEdit,
    canCommit,
    canCreateDatastream,
    roleName,
  }
}
