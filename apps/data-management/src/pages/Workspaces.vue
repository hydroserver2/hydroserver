<template>
  <div v-if="isPageLoaded" class="workspaces-page">
    <v-alert
      v-if="pendingWorkspaces.length"
      class="pending-transfer-alert"
      type="info"
      variant="tonal"
      border="start"
      :icon="mdiAccountArrowRightOutline"
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
        <v-btn-primary
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
        </v-btn-primary>
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

    <div class="workspaces-page-body">
      <HsMasterDetailLayout sidebar-test-id="workspace-sidebar">
        <template #sidebar>
          <WorkspaceSidebar
            :workspaces="workspaces"
            :selected-id="selectedId"
            :can-create="canCreateWorkspace"
            @create="openCreate = true"
            @select="selectWorkspace"
            @edit="openDialog($event, 'edit')"
            @delete="openDialog($event, 'delete')"
          />
        </template>

        <section v-if="selected" class="detail" data-testid="workspace-detail">
          <header class="detail-header">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h1 class="detail-title hs-heading">
                  {{ selected.name }}
                </h1>
                <v-chip
                  size="small"
                  variant="tonal"
                  color="default"
                  :prepend-icon="selected.isPrivate ? mdiLock : mdiEarth"
                >
                  {{ selected.isPrivate ? 'Private' : 'Public' }}
                </v-chip>
              </div>
              <div class="detail-subtitle hs-text-sm">
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
              <v-tab
                value="collaborators"
                :prepend-icon="mdiAccountGroupOutline"
              >
                Collaborators
              </v-tab>
              <v-tab value="service-accounts" :prepend-icon="mdiKeyVariant">
                Service accounts
              </v-tab>
              <v-tab value="metadata" :prepend-icon="mdiNotebookOutline">
                Metadata
              </v-tab>
              <v-tab value="privacy" :prepend-icon="mdiShieldLockOutline">
                Privacy
              </v-tab>
              <v-tab
                v-if="canEditWorkspace(selected)"
                value="ownership"
                :prepend-icon="mdiAccountArrowRightOutline"
              >
                Ownership
              </v-tab>
            </v-tabs>
          </div>

          <div
            class="detail-body"
            :class="{
              'detail-body--table':
                section === 'service-accounts' || section === 'metadata',
            }"
          >
            <v-window
              v-model="section"
              class="detail-window"
              :class="{
                'detail-window--table':
                  section === 'service-accounts' || section === 'metadata',
              }"
            >
              <v-window-item value="overview">
                <WorkspaceOverview
                  :key="selected.id"
                  :workspace="selected"
                  :active="section === 'overview'"
                />
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

        <HsEmptyState
          v-else
          :icon="mdiBriefcaseOutline"
          eyebrow="Manage workspaces"
          :title="emptyStateTitle"
        >
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
            metadata. After creating one, assign roles like Editor or Viewer to
            collaborators who need access.
          </p>
          <template #actions>
            <v-btn-primary
              v-if="workspaceLoadError"
              :loading="isRetryingWorkspaceLoad"
              @click="retryWorkspaceLoad"
            >
              Retry
            </v-btn-primary>
            <v-btn-primary
              v-else-if="canCreateWorkspace"
              @click="openCreate = true"
            >
              Add workspace
            </v-btn-primary>
          </template>
        </HsEmptyState>
      </HsMasterDetailLayout>
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
  mdiAccountArrowRightOutline,
  mdiAccountGroupOutline,
  mdiBriefcaseOutline,
  mdiCheck,
  mdiEarth,
  mdiKeyVariant,
  mdiLock,
  mdiNotebookOutline,
  mdiShieldLockOutline,
} from '@mdi/js'
import {
  HsEmptyState,
  HsFullScreenLoader as FullScreenLoader,
  HsMasterDetailLayout,
} from '@hydroserver/design-system/vue'
import WorkspaceFormCard from '@/components/Workspace/WorkspaceFormCard.vue'
import DeleteWorkspaceCard from '@/components/Workspace/DeleteWorkspaceCard.vue'
import WorkspaceOverview from '@/components/Workspace/WorkspaceOverview.vue'
import WorkspaceSidebar from '@/components/Workspace/WorkspaceSidebar.vue'
import ManageCollaborators from '@/components/Workspace/AccessControl/ManageCollaborators.vue'
import ManageServiceAccounts from '@/components/Workspace/AccessControl/ManageServiceAccounts.vue'
import ManageWorkspacePrivacy from '@/components/Workspace/AccessControl/ManageWorkspacePrivacy.vue'
import TransferWorkspaceOwnership from '@/components/Workspace/AccessControl/TransferWorkspaceOwnership.vue'
import MetadataTable from '@/components/Metadata/MetadataTable.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { useUserStore } from '@/store/user'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { Snackbar } from '@/utils/notifications'

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
const { hasPermission, isOwner } = useWorkspacePermissions()
const { user } = storeToRefs(useUserStore())

const canEditWorkspace = (ws: Workspace | null) =>
  !!ws && hasPermission(PermissionResource.Workspace, PermissionAction.Edit, ws)
const canDeleteWorkspace = (ws: Workspace | null) =>
  !!ws &&
  hasPermission(PermissionResource.Workspace, PermissionAction.Delete, ws)

const isPageLoaded = ref(false)
const workspaceLoadError = ref('')
const isRetryingWorkspaceLoad = ref(false)

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

const emptyStateTitle = computed(() =>
  workspaceLoadError.value
    ? 'Unable to load workspaces'
    : workspaces.value.length
      ? 'Select a workspace to manage it'
      : !canCreateWorkspace.value
        ? 'No workspaces available'
        : 'Create your first workspace'
)

watch(
  selected,
  (ws) => {
    if (!ws) return
    if (selectedWorkspace.value?.id !== ws.id) selectedWorkspace.value = ws
    if (section.value === 'ownership' && !canEditWorkspace(ws))
      section.value = 'overview'
  },
  { immediate: true }
)

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
/* Page chrome mirrors the Job Orchestration page (Orchestration.vue /
   OrchestrationContextSidebar.vue) so the two workspace-management entry
   points feel like the same product surface. */
.workspaces-page {
  background-color: var(--hs-background);
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  min-height: 0;
  overflow: hidden;
}
.pending-transfer-alert {
  margin: 0;
  border-radius: 0;
  flex-shrink: 0;
}
.workspace-load-alert {
  margin: 0;
  border-radius: 0;
  flex-shrink: 0;
}
.workspaces-page-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

/* ── detail panel ── */
.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--hs-background);
  background-image:
    radial-gradient(
      1100px 760px at 12% -8%,
      rgba(26, 111, 168, 0.045),
      transparent 62%
    ),
    radial-gradient(
      900px 680px at 102% 28%,
      rgba(10, 46, 77, 0.038),
      transparent 58%
    ),
    radial-gradient(
      700px 900px at 50% 115%,
      rgba(26, 111, 168, 0.028),
      transparent 60%
    );
  background-repeat: no-repeat, no-repeat, no-repeat;
  background-position:
    0 0,
    0 0,
    0 0;
  min-width: 0;
}
.detail-header {
  padding: var(--hs-space-20) var(--hs-space-24) var(--hs-space-12);
  border-bottom: 1px solid var(--hs-border);
  min-height: 93px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: var(--hs-space-12);
  background: var(--hs-surface-subtle);
  flex-shrink: 0;
}
.detail-title {
  margin: 0;
  color: var(--hs-text-primary);
  line-height: 1.2;
}
.detail-subtitle {
  margin-top: var(--hs-space-4);
  color: var(--hs-text-secondary);
}
.detail-tabbar {
  padding: 0 var(--hs-space-24);
  border-bottom: 1px solid var(--hs-border);
  background: var(--hs-surface-subtle);
  flex-shrink: 0;
}
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--hs-space-16) var(--hs-space-24);
}
.detail-body--table {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.detail-window--table {
  flex: 1;
  height: 100%;
  min-height: 0;
}
.detail-window--table :deep(.v-window__container),
.detail-window--table :deep(.v-window-item) {
  height: 100%;
  min-height: 0;
}
.detail-window--table :deep(.service-accounts-section),
.detail-window--table :deep(.metadata-section) {
  max-height: 100%;
  overflow: hidden;
}
.detail-window--table :deep(.metadata-section) {
  height: 100%;
}
.detail-window--table :deep(.service-accounts-table-card) {
  flex: 0 1 auto;
  min-height: 0;
  max-height: 100%;
}
.detail-window--table :deep(.metadata-table-frame),
.detail-window--table :deep(.metadata-table-card) {
  flex: 0 1 auto;
  min-height: 0;
  max-height: 100%;
}
.detail-window--table :deep(.service-accounts-data-table) {
  flex: 0 1 auto;
  height: auto !important;
  max-height: 100%;
  overflow: auto;
}
.detail-window--table :deep(.metadata-window),
.detail-window--table :deep(.metadata-window .v-data-table) {
  flex: 0 1 auto;
  height: auto !important;
  max-height: 100%;
  overflow: hidden;
}
@media (max-width: 700px) {
  .workspaces-page {
    height: auto;
    min-height: calc(
      100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px)
    );
    overflow: visible;
  }
  .workspaces-page-body {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    overflow: visible;
  }
  .detail {
    width: 100%;
    max-width: 100%;
    overflow: visible;
  }
  .detail-header {
    padding: var(--hs-space-12) var(--hs-space-16);
  }
  .detail-tabbar {
    padding: 0 var(--hs-space-8);
  }
  .detail-body {
    overflow: visible;
    padding: var(--hs-space-16);
  }
  .detail-body--table {
    display: block;
  }
  .detail-window--table,
  .detail-window--table :deep(.v-window__container),
  .detail-window--table :deep(.v-window-item) {
    height: auto;
  }
}
</style>
