import { computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'

// Load once per mapping view, rather than once per target card or only when
// opening the task editor. The store reuses metadata for the same workspace.
export function useMappingDatastreams() {
  const store = useOrchestrationStore()
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
  const workspaceId = computed(() => selectedWorkspace.value?.id ?? null)
  watch(
    workspaceId,
    async (id) => {
      if (!id) return
      try {
        await Promise.all([
          store.ensureWorkspaceDatastreams(id),
          store.ensureWorkspaceMonitoringSites(id),
        ])
      } catch (error) {
        console.error('Error fetching mapping target details', error)
      }
    },
    { immediate: true }
  )
}
