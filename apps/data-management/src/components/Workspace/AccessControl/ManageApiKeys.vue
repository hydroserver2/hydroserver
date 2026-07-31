<template>
  <div class="api-keys-header">
    <h6 class="text-h6">API keys</h6>
    <v-icon
      :icon="mdiHelpCircleOutline"
      @click="showApiKeyHelp = !showApiKeyHelp"
      color="grey"
      size="18"
      class="api-keys-help-icon"
    />
  </div>

  <p v-if="showApiKeyHelp" class="api-keys-help-text">
    API keys are intended to provide remote systems with a subset of permissions
    to this workspace.
  </p>

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
        :aria-label="`Copy API key ${newKey.key}`"
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

const workspaceId = computed(() => props.workspace.id)
const { hasPermission } = useWorkspacePermissions()
const canCreate = computed(() =>
  hasPermission(
    PermissionResource.ApiKey,
    PermissionAction.Create,
    props.workspace
  )
)
const canEdit = computed(() =>
  hasPermission(
    PermissionResource.ApiKey,
    PermissionAction.Edit,
    props.workspace
  )
)
const canDelete = computed(() =>
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

const showNewKey = ref(false)
const newKey = ref<ApiKey>()

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  useTableLogic(
    async (wsId: string) => {
      const res = await hs.workspaces.getApiKeys(wsId)
      return res.ok ? res.data : []
    },
    async (keyId: string) => {
      await hs.workspaces.deleteApiKey(workspaceId.value, keyId)
    },
    ApiKey,
    workspaceId
  )

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Role', key: 'role.name' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const

const onCreate = (key: ApiKey) => {
  items.value.push(key)
  displayNewKey(key)
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
  } catch (error) {
    Snackbar.error('Failed to refresh API key')
    console.error('Failed to refresh API key', error)
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

onMounted(async () => {
  try {
    const res = await hs.workspaces.getRoles({
      is_apikey_role: true,
      order_by: ['name'],
    })
    if (res.ok) roles.value = res.data
  } catch (error) {
    console.error('Error fetching collaborators for workspace', error)
  }
})
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
