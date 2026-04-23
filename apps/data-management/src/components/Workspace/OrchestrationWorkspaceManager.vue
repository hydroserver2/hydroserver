<template>
  <div class="workspace-manager">
    <v-card class="workspace-manager-card" rounded="lg" elevation="0">
      <v-toolbar flat color="secondary-darken-2">
        <v-text-field
          :disabled="!workspaces?.length"
          class="mx-4"
          clearable
          v-model="search"
          :prepend-inner-icon="mdiMagnify"
          label="Search"
          hide-details
          density="compact"
          variant="underlined"
          rounded="xl"
          maxWidth="300"
        />

        <v-spacer />

        <PermissionTooltip
          :has-permission="canCreateWorkspace"
          message="You don't have permissions to create a workspace. Contact your system administrator to change your permissions."
        >
          <template #default>
            <v-btn-add class="mr-2" color="white" @click="openCreate = true">
              Add workspace
            </v-btn-add>
          </template>

          <template #denied>
            <v-btn-add
              disabled
              class="mr-2"
              color="white"
              variant="outlined"
            >
              Add workspace
            </v-btn-add>
          </template>
        </PermissionTooltip>
      </v-toolbar>

      <v-data-table
        :headers="headers"
        :items="workspaces"
        :sort-by="[{ key: 'name' }]"
        :search="search"
        multi-sort
        item-value="id"
        class="elevation-0 workspace-manager-table"
        color="secondary-darken-2"
        :style="{ maxHeight: props.tableHeight }"
        fixed-header
        hide-default-footer
        loading-text="Loading workspaces..."
      >
        <template #no-data>
          <div class="text-center pa-4" v-if="workspaces.length === 0">
            <v-icon
              :icon="mdiBriefcaseOutline"
              size="48"
              color="grey lighten-1"
            />
            <h4 class="mt-2">No workspaces found</h4>
            <p class="mb-4">
              Click the "Add workspace" button to create one.
            </p>
            <v-icon
              class="mb-4"
              @click="showWorkspaceHelp = !showWorkspaceHelp"
              color="grey"
              small
              :icon="mdiHelpCircleOutline"
            />
            <p v-if="showWorkspaceHelp" class="mb-4">
              A workspace is an organizational concept for access control. All
              resources in HydroServer belong to a workspace. After creating
              one, you can assign roles to users who need different permission
              levels.
            </p>
          </div>
        </template>

        <template #item.isPrivate="{ item }">
          {{ item.isPrivate ? 'Private' : 'Public' }}
        </template>

        <template #item.collaboratorRole="{ item }">
          {{ getUserRoleName(item) }}
        </template>

        <template #item.actions="{ item }">
          <v-btn
            variant="text"
            color="primary-darken-2"
            @click="openDialog(item, 'accessControl')"
            :icon="mdiLockPlusOutline"
            :data-testid="`workspace-access-control-${item.id}`"
            rounded="xl"
          />

          <v-btn
            :disabled="
              !hasPermission(
                PermissionResource.Workspace,
                PermissionAction.Edit,
                item
              )
            "
            variant="text"
            color="grey-darken-2"
            @click="openDialog(item, 'edit')"
            :icon="mdiPencil"
            :data-testid="`workspace-edit-${item.id}`"
            rounded="xl"
          />

          <v-btn
            :disabled="
              !hasPermission(
                PermissionResource.Workspace,
                PermissionAction.Delete,
                item
              )
            "
            variant="text"
            color="red-darken-2"
            @click="openDialog(item, 'delete')"
            :icon="mdiDelete"
            :data-testid="`workspace-delete-${item.id}`"
            rounded="xl"
          />
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="openCreate" width="30rem">
      <WorkspaceFormCard
        @close="openCreate = false"
        @created="refreshWorkspaces"
      />
    </v-dialog>

    <v-dialog v-model="openAccessControl" width="70rem">
      <WorkspaceAccessControl
        :workspace="activeItem"
        @close="openAccessControl = false"
        @privacy-updated="activeItem.isPrivate = $event"
        @needs-refresh="refreshAccessControl(activeItem.id)"
      />
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
        @switch-to-access-control="switchToAccessControlModal"
        :workspace="activeItem"
      />
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import hs, {
  PermissionAction,
  PermissionResource,
  Workspace,
} from '@hydroserver/client'
import {
  mdiBriefcaseOutline,
  mdiDelete,
  mdiHelpCircleOutline,
  mdiLockPlusOutline,
  mdiMagnify,
  mdiPencil,
} from '@mdi/js'
import WorkspaceFormCard from '@/components/Workspace/WorkspaceFormCard.vue'
import DeleteWorkspaceCard from '@/components/Workspace/DeleteWorkspaceCard.vue'
import WorkspaceAccessControl from '@/components/Workspace/AccessControl/WorkspaceAccessControl.vue'
import PermissionTooltip from '@/components/PermissionTooltip.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useUserStore } from '@/store/user'
import { Snackbar } from '@/utils/notifications'

const props = withDefaults(
  defineProps<{
    tableHeight?: string
  }>(),
  {
    tableHeight: '400px',
  }
)

const { selectedWorkspace, workspaces } = storeToRefs(useWorkspaceStore())
const { setWorkspaces } = useWorkspaceStore()
const { hasPermission, getUserRoleName } = useWorkspacePermissions()
const { user } = storeToRefs(useUserStore())

const openCreate = ref(false)
const openEdit = ref(false)
const openDelete = ref(false)
const openAccessControl = ref(false)
const search = ref('')
const activeItem = ref<Workspace>({} as Workspace)
const showWorkspaceHelp = ref(false)

const canCreateWorkspace = computed(() =>
  ['admin', 'standard'].includes(user.value?.accountType ?? '')
)

function openDialog(
  item: Workspace,
  dialog: 'edit' | 'delete' | 'accessControl'
) {
  activeItem.value = item
  if (dialog === 'edit') openEdit.value = true
  if (dialog === 'delete') openDelete.value = true
  if (dialog === 'accessControl') openAccessControl.value = true
}

const refreshWorkspaces = async (workspace?: Workspace) => {
  const res = await hs.workspaces.listItems({
    is_associated: true,
    fetch_all: true,
  })
  setWorkspaces(res)

  if (
    workspace &&
    (!selectedWorkspace.value || selectedWorkspace.value.id === workspace.id)
  ) {
    selectedWorkspace.value = workspace
  }
}

const refreshAccessControl = async (workspaceId: string) => {
  try {
    activeItem.value = (await hs.workspaces.getItem(workspaceId)) as Workspace
  } catch (error) {
    console.error('Error refreshing workspaces', error)
  }
}

async function onDelete() {
  if (!activeItem.value) return
  const res = await hs.workspaces.delete(activeItem.value.id)
  if (res.ok) {
    Snackbar.success('Workspace deleted')
    refreshWorkspaces()
  } else Snackbar.error(res.message)
}

function switchToAccessControlModal() {
  openDelete.value = false
  openAccessControl.value = true
}

const headers = [
  { title: 'Workspace name', key: 'name' },
  { title: 'Visibility', key: 'isPrivate' },
  { title: 'Your role', key: 'collaboratorRole' },
  { title: 'Id', key: 'id' },
  { title: 'Actions', key: 'actions', align: 'end' },
] as const
</script>

<style scoped>
.workspace-manager {
  height: 100%;
}

.workspace-manager-card {
  height: 100%;
  border: 1px solid #e8e8e8;
  background: white;
}

:deep(.workspace-manager-table .v-table__wrapper) {
  height: auto !important;
  max-height: v-bind('props.tableHeight');
  border-top: 1px solid #e8e8e8;
}
</style>
