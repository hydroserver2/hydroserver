<template>
  <v-container class="py-8" style="max-width: 720px">
    <div class="d-flex align-center mb-6">
      <v-icon icon="mdi-view-grid-outline" color="primary" size="28" class="mr-3" />
      <div>
        <h1 class="text-h5 mb-1">Select a workspace</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Pick the workspace you'd like to work in. Only workspaces you
          own or have been given a role on are listed.
        </p>
      </div>
    </div>

    <v-card v-if="isLoading" class="pa-6 text-center">
      <v-progress-circular indeterminate color="primary" size="32" />
      <div class="text-caption text-medium-emphasis mt-3">
        Loading workspaces…
      </div>
    </v-card>

    <v-card
      v-else-if="!availableWorkspaces.length"
      class="pa-6 text-center"
    >
      <v-icon icon="mdi-alert-outline" color="warning" size="32" class="mb-2" />
      <div class="text-body-2">
        You don't have access to any workspaces yet. Ask a workspace
        owner to add you as a collaborator, then reload this page.
      </div>
    </v-card>

    <v-list v-else class="rounded-lg elevation-1 pa-0" density="comfortable">
      <template v-for="(ws, idx) in availableWorkspaces" :key="ws.id">
        <v-list-item
          :title="ws.name"
          :active="selectedWorkspace?.id === ws.id"
          @click="onPick(ws.id)"
        >
          <template #prepend>
            <v-icon
              :icon="
                ws.isPrivate ? 'mdi-lock-outline' : 'mdi-earth'
              "
              :color="selectedWorkspace?.id === ws.id ? 'primary' : undefined"
            />
          </template>

          <template #subtitle>
            <span class="text-caption">
              {{ roleLabel(ws) }}
              <span v-if="ws.owner?.name"> · {{ ws.owner.name }}</span>
            </span>
          </template>

          <template #append>
            <v-btn
              size="small"
              variant="flat"
              color="primary"
              :disabled="selectedWorkspace?.id === ws.id"
              @click.stop="onPick(ws.id)"
            >
              {{ selectedWorkspace?.id === ws.id ? 'Selected' : 'Select' }}
            </v-btn>
          </template>
        </v-list-item>
        <v-divider v-if="idx < availableWorkspaces.length - 1" />
      </template>
    </v-list>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import { Workspace } from '@hydroserver/client'
import { useWorkspaceStore } from '@/store/workspaces'

const router = useRouter()
const route = useRoute()
const store = useWorkspaceStore()
const { availableWorkspaces, selectedWorkspace, isLoading } = storeToRefs(store)

onMounted(async () => {
  // Always refresh when we land here — role changes on the server side
  // (added/removed from a workspace) should show up without a hard
  // reload.
  await store.loadWorkspaces()

  // If the user already has a valid selection (e.g. returning from a
  // deep-linked URL after a reload), skip the picker and continue to
  // the originally-requested route.
  if (selectedWorkspace.value) {
    const next = typeof route.query.next === 'string' ? route.query.next : 'Home'
    router.replace({ name: next })
  }
})

function onPick(id: string) {
  const picked = store.selectWorkspace(id)
  if (!picked) return
  const next = typeof route.query.next === 'string' ? route.query.next : 'Home'
  router.push({ name: next })
}

function roleLabel(ws: Workspace): string {
  // Owners have `collaboratorRole === null` — the role table only
  // applies to invited collaborators.
  if (!ws.collaboratorRole) return 'Owner'
  return ws.collaboratorRole.name || 'Collaborator'
}
</script>
