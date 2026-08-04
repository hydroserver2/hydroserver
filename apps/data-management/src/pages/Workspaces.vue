<template>
  <div v-if="isPageLoaded" class="workspaces-page">
    <div class="workspaces-page-toolbar">
      <div class="workspaces-header">
        <div class="workspaces-header-inner">
          <h1 class="workspaces-header-title">Manage workspaces</h1>
        </div>
      </div>

      <v-alert
        v-if="pendingWorkspaces.length"
        class="pending-transfer-alert"
        type="info"
        variant="tonal"
        border="start"
        :icon="mdiTransitTransfer"
        data-testid="pending-transfers-banner"
      >
        <div
          v-for="ws in pendingWorkspaces"
          :key="ws.id"
          class="d-flex align-center flex-wrap ga-2"
        >
          <span>
            <strong>{{ ws.name }}</strong> — {{ ws.owner?.name }} wants to
            transfer ownership of this workspace to you.
          </span>
          <v-spacer />
          <v-btn-cancel
            density="comfortable"
            :loading="
              pendingTransferActionId === ws.id &&
              pendingTransferActionType === 'decline'
            "
            :disabled="
              !!pendingTransferActionId &&
              (pendingTransferActionId !== ws.id ||
                pendingTransferActionType !== 'decline')
            "
            :aria-label="`Decline transfer of ${ws.name}`"
            @click="onCancelTransfer(ws)"
          >
            Decline
          </v-btn-cancel>
          <v-btn
            color="green-darken-2"
            density="comfortable"
            :prepend-icon="mdiCheck"
            :loading="
              pendingTransferActionId === ws.id &&
              pendingTransferActionType === 'accept'
            "
            :disabled="
              !!pendingTransferActionId &&
              (pendingTransferActionId !== ws.id ||
                pendingTransferActionType !== 'accept')
            "
            :aria-label="`Accept transfer of ${ws.name}`"
            @click="onAcceptTransfer(ws)"
          >
            Accept transfer
          </v-btn>
        </div>
      </v-alert>

      <v-alert
        v-if="workspaceLoadError && selected"
        class="workspace-load-alert"
        type="error"
        variant="tonal"
        border="start"
      >
        <div class="d-flex align-center flex-wrap ga-2">
          <span>{{ workspaceLoadError }}</span>
          <v-spacer />
          <v-btn
            variant="text"
            :loading="isRetryingWorkspaceLoad"
            @click="retryWorkspaceLoad"
          >
            Retry
          </v-btn>
        </div>
      </v-alert>
    </div>

    <div class="workspaces-page-body">
      <div class="workspaces-shell">
        <aside class="sidebar" data-testid="workspace-sidebar">
          <div class="sidebar-header">
            <div class="flex items-center">
              <span class="sidebar-title">Workspaces</span>
              <PermissionTooltip
                :has-permission="canCreateWorkspace"
                message="You don't have permissions to create a workspace. Contact your system administrator to change your permissions."
              >
                <template #default>
                  <button
                    type="button"
                    class="sidebar-add ml-auto"
                    :style="{ background: WORKSPACE_ACCENT }"
                    aria-label="New workspace"
                    title="New workspace"
                    @click="openCreate = true"
                  >
                    <v-icon :icon="mdiPlus" size="16" color="white" />
                  </button>
                </template>
                <template #denied>
                  <button
                    type="button"
                    class="sidebar-add ml-auto"
                    style="background: #9e9e9e; opacity: 0.6"
                    disabled
                    aria-label="New workspace"
                    title="New workspace"
                  >
                    <v-icon :icon="mdiPlus" size="16" color="white" />
                  </button>
                </template>
              </PermissionTooltip>
            </div>
            <div class="sidebar-search">
              <v-icon
                :icon="mdiMagnify"
                size="16"
                class="sidebar-search-icon"
              />
              <input
                :value="search"
                placeholder="Search workspaces…"
                class="sidebar-search-input"
                @input="search = ($event.target as HTMLInputElement).value"
              />
            </div>
          </div>

          <div class="sidebar-list">
            <div
              v-for="ws in filteredWorkspaces"
              :key="ws.id"
              class="sidebar-item sidebar-item--workspace"
              :class="{ selected: ws.id === selectedId }"
              :style="
                ws.id === selectedId
                  ? { background: WORKSPACE_ACCENT, color: 'white' }
                  : {}
              "
              :data-testid="`workspace-list-item-${ws.id}`"
            >
              <button
                type="button"
                class="sidebar-item-body"
                :aria-label="`Select ${ws.name} workspace`"
                :aria-current="ws.id === selectedId ? 'true' : undefined"
                @click="selectWorkspace(ws.id)"
              >
                <div class="sidebar-item-title">{{ ws.name }}</div>
                <div class="sidebar-item-meta">
                  <span class="sidebar-item-meta-text">
                    {{ getUserRoleName(ws) }} ·
                    {{ ws.isPrivate ? 'Private' : 'Public' }}
                  </span>
                </div>
              </button>
              <span class="sidebar-item-actions">
                <button
                  type="button"
                  class="sidebar-item-action"
                  :class="{
                    'sidebar-item-action--selected': ws.id === selectedId,
                  }"
                  :disabled="!canEditWorkspace(ws)"
                  :title="canEditWorkspace(ws) ? '' : EDIT_DENIED_MESSAGE"
                  :aria-label="`Edit ${ws.name}`"
                  :data-testid="`workspace-edit-${ws.id}`"
                  @click.stop="openDialog(ws, 'edit')"
                >
                  <v-icon :icon="mdiPencil" size="15" />
                </button>
                <button
                  type="button"
                  class="sidebar-item-action sidebar-item-action--danger"
                  :class="{
                    'sidebar-item-action--selected': ws.id === selectedId,
                  }"
                  :disabled="!canDeleteWorkspace(ws)"
                  :title="canDeleteWorkspace(ws) ? '' : DELETE_DENIED_MESSAGE"
                  :aria-label="`Delete ${ws.name}`"
                  :data-testid="`workspace-delete-${ws.id}`"
                  @click.stop="openDialog(ws, 'delete')"
                >
                  <v-icon :icon="mdiTrashCanOutline" size="15" />
                </button>
              </span>
            </div>
            <div
              v-if="workspaces.length && !filteredWorkspaces.length"
              class="sidebar-empty"
            >
              No matching workspaces.
            </div>
            <div v-else-if="!workspaces.length" class="sidebar-empty">
              No workspaces yet.
            </div>
          </div>

          <div class="sidebar-footer">
            <PermissionTooltip
              :has-permission="canCreateWorkspace"
              message="You don't have permissions to create a workspace. Contact your system administrator to change your permissions."
            >
              <template #default>
                <button
                  type="button"
                  class="sidebar-footer-btn"
                  :style="{
                    color: WORKSPACE_ACCENT,
                    borderColor: WORKSPACE_ACCENT + '66',
                  }"
                  @click="openCreate = true"
                >
                  <v-icon :icon="mdiPlus" size="16" class="mr-1" />
                  Add workspace
                </button>
              </template>
              <template #denied>
                <button type="button" class="sidebar-footer-btn" disabled>
                  <v-icon :icon="mdiPlus" size="16" class="mr-1" />
                  Add workspace
                </button>
              </template>
            </PermissionTooltip>
          </div>
        </aside>

        <section v-if="selected" class="detail" data-testid="workspace-detail">
          <header class="detail-header">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="detail-title">{{ selected.name }}</h2>
                <v-chip
                  size="small"
                  variant="tonal"
                  :color="selected.isPrivate ? 'grey-darken-2' : 'primary'"
                  :prepend-icon="selected.isPrivate ? mdiLock : mdiEarth"
                >
                  {{ selected.isPrivate ? 'Private' : 'Public' }}
                </v-chip>
                <v-chip size="small" variant="tonal" color="secondary-darken-2">
                  {{ getUserRoleName(selected) }}
                </v-chip>
              </div>
              <div class="detail-subtitle">
                {{
                  isOwner(selected)
                    ? 'Owned by you'
                    : `Owner · ${selected.owner?.name || 'Unknown'}`
                }}
              </div>
            </div>
          </header>

          <div class="detail-tabbar">
            <v-tabs
              v-model="section"
              color="primary"
              density="comfortable"
              show-arrows
            >
              <v-tab value="overview" :prepend-icon="mdiBriefcaseOutline">
                Overview
              </v-tab>
              <v-tab value="collaborators" :prepend-icon="mdiAccountCircle">
                Collaborators
              </v-tab>
              <v-tab value="service-accounts" :prepend-icon="mdiKeyVariant">
                Service accounts
              </v-tab>
              <v-tab value="metadata" :prepend-icon="mdiDatabaseCog">
                Metadata
              </v-tab>
              <v-tab value="privacy" :prepend-icon="mdiLock">Privacy</v-tab>
              <v-tab
                v-if="canEditWorkspace(selected)"
                value="ownership"
                :prepend-icon="mdiTransitTransfer"
              >
                Ownership
              </v-tab>
            </v-tabs>
          </div>

          <div class="detail-body">
            <v-window v-model="section">
              <v-window-item value="overview">
                <h6 class="text-h6 mb-1">Overview</h6>

                <div class="overview-stats">
                  <div class="stat-tile stat-tile--members">
                    <div class="stat-tile-head">
                      <span class="stat-tile-icon">
                        <v-icon :icon="mdiAccountCircle" size="14" />
                      </span>
                      <span>Members</span>
                    </div>
                    <div
                      class="stat-tile-value"
                      data-testid="overview-members-count"
                    >
                      {{
                        overviewStatsLoaded
                          ? (overviewStats.members ?? '—')
                          : '—'
                      }}
                    </div>
                  </div>
                  <div class="stat-tile stat-tile--sites">
                    <div class="stat-tile-head">
                      <span class="stat-tile-icon">
                        <v-icon :icon="mdiRadioTower" size="14" />
                      </span>
                      <span>Sites</span>
                    </div>
                    <div
                      class="stat-tile-value"
                      data-testid="overview-sites-count"
                    >
                      {{
                        overviewStatsLoaded ? (overviewStats.sites ?? '—') : '—'
                      }}
                    </div>
                  </div>
                  <div class="stat-tile stat-tile--keys">
                    <div class="stat-tile-head">
                      <span class="stat-tile-icon">
                        <v-icon :icon="mdiKeyVariant" size="14" />
                      </span>
                      <span>Service accounts</span>
                    </div>
                    <div
                      class="stat-tile-value"
                      data-testid="overview-service-accounts-count"
                    >
                      {{
                        overviewStatsLoaded
                          ? (overviewStats.serviceAccounts ?? '—')
                          : '—'
                      }}
                    </div>
                  </div>
                  <div class="stat-tile stat-tile--metadata">
                    <div class="stat-tile-head">
                      <span class="stat-tile-icon">
                        <v-icon :icon="mdiDatabaseCog" size="14" />
                      </span>
                      <span>Metadata items</span>
                    </div>
                    <div
                      class="stat-tile-value"
                      data-testid="overview-metadata-count"
                    >
                      {{
                        overviewStatsLoaded
                          ? (overviewStats.metadata ?? '—')
                          : '—'
                      }}
                    </div>
                  </div>
                </div>

                <div v-if="overviewStatsError" class="overview-stats-error">
                  Some totals could not be loaded.
                  <button type="button" @click="loadOverviewStats(selected.id)">
                    Retry
                  </button>
                </div>

                <v-table class="hs-table-card">
                  <tbody>
                    <tr>
                      <td class="text-medium-emphasis" style="width: 200px">
                        Workspace name
                      </td>
                      <td>{{ selected.name }}</td>
                    </tr>
                    <tr>
                      <td class="text-medium-emphasis">Owner</td>
                      <td>
                        {{ selected.owner?.name || 'Unknown'
                        }}<span v-if="isOwner(selected)"> (you)</span>
                      </td>
                    </tr>
                    <tr>
                      <td class="text-medium-emphasis">Your role</td>
                      <td>{{ getUserRoleName(selected) }}</td>
                    </tr>
                    <tr>
                      <td class="text-medium-emphasis">Visibility</td>
                      <td>{{ selected.isPrivate ? 'Private' : 'Public' }}</td>
                    </tr>
                    <tr>
                      <td class="text-medium-emphasis">Workspace ID</td>
                      <td class="workspace-id-cell">
                        <span>{{ selected.id }}</span>
                        <v-btn
                          size="x-small"
                          variant="text"
                          density="comfortable"
                          :icon="mdiContentCopy"
                          aria-label="Copy workspace ID"
                          @click="copyId(selected.id)"
                        />
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-window-item>

              <v-window-item value="collaborators">
                <ManageCollaborators
                  :key="selected.id"
                  :workspace="selected"
                  @self-removed="onSelfRemoved"
                />
              </v-window-item>

              <v-window-item value="service-accounts">
                <ManageServiceAccounts
                  v-if="
                    hasPermission(
                      PermissionResource.ServiceAccount,
                      PermissionAction.View,
                      selected
                    )
                  "
                  :key="selected.id"
                  :workspace="selected"
                />
                <p v-else>
                  You don't have permission to view service accounts for this
                  workspace. Contact the workspace owner if you need access.
                </p>
              </v-window-item>

              <v-window-item value="metadata">
                <MetadataTable :key="selected.id" :workspace="selected" />
              </v-window-item>

              <v-window-item value="privacy">
                <ManageWorkspacePrivacy
                  :key="selected.id"
                  :workspace="selected"
                  @privacy-updated="selected.isPrivate = $event"
                />
              </v-window-item>

              <v-window-item
                v-if="canEditWorkspace(selected)"
                value="ownership"
              >
                <TransferWorkspaceOwnership
                  :key="selected.id"
                  :workspace="selected"
                  @needs-refresh="refreshWorkspace(selected.id)"
                />
              </v-window-item>
            </v-window>
          </div>
        </section>

        <section v-else class="no-workspace-state">
          <div class="no-workspace-state-content">
            <div class="no-workspace-icon">
              <v-icon :icon="mdiBriefcaseOutline" size="28" />
            </div>
            <p class="no-workspace-eyebrow">Manage workspaces</p>
            <h2>
              {{
                workspaceLoadError
                  ? 'Unable to load workspaces'
                  : workspaces.length
                    ? 'Select a workspace to manage it'
                    : !canCreateWorkspace
                      ? 'No workspaces available'
                      : 'Create your first workspace'
              }}
            </h2>
            <p v-if="workspaceLoadError">
              We could not load your workspaces. Check your connection and try
              again.
            </p>
            <p v-else-if="!workspaces.length && !canCreateWorkspace">
              You do not belong to a workspace yet. Ask a workspace owner to
              invite you as a collaborator.
            </p>
            <p v-else>
              Workspaces control who can access your sites, datastreams, and
              metadata. After creating one, assign roles like Editor or Viewer
              to collaborators who need access.
            </p>
            <div class="no-workspace-actions">
              <v-btn
                v-if="workspaceLoadError"
                color="primary-darken-2"
                variant="flat"
                rounded="xl"
                :loading="isRetryingWorkspaceLoad"
                @click="retryWorkspaceLoad"
              >
                Retry
              </v-btn>
              <v-btn
                v-else-if="canCreateWorkspace"
                color="green-darken-2"
                variant="flat"
                rounded="xl"
                @click="openCreate = true"
              >
                Add workspace
              </v-btn>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
  <FullScreenLoader v-else />

  <v-dialog v-model="openCreate" width="30rem">
    <WorkspaceFormCard @close="openCreate = false" @created="onCreated" />
  </v-dialog>

  <v-dialog v-model="openEdit" width="30rem">
    <WorkspaceFormCard
      @close="openEdit = false"
      :workspace="activeItem"
      @updated="refreshWorkspaces"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="30rem">
    <DeleteWorkspaceCard
      @close="openDelete = false"
      @delete="onDelete"
      @switch-to-transfer="onSwitchToTransfer"
      :workspace="activeItem"
      :can-transfer="canEditWorkspace(activeItem)"
      :loading="isDeletingWorkspace"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import hs, {
  PermissionAction,
  PermissionResource,
  Workspace,
} from '@hydroserver/client'
import {
  mdiAccountCircle,
  mdiBriefcaseOutline,
  mdiCheck,
  mdiContentCopy,
  mdiDatabaseCog,
  mdiEarth,
  mdiKeyVariant,
  mdiLock,
  mdiMagnify,
  mdiPencil,
  mdiPlus,
  mdiRadioTower,
  mdiTransitTransfer,
  mdiTrashCanOutline,
} from '@mdi/js'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import PermissionTooltip from '@/components/PermissionTooltip.vue'
import WorkspaceFormCard from '@/components/Workspace/WorkspaceFormCard.vue'
import DeleteWorkspaceCard from '@/components/Workspace/DeleteWorkspaceCard.vue'
import ManageCollaborators from '@/components/Workspace/AccessControl/ManageCollaborators.vue'
import ManageServiceAccounts from '@/components/Workspace/AccessControl/ManageServiceAccounts.vue'
import ManageWorkspacePrivacy from '@/components/Workspace/AccessControl/ManageWorkspacePrivacy.vue'
import TransferWorkspaceOwnership from '@/components/Workspace/AccessControl/TransferWorkspaceOwnership.vue'
import MetadataTable from '@/components/Metadata/MetadataTable.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { useUserStore } from '@/store/user'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { Snackbar } from '@/utils/notifications'

// Matches the accent used for the "Workspaces" entry in the orchestration nav
// rail, so the two workspace-management entry points read as the same place.
const WORKSPACE_ACCENT = '#2E7D32'

const SECTIONS = [
  'overview',
  'collaborators',
  'service-accounts',
  'metadata',
  'privacy',
  'ownership',
] as const

type WorkspaceSection = (typeof SECTIONS)[number]

const route = useRoute()
const router = useRouter()

const workspaceStore = useWorkspaceStore()
const { selectedWorkspace, workspaces } = storeToRefs(workspaceStore)
const { setWorkspaces } = workspaceStore
const { hasPermission, getUserRoleName, isOwner } = useWorkspacePermissions()
const { user } = storeToRefs(useUserStore())

const EDIT_DENIED_MESSAGE = 'You do not have permission to edit this workspace.'
const DELETE_DENIED_MESSAGE =
  'You do not have permission to delete this workspace.'
const canEditWorkspace = (ws: Workspace | null) =>
  !!ws && hasPermission(PermissionResource.Workspace, PermissionAction.Edit, ws)
const canDeleteWorkspace = (ws: Workspace | null) =>
  !!ws &&
  hasPermission(PermissionResource.Workspace, PermissionAction.Delete, ws)

const isPageLoaded = ref(false)
const workspaceLoadError = ref('')
const isRetryingWorkspaceLoad = ref(false)
const search = ref('')

const selectedId = ref('')
const section = ref<WorkspaceSection>('overview')

const openCreate = ref(false)
const openEdit = ref(false)
const openDelete = ref(false)
const isDeletingWorkspace = ref(false)
const pendingTransferActionId = ref<string | null>(null)
const pendingTransferActionType = ref<'accept' | 'decline' | null>(null)
const activeItem = ref<Workspace>({} as Workspace)

const selected = computed(
  () => workspaces.value.find((ws) => ws.id === selectedId.value) ?? null
)

/** At-a-glance counts shown as the large stat tiles on the Overview tab. */
const overviewStats = ref<{
  members: number | null
  sites: number | null
  serviceAccounts: number | null
  metadata: number | null
}>({ members: null, sites: null, serviceAccounts: null, metadata: null })
const overviewStatsLoaded = ref(false)
const overviewStatsError = ref(false)
let overviewRequestId = 0

function responseCount(result: PromiseSettledResult<unknown>): number | null {
  if (result.status === 'rejected') return null
  const response = result.value as {
    ok?: boolean
    data?: unknown[]
  } | null
  return response?.ok && Array.isArray(response.data)
    ? response.data.length
    : null
}

const loadOverviewStats = async (workspaceId: string) => {
  const requestId = ++overviewRequestId
  overviewStatsLoaded.value = false
  overviewStatsError.value = false
  overviewStats.value = {
    members: null,
    sites: null,
    serviceAccounts: null,
    metadata: null,
  }

  const workspace = workspaces.value.find((item) => item.id === workspaceId)
  const canViewServiceAccounts =
    !!workspace &&
    hasPermission(
      PermissionResource.ServiceAccount,
      PermissionAction.View,
      workspace
    )
  const serviceAccountRequest = canViewServiceAccounts
    ? hs.workspaces.getServiceAccounts(workspaceId)
    : Promise.resolve(null)

  const results = await Promise.allSettled([
    hs.workspaces.getCollaborators(workspaceId),
    hs.things.listSiteSummaries(workspaceId),
    serviceAccountRequest,
    hs.sensors.list({ workspace_id: [workspaceId], fetch_all: true }),
    hs.observedProperties.list({
      workspace_id: [workspaceId],
      fetch_all: true,
    }),
    hs.processingLevels.list({
      workspace_id: [workspaceId],
      fetch_all: true,
    }),
    hs.units.list({ workspace_id: [workspaceId], fetch_all: true }),
    hs.resultQualifiers.list({
      workspace_id: [workspaceId],
      fetch_all: true,
    }),
  ])

  if (requestId !== overviewRequestId || selectedId.value !== workspaceId)
    return

  const counts = results.map(responseCount)
  const metadataCounts = counts.slice(3)
  const metadata = metadataCounts.every((count) => count !== null)
    ? metadataCounts.reduce<number>((total, count) => total + (count ?? 0), 0)
    : null

  overviewStats.value = {
    // +1 for the owner, who isn't included in the collaborators list.
    members: counts[0] === null ? null : counts[0] + 1,
    sites: counts[1],
    serviceAccounts: canViewServiceAccounts ? counts[2] : null,
    metadata,
  }
  overviewStatsError.value =
    counts[0] === null ||
    counts[1] === null ||
    (canViewServiceAccounts && counts[2] === null) ||
    metadata === null
  overviewStatsLoaded.value = true
}

watch(
  selected,
  (ws) => {
    if (!ws) return
    if (selectedWorkspace.value?.id !== ws.id) selectedWorkspace.value = ws
    if (section.value === 'ownership' && !canEditWorkspace(ws))
      section.value = 'overview'
    else if (section.value === 'overview') void loadOverviewStats(ws.id)
  },
  { immediate: true }
)

watch(section, (value) => {
  if (value === 'overview' && selected.value)
    void loadOverviewStats(selected.value.id)
})

const filteredWorkspaces = computed(() => {
  const term = (search.value || '').toLowerCase()
  if (!term) return workspaces.value
  return workspaces.value.filter((ws) => ws.name.toLowerCase().includes(term))
})

const canCreateWorkspace = computed(() =>
  ['admin', 'standard'].includes(user.value?.accountType ?? '')
)

/** Workspaces that are pending a transfer to the current user */
const pendingWorkspaces = computed(() =>
  workspaces.value.filter(
    (ws) =>
      ws.pendingTransferTo?.email &&
      ws.pendingTransferTo?.email === user.value?.email
  )
)

function selectWorkspace(id: string) {
  selectedId.value = id
}

function openDialog(item: Workspace, dialog: 'edit' | 'delete') {
  if (
    (dialog === 'edit' && !canEditWorkspace(item)) ||
    (dialog === 'delete' && !canDeleteWorkspace(item))
  )
    return
  activeItem.value = item
  if (dialog === 'edit') openEdit.value = true
  if (dialog === 'delete') openDelete.value = true
}

async function loadWorkspaceList() {
  try {
    const response = await hs.workspaces.list({
      is_associated: true,
      fetch_all: true,
    })
    if (!response.ok) {
      workspaceLoadError.value =
        response.message || 'We could not load your workspaces.'
      return false
    }

    setWorkspaces(response.data)
    workspaceLoadError.value = ''
    return true
  } catch (error) {
    console.error('Error fetching workspaces', error)
    workspaceLoadError.value = 'We could not load your workspaces.'
    return false
  }
}

/** Sync the local list with the database and the global workspace store. */
const refreshWorkspaces = async (fallbackWorkspace?: Workspace) => {
  const refreshed = await loadWorkspaceList()

  // The mutation already succeeded, so keep its result usable even when the
  // follow-up list request is temporarily unavailable.
  if (!refreshed && fallbackWorkspace) {
    setWorkspaces([
      ...workspaces.value.filter((ws) => ws.id !== fallbackWorkspace.id),
      fallbackWorkspace,
    ])
  }

  if (!selected.value) selectedId.value = workspaces.value[0]?.id ?? ''
  return refreshed
}

const refreshWorkspace = async (workspaceId: string) => {
  try {
    const workspace = await hs.workspaces.getItem(workspaceId)
    if (!workspace) {
      Snackbar.error('Unable to refresh the workspace.')
      return false
    }
    const index = workspaces.value.findIndex((ws) => ws.id === workspaceId)
    if (index !== -1) workspaces.value.splice(index, 1, workspace)
    return true
  } catch (error) {
    console.error('Error refreshing workspace', error)
    Snackbar.error('Unable to refresh the workspace.')
    return false
  }
}

const onCreated = async (workspace: Workspace) => {
  await refreshWorkspaces(workspace)
  selectedId.value = workspace.id
}

async function onDelete() {
  if (
    !activeItem.value ||
    !canDeleteWorkspace(activeItem.value) ||
    isDeletingWorkspace.value
  )
    return
  isDeletingWorkspace.value = true
  try {
    const res = await hs.workspaces.delete(activeItem.value.id)
    if (res.ok) {
      setWorkspaces(
        workspaces.value.filter(
          (workspace) => workspace.id !== activeItem.value.id
        )
      )
      openDelete.value = false
      Snackbar.success('Workspace deleted')
      await refreshWorkspaces()
    } else Snackbar.error(res.message || 'Unable to delete the workspace.')
  } catch (error) {
    console.error('Error deleting workspace', error)
    Snackbar.error('Unable to delete the workspace.')
  } finally {
    isDeletingWorkspace.value = false
  }
}

// DeleteWorkspaceCard only offers this link when the acting user can edit the
// workspace (see :can-transfer above), so the Ownership tab always exists.
function onSwitchToTransfer() {
  openDelete.value = false
  selectedId.value = activeItem.value.id
  section.value = 'ownership'
}

const onSelfRemoved = async () => {
  const removedWorkspaceId = selectedId.value
  setWorkspaces(
    workspaces.value.filter((workspace) => workspace.id !== removedWorkspaceId)
  )
  await refreshWorkspaces()
}

async function onCancelTransfer(ws: Workspace) {
  if (pendingTransferActionId.value) return
  pendingTransferActionId.value = ws.id
  pendingTransferActionType.value = 'decline'
  try {
    const res = await hs.workspaces.rejectOwnershipTransfer(ws.id)
    if (res.ok) {
      await refreshWorkspaces()
      Snackbar.success('Workspace transfer declined.')
    } else {
      console.error('Error declining workspace transfer.', res)
      Snackbar.error(res.message || 'Unable to decline the workspace transfer.')
    }
  } catch (error) {
    console.error('Error declining workspace transfer.', error)
    Snackbar.error('Unable to decline the workspace transfer.')
  } finally {
    pendingTransferActionId.value = null
    pendingTransferActionType.value = null
  }
}

async function onAcceptTransfer(ws: Workspace) {
  if (pendingTransferActionId.value) return
  pendingTransferActionId.value = ws.id
  pendingTransferActionType.value = 'accept'
  try {
    const res = await hs.workspaces.acceptOwnershipTransfer(ws.id)
    if (res.ok) {
      await refreshWorkspaces()
      Snackbar.success('Workspace transfer accepted.')
    } else {
      console.error('Error accepting workspace transfer.', res)
      Snackbar.error(res.message || 'Unable to accept the workspace transfer.')
    }
  } catch (error) {
    console.error('Error accepting workspace transfer.', error)
    Snackbar.error('Unable to accept the workspace transfer.')
  } finally {
    pendingTransferActionId.value = null
    pendingTransferActionType.value = null
  }
}

async function retryWorkspaceLoad() {
  isRetryingWorkspaceLoad.value = true
  await refreshWorkspaces()
  isRetryingWorkspaceLoad.value = false
}

async function copyId(id: string) {
  try {
    await navigator.clipboard.writeText(id)
    Snackbar.success('Workspace ID copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy workspace ID')
  }
}

function queryString(value: unknown) {
  return `${Array.isArray(value) ? (value[0] ?? '') : (value ?? '')}`
}

function availableSection(value: string, workspace: Workspace | null) {
  const normalized = value === 'api-keys' ? 'service-accounts' : value
  const requested = SECTIONS.includes(normalized as WorkspaceSection)
    ? (normalized as WorkspaceSection)
    : 'overview'
  return requested === 'ownership' &&
    (!workspace || !canEditWorkspace(workspace))
    ? 'overview'
    : requested
}

function syncRouteQuery() {
  if (!isPageLoaded.value) return
  const workspaceQuery = selectedId.value || undefined
  const sectionQuery = section.value !== 'overview' ? section.value : undefined
  if (
    queryString(route.query.workspace) === (workspaceQuery ?? '') &&
    queryString(route.query.section) === (sectionQuery ?? '')
  )
    return

  void router.replace({
    query: {
      ...route.query,
      workspace: workspaceQuery,
      section: sectionQuery,
    },
  })
}

// Respond to browser history and links that update the query while this page
// is already mounted.
watch(
  () => [route.query.workspace, route.query.section],
  ([workspaceQuery, sectionQuery]) => {
    if (!isPageLoaded.value) return

    const requestedWorkspace = queryString(workspaceQuery)
    if (
      requestedWorkspace &&
      requestedWorkspace !== selectedId.value &&
      workspaces.value.some((workspace) => workspace.id === requestedWorkspace)
    )
      selectedId.value = requestedWorkspace

    const nextSection = availableSection(
      queryString(sectionQuery),
      selected.value
    )
    if (section.value !== nextSection) section.value = nextSection
    syncRouteQuery()
  }
)

// Keep the selected workspace and section shareable through the URL.
watch([selectedId, section], syncRouteQuery)

onMounted(async () => {
  await loadWorkspaceList()

  const queryWorkspace = queryString(route.query.workspace)
  if (workspaces.value.some((ws) => ws.id === queryWorkspace))
    selectedId.value = queryWorkspace
  else
    selectedId.value =
      selectedWorkspace.value?.id ?? workspaces.value[0]?.id ?? ''

  section.value = availableSection(
    queryString(route.query.section),
    selected.value
  )
  isPageLoaded.value = true
  syncRouteQuery()
})
</script>

<style scoped>
/* ── overview stat tiles ── */
.overview-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-tile {
  flex: 1;
  min-width: 0;
  padding: 15px 16px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 11px;
  background: #ffffff;
}
.stat-tile-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 9px;
}
.stat-tile-head span:last-child {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #757575;
}
.stat-tile-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex-shrink: 0;
}
.stat-tile-value {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1c1b1f;
}
.overview-stats-error {
  margin: -6px 0 14px;
  color: #8a5a00;
  font-size: 12px;
}
.overview-stats-error button {
  margin-left: 4px;
  color: #1565c0;
  font-weight: 600;
}
/* A little color per metric instead of one uniform grey, so the overview
   reads as more than a wall of numbers. */
.stat-tile--members .stat-tile-icon {
  background: #e3f2fd;
  color: #1565c0;
}
.stat-tile--members .stat-tile-value {
  color: #1565c0;
}
.stat-tile--sites .stat-tile-icon {
  background: #e8f5e9;
  color: #2e7d32;
}
.stat-tile--sites .stat-tile-value {
  color: #2e7d32;
}
.stat-tile--keys .stat-tile-icon {
  background: #fff3e0;
  color: #e65100;
}
.stat-tile--keys .stat-tile-value {
  color: #e65100;
}
.stat-tile--metadata .stat-tile-icon {
  background: #e0f7fa;
  color: #00838f;
}
.stat-tile--metadata .stat-tile-value {
  color: #00838f;
}

/* Page chrome mirrors the Job Orchestration page (Orchestration.vue /
   OrchestrationContextSidebar.vue) so the two workspace-management entry
   points feel like the same product surface. */
.workspaces-page {
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  min-height: 0;
  overflow: hidden;
}
.workspaces-page-toolbar {
  flex-shrink: 0;
}
.workspaces-header {
  background: linear-gradient(120deg, #eaf5fd 0%, #eefaf0 100%);
  border-bottom: 1px solid #dfe8e2;
}
.workspaces-header-inner {
  padding: 12px 24px;
}
.workspaces-header-title {
  font-size: 22px;
  font-weight: 400;
  color: #1c1b1f;
  letter-spacing: 0;
  line-height: 1.2;
}
.pending-transfer-alert {
  margin: 0;
  border-radius: 0;
}
.workspace-load-alert {
  margin: 0;
  border-radius: 0;
}
.workspaces-page-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}
.workspaces-shell {
  display: flex;
  flex: 1;
  min-height: 0;
  background: #ffffff;
  overflow: hidden;
}

/* ── left-hand workspace selection sidebar ── */
.sidebar {
  position: relative;
  width: 260px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-height: 0;
}
.sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #2196f3, #4caf50);
}
.sidebar-header {
  padding: 11px 14px 10px;
  border-bottom: 1px solid #ebebeb;
}
.sidebar-title {
  font-size: 11px;
  font-weight: 700;
  color: #49454f;
  text-transform: uppercase;
  letter-spacing: 0.7px;
}
.sidebar-add {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.sidebar-search {
  position: relative;
  margin-top: 8px;
}
.sidebar-search-icon {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: #cac4d0;
  pointer-events: none;
}
.sidebar-search-input {
  width: 100%;
  border: 1px solid #cac4d0;
  border-radius: 20px;
  height: 30px;
  padding-left: 30px;
  padding-right: 10px;
  font-size: 12px;
  outline: none;
  background: white;
}
.sidebar-list {
  flex: 1;
  overflow-y: auto;
}
.sidebar-item {
  position: relative;
  padding: 10px 14px;
  cursor: default;
  border-bottom: 1px solid #ebebeb;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  transition: background 0.1s;
}
.sidebar-item:not(.selected):hover {
  background: rgba(33, 150, 243, 0.06);
}
.sidebar-item-body {
  flex: 1;
  min-width: 0;
  width: 100%;
  border: 0;
  padding: 0;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.sidebar-item--workspace .sidebar-item-body {
  padding-right: 62px;
}
.sidebar-item-title {
  font-size: 13px;
  color: inherit;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sidebar-item.selected .sidebar-item-title {
  font-weight: 600;
}
.sidebar-item-meta {
  font-size: 11px;
  color: #49454f;
  margin-top: 2px;
  min-height: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.sidebar-item.selected .sidebar-item-meta {
  color: rgba(255, 255, 255, 0.75);
}
.sidebar-item-meta-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sidebar-item-actions {
  position: absolute;
  right: 14px;
  top: 10px;
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.1s;
}
.sidebar-item:hover .sidebar-item-actions,
.sidebar-item:focus-within .sidebar-item-actions,
.sidebar-item.selected .sidebar-item-actions {
  opacity: 1;
}
.sidebar-item-action {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  color: #546e7a;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.sidebar-item-action:hover:not(:disabled) {
  background: rgba(84, 110, 122, 0.12);
}
.sidebar-item-action--danger {
  color: #b3261e;
}
.sidebar-item-action--danger:hover:not(:disabled) {
  background: rgba(179, 38, 30, 0.1);
}
.sidebar-item-action--selected {
  color: white;
}
.sidebar-item-action--selected:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.18);
}
.sidebar-item-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.sidebar-empty {
  padding: 16px 14px;
  font-size: 12px;
  color: #9ca3af;
}
.sidebar-footer {
  padding: 10px 14px;
  border-top: 1px solid #ebebeb;
}
.sidebar-footer-btn {
  background: none;
  border: 1px dashed;
  border-radius: 8px;
  padding: 6px 0;
  width: 100%;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.sidebar-footer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── detail panel ── */
.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
  min-width: 0;
}
.detail-header {
  padding: 12px 22px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  gap: 12px;
  background: white;
  flex-shrink: 0;
}
.detail-title {
  font-size: 17px;
  font-weight: 400;
  color: #1c1b1f;
}
.detail-subtitle {
  margin-top: 4px;
  font-size: 12.5px;
  color: #49454f;
}
.detail-tabbar {
  padding: 0 22px;
  border-bottom: 1px solid #e8e8e8;
  background: white;
  flex-shrink: 0;
}
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px;
}
.workspace-id-cell {
  overflow-wrap: anywhere;
}
.workspace-id-cell span {
  vertical-align: middle;
}

.no-workspace-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  overflow: auto;
  background: white;
  padding: 32px;
}
.no-workspace-state-content {
  max-width: 560px;
  color: #3c4043;
}
.no-workspace-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e3f2fd, #e8f5e9);
  color: #2e7d32;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}
.no-workspace-eyebrow {
  margin: 0 0 8px;
  color: #5f6368;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.no-workspace-state h2 {
  margin: 0 0 12px;
  color: #202124;
  font-size: 1.5rem;
  line-height: 1.25;
}
.no-workspace-state p {
  line-height: 1.55;
}
.no-workspace-actions {
  margin-top: 22px;
}

@media (hover: none) {
  .sidebar-item-actions {
    opacity: 1;
  }
}

@media (max-width: 700px) {
  .workspaces-page {
    height: auto;
    min-height: calc(
      100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px)
    );
    overflow: visible;
  }
  .workspaces-page-body,
  .workspaces-shell {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    overflow: visible;
  }
  .workspaces-shell {
    flex-direction: column;
  }
  .sidebar {
    width: 100%;
    max-width: 100%;
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid #e8e8e8;
  }
  .sidebar-list {
    display: flex;
    flex: none;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .sidebar-item {
    min-width: 175px;
    border-right: 1px solid #ebebeb;
    border-bottom: 0;
  }
  .sidebar-footer {
    display: none;
  }
  .detail {
    width: 100%;
    max-width: 100%;
    overflow: visible;
  }
  .detail-header {
    padding: 12px 16px;
  }
  .detail-tabbar {
    padding: 0 8px;
  }
  .detail-body {
    overflow: visible;
    padding: 16px;
  }
  .overview-stats {
    flex-wrap: wrap;
  }
  .stat-tile {
    flex: 1 1 calc(50% - 6px);
  }
}
</style>
