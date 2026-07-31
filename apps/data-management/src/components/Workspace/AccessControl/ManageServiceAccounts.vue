<template>
  <v-row align="center">
    <v-col cols="auto" class="pr-0">
      <v-card-item>
        <v-card-title> Service accounts </v-card-title>
      </v-card-item>
    </v-col>
    <v-col class="pl-0">
      <v-icon
        :icon="mdiHelpCircleOutline"
        @click="showServiceAccountHelp = !showServiceAccountHelp"
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
      >Create service account</v-btn
    >
  </v-row>

  <v-card-text v-if="showServiceAccountHelp">
    Service accounts are intended to provide remote systems with a subset of
    permissions to workspaces.
  </v-card-text>

  <v-card-text v-if="showNewKey && newKey">
    <v-alert
      type="success"
      border="start"
      elevation="2"
      variant="tonal"
      class="mb-4"
    >
      Your service account API key has been generated. Please copy it and store it
      somewhere safe — you won’t be able to see it again after leaving this
      page.
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
        :aria-label="`Copy service account API key ${newKey.key}`"
      />
    </v-sheet>
  </v-card-text>

  <v-data-table-virtual
    :headers="headers"
    :items="items"
    :sort-by="sortBy"
    :search="search"
    :style="{ 'max-height': `100vh` }"
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
      <v-icon :icon="mdiRefresh" @click="onOpenRegenerateDialog(item)" />
      <v-icon :icon="mdiPencil" @click="openDialog(item, 'edit')" />
      <v-icon :icon="mdiTrashCanOutline" @click="openDialog(item, 'delete')" />
    </template>
  </v-data-table-virtual>

  <v-dialog v-model="openCreate" width="40rem">
    <ServiceAccountForm
      @close="openCreate = false"
      @created="onCreate"
      :workspace-id="workspaceId"
      :roles="roles"
    />
  </v-dialog>

  <v-dialog v-model="openRefresh" width="40rem">
    <ServiceAccountRegenerateForm
      @close="openRefresh = false"
      @regenerated="onRegenerate"
    />
  </v-dialog>

  <v-dialog v-model="openEdit" width="40rem">
    <ServiceAccountForm
      @close="openEdit = false"
      @updated="onUpdate"
      :workspace-id="workspaceId"
      :roles="roles"
      :service-account="item"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteServiceAccount
      :itemName="item.name"
      @delete="onDelete"
      @close="openDelete = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import hs, { ServiceAccount, CollaboratorRole } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { onMounted, ref, toRef } from 'vue'
import { useTableLogic } from '@/composables/useTableLogic'
import ServiceAccountForm from './ServiceAccountForm.vue'
import DeleteServiceAccount from './DeleteServiceAccount.vue'
import ServiceAccountRegenerateForm from './ServiceAccountRegenerateForm.vue'
import {
  mdiContentCopy,
  mdiTrashCanOutline,
  mdiHelpCircleOutline,
  mdiPencil,
  mdiPlus,
  mdiRefresh,
} from '@mdi/js'

type ServiceAccountRow = ServiceAccount & { role?: CollaboratorRole }

const props = defineProps({
  workspaceId: { type: String, required: true },
})

const openCreate = ref(false)
const openRefresh = ref(false)
const showServiceAccountHelp = ref(false)
const sortBy = [{ key: 'OPName' }]
const search = ref()
const roles = ref<CollaboratorRole[]>([])

const showNewKey = ref(false)
const newKey = ref<ServiceAccount>()

async function fetchServiceAccountsWithRoles(
  wsId: string
): Promise<ServiceAccountRow[]> {
  const [accountsRes, collaboratorsRes] = await Promise.all([
    hs.workspaces.getServiceAccounts(wsId),
    hs.workspaces.getCollaborators(wsId),
  ])
  if (!accountsRes.ok) return []

  const roleByEmail = new Map<string, CollaboratorRole>()
  if (collaboratorsRes.ok) {
    for (const c of collaboratorsRes.data) {
      if (c.serviceAccount) roleByEmail.set(c.serviceAccount.email, c.role)
    }
  }

  return accountsRes.data.map((account) => ({
    ...account,
    role: roleByEmail.get(account.email),
  }))
}

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  useTableLogic<ServiceAccountRow>(
    fetchServiceAccountsWithRoles,
    async (serviceAccountId: string) => {
      await hs.workspaces.deleteServiceAccount(
        props.workspaceId,
        serviceAccountId
      )
    },
    ServiceAccount,
    toRef(props, 'workspaceId')
  )

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Role', key: 'role.name' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const

const onCreate = (account: ServiceAccountRow) => {
  items.value.push(account)
  displayNewKey(account)
}

const displayNewKey = (account: ServiceAccount) => {
  newKey.value = account
  showNewKey.value = true
}

function onOpenRegenerateDialog(selectedItem: ServiceAccountRow) {
  item.value = selectedItem
  openRefresh.value = true
}

const onRegenerate = async () => {
  try {
    const res = await hs.workspaces.regenerateServiceAccountKey(
      props.workspaceId,
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
  } catch (error) {
    Snackbar.error('Failed to refresh service account API key')
    console.error('Failed to refresh service account API key', error)
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

onMounted(async () => {
  try {
    const res = await hs.workspaces.getRoles({
      order_by: ['name'],
    })
    if (res.ok) roles.value = res.data
  } catch (error) {
    console.error('Error fetching collaborators for workspace', error)
  }
})
</script>