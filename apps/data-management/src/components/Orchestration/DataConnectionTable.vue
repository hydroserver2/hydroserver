<template>
  <v-card>
    <v-toolbar title="Data connections" flat color="teal">
      <v-spacer />
      <v-text-field
        label="Search"
        clearable
        v-model="search"
        :prepend-inner-icon="mdiMagnify"
        hide-details
        density="compact"
        variant="underlined"
        maxWidth="300"
      />

      <v-btn
        class="ml-4"
        color="white"
        variant="outlined"
        density="compact"
        :append-icon="mdiMenuUp"
        @click="openDataConnectionTableDialog = false"
      >
        Close data connections table
      </v-btn>

      <v-tooltip location="top" :disabled="canEditWorkspace">
        <template #activator="{ props: tooltipProps }">
          <span v-bind="tooltipProps" class="inline-flex">
            <v-btn-add
              color="teal-lighten-3"
              class="mx-4"
              :disabled="!canEditWorkspace"
              @click="openCreateDialog(null)"
              >Add data connection</v-btn-add
            >
          </span>
        </template>
        <span>{{ readOnlyTooltip }}</span>
      </v-tooltip>
    </v-toolbar>

    <v-data-table-virtual
      :headers="headers"
      :items="items"
      :search="search"
      :loading="loading"
      class="data-connection-table"
      fixed-header
      no-data-text="There's currently no templates for this workspace"
    >
      <template v-slot:item.actions="{ item }">
        <v-tooltip location="top" :disabled="canEditWorkspace">
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="inline-flex">
              <v-btn
                :icon="mdiPencil"
                size="small"
                variant="text"
                color="secondary"
                :disabled="!canEditWorkspace"
                @click="openDialogIfAllowed(item, 'edit')"
              />
            </span>
          </template>
          <span>{{ readOnlyTooltip }}</span>
        </v-tooltip>
        <v-tooltip location="top" :disabled="canEditWorkspace">
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="inline-flex">
              <v-btn
                :icon="mdiDelete"
                size="small"
                variant="text"
                color="delete"
                :disabled="!canEditWorkspace"
                @click="openDialogIfAllowed(item, 'delete')"
              />
            </span>
          </template>
          <span>{{ readOnlyTooltip }}</span>
        </v-tooltip>
      </template>
    </v-data-table-virtual>
  </v-card>

  <v-dialog
    v-model="openCreate"
    transition="dialog-bottom-transition"
    width="60rem"
  >
    <DataConnectionForm @close="openCreate = false" @created="refreshTable" />
  </v-dialog>

  <v-dialog v-model="openEdit" width="80rem">
    <DataConnectionForm
      :dataConnection="item"
      @close="openEdit = false"
      @updated="onUpdate"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteDataConnectionCard
      @close="openDelete = false"
      @delete="onDelete"
      :itemName="item.name"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, toRef } from 'vue'
import DataConnectionForm from '@/components/Orchestration/DataConnectionForm.vue'
import hs, {
  DataConnection,
  OrchestrationSystem,
  PermissionAction,
  PermissionResource,
} from '@hydroserver/client'
import { mdiMagnify, mdiPencil, mdiDelete, mdiMenuUp } from '@mdi/js'
import { useTableLogic } from '@/composables/useTableLogic'
import DeleteDataConnectionCard from './DeleteDataConnectionCard.vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useWorkspaceStore } from '@/store/workspaces'
import { useDataConnectionStore } from '@/store/dataConnection'
import { storeToRefs } from 'pinia'

const props = defineProps<{
  workspaceId: string
}>()

const openCreate = ref(false)
const search = ref()
const selectedOrchestrationSystem = ref<OrchestrationSystem>()
const loading = ref(false)
const { workspaces } = storeToRefs(useWorkspaceStore())
const { openDataConnectionTableDialog } = storeToRefs(useDataConnectionStore())
const { hasPermission, isAdmin, isOwner } = useWorkspacePermissions()

const workspaceForPage = computed(() =>
  workspaces.value.find((workspace) => workspace.id === props.workspaceId)
)

const canEditWorkspace = computed(() => {
  const workspace = workspaceForPage.value
  if (!workspace) return false

  const roleName = `${workspace.collaboratorRole?.name ?? ''}`.toLowerCase()
  if (isAdmin() || isOwner(workspace) || roleName === 'editor') return true

  return hasPermission(
    PermissionResource.Workspace,
    PermissionAction.Edit,
    workspace
  )
})
const readOnlyTooltip =
  'You have read-only access to this workspace. Ask an editor or owner to make changes.'

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  useTableLogic(
    async (wsId: string) =>
      await hs.dataConnections.listAllItems({
        workspace_id: [wsId],
        expand_related: true,
        order_by: ['name'],
      }),
    hs.dataConnections.delete,
    DataConnection,
    toRef(props, 'workspaceId')
  )

const refreshTable = async () => {
  items.value = await hs.dataConnections.listAllItems({
    workspace_id: [props.workspaceId],
    expand_related: true,
    order_by: ['name'],
  })
}

const openCreateDialog = (selectedItem: any) => {
  if (!canEditWorkspace.value) return
  selectedOrchestrationSystem.value = selectedItem
  openCreate.value = true
}

const openDialogIfAllowed = (selectedItem: any, action: 'edit' | 'delete') => {
  if (!canEditWorkspace.value) return
  openDialog(selectedItem, action)
}

const headers = [
  {
    title: 'Data connection name',
    key: 'name',
  },
  {
    title: 'Extractor',
    key: 'extractor.type',
  },
  {
    title: 'Transformer',
    key: 'transformer.type',
  },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const
</script>

<style scoped>
.data-connection-table :deep(.v-table__wrapper) {
  max-height: 56vh;
}
</style>
