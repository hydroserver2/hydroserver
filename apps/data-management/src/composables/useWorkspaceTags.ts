import { useWorkspaceStore } from '@/store/workspaces'
import hs, { Workspace } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { ref, computed, Ref, watch } from 'vue'

interface TagsMap {
  [key: string]: string[]
}

export function useWorkspaceTags(localWorkspace?: Ref<Workspace | undefined>) {
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

  const effectiveWorkspace = computed(() => {
    if (localWorkspace?.value) return localWorkspace.value
    return selectedWorkspace.value
  })

  const workspaceId = computed(() => effectiveWorkspace.value?.id ?? null)

  const tags = ref<TagsMap>({})

  /**
   * Watch the effective workspace ID. When it changes (including on first mount),
   *    immediately fetch metadata if a valid workspace ID is available.
   */
  watch(
    workspaceId,
    async (id) => {
      if (id) {
        const res = await hs.things.getTagKeys({ workspace_id: id })
        tags.value = res.data
      }
    },
    { immediate: true }
  )

  return { tags }
}
