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
          <v-btn-cancel density="comfortable" @click="onCancelTransfer(ws)">
            Decline
          </v-btn-cancel>
          <v-btn
            color="green-darken-2"
            density="comfortable"
            :prepend-icon="mdiCheck"
            @click="onAcceptTransfer(ws)"
          >
            Accept transfer
          </v-btn>
        </div>
      </v-alert>
    </div>

    <div class="workspaces-page-body">
      <div class="workspaces-shell">
        <aside class="sidebar">
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
              <v-icon :icon="mdiMagnify" size="16" class="sidebar-search-icon" />
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
              @click="selectWorkspace(ws.id)"
            >
              <div class="sidebar-item-body">
                <div class="sidebar-item-title">{{ ws.name }}</div>
                <div class="sidebar-item-meta">
                  <span class="sidebar-item-meta-text">
                    {{ getUserRoleName(ws) }} ·
                    {{ ws.isPrivate ? 'Private' : 'Public' }}
                  </span>
                </div>
              </div>
              <span class="sidebar-item-actions">
                <button
                  type="button"
                  class="sidebar-item-action"
                  :class="{ 'sidebar-item-action--selected': ws.id === selectedId }"
                  :disabled="!canManageWorkspace(ws)"
                  :title="canManageWorkspace(ws) ? '' : OWNER_ONLY_MESSAGE"
                  :aria-label="`Edit ${ws.name}`"
                  :data-testid="`workspace-edit-${ws.id}`"
                  @click.stop="openDialog(ws, 'edit')"
                >
                  <v-icon :icon="mdiPencil" size="15" />
                </button>
                <button
                  type="button"
                  class="sidebar-item-action sidebar-item-action--danger"
                  :class="{ 'sidebar-item-action--selected': ws.id === selectedId }"
                  :disabled="!canManageWorkspace(ws)"
                  :title="canManageWorkspace(ws) ? '' : OWNER_ONLY_MESSAGE"
                  :aria-label="`Delete ${ws.name}`"
                  :data-testid="`workspace-delete-${ws.id}`"
                  @click.stop="openDialog(ws, 'delete')"
                >
                  <v-icon :icon="mdiTrashCanOutline" size="15" />
                </button>
              </span>
            </div>
            <div v-if="workspaces.length && !filteredWorkspaces.length" class="sidebar-empty">
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
                  :style="{ color: WORKSPACE_ACCENT, borderColor: WORKSPACE_ACCENT + '66' }"
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
            <v-tabs v-model="section" color="primary" density="comfortable" show-arrows>
              <v-tab value="overview" :prepend-icon="mdiBriefcaseOutline">
                Overview
              </v-tab>
              <v-tab value="collaborators" :prepend-icon="mdiAccountCircle">
                Collaborators
              </v-tab>
              <v-tab value="api-keys" :prepend-icon="mdiKeyVariant">
                API keys
              </v-tab>
              <v-tab value="metadata" :prepend-icon="mdiDatabaseCog">
                Metadata
              </v-tab>
              <v-tab value="privacy" :prepend-icon="mdiLock">Privacy</v-tab>
              <v-tab
                v-if="isOwner(selected)"
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
                <v-row align="center" class="mb-1" no-gutters>
                  <v-col cols="auto">
                    <h6 class="text-h6">Overview</h6>
                  </v-col>
                  <v-spacer />
                  <v-col cols="auto">
                    <v-btn
                      :disabled="!canManageWorkspace(selected)"
                      :title="canManageWorkspace(selected) ? '' : OWNER_ONLY_MESSAGE"
                      variant="outlined"
                      :prepend-icon="mdiPencil"
                      @click="openDialog(selected, 'edit')"
                    >
                      Edit details
                    </v-btn>
                  </v-col>
                </v-row>

                <div class="overview-stats">
                  <div class="stat-tile stat-tile--accent">
                    <div class="stat-tile-head">
                      <v-icon :icon="mdiAccountCircle" size="16" />
                      <span>Members</span>
                    </div>
                    <div class="stat-tile-value">
                      {{ overviewStatsLoaded ? overviewStats.members : '—' }}
                    </div>
                  </div>
                  <div class="stat-tile">
                    <div class="stat-tile-head">
                      <v-icon :icon="mdiRadioTower" size="16" />
                      <span>Sites</span>
                    </div>
                    <div class="stat-tile-value">
                      {{ overviewStatsLoaded ? overviewStats.sites : '—' }}
                    </div>
                  </div>
                  <div class="stat-tile">
                    <div class="stat-tile-head">
                      <v-icon :icon="mdiKeyVariant" size="16" />
                      <span>API keys</span>
                    </div>
                    <div class="stat-tile-value">
                      {{ overviewStatsLoaded ? overviewStats.keys : '—' }}
                    </div>
                  </div>
                  <div class="stat-tile">
                    <div class="stat-tile-head">
                      <v-icon :icon="mdiDatabaseCog" size="16" />
                      <span>Metadata items</span>
                    </div>
                    <div class="stat-tile-value">
                      {{ overviewStatsLoaded ? overviewStats.metadata : '—' }}
                    </div>
                  </div>
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
                      <td>
                        {{ selected.id }}
                        <v-icon
                          size="x-small"
                          class="ml-2"
                          :icon="mdiContentCopy"
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

              <v-window-item value="api-keys">
                <ManageApiKeys
                  v-if="
                    hasPermission(
                      PermissionResource.ApiKey,
                      PermissionAction.Create,
                      selected
                    )
                  "
                  :key="selected.id"
                  :workspace-id="selected.id"
                />
                <p v-else>
                  You don't have permissions to create or edit API Keys for this
                  workspace. If you need one, contact the workspace owner.
                </p>
              </v-window-item>

              <v-window-item value="metadata">
                <div
                  class="d-flex flex-wrap align-center justify-space-between ga-4 mb-4"
                >
                  <v-btn-toggle
                    v-model="metadataScope"
                    mandatory
                    density="comfortable"
                    color="primary"
                    variant="outlined"
                    rounded="xl"
                    divided
                  >
                    <v-btn value="all">All</v-btn>
                    <v-btn value="workspace">Workspace metadata</v-btn>
                    <v-btn value="system">System metadata</v-btn>
                  </v-btn-toggle>

                  <v-text-field
                    class="metadata-search"
                    clearable
                    v-model="metadataSearch"
                    :prepend-inner-icon="mdiMagnify"
                    label="Search metadata"
                    hide-details
                    density="compact"
                    variant="underlined"
                    rounded="xl"
                  />
                </div>

                <MetadataTable
                  :key="`${metadataScope}-${selected.id}`"
                  :workspace="selected"
                  :search="metadataSearch"
                  :scope="metadataScope"
                />
              </v-window-item>

              <v-window-item value="privacy">
                <ManageWorkspacePrivacy
                  :key="selected.id"
                  :workspace="selected"
                  @privacy-updated="selected.isPrivate = $event"
                />
              </v-window-item>

              <v-window-item v-if="isOwner(selected)" value="ownership">
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
            <p class="no-workspace-eyebrow">Manage workspaces</p>
            <h2>
              {{
                workspaces.length
                  ? 'Select a workspace to manage it'
                  : 'Create your first workspace'
              }}
            </h2>
            <p>
              Workspaces control who can access your sites, datastreams, and
              metadata. After creating one, assign roles like Editor or Viewer
              to collaborators who need access.
            </p>
            <div class="no-workspace-actions">
              <v-btn
                color="primary-darken-2"
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
      :can-transfer="isOwner(activeItem)"
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
import ManageApiKeys from '@/components/Workspace/AccessControl/ManageApiKeys.vue'
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
  'api-keys',
  'metadata',
  'privacy',
  'ownership',
]

const route = useRoute()
const router = useRouter()

const { selectedWorkspace, workspaces } = storeToRefs(useWorkspaceStore())
const { setWorkspaces } = useWorkspaceStore()
const { hasPermission, getUserRoleName, isOwner, isAdmin } =
  useWorkspacePermissions()
const { user } = storeToRefs(useUserStore())

// Renaming, deleting, and toggling the privacy of a workspace are reserved
// for its actual owner (or a system admin) — a collaborator role granted
// broad permissions on the workspace should not be able to take them over.
const OWNER_ONLY_MESSAGE = 'Only the workspace owner can do this.'
const canManageWorkspace = (ws: Workspace | null) =>
  isOwner(ws) || isAdmin()

const isPageLoaded = ref(false)
const search = ref('')
const metadataSearch = ref()
const metadataScope = ref<'all' | 'workspace' | 'system'>('all')

const selectedId = ref('')
const section = ref('overview')

const openCreate = ref(false)
const openEdit = ref(false)
const openDelete = ref(false)
const activeItem = ref<Workspace>({} as Workspace)

const selected = computed(
  () => workspaces.value.find((ws) => ws.id === selectedId.value) ?? null
)

/** At-a-glance counts shown as the large stat tiles on the Overview tab. */
const overviewStats = ref({ members: 0, sites: 0, keys: 0, metadata: 0 })
const overviewStatsLoaded = ref(false)

const loadOverviewStats = async (workspaceId: string) => {
  overviewStatsLoaded.value = false
  try {
    const [
      collaboratorsRes,
      sitesRes,
      keysRes,
      sensors,
      observedProperties,
      processingLevels,
      units,
      resultQualifiers,
    ] = await Promise.all([
      hs.workspaces.getCollaborators(workspaceId),
      hs.things.listSiteSummaries(workspaceId),
      hs.workspaces.getApiKeys(workspaceId),
      hs.sensors.listAllItems({ workspace_id: [workspaceId] }),
      hs.observedProperties.listAllItems({ workspace_id: [workspaceId] }),
      hs.processingLevels.listAllItems({ workspace_id: [workspaceId] }),
      hs.units.listAllItems({ workspace_id: [workspaceId] }),
      hs.resultQualifiers.listAllItems({ workspace_id: [workspaceId] }),
    ])
    overviewStats.value = {
      // +1 for the owner, who isn't included in the collaborators list.
      members: (collaboratorsRes.ok ? collaboratorsRes.data.length : 0) + 1,
      sites: sitesRes.ok ? sitesRes.data.length : 0,
      keys: keysRes.ok ? keysRes.data.length : 0,
      metadata:
        sensors.length +
        observedProperties.length +
        processingLevels.length +
        units.length +
        resultQualifiers.length,
    }
  } catch (error) {
    console.error('Error loading workspace overview stats', error)
  } finally {
    overviewStatsLoaded.value = true
  }
}

watch(
  selected,
  (ws) => {
    if (ws) loadOverviewStats(ws.id)
  },
  { immediate: true }
)

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
  activeItem.value = item
  if (dialog === 'edit') openEdit.value = true
  if (dialog === 'delete') openDelete.value = true
}

/** Sync the local list with the db and the global workspaces array, which
 * should always be the source of truth. */
const refreshWorkspaces = async (workspace?: Workspace) => {
  const res = await hs.workspaces.listItems({
    is_associated: true,
    fetch_all: true,
  })
  setWorkspaces(res)

  if (
    workspace &&
    (!selectedWorkspace.value || selectedWorkspace.value.id === workspace.id)
  )
    selectedWorkspace.value = workspace

  if (!selected.value) selectedId.value = workspaces.value[0]?.id ?? ''
}

const refreshWorkspace = async (workspaceId: string) => {
  try {
    const workspace = (await hs.workspaces.getItem(workspaceId)) as Workspace
    const index = workspaces.value.findIndex((ws) => ws.id === workspaceId)
    if (index !== -1) workspaces.value.splice(index, 1, workspace)
  } catch (error) {
    console.error('Error refreshing workspace', error)
  }
}

const onCreated = async (workspace: Workspace) => {
  await refreshWorkspaces(workspace)
  selectedId.value = workspace.id
}

async function onDelete() {
  if (!activeItem.value) return
  const res = await hs.workspaces.delete(activeItem.value.id)
  if (res.ok) {
    Snackbar.success('Workspace deleted')
    await refreshWorkspaces()
  } else Snackbar.error(res.message)
}

// DeleteWorkspaceCard only offers this link when the acting user owns the
// workspace (see :can-transfer above), so the Ownership tab always exists.
function onSwitchToTransfer() {
  openDelete.value = false
  selectedId.value = activeItem.value.id
  section.value = 'ownership'
}

const onSelfRemoved = async () => {
  await refreshWorkspaces()
}

async function onCancelTransfer(ws: Workspace) {
  const res = await hs.workspaces.rejectOwnershipTransfer(ws.id)
  if (res.ok) {
    await refreshWorkspaces()
    Snackbar.success('Workspace transfer cancelled.')
  } else console.error('Error cancelling workspace transfer.', res)
}

async function onAcceptTransfer(ws: Workspace) {
  const res = await hs.workspaces.acceptOwnershipTransfer(ws.id)
  if (res.ok) {
    await refreshWorkspaces()
    Snackbar.success('Workspace transfer accepted.')
  } else console.error('Error accepting workspace transfer.', res)
}

async function copyId(id: string) {
  try {
    await navigator.clipboard.writeText(id)
    Snackbar.success('Workspace ID copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy workspace ID')
  }
}

// The ownership tab is only rendered for owners; fall back to the overview
// tab whenever the current selection makes the active section unavailable.
watch(selected, (ws) => {
  if (section.value === 'ownership' && (!ws || !isOwner(ws)))
    section.value = 'overview'
})

// Keep the selected workspace and section shareable through the URL.
watch([selectedId, section], () => {
  if (!isPageLoaded.value) return
  router.replace({
    query: {
      ...route.query,
      workspace: selectedId.value || undefined,
      section: section.value !== 'overview' ? section.value : undefined,
    },
  })
})

onMounted(async () => {
  try {
    const workspacesResponse = await hs.workspaces.listAllItems({
      is_associated: true,
    })
    setWorkspaces(workspacesResponse)
  } catch (error) {
    console.error('Error fetching workspaces', error)
  } finally {
    const queryWorkspace = `${route.query.workspace ?? ''}`
    const querySection = `${route.query.section ?? ''}`

    if (workspaces.value.some((ws) => ws.id === queryWorkspace))
      selectedId.value = queryWorkspace
    else
      selectedId.value =
        selectedWorkspace.value?.id ?? workspaces.value[0]?.id ?? ''

    if (SECTIONS.includes(querySection)) section.value = querySection

    isPageLoaded.value = true
  }
})
</script>

<style scoped>
.metadata-search {
  max-width: 260px;
  flex-shrink: 0;
}

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
  gap: 7px;
  color: #9ca3af;
  margin-bottom: 9px;
}
.stat-tile-head span {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #757575;
}
.stat-tile--accent .stat-tile-head,
.stat-tile--accent .stat-tile-head span {
  color: #1976d2;
}
.stat-tile-value {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1c1b1f;
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
  background: #ffffff;
  border-bottom: 1px solid #ebebeb;
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
  width: 260px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-height: 0;
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
  cursor: pointer;
  border-bottom: 1px solid #ebebeb;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  transition: background 0.1s;
}
.sidebar-item:not(.selected):hover {
  background: rgba(0, 0, 0, 0.035);
}
.sidebar-item-body {
  flex: 1;
  min-width: 0;
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
</style>
