<template>
  <v-app>
    <v-main>
      <FullScreenLoader v-if="isLoading" />
      <router-view v-else />
    </v-main>

    <Notifications />
  </v-app>
</template>

<script setup lang="ts">
import Notifications from '@/components/base/Notifications.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'

import router, { setupRouteGuards } from '@/router/router'
import { ref, watch } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'
import { storeToRefs } from 'pinia'
import {
  HydroServer,
  Datastream,
  type DatastreamExtended,
} from '@hydroserver/client'

// Use stores
const isLoading = ref(true)

const { things, processingLevels, observedProperties, datastreams } =
  storeToRefs(useDataVisStore())

const { hs } = storeToRefs(useHydroServer())
const workspaceStore = useWorkspaceStore()
const { selectedWorkspaceId, availableWorkspaces } =
  storeToRefs(workspaceStore)

/**
 * Fetch workspace-scoped catalogs (things / datastreams / processing
 * levels / observed properties) for the given workspace. Everything
 * downstream — filters, the datastream picker, QC edits — works
 * against what we load here, so re-running this is how we "switch
 * workspaces" without a full page reload.
 */
async function loadWorkspaceCatalog(workspaceId: string) {
  const [
    thingsResponse,
    datastreamsResponse,
    processingLevelsResponse,
    observedPropertiesResponse,
  ] = await Promise.all([
    hs.value.things.list({ workspace_id: workspaceId } as any),
    hs.value.datastreams.list({
      expand_related: true,
      workspace_id: workspaceId,
    } as any),
    hs.value.processingLevels.list({ workspace_id: workspaceId } as any),
    hs.value.observedProperties.list({ workspace_id: workspaceId } as any),
  ])

  things.value = thingsResponse.data
  datastreams.value = datastreamsResponse.data as (Datastream &
    DatastreamExtended)[]
  processingLevels.value = processingLevelsResponse.data
  observedProperties.value = observedPropertiesResponse.data
}

const initializeHydroServer = async () => {
  hs.value = await HydroServer.initialize({
    host: import.meta.env.VITE_APP_API_URL,
  })
  await hs.value.session.login(
    import.meta.env.VITE_APP_HS_USER,
    import.meta.env.VITE_APP_HS_PW
  )

  // Populate the workspace list first; the route guard depends on this
  // to know whether to send the user to the picker. If the persisted
  // workspace id is still in the user's accessible list, the store
  // restores the selection — otherwise selection stays null and the
  // guard redirects to /workspaces.
  await workspaceStore.loadWorkspaces()

  if (selectedWorkspaceId.value) {
    await loadWorkspaceCatalog(selectedWorkspaceId.value)
  } else if (!availableWorkspaces.value.length) {
    // No accessible workspaces — leave the catalog empty. The picker
    // page surfaces a "contact your admin" message.
  } else {
    router.replace({ name: 'Workspaces' })
  }

  isLoading.value = false
}

// Reload the catalog whenever the user commits to a different
// workspace. Clearing the selection wipes the catalogs so stale data
// from the old workspace can't leak into the picker transition.
watch(selectedWorkspaceId, async (id, prev) => {
  if (id === prev) return
  if (!id) {
    things.value = []
    datastreams.value = []
    processingLevels.value = []
    observedProperties.value = []
    return
  }
  if (!hs.value) return
  isLoading.value = true
  try {
    await loadWorkspaceCatalog(id)
  } finally {
    isLoading.value = false
  }
})

initializeHydroServer()
// TODO: use route guard setup in Router v3
setupRouteGuards()
</script>
