<template>
  <div
    v-if="
      hasPermission(
        PermissionResource.Workspace,
        PermissionAction.Edit,
        workspace
      )
    "
  >
    <v-row align="center">
      <v-col cols="auto" class="pr-0">
        <v-card-title class="text-h6"> Privacy </v-card-title>
      </v-col>
      <v-col cols="auto" class="pl-0">
        <v-icon
          :icon="mdiHelpCircleOutline"
          @click="showPrivacyHelp = !showPrivacyHelp"
          color="grey"
          small
        />
      </v-col>
    </v-row>

    <v-card-text cols="12" md="6" v-if="showPrivacyHelp" class="py-0">
      Setting your workspace to private will make it and all related sites,
      datastreams, and workspace metadata visible to only you and other
      collaborators of your workspace. Setting your workspace to public will
      make it visible to all users and guests of the system. By default, all
      related sites and datastreams will also be public, but can be made private
      from on the Site Details page.
    </v-card-text>

    <v-card-text>
      <v-checkbox
        v-model="isPrivate"
        label="Make this workspace private"
        @change="togglePrivacy"
        hide-details
      />
    </v-card-text>
  </div>

  <div v-else>
    <v-row cols="12" md="6" class="py-0">
      <v-col> You don't have permissions to edit a workspace. </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import hs, {
  Workspace,
  PermissionAction,
  PermissionResource,
} from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { ref } from 'vue'
import { mdiHelpCircleOutline } from '@mdi/js'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['privacy-updated'])

const { hasPermission } = useWorkspacePermissions()

const isPrivate = ref(props.workspace.isPrivate)
const openHydroSharePrivacy = ref(false)
const isUpdating = ref(false)
const showPrivacyHelp = ref(false)

async function togglePrivacy() {
  isUpdating.value = true

  const res = await hs.workspaces.update({
    id: props.workspace.id,
    isPrivate: isPrivate.value,
  } as Workspace)

  if (res.ok) emits('privacy-updated', isPrivate.value)
  else {
    isPrivate.value = !isPrivate.value
    Snackbar.error(res.message)
    console.error('Error updating thing privacy', res)
  }

  isUpdating.value = false
  openHydroSharePrivacy.value = false
}
</script>
