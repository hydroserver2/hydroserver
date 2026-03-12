<template>
  <v-row align="center">
    <v-col cols="auto" class="pr-0">
      <v-card-title class="text-h6">
        Transfer workspace ownership
      </v-card-title>
    </v-col>
    <v-col class="pl-0">
      <v-icon
        :icon="mdiHelpCircleOutline"
        @click="showTransferHelp = !showTransferHelp"
        color="grey"
        small
      />
    </v-col>
  </v-row>
  <v-card-text v-if="showTransferHelp">
    This action will irreversibly de-elevate your permission level to
    collaborator and elevate the chosen user's permission level to owner once
    the chosen user has accepted the transfer request. Permissions unique to the
    owner are:
    <ul class="ml-5">
      <li>Rename a workspace</li>
      <li>Delete a workspace</li>
      <li>Make a workspace public or private</li>
    </ul>
  </v-card-text>

  <template v-if="showPendingTransferText">
    <v-card-text style="color: #2196f3">
      <p>
        An ownership transfer is pending to
        {{ workspace.pendingTransferTo?.name }}
      </p>
      <v-btn-cancel class="mt-4" @click="onCancelTransfer">
        Cancel transfer
      </v-btn-cancel>
    </v-card-text>
  </template>
  <template v-else>
    <v-card-text>
      <v-text-field
        v-model="newOwnerEmail"
        label="New owner's email"
        required
      />
      <p v-if="showTransferConfirmation" style="color: red" class="pb-4">
        WARNING: Once transfer has been accepted by the chosen user, you will no
        longer have access to this workspace.
      </p>
      <v-btn-primary
        v-if="showTransferConfirmation"
        @click="onTransferOwnership"
      >
        Confirm
      </v-btn-primary>
      <v-btn-primary v-else @click="showTransferConfirmation = true"
        >Submit</v-btn-primary
      >
    </v-card-text>
  </template>
</template>

<script setup lang="ts">
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import hs, { Workspace } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { computed, ref } from 'vue'
import { mdiHelpCircleOutline } from '@mdi/js'

const permissionsStore = useWorkspacePermissions()

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['needs-refresh'])

const showTransferHelp = ref(false)

const showPendingTransferText = computed(
  () =>
    props.workspace.pendingTransferTo?.email &&
    permissionsStore.isOwner(props.workspace)
)

const newOwnerEmail = ref('')
const showTransferConfirmation = ref(false)

async function onTransferOwnership() {
  if (!newOwnerEmail.value) return

  const res = await hs.workspaces.transferOwnership(
    props.workspace!.id,
    newOwnerEmail.value
  )

  if (res.ok) {
    emits('needs-refresh')
    Snackbar.success('Workspace transfer initiated.')
  } else {
    console.error('Error transferring workspace.', res)
    Snackbar.error(res.message)
  }

  newOwnerEmail.value = ''
  showTransferConfirmation.value = false
}

async function onCancelTransfer() {
  const res = await hs.workspaces.rejectOwnershipTransfer(props.workspace!.id)

  if (res.ok) {
    emits('needs-refresh')
    Snackbar.success('Workspace transfer cancelled.')
  } else console.error('Error cancelling workspace transfer.', res)
}
</script>
