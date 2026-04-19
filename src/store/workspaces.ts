import { defineStore, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { Workspace } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'

const SELECTED_WORKSPACE_ID_KEY = 'qc-app.selected-workspace-id'
const SELECTED_WORKSPACE_KEY = 'qc-app.selected-workspace'

/**
 * Rehydrate the full Workspace object from localStorage at module
 * load. Called from the store factory's state initializer so the
 * selection is visible on the very first router guard evaluation.
 * Falls back to a placeholder with just the id if only the legacy
 * id key is present, so existing installs don't re-select on first
 * run with the new code.
 */
function readStoredWorkspace(): Workspace | null {
  try {
    const full = localStorage.getItem(SELECTED_WORKSPACE_KEY)
    if (full) {
      const parsed = JSON.parse(full) as Workspace
      if (parsed?.id) return parsed
    }
    const legacyId = localStorage.getItem(SELECTED_WORKSPACE_ID_KEY)
    if (legacyId) return { id: legacyId } as Workspace
  } catch {
    // storage disabled / corrupt JSON — fall through to null
  }
  return null
}

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
  // Seed the selected workspace synchronously from localStorage so the
  // router's `hasWorkspaceGuard` sees the restored selection on the
  // very first navigation. Previously the guard fired before the
  // async `loadWorkspaces` in `main.ts` resolved — with no selection
  // in memory it redirected every reload to the picker, regardless
  // of what the user had chosen in their last session. Storing the
  // full Workspace object (not just the id) means reload survives
  // even when the backend session is anonymous (e.g. dev pointing at
  // a cross-origin backend where cookies don't carry over).
  const selectedWorkspace = ref<Workspace | null>(readStoredWorkspace())
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

      // Reconcile against the fresh list: promote the stored placeholder
      // to the real Workspace object if still accessible, drop it if
      // the user lost access, keep the placeholder if the backend
      // didn't return anything (anonymous session / network error) so
      // we don't kick the user out just because `loadWorkspaces` failed.
      const storedId = selectedWorkspace.value?.id ?? readStoredId()
      if (storedId) {
        const match = list.find((w) => w.id === storedId)
        if (match) {
          selectedWorkspace.value = match
          writeStoredWorkspace(match)
        } else if (list.length > 0) {
          // List came back non-empty but didn't contain the stored id:
          // user genuinely lost access. Clear.
          selectedWorkspace.value = null
          writeStoredWorkspace(null)
        }
        // list is empty → leave the placeholder in place; the user may
        // just be unauthenticated right now.
      }

      return list
    } finally {
      isLoading.value = false
    }
  }

  function selectWorkspace(id: string | null): Workspace | null {
    if (!id) {
      selectedWorkspace.value = null
      writeStoredWorkspace(null)
      return null
    }
    const ws = availableWorkspaces.value.find((w) => w.id === id) ?? null
    selectedWorkspace.value = ws
    writeStoredWorkspace(ws)
    return ws
  }

  function clearSelection() {
    selectedWorkspace.value = null
    writeStoredWorkspace(null)
  }

  function readStoredId(): string | null {
    try {
      return localStorage.getItem(SELECTED_WORKSPACE_ID_KEY)
    } catch {
      return null
    }
  }

  function writeStoredWorkspace(ws: Workspace | null) {
    try {
      if (ws) {
        localStorage.setItem(SELECTED_WORKSPACE_KEY, JSON.stringify(ws))
        localStorage.setItem(SELECTED_WORKSPACE_ID_KEY, ws.id)
      } else {
        localStorage.removeItem(SELECTED_WORKSPACE_KEY)
        localStorage.removeItem(SELECTED_WORKSPACE_ID_KEY)
      }
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
