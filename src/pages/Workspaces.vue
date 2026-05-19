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
          :class="{ 'workspace-picker__item--current': selectedWorkspace?.id === ws.id }"
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
            <div class="d-flex align-center gap-3">
              <v-tooltip
                location="top"
                :text="datastreamCountTooltip(ws.id)"
              >
                <template #activator="{ props: tp }">
                  <v-chip
                    v-bind="tp"
                    size="x-small"
                    variant="tonal"
                    :color="
                      !datastreamCountsLoading && datastreamCount(ws.id) > 0
                        ? 'primary'
                        : 'grey-darken-1'
                    "
                    prepend-icon="mdi-chart-timeline-variant"
                  >
                    <template v-if="datastreamCountsLoading">…</template>
                    <template v-else>
                      {{ datastreamCount(ws.id).toLocaleString() }}
                    </template>
                  </v-chip>
                </template>
              </v-tooltip>
              <v-tooltip
                location="top"
                :text="qualifierCountTooltip(ws.id)"
              >
                <template #activator="{ props: tp }">
                  <v-chip
                    v-bind="tp"
                    size="x-small"
                    variant="tonal"
                    :color="
                      !qualifierCountsLoading && qualifierCount(ws.id) > 0
                        ? 'primary'
                        : 'grey-darken-1'
                    "
                    prepend-icon="mdi-flag-outline"
                  >
                    <template v-if="qualifierCountsLoading">…</template>
                    <template v-else>
                      {{ qualifierCount(ws.id).toLocaleString() }}
                    </template>
                  </v-chip>
                </template>
              </v-tooltip>
              <v-btn
                size="small"
                variant="flat"
                color="primary"
                :disabled="selectedWorkspace?.id === ws.id"
                @click.stop="onPick(ws.id)"
              >
                {{ selectedWorkspace?.id === ws.id ? 'Selected' : 'Select' }}
              </v-btn>
            </div>
          </template>
        </v-list-item>
        <v-divider v-if="idx < availableWorkspaces.length - 1" />
      </template>
    </v-list>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import { Workspace, Datastream, ResultQualifier } from '@hydroserver/client'
import { useWorkspaceStore } from '@/store/workspaces'
import { useHydroServer } from '@/store/hydroserver'

const router = useRouter()
const route = useRoute()
const store = useWorkspaceStore()
const { availableWorkspaces, selectedWorkspace, isLoading } = storeToRefs(store)
const { hs } = storeToRefs(useHydroServer())

/**
 * Datastream count per workspace id. Populated by a single
 * `hs.datastreams.list({ fetch_all: true })` call — the server's
 * RBAC filters to only datastreams the signed-in user can see
 * (which spans every workspace in `availableWorkspaces`), so one
 * listing bucketed by `workspaceId` is cheaper than N scoped
 * listings.
 */
const datastreamCounts = ref<Record<string, number>>({})
const datastreamCountsLoading = ref(true)

const datastreamCount = (workspaceId: string) =>
  datastreamCounts.value[workspaceId] ?? 0

const datastreamCountTooltip = (workspaceId: string) => {
  if (datastreamCountsLoading.value) return 'Counting datastreams…'
  const n = datastreamCount(workspaceId)
  return `${n.toLocaleString()} datastream${n === 1 ? '' : 's'} in this workspace`
}

/**
 * ResultQualifier count per workspace id — same bucket-by-`workspaceId`
 * pattern as the datastream count. Useful for answering "which
 * workspace has qualifiers already defined?" at a glance in the picker.
 */
const qualifierCounts = ref<Record<string, number>>({})
const qualifierCountsLoading = ref(true)

const qualifierCount = (workspaceId: string) =>
  qualifierCounts.value[workspaceId] ?? 0

const qualifierCountTooltip = (workspaceId: string) => {
  if (qualifierCountsLoading.value) return 'Counting qualifiers…'
  const n = qualifierCount(workspaceId)
  return `${n.toLocaleString()} result qualifier${n === 1 ? '' : 's'} defined in this workspace`
}

async function loadQualifierCounts() {
  qualifierCountsLoading.value = true
  try {
    const response = await hs.value.resultQualifiers.list({
      fetch_all: true,
    })
    const list = (response.data ?? []) as ResultQualifier[]
    const counts: Record<string, number> = {}
    for (const q of list) {
      const wsId = q.workspaceId
      if (!wsId) continue
      counts[wsId] = (counts[wsId] ?? 0) + 1
    }
    qualifierCounts.value = counts
  } catch (e) {
    console.error('Failed to load qualifier counts:', e)
    qualifierCounts.value = {}
  } finally {
    qualifierCountsLoading.value = false
  }
}

async function loadDatastreamCounts() {
  datastreamCountsLoading.value = true
  try {
    const response = await hs.value.datastreams.list({
      fetch_all: true,
    })
    const list = (response.data ?? []) as Datastream[]
    const counts: Record<string, number> = {}
    for (const ds of list) {
      const wsId = ds.workspaceId
      if (!wsId) continue
      counts[wsId] = (counts[wsId] ?? 0) + 1
    }
    datastreamCounts.value = counts
  } catch (e) {
    console.error('Failed to load datastream counts:', e)
    datastreamCounts.value = {}
  } finally {
    datastreamCountsLoading.value = false
  }
}

onMounted(async () => {
  // Always refresh when we land here — role changes on the server side
  // (added/removed from a workspace) should show up without a hard
  // reload. The "skip picker when a selection already exists" redirect
  // lives in `router/guards.ts` so it fires before the component
  // mounts (otherwise the picker flashes briefly on a reload).
  await store.loadWorkspaces()

  void loadDatastreamCounts()
  void loadQualifierCounts()
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

<style scoped>
/* Vuetify's default `:active` state on v-list-item is a barely-visible
   tint — easy to miss on a list of ten workspaces. Strengthen it with
   a primary-tinted background plus a left accent bar so the currently
   selected workspace is obvious at a glance. */
.workspace-picker__item--current {
  background-color: rgba(var(--v-theme-primary), 0.1);
  position: relative;
}

.workspace-picker__item--current::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background-color: rgb(var(--v-theme-primary));
}
</style>
