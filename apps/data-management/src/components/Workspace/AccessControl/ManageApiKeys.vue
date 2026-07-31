<template>
  <div class="api-keys-header">
    <h6 class="text-h6">API keys</h6>
    <v-btn
      @click="showApiKeyHelp = !showApiKeyHelp"
      :icon="mdiHelpCircleOutline"
      variant="text"
      density="compact"
      size="x-small"
      class="api-keys-help-icon"
      aria-label="Toggle API key help"
      :aria-expanded="showApiKeyHelp"
    />
  </div>

  <p v-if="showApiKeyHelp" class="api-keys-help-text">
    API keys are intended to provide remote systems with a subset of permissions
    to this workspace.
  </p>

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
      Your API key has been generated. Please copy it and store it somewhere
      safe — you won’t be able to see it again after leaving this page.
    </v-alert>

    <v-sheet
      color="grey-lighten-5"
      class="pa-4 rounded d-flex align-center justify-space-between"
      border
    >
      <span class="text-mono text-wrap break-all">{{ newKey.key }}</span>
      <v-btn
        :icon="mdiContentCopy"
        variant="text"
        @click="copyKey(newKey.key)"
        aria-label="Copy API key"
      />
    </v-sheet>
  </v-card-text>

  <v-card class="hs-table-card api-keys-table-card" flat>
    <v-toolbar flat density="compact">
      <v-spacer />
      <PermissionTooltip
        :has-permission="canCreate"
        message="You don't have permission to create API keys for this workspace."
      >
        <template #default>
          <v-btn-add class="mr-2" @click="openCreate = true">
            Create API key
          </v-btn-add>
        </template>
        <template #denied>
          <v-btn-add class="mr-2" disabled>Create API key</v-btn-add>
        </template>
      </PermissionTooltip>
    </v-toolbar>

    <v-data-table-virtual
      :headers="headers"
      :items="items"
      :sort-by="sortBy"
      :search="search"
      :style="{ 'max-height': `100vh` }"
      no-data-text="No keys available"
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
          :disabled="!canEdit"
          :aria-label="`Regenerate ${item.name}`"
          @click="onOpenRegenerateDialog(item)"
        />
        <v-btn
          :icon="mdiPencil"
          variant="text"
          size="small"
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

  <v-dialog v-model="openCreate" width="40rem">
    <ApiKeyForm
      @close="openCreate = false"
      @created="onCreate"
      :workspace-id="workspaceId"
      :roles="roles"
    />
  </v-dialog>

  <v-dialog v-model="openRefresh" width="40rem">
    <ApiKeyRegenerateForm
      @close="openRefresh = false"
      @regenerated="onRegenerate"
      :loading="isRegenerating"
    />
  </v-dialog>

  <v-dialog v-model="openEdit" width="40rem">
    <ApiKeyForm
      @close="openEdit = false"
      @updated="onUpdate"
      :workspace-id="workspaceId"
      :roles="roles"
      :api-key="item"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteApiKey
      :itemName="item.name"
      :loading="isDeleting"
      @delete="onDelete"
      @close="openDelete = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import hs, {
  ApiKey,
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
import ApiKeyForm from './ApiKeyForm.vue'
import DeleteApiKey from './DeleteApiKey.vue'
import ApiKeyRegenerateForm from './ApiKeyRegenerateForm.vue'
import {
  mdiContentCopy,
  mdiTrashCanOutline,
  mdiHelpCircleOutline,
  mdiPencil,
  mdiRefresh,
} from '@mdi/js'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['changed'])

const workspaceId = computed(() => props.workspace.id)
const { hasPermission } = useWorkspacePermissions()
const apiKeysLoaded = ref(false)
const rolesLoaded = ref(false)
const canCreate = computed(
  () =>
    apiKeysLoaded.value &&
    rolesLoaded.value &&
    hasPermission(
      PermissionResource.ApiKey,
      PermissionAction.Create,
      props.workspace
    )
)
const canEdit = computed(
  () =>
    apiKeysLoaded.value &&
    rolesLoaded.value &&
    hasPermission(
      PermissionResource.ApiKey,
      PermissionAction.Edit,
      props.workspace
    )
)
const canDelete = computed(
  () =>
    apiKeysLoaded.value &&
    hasPermission(
      PermissionResource.ApiKey,
      PermissionAction.Delete,
      props.workspace
    )
)

const openCreate = ref(false)
const openRefresh = ref(false)
const showApiKeyHelp = ref(false)
const sortBy = [{ key: 'OPName' }]
const search = ref()
const roles = ref<CollaboratorRole[]>([])
const apiKeysLoadError = ref('')
const rolesLoadError = ref('')
const isLoading = ref(false)
const isDeleting = ref(false)
const isRegenerating = ref(false)
const loadError = computed(() => apiKeysLoadError.value || rolesLoadError.value)

const showNewKey = ref(false)
const newKey = ref<ApiKey>()

const {
  item,
  items,
  openEdit,
  openDelete,
  openDialog,
  onUpdate: updateTableItem,
  onDelete: deleteTableItem,
  loadData,
} = useTableLogic(
  async (wsId: string) => {
    try {
      const res = await hs.workspaces.getApiKeys(wsId)
      if (!res.ok) {
        apiKeysLoadError.value = 'Unable to load API keys.'
        apiKeysLoaded.value = false
        throw new Error(res.message || 'Unable to load API keys.')
      }
      apiKeysLoadError.value = ''
      apiKeysLoaded.value = true
      return res.data
    } catch (error) {
      apiKeysLoadError.value = 'Unable to load API keys.'
      apiKeysLoaded.value = false
      throw error
    }
  },
  async (keyId: string) => {
    const res = await hs.workspaces.deleteApiKey(workspaceId.value, keyId)
    if (!res.ok) {
      Snackbar.error(res.message || 'Failed to delete API key')
      throw new Error(res.message || 'Failed to delete API key')
    }
  },
  ApiKey,
  workspaceId
)

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Role', key: 'role.name' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const

const onUpdate = (key: ApiKey) => {
  updateTableItem(key)
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

const onCreate = (key: ApiKey) => {
  items.value.push(key)
  displayNewKey(key)
  emits('changed')
}

const displayNewKey = (key: ApiKey) => {
  newKey.value = key
  showNewKey.value = true
}

function onOpenRegenerateDialog(selectedItem: ApiKey) {
  if (!canEdit.value) return
  item.value = selectedItem
  openRefresh.value = true
}

const onRegenerate = async () => {
  if (isRegenerating.value) return
  isRegenerating.value = true
  try {
    const res = await hs.workspaces.regenerateApiKey(
      workspaceId.value,
      item.value.id
    )
    if (!res.ok) {
      Snackbar.error('Failed to refresh API key')
      return
    }
    const responseKey = res.data
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
    Snackbar.error('Failed to refresh API key')
    console.error('Failed to refresh API key', error)
  } finally {
    isRegenerating.value = false
  }
}

async function copyKey(key: string) {
  try {
    await navigator.clipboard.writeText(key)
    Snackbar.success('API key copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy key')
  }
}

async function loadRoles() {
  try {
    const res = await hs.workspaces.getRoles({
      is_apikey_role: true,
      order_by: ['name'],
    })
    if (!res.ok) {
      rolesLoadError.value = 'Unable to load API key roles.'
      rolesLoaded.value = false
      return
    }
    roles.value = res.data
    rolesLoadError.value = ''
    rolesLoaded.value = true
  } catch (error) {
    console.error('Error fetching API key roles', error)
    rolesLoadError.value = 'Unable to load API key roles.'
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
.api-keys-header {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}
.api-keys-help-icon {
  cursor: pointer;
}
.api-keys-help-text {
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.5;
  max-width: 640px;
  margin-bottom: 10px;
}
.api-keys-table-card {
  margin-top: 6px;
}
</style>
