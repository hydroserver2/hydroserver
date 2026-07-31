<template>
  <v-row align="center">
    <v-col cols="auto" class="pr-0">
      <v-card-title class="text-h6">
        Transfer workspace ownership
      </v-card-title>
    </v-col>
  </v-row>

  <v-card-text>
    <div class="ownership-card hs-table-card">
      <template v-if="showPendingTransferText">
        <div class="ownership-pending">
          <v-icon :icon="mdiTransitTransfer" size="18" color="primary" />
          <span>
            An ownership transfer is pending to
            <strong>{{ workspace.pendingTransferTo?.name }}</strong>
          </span>
        </div>
        <v-btn-cancel class="mt-4" @click="onCancelTransfer">
          Cancel transfer
        </v-btn-cancel>
      </template>

      <template v-else>
        <p class="ownership-copy">
          Transfer is irreversible once accepted: your role drops to
          collaborator and the new owner gains the owner-only powers to
          <strong>rename</strong>, <strong>delete</strong>, and
          <strong>change the privacy</strong> of this workspace.
        </p>

        <v-form v-model="emailFormValid" class="ownership-form">
          <v-text-field
            v-model="newOwnerEmail"
            label="New owner's email"
            placeholder="collaborator@organization.org"
            density="comfortable"
            :rules="rules.email"
            hide-details="auto"
          />
          <v-btn-primary
            v-if="showTransferConfirmation"
            :disabled="!emailFormValid"
            @click="onTransferOwnership"
          >
            Confirm transfer
          </v-btn-primary>
          <v-btn
            v-else
            variant="outlined"
            :prepend-icon="mdiTransitTransfer"
            :disabled="!emailFormValid"
            @click="showTransferConfirmation = true"
          >
            Begin transfer
          </v-btn>
        </v-form>

        <v-alert
          v-if="showTransferConfirmation"
          type="warning"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          Once accepted, you'll lose access to administer this workspace.
        </v-alert>
      </template>
    </div>
  </v-card-text>
</template>

<script setup lang="ts">
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import hs, { Workspace } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { rules } from '@/utils/rules'
import { computed, ref } from 'vue'
import { mdiTransitTransfer } from '@mdi/js'

const permissionsStore = useWorkspacePermissions()

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['needs-refresh'])

const showPendingTransferText = computed(
  () =>
    props.workspace.pendingTransferTo?.email &&
    permissionsStore.isOwner(props.workspace)
)

const newOwnerEmail = ref('')
const emailFormValid = ref(false)
const showTransferConfirmation = ref(false)

async function onTransferOwnership() {
  if (!newOwnerEmail.value || !emailFormValid.value) return

  const res = await hs.workspaces.transferOwnership(
    props.workspace!.id,
    newOwnerEmail.value
  )

  if (res.ok) {
    emits('needs-refresh')
    Snackbar.success('Workspace transfer initiated.')
    newOwnerEmail.value = ''
    showTransferConfirmation.value = false
  } else {
    // Keep what they typed so they can fix it rather than starting over -
    // most commonly this means the email doesn't match an existing account.
    console.error('Error transferring workspace.', res)
    Snackbar.error(res.message)
    showTransferConfirmation.value = false
  }
}

async function onCancelTransfer() {
  const res = await hs.workspaces.rejectOwnershipTransfer(props.workspace!.id)

  if (res.ok) {
    emits('needs-refresh')
    Snackbar.success('Workspace transfer cancelled.')
  } else console.error('Error cancelling workspace transfer.', res)
}
</script>

<style scoped>
.ownership-card {
  padding: 18px 20px;
}
.ownership-copy {
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.6;
  margin-bottom: 16px;
  max-width: 560px;
}
.ownership-copy strong {
  color: #374151;
}
.ownership-form {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: center;
  max-width: 560px;
}
.ownership-pending {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13.5px;
  color: #1c1b1f;
}
</style>
