<template>
  <div class="service-accounts-section" data-testid="service-accounts-section">
    <v-alert
      v-if="loadError"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-3"
    >
      <div class="d-flex align-center ga-2">
        <span>{{ loadError }}</span>
        <v-spacer />
        <v-btn variant="text" size="small" @click="reloadData">Retry</v-btn>
      </div>
    </v-alert>
    <v-progress-linear v-if="isLoading" indeterminate class="mb-2" />

    <v-card-text v-if="showNewKey && newKey">
      <v-alert
        type="success"
        border="start"
        elevation="2"
        variant="tonal"
        class="mb-4"
      >
        Your service account API key has been generated. Please copy it and
        store it somewhere safe — you won’t be able to see it again after
        leaving this page.
      </v-alert>

      <v-sheet
        color="surface-muted"
        class="pa-4 rounded d-flex align-center justify-space-between"
        border
      >
        <span class="text-mono text-wrap break-all">{{ newKey.key }}</span>
        <v-btn
          :icon="mdiContentCopy"
          variant="text"
          color="grey-darken-2"
          @click="copyKey(newKey.key)"
          aria-label="Copy service account API key"
        />
      </v-sheet>
    </v-card-text>

    <div class="hs-table-tools">
      <div class="workspace-table-search">
        <v-icon
          :icon="mdiMagnify"
          size="16"
          class="workspace-table-search-icon"
        />
        <input
          v-model="search"
          placeholder="Search service accounts…"
          class="workspace-table-search-input hs-text-sm"
          aria-label="Search service accounts"
        />
      </div>

      <v-btn
        :icon="mdiHelpCircleOutline"
        variant="text"
        size="small"
        color="grey-darken-2"
        title="About service accounts"
        aria-label="Toggle service account help"
        :aria-expanded="showServiceAccountHelp"
        @click="showServiceAccountHelp = !showServiceAccountHelp"
      />

      <div class="hs-table-actions">
        <PermissionTooltip
          :has-permission="canCreate"
          message="You don't have permission to create service accounts for this workspace."
        >
          <template #default>
            <v-btn-secondary variant="flat" @click="openCreate = true">
              Create service account
            </v-btn-secondary>
          </template>
          <template #denied>
            <v-btn-secondary variant="flat" disabled>
              Create service account
            </v-btn-secondary>
          </template>
        </PermissionTooltip>
      </div>
    </div>

    <p v-if="showServiceAccountHelp" class="service-accounts-help-text">
      <small>
        Service accounts provide remote systems with a controlled set of
        permissions. A service account can collaborate on other workspaces after
        it is created.
      </small>
    </p>

    <v-card class="hs-table-card service-accounts-table-card" flat>
      <v-data-table-virtual
        class="service-accounts-data-table"
        :headers="headers"
        :items="items"
        :sort-by="sortBy"
        :search="search"
        height="100%"
        no-data-text="No service accounts available"
        fixed-header
      >
        <template #item.id="{ item }">
          <div class="d-flex align-center">
            {{ item.id }}
            <v-icon size="x-small" class="ml-2" @click="copyKey(item.id)">
              <v-icon :icon="mdiContentCopy" />
            </v-icon>
          </div>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            :icon="mdiRefresh"
            variant="text"
            size="small"
            color="grey-darken-2"
            :disabled="!canEdit"
            :aria-label="`Regenerate ${item.name}`"
            @click="onOpenRegenerateDialog(item)"
          />
          <v-btn
            :icon="mdiPencil"
            variant="text"
            size="small"
            color="grey-darken-2"
            :disabled="!canEdit"
            :aria-label="`Edit ${item.name}`"
            @click="openDialog(item, 'edit')"
          />
          <v-btn
            :icon="mdiTrashCanOutline"
            variant="text"
            size="small"
            color="red-darken-2"
            :disabled="!canDelete"
            :aria-label="`Delete ${item.name}`"
            @click="openDialog(item, 'delete')"
          />
        </template>
      </v-data-table-virtual>
    </v-card>
  </div>

  <v-dialog v-model="openCreate" width="40rem">
    <ServiceAccountForm
      @close="openCreate = false"
      @created="onCreate"
      :workspace-id="workspaceId"
      :roles="roles"
      :can-assign-role="canAssignRoleOnCreate"
    />
  </v-dialog>

  <v-dialog v-model="openRefresh" width="40rem">
    <ServiceAccountRegenerateForm
      @close="openRefresh = false"
      @regenerated="onRegenerate"
      :loading="isRegenerating"
    />
  </v-dialog>

  <v-dialog v-model="openEdit" width="40rem">
    <ServiceAccountForm
      @close="openEdit = false"
      @updated="onUpdate"
      :workspace-id="workspaceId"
      :roles="roles"
      :service-account="item"
      :can-assign-role="canAssignRoleOnEdit"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteServiceAccount
      :itemName="item.name"
      :loading="isDeleting"
      @delete="onDelete"
      @close="openDelete = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import hs, {
  ServiceAccount,
  CollaboratorRole,
  PermissionAction,
  PermissionResource,
  Workspace,
} from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { computed, onMounted, ref } from 'vue'
import { useTableLogic } from '@/composables/useTableLogic'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import PermissionTooltip from '@/components/PermissionTooltip.vue'
import ServiceAccountForm from './ServiceAccountForm.vue'
import DeleteServiceAccount from './DeleteServiceAccount.vue'
import ServiceAccountRegenerateForm from './ServiceAccountRegenerateForm.vue'
import {
  mdiContentCopy,
  mdiTrashCanOutline,
  mdiHelpCircleOutline,
  mdiMagnify,
  mdiPencil,
  mdiRefresh,
} from '@mdi/js'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['changed'])

const workspaceId = computed(() => props.workspace.id)
const { hasPermission } = useWorkspacePermissions()
const serviceAccountsLoaded = ref(false)
const rolesLoaded = ref(false)
const canAssignRoleOnCreate = computed(() =>
  hasPermission(
    PermissionResource.Collaborator,
    PermissionAction.Create,
    props.workspace
  )
)
const canAssignRoleOnEdit = computed(() =>
  hasPermission(
    PermissionResource.Collaborator,
    PermissionAction.Edit,
    props.workspace
  )
)
const canCreate = computed(
  () =>
    serviceAccountsLoaded.value &&
    rolesLoaded.value &&
    canAssignRoleOnCreate.value &&
    hasPermission(
      PermissionResource.ServiceAccount,
      PermissionAction.Create,
      props.workspace
    )
)
const canEdit = computed(
  () =>
    serviceAccountsLoaded.value &&
    hasPermission(
      PermissionResource.ServiceAccount,
      PermissionAction.Edit,
      props.workspace
    )
)
const canDelete = computed(
  () =>
    serviceAccountsLoaded.value &&
    hasPermission(
      PermissionResource.ServiceAccount,
      PermissionAction.Delete,
      props.workspace
    )
)

const openCreate = ref(false)
const openRefresh = ref(false)
const showServiceAccountHelp = ref(false)
const sortBy = [{ key: 'OPName' }]
const search = ref('')
const roles = ref<CollaboratorRole[]>([])
const serviceAccountsLoadError = ref('')
const rolesLoadError = ref('')
const isLoading = ref(false)
const isDeleting = ref(false)
const isRegenerating = ref(false)
const loadError = computed(
  () => serviceAccountsLoadError.value || rolesLoadError.value
)

const showNewKey = ref(false)
type ServiceAccountRow = ServiceAccount & { role?: CollaboratorRole }

const newKey = ref<ServiceAccountRow>()

const {
  item,
  items,
  openEdit,
  openDelete,
  openDialog,
  onUpdate: updateTableItem,
  onDelete: deleteTableItem,
  loadData,
} = useTableLogic<ServiceAccountRow>(
  async (wsId: string) => {
    try {
      const [accountsRes, collaboratorsRes] = await Promise.all([
        hs.workspaces.getServiceAccounts(wsId),
        hs.workspaces.getCollaborators(wsId),
      ])
      if (!accountsRes.ok) {
        serviceAccountsLoadError.value = 'Unable to load service accounts.'
        serviceAccountsLoaded.value = false
        throw new Error(
          accountsRes.message || 'Unable to load service accounts.'
        )
      }

      const roleByEmail = new Map<string, CollaboratorRole>()
      if (collaboratorsRes.ok) {
        for (const collaborator of collaboratorsRes.data) {
          if (collaborator.serviceAccount)
            roleByEmail.set(
              collaborator.serviceAccount.email,
              collaborator.role
            )
        }
      }

      serviceAccountsLoadError.value = ''
      serviceAccountsLoaded.value = true
      return accountsRes.data.map((account) => ({
        ...account,
        role: roleByEmail.get(account.email),
      }))
    } catch (error) {
      serviceAccountsLoadError.value = 'Unable to load service accounts.'
      serviceAccountsLoaded.value = false
      throw error
    }
  },
  async (serviceAccountId: string) => {
    const res = await hs.workspaces.deleteServiceAccount(
      workspaceId.value,
      serviceAccountId
    )
    if (!res.ok) {
      Snackbar.error(res.message || 'Failed to delete service account')
      throw new Error(res.message || 'Failed to delete service account')
    }
  },
  ServiceAccount,
  workspaceId
)

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Role', key: 'role.name' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const

const onUpdate = (account: ServiceAccountRow) => {
  updateTableItem(account)
  emits('changed')
}

const onDelete = async () => {
  if (isDeleting.value) return
  isDeleting.value = true
  try {
    if (await deleteTableItem()) {
      if (newKey.value?.id === item.value.id) {
        showNewKey.value = false
        newKey.value = undefined
      }
      emits('changed')
    }
  } finally {
    isDeleting.value = false
  }
}

const onCreate = (account: ServiceAccountRow) => {
  items.value.push(account)
  displayNewKey(account)
  emits('changed')
}

const displayNewKey = (account: ServiceAccountRow) => {
  newKey.value = account
  showNewKey.value = true
}

function onOpenRegenerateDialog(selectedItem: ServiceAccountRow) {
  if (!canEdit.value) return
  item.value = selectedItem
  openRefresh.value = true
}

const onRegenerate = async () => {
  if (isRegenerating.value) return
  isRegenerating.value = true
  try {
    const res = await hs.workspaces.regenerateServiceAccountKey(
      workspaceId.value,
      item.value.id
    )
    if (!res.ok) {
      Snackbar.error('Failed to refresh service account API key')
      return
    }
    const responseKey: ServiceAccountRow = {
      ...res.data,
      role: item.value.role,
    }
    const idx = items.value.findIndex((k) => k.id === responseKey.id)
    if (idx !== -1) {
      items.value.splice(idx, 1, responseKey)
    } else {
      items.value.push(responseKey)
    }
    displayNewKey(responseKey)
    openRefresh.value = false
    emits('changed')
  } catch (error) {
    Snackbar.error('Failed to refresh service account API key')
    console.error('Failed to refresh service account API key', error)
  } finally {
    isRegenerating.value = false
  }
}

async function copyKey(key: string) {
  try {
    await navigator.clipboard.writeText(key)
    Snackbar.success('Service account API key copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy key')
  }
}

async function loadRoles() {
  try {
    const res = await hs.workspaces.getRoles({
      workspace_id: [workspaceId.value, 'null'],
      order_by: ['name'],
    })
    if (!res.ok) {
      rolesLoadError.value = 'Unable to load service account roles.'
      rolesLoaded.value = false
      return
    }
    roles.value = res.data
    rolesLoadError.value = ''
    rolesLoaded.value = true
  } catch (error) {
    console.error('Error fetching service account roles', error)
    rolesLoadError.value = 'Unable to load service account roles.'
    rolesLoaded.value = false
  }
}

async function reloadData() {
  isLoading.value = true
  await Promise.all([loadData(), loadRoles()])
  isLoading.value = false
}

onMounted(loadRoles)
</script>

<style scoped>
.service-accounts-section {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.service-accounts-help-text {
  color: var(--hs-text-secondary);
  line-height: 1.5;
  max-width: 640px;
  margin-bottom: 10px;
}
.workspace-table-search {
  position: relative;
  flex: 1;
  max-width: 560px;
}
.workspace-table-search-icon {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--hs-input-border);
  pointer-events: none;
}
.workspace-table-search-input {
  width: 100%;
  height: 30px;
  border: 1px solid var(--hs-input-border);
  border-radius: var(--hs-radius-sm);
  padding-left: 30px;
  padding-right: var(--hs-space-10);
  outline: none;
  background: var(--hs-surface);
}
.workspace-table-search-input::placeholder {
  color: var(--hs-text-secondary);
  opacity: 1;
}
.workspace-table-search-input:focus {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 1px rgb(var(--v-theme-primary));
}
.service-accounts-table-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  margin-top: 0;
  overflow: hidden;
}
.service-accounts-data-table {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
</style>
