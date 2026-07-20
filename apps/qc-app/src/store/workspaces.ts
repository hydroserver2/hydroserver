import { defineStore, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { Workspace } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'

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
  // `selectedWorkspace` is persisted (see the `persist` config below)
  // so the router's `hasWorkspaceGuard` sees the restored selection on
  // the very first navigation. Storing the full Workspace object (not
  // just the id) means reload survives even when the backend session
  // is anonymous (e.g. dev pointing at a cross-origin backend where
  // cookies don't carry over).
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
      const list = (response.ok ? response.data : []) as Workspace[]
      availableWorkspaces.value = list

      // Reconcile against the fresh list: promote the stored placeholder
      // to the real Workspace object if still accessible, drop it if
      // the user lost access, keep the placeholder if the backend
      // didn't return anything (anonymous session / network error) so
      // we don't kick the user out just because `loadWorkspaces` failed.
      const storedId = selectedWorkspace.value?.id ?? null
      if (storedId) {
        const match = list.find((w) => w.id === storedId)
        if (match) {
          selectedWorkspace.value = match
        } else if (list.length > 0) {
          // List came back non-empty but didn't contain the stored id:
          // user genuinely lost access. Clear.
          selectedWorkspace.value = null
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
      return null
    }
    const ws = availableWorkspaces.value.find((w) => w.id === id) ?? null
    selectedWorkspace.value = ws
    return ws
  }

  /**
   * Apply a workspace selection by id, falling back to a placeholder
   * `{ id }` object when the full Workspace isn't in
   * `availableWorkspaces` yet. Used by shared-link hydration in
   * `main.ts` and the matching router guard — those can fire before
   * `loadWorkspaces` has populated the list (e.g. cross-origin dev
   * setups where the session endpoint 401s silently, or a fresh boot
   * where the list fetch is still in flight). The downstream catalog
   * load in App.vue only reads `selectedWorkspaceId`, so a placeholder
   * is enough to get the right data loaded; `loadWorkspaces` will
   * promote the placeholder to the real object when it next runs.
   */
  function applyWorkspaceById(id: string): Workspace | null {
    if (!id) return null
    if (selectedWorkspace.value?.id === id) return selectedWorkspace.value
    const match =
      availableWorkspaces.value.find((w) => w.id === id) ??
      ({ id } as Workspace)
    selectedWorkspace.value = match
    return match
  }

  function clearSelection() {
    selectedWorkspace.value = null
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
    applyWorkspaceById,
    clearSelection,
  }
}, {
  // Only the user's selection needs to survive reloads; the list of
  // available workspaces is refetched on every session from the
  // server. The `:v1` suffix lets us invalidate stored selections by
  // bumping the version when the persisted shape changes (matches the
  // `qc-utils:calibration:v1` template).
  persist: {
    key: 'qc:selectedWorkspace:v1',
    pick: ['selectedWorkspace'],
  },
})
