<template>
  <v-row align="center">
    <v-col cols="auto" class="pr-0">
      <v-card-item>
        <v-card-title> Collaborators </v-card-title>
      </v-card-item>
    </v-col>
    <v-col class="pl-0">
      <v-icon
        @click="showAddCollaboratorHelp = !showAddCollaboratorHelp"
        color="grey"
        small
        :icon="mdiHelpCircleOutline"
      />
    </v-col>

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
          class="mr-4"
          @click="showAddCollaborator = true"
          >Add collaborator</v-btn
        >
      </template>

      <template #denied>
        <v-btn
          disabled
          variant="text"
          :prepend-icon="mdiPlus"
          class="mr-4"
          @click="showAddCollaborator = true"
          >Add collaborator</v-btn
        >
      </template>
    </PermissionTooltip>
  </v-row>

  <v-card-text v-if="showAddCollaboratorHelp">
    You can add collaborators to this workspace with either Editor or Viewer
    roles. Viewers can see everything in the workspace but cannot edit. Editors
    can create, read, update, and delete all sites, metadata, and datastreams as
    well as set their visibility. Users can remove themselves as collaborators.
  </v-card-text>

  <v-card-text v-if="showAddCollaborator">
    <v-text-field
      v-model="newCollaboratorEmail"
      label="New collaborator's email"
    />
    <v-select
      v-model="selectedRole"
      :items="roles"
      label="New collaborator's role"
      item-title="name"
      :return-object="true"
      variant="outlined"
    />
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="cancelAddCollaborator">Cancel</v-btn-cancel>
      <v-btn-primary @click="onAddCollaborator">Add collaborator</v-btn-primary>
    </v-card-actions>
  </v-card-text>

  <v-card-text>
    <div class="collaborator-list-container">
      <v-list lines="three" v-model:selected="selection" select-strategy="leaf">
        <v-list-group v-for="item in collaboratorList" :key="item.value">
          <template v-slot:activator="{ props }">
            <v-list-item
              v-bind="props"
              :title="item.name"
              :value="item.value"
              active-class="text-red"
            >
              <v-list-item-subtitle
                v-if="item.isBeingEdited"
                class="mb-1 text-high-emphasis opacity-100"
              >
                <v-select
                  v-model="item.pendingRole"
                  :items="roles"
                  item-title="name"
                  @click.stop
                  @mousedown.stop
                  :return-object="true"
                  variant="outlined"
                  hide-details
                />
                <div class="d-flex my-2">
                  <v-btn-cancel class="mr-2" @click="onCancelEdit(item)"
                    >Cancel</v-btn-cancel
                  >
                  <v-btn @click="onSaveRole(item)">Save</v-btn>
                </div>
              </v-list-item-subtitle>
              <v-list-item-subtitle
                v-else
                class="mb-1 text-high-emphasis opacity-100"
              >
                {{ item.role.name }}
              </v-list-item-subtitle>

              <v-list-item-subtitle class="mb-2 text-high-emphasis opacity-60">
                {{ item.organization }}
              </v-list-item-subtitle>
            </v-list-item>
          </template>

          <v-list-item>
            <template v-slot:append>
              <v-btn
                variant="outlined"
                class="mr-2"
                :disabled="item.isOwner || item.isBeingEdited"
                @click="item.isBeingEdited = true"
                >Edit role</v-btn
              >
              <v-btn-delete
                variant="outlined"
                :disabled="item.isOwner || item.isBeingEdited"
                @click="onRemoveCollaborator(item.email)"
                >Remove collaborator</v-btn-delete
              >
            </template>
          </v-list-item>
        </v-list-group>
      </v-list>
    </div>
  </v-card-text>
</template>

<script setup lang="ts">
import { useUserStore } from '@/store/user'
import { Snackbar } from '@/utils/notifications'
import { storeToRefs } from 'pinia'
import { onMounted, ref } from 'vue'
import router from '@/router/router'
import hs, {
  PermissionAction,
  PermissionResource,
  Collaborator,
  CollaboratorRole,
  Workspace,
} from '@hydroserver/client'
import { mdiHelpCircleOutline, mdiPlus } from '@mdi/js'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import PermissionTooltip from '@/components/PermissionTooltip.vue'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})

const { user } = storeToRefs(useUserStore())
const { hasPermission } = useWorkspacePermissions()

const selection = ref([])
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
    if (email === user.value.email) await router.push({ name: 'Sites' })
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

  roles.value = rolesResponse.data.filter(
    (r: CollaboratorRole) =>
      r.workspaceId === null || r.workspaceId == props.workspace.id
  )
  setCollaboratorList(cRes.data)
})
</script>

<style scoped>
.collaborator-list-container {
  max-height: 360px; /* max-height to about 4 collaborator items */
  overflow-y: auto;
}
</style>
