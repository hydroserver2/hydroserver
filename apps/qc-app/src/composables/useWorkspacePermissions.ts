/**
 * Reactive workspace permission checks for the QC app.
 *
 * The signed-in user's role on a workspace travels with the `Workspace`
 * object: owners have a null `collaboratorRole`, collaborators carry their
 * role's `permissions[]`, and admins (`accountType === 'admin'`) override
 * everything. No separate "am I an editor" endpoint is needed — the role is
 * embedded in `hs.workspaces.list()`. (`hs.user.can()` is the async
 * single-shot equivalent; this composable is the synchronous, reactive one
 * for gating UI.)
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
  const { availableWorkspaces, selectedWorkspace } = storeToRefs(
    useWorkspaceStore()
  )
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

  /** Can create a managed datastream in this workspace (the QC setup step). */
  function canCreateDatastream(ws?: Workspace | null): boolean {
    return can(PermissionAction.Create, PermissionResource.Datastream, ws)
  }

  /**
   * Can run the QC edit workflow in this workspace — needs to create the
   * managed datastream and/or write observations. Used to gate the editor's
   * Start editing / Save / Commit controls.
   */
  function canEdit(ws?: Workspace | null): boolean {
    return (
      can(PermissionAction.Create, PermissionResource.Datastream, ws) ||
      can(PermissionAction.Edit, PermissionResource.Datastream, ws) ||
      can(PermissionAction.Create, PermissionResource.Observation, ws) ||
      can(PermissionAction.Edit, PermissionResource.Observation, ws)
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

  function workspaceById(id?: string | null): Workspace | null {
    if (!id) return null
    return availableWorkspaces.value.find((w) => w.id === id) ?? null
  }

  return {
    isAdmin,
    isOwner,
    can,
    canEdit,
    canCreateDatastream,
    roleName,
    workspaceById,
  }
}
