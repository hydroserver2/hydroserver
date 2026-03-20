<template>
  <v-row align="center">
    <v-col cols="auto" class="pr-0">
      <v-card-item>
        <v-card-title> API keys </v-card-title>
      </v-card-item>
    </v-col>
    <v-col class="pl-0">
      <v-icon
        :icon="mdiHelpCircleOutline"
        @click="showApiKeyHelp = !showApiKeyHelp"
        color="grey"
        small
      />
    </v-col>

    <v-spacer />

    <v-btn
      variant="text"
      :prepend-icon="mdiPlus"
      class="mr-4"
      @click="openCreate = true"
      >Create API key</v-btn
    >
  </v-row>

  <v-card-text v-if="showApiKeyHelp">
    API keys are intended to provide remote systems with a subset of permissions
    to this workspace.
  </v-card-text>

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
      <v-icon :icon="mdiRefresh" @click="onOpenRegenerateDialog(item)" />
      <v-icon :icon="mdiPencil" @click="openDialog(item, 'edit')" />
      <v-icon :icon="mdiDelete" @click="openDialog(item, 'delete')" />
    </template>
  </v-data-table-virtual>

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
import hs, { ApiKey, CollaboratorRole } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { onMounted, ref, toRef } from 'vue'
import { useTableLogic } from '@/composables/useTableLogic'
import ApiKeyForm from './ApiKeyForm.vue'
import DeleteApiKey from './DeleteApiKey.vue'
import ApiKeyRegenerateForm from './ApiKeyRegenerateForm.vue'
import {
  mdiContentCopy,
  mdiDelete,
  mdiHelpCircleOutline,
  mdiPencil,
  mdiPlus,
  mdiRefresh,
} from '@mdi/js'

const props = defineProps({
  workspaceId: { type: String, required: true },
})

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
      return res.data
    },
    async (keyId: string) => {
      await hs.workspaces.deleteApiKey(props.workspaceId, keyId)
    },
    ApiKey,
    toRef(props, 'workspaceId')
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
  item.value = selectedItem
  openRefresh.value = true
}

const onRegenerate = async () => {
  try {
    const res = await hs.workspaces.regenerateApiKey(
      props.workspaceId,
      item.value.id
    )
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
    roles.value = res.data
  } catch (error) {
    console.error('Error fetching collaborators for workspace', error)
  }
})
</script>
