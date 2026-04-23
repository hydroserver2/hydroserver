import { defineStore, storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { ResultQualifier } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'

export interface Qualifier {
  id: string
  code: string
  description: string
  /** Server-side workspace scope. Present on records loaded from
   *  `hs.resultQualifiers.list`; empty on the (rare) unsaved local
   *  fallbacks that get created before the workspace is known. */
  workspaceId?: string
}

export interface QualifierApplication {
  qualifierId: string
  appliedAt: string
  appliedBy: string
}

type ApplicationsByIndex = Record<number, QualifierApplication[]>
type ApplicationsByDatastream = Record<string, ApplicationsByIndex>

export const useQualifierStore = defineStore(
  'qualifiers',
  () => {
    const qualifiers = ref<Qualifier[]>([])
    const applied = ref<ApplicationsByDatastream>({})
    const isLoading = ref(false)

    const qualifierById = computed<Record<string, Qualifier>>(() =>
      Object.fromEntries(qualifiers.value.map((q) => [q.id, q]))
    )

    /**
     * Load the workspace-scoped ResultQualifier dictionary from
     * HydroServer. Called on app init and whenever the active
     * workspace changes (see the watcher below). Replaces the
     * previous hard-coded seed list.
     */
    async function loadQualifiers() {
      const { hs } = storeToRefs(useHydroServer())
      const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())
      if (!hs.value || !selectedWorkspaceId.value) {
        qualifiers.value = []
        return
      }

      isLoading.value = true
      try {
        const response = await hs.value.resultQualifiers.list({
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          workspace_id: selectedWorkspaceId.value,
          fetch_all: true,
        } as any)
        const list = (response.data ?? []) as ResultQualifier[]
        qualifiers.value = list.map((q) => ({
          id: q.id,
          code: q.code,
          description: q.description,
          workspaceId: q.workspaceId,
        }))
      } catch (e) {
        console.error('Failed to load result qualifiers:', e)
      } finally {
        isLoading.value = false
      }
    }

    // Load on setup, then reload whenever the active workspace
    // changes, so the picker / qualifier band only ever shows codes
    // the user has access to in the current context.
    watch(
      () => useWorkspaceStore().selectedWorkspaceId,
      () => {
        void loadQualifiers()
      },
      { immediate: true }
    )

    // `qualifiers` loads asynchronously from the server. If `applied`
    // is populated before the dictionary arrives, `buildQualifierBand`
    // drops every application whose `qualifierId` isn't yet in
    // `qualifierById` — the band paints, then disappears on the next
    // redraw. Trigger a zoom-preserving replot once the dictionary
    // arrives so the band re-materialises against the freshly loaded
    // codes.
    watch(
      () => qualifiers.value.length,
      async () => {
        const { usePlotlyStore } = await import('@/store/plotly')
        const { handleNewPlot } = await import('@/utils/plotting/plotly')
        const plotStore = usePlotlyStore()
        if (!plotStore.plotlyRef) return
        plotStore.updateOptions()
        await handleNewPlot(undefined, { preserveZoom: true })
      }
    )

    /**
     * Create a ResultQualifier on the server for the active workspace.
     * Falls back to a purely local record (no `workspaceId`) if no
     * workspace is selected — that's the only path on which an entry
     * can exist without a server id; callers that need persistence
     * should wait until a workspace is active.
     */
    async function createQualifier(
      code: string,
      description: string
    ): Promise<Qualifier> {
      const existing = qualifiers.value.find(
        (q) => q.code.toLowerCase() === code.toLowerCase()
      )
      if (existing) return existing

      const { hs } = storeToRefs(useHydroServer())
      const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())
      if (hs.value && selectedWorkspaceId.value) {
        try {
          const body = new ResultQualifier()
          body.code = code.trim()
          body.description = description.trim()
          body.workspaceId = selectedWorkspaceId.value
          const response = await hs.value.resultQualifiers.create(body)
          const saved = response.data as ResultQualifier | undefined
          if (saved?.id) {
            const q: Qualifier = {
              id: saved.id,
              code: saved.code,
              description: saved.description,
              workspaceId: saved.workspaceId,
            }
            qualifiers.value.push(q)
            return q
          }
        } catch (e) {
          console.error('Failed to create result qualifier:', e)
        }
      }

      // Local fallback so the UI doesn't lose the user's input if the
      // server call failed or no workspace was active.
      const fallback: Qualifier = {
        id: `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
        code: code.trim(),
        description: description.trim(),
      }
      qualifiers.value.push(fallback)
      return fallback
    }

    function applyQualifiers(
      datastreamId: string,
      indices: number[],
      qualifierIds: string[],
      appliedBy: string
    ) {
      if (!datastreamId || !indices?.length || !qualifierIds?.length) return

      const appliedAt = new Date().toISOString()
      const dsMap = { ...(applied.value[datastreamId] ?? {}) }

      for (const i of indices) {
        const existing = dsMap[i] ? [...dsMap[i]] : []
        for (const qid of qualifierIds) {
          if (!existing.some((a) => a.qualifierId === qid)) {
            existing.push({ qualifierId: qid, appliedAt, appliedBy })
          }
        }
        dsMap[i] = existing
      }

      applied.value = { ...applied.value, [datastreamId]: dsMap }
    }

    function removeQualifier(
      datastreamId: string,
      index: number,
      qualifierId: string
    ) {
      const dsMap = applied.value[datastreamId]
      if (!dsMap || !dsMap[index]) return
      const remaining = dsMap[index].filter((a) => a.qualifierId !== qualifierId)
      const next = { ...dsMap }
      if (remaining.length) next[index] = remaining
      else delete next[index]
      applied.value = { ...applied.value, [datastreamId]: next }
    }

    /**
     * Returns, for a datastream, one entry per (qualifierId, dataIndex) application
     * suitable for plotting as markers.
     */
    function getApplicationsForDatastream(datastreamId: string) {
      const dsMap = applied.value[datastreamId]
      if (!dsMap) return [] as Array<{
        index: number
        qualifierId: string
        appliedAt: string
        appliedBy: string
      }>
      const out: Array<{
        index: number
        qualifierId: string
        appliedAt: string
        appliedBy: string
      }> = []
      for (const [idxStr, apps] of Object.entries(dsMap)) {
        const index = Number(idxStr)
        for (const a of apps) {
          out.push({ index, ...a })
        }
      }
      return out
    }

    function getApplicationsAtIndex(datastreamId: string, index: number) {
      return applied.value[datastreamId]?.[index] ?? []
    }

    return {
      qualifiers,
      applied,
      isLoading,
      qualifierById,
      loadQualifiers,
      createQualifier,
      applyQualifiers,
      removeQualifier,
      getApplicationsForDatastream,
      getApplicationsAtIndex,
    }
  },
  {
    // Persist only the per-observation application map — the
    // dictionary is reloaded from the server on every workspace
    // change, and persisting it would compete with that fresh data.
    persist: {
      pick: ['applied'],
    },
  }
)
