<template>
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
      <v-btn variant="text" size="small" @click="loadCollaboratorData">
        Retry
      </v-btn>
    </div>
  </v-alert>
  <v-progress-linear v-if="isLoading" indeterminate class="mb-2" />

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
      <v-btn-primary
        data-testid="submit-collaborator-button"
        :loading="isAdding"
        :disabled="isAdding"
        @click="onAddCollaborator"
      >
        Add collaborator
      </v-btn-primary>
    </v-card-actions>
  </v-card-text>

  <div class="hs-table-tools">
    <v-text-field
      v-model="search"
      class="hs-table-search"
      placeholder="Search collaborators"
      aria-label="Search collaborators"
      :prepend-inner-icon="mdiMagnify"
      clearable
      hide-details
      density="compact"
    />

    <div class="hs-table-actions">
      <v-btn
        :icon="mdiHelpCircleOutline"
        variant="text"
        size="small"
        color="grey-darken-2"
        title="About collaborators"
        aria-label="Toggle collaborator help"
        :aria-expanded="showAddCollaboratorHelp"
        @click="showAddCollaboratorHelp = !showAddCollaboratorHelp"
      />

      <PermissionTooltip
        :has-permission="canCreate"
        message="You don't have permission to add collaborators to this workspace."
      >
        <template #default>
          <v-btn-primary
            variant="flat"
            data-testid="add-collaborator-button"
            @click="showAddCollaborator = true"
            >Add collaborator</v-btn-primary
          >
        </template>

        <template #denied>
          <v-btn-primary
            variant="flat"
            disabled
            data-testid="add-collaborator-button"
            @click="showAddCollaborator = true"
            >Add collaborator</v-btn-primary
          >
        </template>
      </PermissionTooltip>
    </div>
  </div>

  <p v-if="showAddCollaboratorHelp" class="collaborators-help-text">
    <small>
      You can add collaborators to this workspace with either Editor or Viewer
      roles. Viewers can see everything in the workspace but cannot edit.
      Editors can create, read, update, and delete all sites, metadata, and
      datastreams as well as set their visibility. Users can remove themselves
      as collaborators.
    </small>
  </p>

  <v-card class="hs-table-card collaborators-table-card" flat>
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
          v-for="item in filteredCollaborators"
          :key="item.email"
          :data-testid="`collaborator-row-${item.email}`"
        >
          <td>
            <div class="font-weight-medium">
              {{ item.name }}
            </div>
            <div class="hs-text-2xs text-medium-emphasis">
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
              <v-btn-cancel
                size="small"
                class="mr-2"
                @click="onCancelEdit(item)"
                >Cancel</v-btn-cancel
              >
              <v-btn
                size="small"
                :loading="item.isSaving"
                :disabled="item.isSaving"
                :data-testid="`save-collaborator-${item.email}`"
                @click="onSaveRole(item)"
                >Save</v-btn
              >
            </template>
            <template v-else>
              <v-btn
                variant="text"
                color="grey-darken-2"
                :icon="mdiPencil"
                :disabled="!canEdit"
                :data-testid="`edit-collaborator-${item.email}`"
                :aria-label="`Edit ${item.name}`"
                @click="item.isBeingEdited = true"
              />
              <v-btn
                variant="text"
                color="red-darken-2"
                :icon="mdiTrashCanOutline"
                :loading="removingEmail === item.email"
                :disabled="!canRemove(item) || !!removingEmail"
                :data-testid="`remove-collaborator-${item.email}`"
                :aria-label="`Remove ${item.name}`"
                @click="onRemoveCollaborator(item.email)"
              />
            </template>
          </td>
        </tr>
        <tr v-if="!filteredCollaborators.length">
          <td colspan="4" class="text-center text-medium-emphasis">
            {{
              search ? 'No matching collaborators.' : 'No collaborators yet.'
            }}
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
import { computed, onMounted, ref } from 'vue'
import hs, {
  PermissionAction,
  PermissionResource,
  Collaborator,
  CollaboratorRole,
  Workspace,
} from '@hydroserver/client'
import {
  mdiHelpCircleOutline,
  mdiMagnify,
  mdiPencil,
  mdiTrashCanOutline,
} from '@mdi/js'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import PermissionTooltip from '@/components/PermissionTooltip.vue'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['self-removed', 'changed'])

const { user } = storeToRefs(useUserStore())
const { hasPermission } = useWorkspacePermissions()
const isDataReady = ref(false)
const canCreate = computed(
  () =>
    isDataReady.value &&
    hasPermission(
      PermissionResource.Collaborator,
      PermissionAction.Create,
      props.workspace
    )
)
const canEdit = computed(
  () =>
    isDataReady.value &&
    hasPermission(
      PermissionResource.Collaborator,
      PermissionAction.Edit,
      props.workspace
    )
)
const canDelete = computed(() =>
  hasPermission(
    PermissionResource.Collaborator,
    PermissionAction.Delete,
    props.workspace
  )
)
const canRemove = (item: { email: string }) =>
  canDelete.value || item.email === user.value?.email

const showAddCollaboratorHelp = ref(false)
const showAddCollaborator = ref(false)
const selectedRole = ref()
const newCollaboratorEmail = ref('')
const roles = ref<CollaboratorRole[]>([])
const collaboratorList = ref<any[]>([])
const search = ref('')
const filteredCollaborators = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  if (!query) return collaboratorList.value

  return collaboratorList.value.filter((collaborator) =>
    [
      collaborator.name,
      collaborator.email,
      collaborator.organization,
      collaborator.role?.name,
    ].some((value) =>
      String(value ?? '')
        .toLocaleLowerCase()
        .includes(query)
    )
  )
})
const isLoading = ref(false)
const loadError = ref('')
const isAdding = ref(false)
const removingEmail = ref('')

/**
 * Save the new role, then reset editing state
 */
async function onSaveRole(item: any) {
  if (!canEdit.value || item.isSaving) return
  item.isSaving = true
  try {
    const res = await hs.workspaces.updateCollaboratorRole(
      props.workspace.id,
      item.email,
      item.pendingRole.id
    )
    if (res.ok) {
      item.role = res.data.role
      item.isBeingEdited = false
      Snackbar.success('Collaborator role updated.')
      emits('changed')
    } else {
      console.error('Error updating collaborator role:', res)
      Snackbar.error(res.message || 'Unable to update the collaborator role.')
      item.isBeingEdited = true
    }
  } catch (error) {
    console.error('Error updating collaborator role:', error)
    Snackbar.error('Unable to update the collaborator role.')
  } finally {
    item.isSaving = false
  }
}

function cancelAddCollaborator() {
  showAddCollaborator.value = false
  selectedRole.value = ''
  newCollaboratorEmail.value = ''
}

async function onAddCollaborator() {
  if (!canCreate.value || isAdding.value) return
  if (!newCollaboratorEmail.value || !selectedRole.value) {
    Snackbar.warn('Please fill out collaborator email and role.')
    return
  }

  isAdding.value = true
  try {
    const res = await hs.workspaces.addCollaborator(
      props.workspace!.id,
      newCollaboratorEmail.value,
      selectedRole.value.id
    )
    if (res.ok) {
      if (res.data.user && !res.data.serviceAccount) {
        collaboratorList.value.push(collaboratorToFormData(res.data))
      }
      collaboratorList.value.sort((a, b) => a.name.localeCompare(b.name))
      Snackbar.success('Collaborator added to workspace.')
      showAddCollaborator.value = false
      newCollaboratorEmail.value = ''
      selectedRole.value = ''
      emits('changed')
    } else {
      console.error('Error adding collaborator', res)
      Snackbar.error(res.message || 'Unable to add the collaborator.')
    }
  } catch (error) {
    console.error('Error adding collaborator', error)
    Snackbar.error('Unable to add the collaborator.')
  } finally {
    isAdding.value = false
  }
}

async function onRemoveCollaborator(email: string) {
  if (removingEmail.value || (!canDelete.value && email !== user.value?.email))
    return
  removingEmail.value = email
  try {
    const res = await hs.workspaces.removeCollaborator(
      props.workspace!.id,
      email
    )

    if (res.ok) {
      const index = collaboratorList.value.findIndex((c) => c.email === email)
      if (index !== -1) collaboratorList.value.splice(index, 1)
      Snackbar.success('Collaborator removed.')
      emits('changed')
      if (email === user.value.email) emits('self-removed')
    } else {
      console.error('Error removing collaborator', res)
      Snackbar.error(res.message || 'Unable to remove the collaborator.')
    }
  } catch (error) {
    console.error('Error removing collaborator', error)
    Snackbar.error('Unable to remove the collaborator.')
  } finally {
    removingEmail.value = ''
  }
}

const setCollaboratorList = (collaborators: Collaborator[]) => {
  collaboratorList.value = collaborators
    .filter((collaborator) => collaborator.user && !collaborator.serviceAccount)
    .map((collaborator) => collaboratorToFormData(collaborator))

  if (props.workspace?.owner) {
    collaboratorList.value.unshift({
      email: props.workspace.owner.email,
      value: props.workspace.owner.email,
      name: props.workspace.owner.name,
      role: { name: 'Owner' },
      organization: props.workspace.owner.organizationName || 'No Organization',
      isOwner: true,
      isBeingEdited: false,
      isSaving: false,
    })
  }
  collaboratorList.value.sort((a, b) => a.name.localeCompare(b.name))
}

async function onCancelEdit(item: any) {
  item.pendingRole = item.role
  item.isBeingEdited = false
}

const collaboratorToFormData = (c: Collaborator) => {
  const contact = c.user
  return {
    email: contact?.email ?? '',
    value: contact?.email ?? '',
    name: contact?.name ?? '',
    role: c.role,
    pendingRole: c.role,
    organization: c.user?.organizationName || 'No Organization',
    isOwner: false,
    isBeingEdited: false,
    isSaving: false,
  }
}

async function loadCollaboratorData() {
  isLoading.value = true
  loadError.value = ''
  isDataReady.value = false
  try {
    const [cRes, rolesResponse] = await Promise.all([
      hs.workspaces.getCollaborators(props.workspace.id),
      hs.workspaces.getRoles({
        order_by: ['name'],
      }),
    ])

    if (!cRes.ok || !rolesResponse.ok) {
      console.error('Error fetching workspace collaborators', {
        collaborators: cRes,
        roles: rolesResponse,
      })
      loadError.value = 'Unable to load all collaborator data.'
    }

    roles.value = rolesResponse.ok
      ? rolesResponse.data.filter(
          (role: CollaboratorRole) =>
            role.workspaceId === null || role.workspaceId === props.workspace.id
        )
      : []
    setCollaboratorList(cRes.ok ? cRes.data : [])
    isDataReady.value = cRes.ok && rolesResponse.ok
  } catch (error) {
    console.error('Error fetching workspace collaborators', error)
    loadError.value = 'Unable to load collaborator data.'
    roles.value = []
    setCollaboratorList([])
  } finally {
    isLoading.value = false
  }
}

onMounted(loadCollaboratorData)
</script>

<style scoped>
.collaborators-help-text {
  color: var(--hs-text-secondary);
  line-height: 1.5;
  max-width: 640px;
  margin-bottom: 10px;
}
.collaborators-table-card {
  margin-top: 0;
}
.collaborator-table :deep(td) {
  vertical-align: middle;
}
</style>
