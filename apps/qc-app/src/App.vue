<template>
  <v-app>
    <v-main>
      <FullScreenLoader v-if="isLoading" />
      <router-view v-else />
    </v-main>

    <Notifications />
    <!-- One dialog for every exit from an edit session, wherever it starts. -->
    <LeaveSessionDialog />
  </v-app>
</template>

<script setup lang="ts">
import Notifications from '@/components/base/Notifications.vue'
import LeaveSessionDialog from '@/components/EditData/LeaveSessionDialog.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'

import { setupRouteGuards } from '@/router/router'
import { ref, watch, onMounted } from 'vue'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'
import { useWorkspaceCatalog } from '@/composables/useWorkspaceCatalog'
import { storeToRefs } from 'pinia'

// Session init runs in `src/main.ts` before the router installs so the
// auth guard sees `hs.session.isAuthenticated` on first navigation.
const isLoading = ref(false)

const { hs } = storeToRefs(useHydroServer())
const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())
const catalog = useWorkspaceCatalog()

// Clearing the selection wipes catalogs so stale data from the old
// workspace can't leak into the picker transition.
watch(selectedWorkspaceId, async (id, prev) => {
  if (id === prev) return
  if (!id) {
    catalog.clear()
    return
  }
  if (!hs.value) return
  isLoading.value = true
  try {
    await catalog.load(id)
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
    await catalog.load(selectedWorkspaceId.value)
  } catch (err) {
    console.error('Failed to load workspace catalog', err)
  } finally {
    isLoading.value = false
  }
})

// TODO: use route guard setup in Router v3
setupRouteGuards()
</script>
