import { defineStore, storeToRefs } from 'pinia'
import hs, {
  Datastream,
  DatastreamExtended,
  TaskExpanded,
} from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import { useWorkspaceStore } from '@/store/workspaces'

export const useOrchestrationStore = defineStore('orchestration', () => {
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

  const workspaceId = computed(() => selectedWorkspace.value?.id ?? null)
  const workspaceDatastreams = ref<Datastream[]>([])
  const linkedDatastreams = ref<Datastream[]>([])
  const draftDatastreams = ref<DatastreamExtended[]>([])
  const workspaceTasks = ref<TaskExpanded[]>([])
  const orchestrationSearch = ref('')
  const orchestrationStatusFilter = ref<string[]>([])

  // Fetch all datastreams for the workspace once, then derive linked datastreams from task mappings
  watch(
    workspaceId,
    async (wsId) => {
      if (!wsId) {
        workspaceDatastreams.value = []
        linkedDatastreams.value = []
        return
      }
      const list = await hs.datastreams.listAllItems({ workspace_id: [wsId] })
      workspaceDatastreams.value = list ?? []
    },
    { immediate: true }
  )

  watch(
    [workspaceTasks, workspaceDatastreams],
    ([tasks, datastreams]) => {
      const ids = new Set(
        tasks.flatMap((t) =>
          (t.mappings ?? []).flatMap((m) =>
            (m.paths ?? [])
              .map((p) => p.targetIdentifier)
              .filter((id) => id !== undefined && id !== null && `${id}` !== '')
          )
        )
      )
      linkedDatastreams.value = datastreams.filter((d) => ids.has(d.id))
    },
    { immediate: true }
  )

  return {
    workspaceTasks,
    linkedDatastreams,
    draftDatastreams,
    workspaceDatastreams,
    orchestrationSearch,
    orchestrationStatusFilter,
  }
})
