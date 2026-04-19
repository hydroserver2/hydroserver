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

import { setupRouteGuards } from '@/router/router'
import { ref, watch, onMounted } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'
import { storeToRefs } from 'pinia'
import type { Datastream, DatastreamExtended } from '@hydroserver/client'

// Session init + user/workspace rehydration now lives in `src/main.ts`
// (mirrors the data-management-app boot flow) and runs before the
// router is installed, so the auth guard can already see
// `hs.session.isAuthenticated` on the first navigation. This component
// only drives the workspace-scoped catalog load.
const isLoading = ref(false)

const { things, processingLevels, observedProperties, datastreams } =
  storeToRefs(useDataVisStore())

const { hs } = storeToRefs(useHydroServer())
const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())

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

onMounted(async () => {
  // Seed the catalog on the first mount if the user arrives already
  // authenticated with a persisted workspace selection (the common
  // reload case). The selection is restored by `useWorkspaceStore`
  // during `loadWorkspaces()` in `main.ts`.
  if (!hs.value?.session?.isAuthenticated) return
  if (!selectedWorkspaceId.value) return
  isLoading.value = true
  try {
    await loadWorkspaceCatalog(selectedWorkspaceId.value)
  } finally {
    isLoading.value = false
  }
})

// TODO: use route guard setup in Router v3
setupRouteGuards()
</script>
