<template>
  <HsEmptyState
    :icon="mdiLockOutline"
    eyebrow="403 — Access denied"
    title="You don't have access to this workspace"
  >
    <p v-if="workspaceId" class="mb-4">
      Requested workspace: <strong>{{ workspaceId }}</strong>
    </p>
    <p>
      Choose an available workspace, or ask its owner or an administrator for
      access.
    </p>
    <template #actions>
      <v-btn-page-action :to="{ name: 'Workspaces' }">
        Open workspaces
      </v-btn-page-action>
      <v-btn-cancel v-if="workspaceId" @click="retryAccess">
        Try again
      </v-btn-cancel>
      <v-btn-cancel :to="{ name: 'Browse' }">
        Browse monitoring sites
      </v-btn-cancel>
    </template>
  </HsEmptyState>
</template>

<script setup lang="ts">
import { HsEmptyState } from '@hydroserver/design-system/vue'
import { mdiLockOutline } from '@mdi/js'

defineProps<{ workspaceId?: string }>()

// A full reload refreshes the user and workspace list before checking access.
const retryAccess = () => window.location.reload()
</script>
