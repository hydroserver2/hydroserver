<template>
  <h2 class="hs-subheading mb-1">Overview</h2>

  <div class="overview-stats">
    <HsStatCard
      :icon="mdiAccountGroupOutline"
      label="Collaborators"
      :value="stats.members"
      test-id="overview-members-count"
    />
    <HsStatCard
      :icon="mdiMapMarkerOutline"
      label="Sites"
      :value="stats.sites"
      test-id="overview-sites-count"
    />
    <HsStatCard
      :icon="mdiKeyVariant"
      label="Service accounts"
      :value="stats.serviceAccounts"
      test-id="overview-service-accounts-count"
    />
    <HsStatCard
      :icon="mdiNotebookOutline"
      label="Metadata items"
      :value="stats.metadata"
      test-id="overview-metadata-count"
    />
  </div>

  <v-alert
    v-if="statsComplete && statsHaveError"
    class="mb-4"
    type="warning"
    variant="tonal"
    border="start"
  >
    Some totals could not be loaded.
  </v-alert>

  <v-table class="hs-table-card">
    <tbody>
      <tr>
        <td class="text-medium-emphasis">Owner</td>
        <td>
          {{ workspace.owner?.name || 'Unknown'
          }}<span v-if="isOwner(workspace)"> (you)</span>
        </td>
      </tr>
      <tr>
        <td class="text-medium-emphasis">Your role</td>
        <td>{{ getUserRoleName(workspace) }}</td>
      </tr>
      <tr>
        <td class="text-medium-emphasis">Visibility</td>
        <td>{{ workspace.isPrivate ? 'Private' : 'Public' }}</td>
      </tr>
      <tr>
        <td class="text-medium-emphasis">Workspace ID</td>
        <td class="workspace-id-cell">
          <span class="hs-font-data">{{ workspace.id }}</span>
          <v-btn
            size="x-small"
            variant="text"
            density="comfortable"
            color="grey-darken-2"
            :icon="mdiContentCopy"
            aria-label="Copy workspace ID"
            @click="copyId"
          />
        </td>
      </tr>
    </tbody>
  </v-table>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import hs, {
  type Collaborator,
  PermissionAction,
  PermissionResource,
  type Workspace,
} from '@hydroserver/client'
import {
  mdiAccountGroupOutline,
  mdiContentCopy,
  mdiKeyVariant,
  mdiMapMarkerOutline,
  mdiNotebookOutline,
} from '@mdi/js'
import HsStatCard from '@/components/base/HsStatCard.vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { Snackbar } from '@/utils/notifications'

const props = defineProps<{
  workspace: Workspace
  active: boolean
}>()

type OverviewStats = {
  members: number | null
  sites: number | null
  serviceAccounts: number | null
  metadata: number | null
}

const emptyStats = (): OverviewStats => ({
  members: null,
  sites: null,
  serviceAccounts: null,
  metadata: null,
})

const { getUserRoleName, hasPermission, isOwner } = useWorkspacePermissions()
const stats = ref<OverviewStats>(emptyStats())
const statsComplete = ref(false)
const statsHaveError = ref(false)
let requestId = 0

function responseData<T>(result: PromiseSettledResult<unknown>): T[] | null {
  if (result.status === 'rejected') return null
  const response = result.value as { ok?: boolean; data?: T[] } | null
  return response?.ok && Array.isArray(response.data) ? response.data : null
}

function responseCount(result: PromiseSettledResult<unknown>): number | null {
  const data = responseData(result)
  return data === null ? null : data.length
}

async function loadStats(workspace: Workspace) {
  const currentRequest = ++requestId
  stats.value = emptyStats()
  statsComplete.value = false
  statsHaveError.value = false

  const canViewServiceAccounts = hasPermission(
    PermissionResource.ServiceAccount,
    PermissionAction.View,
    workspace
  )
  const serviceAccountRequest = canViewServiceAccounts
    ? hs.workspaces.getServiceAccounts(workspace.id)
    : Promise.resolve(null)

  // Show the most useful totals before the slower, paginated metadata lists.
  const primaryResults = Promise.allSettled([
    hs.workspaces.getCollaborators(workspace.id),
    hs.monitoringSites.listSiteSummaries(workspace.id),
    serviceAccountRequest,
  ])
  const metadataResults = Promise.allSettled([
    hs.methods.list({ workspace_id: [workspace.id], fetch_all: true }),
    hs.observedProperties.list({
      workspace_id: [workspace.id],
      fetch_all: true,
    }),
    hs.processingLevels.list({
      workspace_id: [workspace.id],
      fetch_all: true,
    }),
    hs.units.list({ workspace_id: [workspace.id], fetch_all: true }),
    hs.resultQualifiers.list({
      workspace_id: [workspace.id],
      fetch_all: true,
    }),
  ])

  const primary = await primaryResults
  if (currentRequest !== requestId) return

  const counts = primary.map(responseCount)
  const collaborators = responseData<Collaborator>(primary[0])
  stats.value = {
    // The owner is not included in the collaborators response.
    members: collaborators
      ? collaborators.filter(
          (collaborator) => collaborator.user && !collaborator.serviceAccount
        ).length + 1
      : null,
    sites: counts[1],
    serviceAccounts: canViewServiceAccounts ? counts[2] : null,
    metadata: null,
  }
  statsHaveError.value =
    counts[0] === null ||
    counts[1] === null ||
    (canViewServiceAccounts && counts[2] === null)

  const metadataCounts = (await metadataResults).map(responseCount)
  if (currentRequest !== requestId) return

  const metadata = metadataCounts.every((count) => count !== null)
    ? metadataCounts.reduce<number>((total, count) => total + (count ?? 0), 0)
    : null
  stats.value.metadata = metadata
  statsHaveError.value ||= metadata === null
  statsComplete.value = true
}

watch(
  [() => props.workspace, () => props.active],
  ([workspace, active]) => {
    if (active) void loadStats(workspace)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  requestId += 1
})

async function copyId() {
  try {
    await navigator.clipboard.writeText(props.workspace.id)
    Snackbar.success('Workspace ID copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy workspace ID')
  }
}
</script>

<style scoped>
.overview-stats {
  display: flex;
  gap: var(--hs-space-12);
  margin-bottom: var(--hs-space-16);
}

.workspace-id-cell {
  overflow-wrap: anywhere;
}

.workspace-id-cell span {
  vertical-align: middle;
}

@media (max-width: 700px) {
  .overview-stats {
    flex-wrap: wrap;
  }

  :deep(.hs-stat-card) {
    flex: 1 1 calc(50% - 6px);
  }
}
</style>
