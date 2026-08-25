<template>
  <v-container class="workspace-picker-page">
    <div class="workspace-picker-page__header">
      <v-icon icon="mdi-view-grid-outline" color="primary" size="28" />
      <div>
        <h1 class="hs-heading workspace-picker-page__title">
          Select a workspace
        </h1>
        <p class="hs-text-sm text-medium-emphasis mb-0">
          Pick the workspace you'd like to work in. Only workspaces you own or
          have been given a role on are listed.
        </p>
      </div>
    </div>

    <v-card v-if="isLoading" class="workspace-picker-page__loading text-center">
      <v-progress-circular indeterminate color="primary" size="32" />
      <div class="hs-text-sm text-medium-emphasis mt-3">
        Loading workspaces…
      </div>
    </v-card>

    <HsEmptyState
      v-else-if="!availableWorkspaces.length"
      :icon="mdiAlertOutline"
      title="No workspaces available"
    >
      <p>
        You don't have access to any workspaces yet. Ask a workspace owner to
        add you as a collaborator, then reload this page.
      </p>
    </HsEmptyState>

    <v-list v-else class="workspace-picker-list pa-0" density="comfortable">
      <template v-for="(ws, idx) in availableWorkspaces" :key="ws.id">
        <v-list-item
          :title="ws.name"
          :active="selectedWorkspace?.id === ws.id"
          :class="{
            'workspace-picker__item--current': selectedWorkspace?.id === ws.id,
          }"
          @click="onPick(ws.id)"
        >
          <template #prepend>
            <v-icon
              :icon="ws.isPrivate ? 'mdi-lock-outline' : 'mdi-earth'"
              :color="selectedWorkspace?.id === ws.id ? 'primary' : undefined"
            />
          </template>

          <template #subtitle>
            <span class="text-body-small">
              {{ roleLabel(ws) }}
              <span v-if="ws.owner?.name"> · {{ ws.owner.name }}</span>
            </span>
          </template>

          <template #append>
            <div class="d-flex align-center ga-3">
              <v-tooltip location="top" :text="datastreamCountTooltip(ws.id)">
                <template #activator="{ props: tp }">
                  <v-chip
                    v-bind="tp"
                    size="x-small"
                    variant="tonal"
                    :color="
                      !datastreamCountsLoading && datastreamCount(ws.id) > 0
                        ? 'primary'
                        : 'default'
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
              <v-tooltip location="top" :text="qualifierCountTooltip(ws.id)">
                <template #activator="{ props: tp }">
                  <v-chip
                    v-bind="tp"
                    size="x-small"
                    variant="tonal"
                    :color="
                      !qualifierCountsLoading && qualifierCount(ws.id) > 0
                        ? 'primary'
                        : 'default'
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
              <v-btn-primary
                size="small"
                :disabled="selectedWorkspace?.id === ws.id"
                @click.stop="onPick(ws.id)"
              >
                {{ selectedWorkspace?.id === ws.id ? 'Selected' : 'Select' }}
              </v-btn-primary>
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
import { mdiAlertOutline } from '@mdi/js'
import { HsEmptyState } from '@hydroserver/design-system/vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { useHydroServer } from '@/store/hydroserver'

const router = useRouter()
const route = useRoute()
const store = useWorkspaceStore()
const { availableWorkspaces, selectedWorkspace, isLoading } = storeToRefs(store)
const { hs } = storeToRefs(useHydroServer())

// One unscoped listing bucketed by workspaceId is cheaper than N
// scoped listings: server RBAC already filters to visible datastreams.
const datastreamCounts = ref<Record<string, number>>({})
const datastreamCountsLoading = ref(true)

const datastreamCount = (workspaceId: string) =>
  datastreamCounts.value[workspaceId] ?? 0

const datastreamCountTooltip = (workspaceId: string) => {
  if (datastreamCountsLoading.value) return 'Counting datastreams…'
  const n = datastreamCount(workspaceId)
  return `${n.toLocaleString()} datastream${n === 1 ? '' : 's'} in this workspace`
}

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
    const list = (response.ok ? response.data : []) as ResultQualifier[]
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
    const list = (response.ok ? response.data : []) as Datastream[]
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
  // Always refresh: server-side role changes should show up without a
  // hard reload. The "skip picker when a selection exists" redirect
  // lives in `router/guards.ts` so it fires before mount (otherwise
  // the picker flashes briefly on reload).
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
  // Owners have `collaboratorRole === null`.
  if (!ws.collaboratorRole) return 'Owner'
  return ws.collaboratorRole.name || 'Collaborator'
}
</script>

<style scoped>
.workspace-picker-page {
  max-width: 720px;
  padding-block: var(--hs-space-32);
}

.workspace-picker-page__header {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
  margin-bottom: var(--hs-space-24);
}

.workspace-picker-page__title {
  margin-bottom: var(--hs-space-4);
}

.workspace-picker-page__loading {
  padding: var(--hs-space-24);
}

.workspace-picker-list {
  overflow: hidden;
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-lg);
  box-shadow: var(--hs-shadow-popover);
}

/* Vuetify's default `:active` v-list-item tint is too subtle on a long
   list. Strengthen with a primary-tinted background and left accent bar. */
.workspace-picker__item--current {
  background-color: rgb(var(--v-theme-primary) / 0.1);
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
