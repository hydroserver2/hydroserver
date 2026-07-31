<template>
  <div class="collaborators-header">
    <h6 class="text-h6">Collaborators</h6>
    <v-icon
      @click="showAddCollaboratorHelp = !showAddCollaboratorHelp"
      color="grey"
      size="18"
      class="collaborators-help-icon"
      :icon="mdiHelpCircleOutline"
    />
  </div>

  <p v-if="showAddCollaboratorHelp" class="collaborators-help-text">
    You can add collaborators to this workspace with either Editor or Viewer
    roles. Viewers can see everything in the workspace but cannot edit. Editors
    can create, read, update, and delete all sites, metadata, and datastreams as
    well as set their visibility. Users can remove themselves as collaborators.
  </p>

  <v-card-text v-if="showAddCollaborator">
    <v-text-field
      v-model="newCollaboratorEmail"
      label="New collaborator's email"
      data-testid="new-collaborator-email"
    />
    <v-select
      v-model="selectedRole"
      :items="roles"
      label="New collaborator's role"
      item-title="name"
      :return-object="true"
      variant="outlined"
      data-testid="new-collaborator-role"
    />
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="cancelAddCollaborator">Cancel</v-btn-cancel>
      <v-btn-primary @click="onAddCollaborator">Add collaborator</v-btn-primary>
    </v-card-actions>
  </v-card-text>

  <v-card class="hs-table-card collaborators-table-card" flat>
    <v-toolbar flat density="compact">
      <v-spacer />

      <PermissionTooltip
        :has-permission="
          hasPermission(
            PermissionResource.Collaborator,
            PermissionAction.Create,
            workspace
          )
        "
      >
        <template #default>
          <v-btn
            variant="text"
            :prepend-icon="mdiPlus"
            class="mr-2"
            data-testid="add-collaborator-button"
            @click="showAddCollaborator = true"
            >Add collaborator</v-btn
          >
        </template>

        <template #denied>
          <v-btn
            disabled
            variant="text"
            :prepend-icon="mdiPlus"
            class="mr-2"
            data-testid="add-collaborator-button"
            @click="showAddCollaborator = true"
            >Add collaborator</v-btn
          >
        </template>
      </PermissionTooltip>
    </v-toolbar>

    <v-table class="collaborator-table">
      <thead>
        <tr>
          <th>Member</th>
          <th>Organization</th>
          <th style="width: 200px">Role</th>
          <th class="text-right" style="width: 190px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in collaboratorList"
          :key="item.email"
          :data-testid="`collaborator-row-${item.email}`"
        >
          <td>
            <div class="font-weight-medium">{{ item.name }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ item.email }}
            </div>
          </td>
          <td>{{ item.organization }}</td>
          <td>
            <v-select
              v-if="item.isBeingEdited"
              v-model="item.pendingRole"
              :items="roles"
              item-title="name"
              :return-object="true"
              variant="outlined"
              density="compact"
              hide-details
            />
            <span v-else>{{ item.role.name }}</span>
          </td>
          <td class="text-right">
            <span v-if="item.isOwner" class="text-medium-emphasis">—</span>
            <template v-else-if="item.isBeingEdited">
              <v-btn-cancel size="small" class="mr-2" @click="onCancelEdit(item)"
                >Cancel</v-btn-cancel
              >
              <v-btn
                size="small"
                :data-testid="`save-collaborator-${item.email}`"
                @click="onSaveRole(item)"
                >Save</v-btn
              >
            </template>
            <template v-else>
              <v-btn
                variant="text"
                :icon="mdiPencil"
                :data-testid="`edit-collaborator-${item.email}`"
                :aria-label="`Edit ${item.name}`"
                @click="item.isBeingEdited = true"
              />
              <v-btn
                variant="text"
                color="red-darken-2"
                :icon="mdiTrashCanOutline"
                :data-testid="`remove-collaborator-${item.email}`"
                :aria-label="`Remove ${item.name}`"
                @click="onRemoveCollaborator(item.email)"
              />
            </template>
          </td>
        </tr>
        <tr v-if="!collaboratorList.length">
          <td colspan="4" class="text-center text-medium-emphasis">
            No collaborators yet.
          </td>
        </tr>
      </tbody>
    </v-table>
  </v-card>
</template>

<script setup lang="ts">
import { useUserStore } from '@/store/user'
import { Snackbar } from '@/utils/notifications'
import { storeToRefs } from 'pinia'
import { onMounted, ref } from 'vue'
import hs, {
  PermissionAction,
  PermissionResource,
  Collaborator,
  CollaboratorRole,
  Workspace,
} from '@hydroserver/client'
import {
  mdiHelpCircleOutline,
  mdiPencil,
  mdiPlus,
  mdiTrashCanOutline,
} from '@mdi/js'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import PermissionTooltip from '@/components/PermissionTooltip.vue'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['self-removed'])

const { user } = storeToRefs(useUserStore())
const { hasPermission } = useWorkspacePermissions()

const showAddCollaboratorHelp = ref(false)
const showAddCollaborator = ref(false)
const selectedRole = ref()
const newCollaboratorEmail = ref('')
const roles = ref<CollaboratorRole[]>([])
const collaboratorList = ref<any[]>([])

/**
 * Save the new role, then reset editing state
 */
async function onSaveRole(item: any) {
  const res = await hs.workspaces.updateCollaboratorRole(
    props.workspace.id,
    item.email,
    item.pendingRole.id
  )
  if (res.ok) {
    item.role = res.data.role
    item.isBeingEdited = false
    Snackbar.success('Collaborator role updated.')
  } else {
    console.error('Error updating collaborator role:', res)
    Snackbar.error(res.message)
    item.isBeingEdited = true
  }
}

function cancelAddCollaborator() {
  showAddCollaborator.value = false
  selectedRole.value = ''
  newCollaboratorEmail.value = ''
}

async function onAddCollaborator() {
  if (!newCollaboratorEmail.value || !selectedRole.value) {
    Snackbar.warn('Please fill out collaborator email and role.')
    return
  }

  const res = await hs.workspaces.addCollaborator(
    props.workspace!.id,
    newCollaboratorEmail.value,
    selectedRole.value.id
  )
  if (res.ok) {
    collaboratorList.value.push(collaboratorToFormData(res.data))
    collaboratorList.value.sort((a, b) => a.name.localeCompare(b.name))
    Snackbar.success('Collaborator added to workspace.')
    showAddCollaborator.value = false
  } else {
    console.error('Error adding secondary owner', res)
    Snackbar.error(res.message)
    return
  }
  newCollaboratorEmail.value = ''
  selectedRole.value = ''
}

async function onRemoveCollaborator(email: string) {
  const res = await hs.workspaces.removeCollaborator(props.workspace!.id, email)

  if (res.ok) {
    const index = collaboratorList.value.findIndex((c) => c.email === email)
    if (index !== -1) collaboratorList.value.splice(index, 1)
    Snackbar.success('Collaborator removed.')
    if (email === user.value.email) emits('self-removed')
  } else {
    console.error('Error removing collaborator', res)
    Snackbar.error(res.message)
  }
}

const setCollaboratorList = (collaborators: Collaborator[]) => {
  collaboratorList.value = collaborators.map((c) => collaboratorToFormData(c))

  if (props.workspace?.owner) {
    collaboratorList.value.unshift({
      email: props.workspace.owner.email,
      value: props.workspace.owner.email,
      name: props.workspace.owner.name,
      role: { name: 'Owner' },
      organization: props.workspace.owner.organizationName || 'No Organization',
      isOwner: true,
      isBeingEdited: false,
    })
  }
  collaboratorList.value.sort((a, b) => a.name.localeCompare(b.name))
}

async function onCancelEdit(item: any) {
  item.pendingRole = item.role
  item.isBeingEdited = false
}

const collaboratorToFormData = (c: Collaborator) => ({
  email: c.user.email,
  value: c.user.email,
  name: c.user.name,
  role: c.role,
  pendingRole: c.role,
  organization: c.user.organizationName || 'No Organization',
  isOwner: false,
  isBeingEdited: false,
})

onMounted(async () => {
  const [cRes, rolesResponse] = await Promise.all([
    hs.workspaces.getCollaborators(props.workspace.id),
    hs.workspaces.getRoles({
      order_by: ['name'],
      is_user_role: true,
    }),
  ])

  if (!cRes.ok)
    console.error('Error fetching collaborators for workspace', cRes)
  if (!rolesResponse.ok)
    console.error('Error fetching collaborators for workspace', rolesResponse)

  roles.value = rolesResponse.ok
    ? rolesResponse.data.filter(
        (r: CollaboratorRole) =>
          r.workspaceId === null || r.workspaceId == props.workspace.id
      )
    : []
  setCollaboratorList(cRes.ok ? cRes.data : [])
})
</script>

<style scoped>
.collaborators-header {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}
.collaborators-help-icon {
  cursor: pointer;
}
.collaborators-help-text {
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.5;
  max-width: 640px;
  margin-bottom: 10px;
}
.collaborators-table-card {
  margin-top: 6px;
}
.collaborator-table :deep(td) {
  vertical-align: middle;
}
</style>
