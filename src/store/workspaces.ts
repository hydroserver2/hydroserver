import { defineStore, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { Workspace } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'

const SELECTED_WORKSPACE_STORAGE_KEY = 'qc-app.selected-workspace-id'

/**
 * Central state for HydroServer workspace context.
 *
 * The QC app inherits HydroServer's role-based access control at the
 * workspace level. Every CRUD-ish interaction — things, datastreams,
 * observations, qualifiers — is scoped to a workspace the signed-in
 * user has been granted a role on. `hs.workspaces.list()` already
 * filters server-side to workspaces the user can see; we trust that
 * listing and let the user pick one before any data is fetched.
 *
 * The selected id is persisted to localStorage so reloads keep the
 * user in the same workspace. If that stored id is no longer in the
 * user's accessible list (role was revoked, workspace deleted), we
 * drop it and force a fresh selection.
 */
export const useWorkspaceStore = defineStore('workspaces', () => {
  const availableWorkspaces = ref<Workspace[]>([])
  const selectedWorkspace = ref<Workspace | null>(null)
  const isLoading = ref(false)

  const hasSelection = computed(() => !!selectedWorkspace.value)
  const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)

  /**
   * True when the signed-in user holds a role on the selected workspace
   * that lets them create or edit Observations. Owners always pass
   * (their `collaboratorRole` is `null` because ownership supersedes
   * collaborator roles); collaborators need at least one permission
   * that covers editing observations.
   */
  const canEditSelected = computed(() => {
    const ws = selectedWorkspace.value
    if (!ws) return false
    // Owner: `collaboratorRole` is null on owned workspaces — the role
    // machinery only applies to invited collaborators.
    if (!ws.collaboratorRole) return true
    const perms = ws.collaboratorRole.permissions ?? []
    return perms.some(
      (p) =>
        (p.action === 'edit' || p.action === 'create' || p.action === '*') &&
        (p.resource === 'Observation' || p.resource === '*')
    )
  })

  async function loadWorkspaces(): Promise<Workspace[]> {
    const { hs } = storeToRefs(useHydroServer())
    if (!hs.value) return []

    isLoading.value = true
    try {
      const response = await hs.value.workspaces.list({ fetch_all: true })
      const list = (response.data ?? []) as Workspace[]
      availableWorkspaces.value = list

      // Reconcile the stored selection against the fresh list. If the
      // previously-selected workspace is no longer accessible, drop it
      // so the UI prompts for a new choice instead of silently
      // rendering with stale/forbidden context.
      const storedId = readStoredId()
      if (storedId) {
        const match = list.find((w) => w.id === storedId)
        selectedWorkspace.value = match ?? null
        if (!match) writeStoredId(null)
      }

      return list
    } finally {
      isLoading.value = false
    }
  }

  function selectWorkspace(id: string | null): Workspace | null {
    if (!id) {
      selectedWorkspace.value = null
      writeStoredId(null)
      return null
    }
    const ws = availableWorkspaces.value.find((w) => w.id === id) ?? null
    selectedWorkspace.value = ws
    writeStoredId(ws?.id ?? null)
    return ws
  }

  function clearSelection() {
    selectedWorkspace.value = null
    writeStoredId(null)
  }

  function readStoredId(): string | null {
    try {
      return localStorage.getItem(SELECTED_WORKSPACE_STORAGE_KEY)
    } catch {
      return null
    }
  }

  function writeStoredId(id: string | null) {
    try {
      if (id) localStorage.setItem(SELECTED_WORKSPACE_STORAGE_KEY, id)
      else localStorage.removeItem(SELECTED_WORKSPACE_STORAGE_KEY)
    } catch {
      // storage may be disabled (private mode, quota exceeded) — the
      // app still works, the user just has to re-pick on reload.
    }
  }

  return {
    availableWorkspaces,
    selectedWorkspace,
    selectedWorkspaceId,
    isLoading,
    hasSelection,
    canEditSelected,
    loadWorkspaces,
    selectWorkspace,
    clearSelection,
  }
})
