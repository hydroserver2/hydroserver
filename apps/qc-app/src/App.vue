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

// Session init runs in `src/main.ts` before the router installs so the
// auth guard sees `hs.session.isAuthenticated` on first navigation.
const isLoading = ref(false)

const { things, processingLevels, observedProperties, datastreams } =
  storeToRefs(useDataVisStore())

const { hs } = storeToRefs(useHydroServer())
const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())

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

  things.value = thingsResponse.ok ? thingsResponse.data : []
  datastreams.value = (datastreamsResponse.ok
    ? datastreamsResponse.data
    : []) as (Datastream & DatastreamExtended)[]
  processingLevels.value = processingLevelsResponse.ok
    ? processingLevelsResponse.data
    : []
  observedProperties.value = observedPropertiesResponse.ok
    ? observedPropertiesResponse.data
    : []
}

// Clearing the selection wipes catalogs so stale data from the old
// workspace can't leak into the picker transition.
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
  // Don't gate on `hs.session.isAuthenticated`: the session endpoint
  // returns 401 for anonymous callers on cross-origin dev setups even
  // when resource endpoints accept the request, which would leave the
  // Select view empty after every refresh.
  if (!hs.value) return
  if (!selectedWorkspaceId.value) return
  isLoading.value = true
  try {
    await loadWorkspaceCatalog(selectedWorkspaceId.value)
  } catch (err) {
    console.error('Failed to load workspace catalog', err)
  } finally {
    isLoading.value = false
  }
})

// TODO: use route guard setup in Router v3
setupRouteGuards()
</script>
