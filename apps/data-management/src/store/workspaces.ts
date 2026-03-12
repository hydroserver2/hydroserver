import { defineStore, storeToRefs } from 'pinia'
import { Workspace } from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import Storage from '@/utils/storage'
import { useUserStore } from './user'

export const selectedWorkspaceStorage = new Storage<Workspace | null>(
  'data-management-app:selectedWorkspace'
)

export const useWorkspaceStore = defineStore('workspace', () => {
  const { user } = storeToRefs(useUserStore())

  const workspaces = ref<Workspace[]>([])

  const selectedWorkspace = ref(selectedWorkspaceStorage.get() || null)
  watch(selectedWorkspace, (newWorkspace) => {
    selectedWorkspaceStorage.set(newWorkspace)
  })

  const hasWorkspaces = computed(() => workspaces.value?.length)

  const ownedWorkspaces = computed(() =>
    workspaces.value.filter(
      (ws) => !!ws.owner && ws.owner.email === user.value.email
    )
  )

  const setSelectedWorkspaceById = (workspaceId: string) => {
    const selection = workspaces.value.find((ws) => ws.id === workspaceId)
    if (selection) selectedWorkspace.value = selection
    // We're fetching workspaces on app load so this should never console.error
    else console.error('Selected workspace not in workspaces list')
  }

  const setWorkspaces = (newWorkspaces: Workspace[]) => {
    workspaces.value = newWorkspaces
    if (!workspaces.value.length) {
      selectedWorkspace.value = null
      return
    }
    workspaces.value.sort((a, b) => a.name.localeCompare(b.name))

    const currentWorkspace = workspaces.value.find(
      (ws) => selectedWorkspace.value?.id === ws.id
    )

    if (currentWorkspace) {
      // If the user has a workspace selected, and that workspace is still in
      // the workspaces array, that takes priority over the default. But we
      // still want to refresh it in case the database version has changed.
      selectedWorkspace.value = currentWorkspace
    }
    // TODO: if there is a default workspace, select it
    else {
      // If no default, then select the first in the list
      selectedWorkspace.value = workspaces.value[0]
    }
  }

  return {
    workspaces,
    selectedWorkspace,
    hasWorkspaces,
    ownedWorkspaces,
    setWorkspaces,
    setSelectedWorkspaceById,
  }
})
