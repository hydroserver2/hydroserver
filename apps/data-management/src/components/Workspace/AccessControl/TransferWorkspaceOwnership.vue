<template>
  <h6 class="text-h6 ownership-title">Transfer workspace ownership</h6>

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
        <v-btn-cancel
          class="mt-4"
          :loading="isCancelling"
          :disabled="isCancelling"
          @click="onCancelTransfer"
        >
          Cancel transfer
        </v-btn-cancel>
      </template>

      <template v-else>
        <p class="ownership-copy">
          Transfer is irreversible once accepted: the new owner gains the
          ownership rights for this workspace, and its permissions will then
          determine who can
          <strong>rename</strong>, <strong>delete</strong>, and
          <strong>change the privacy</strong> of this workspace. Unless the new
          owner adds you as a collaborator, you may lose access to it entirely.
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
            :loading="isTransferring"
            :disabled="!emailFormValid || isTransferring"
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
          Once accepted, you will no longer own this workspace and may lose
          access to it entirely.
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
const isTransferring = ref(false)
const isCancelling = ref(false)

async function onTransferOwnership() {
  if (!newOwnerEmail.value || !emailFormValid.value || isTransferring.value)
    return

  isTransferring.value = true
  try {
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
      Snackbar.error(res.message || 'Unable to start the workspace transfer.')
      showTransferConfirmation.value = false
    }
  } catch (error) {
    console.error('Error transferring workspace.', error)
    Snackbar.error('Unable to start the workspace transfer.')
  } finally {
    isTransferring.value = false
  }
}

async function onCancelTransfer() {
  if (isCancelling.value) return
  isCancelling.value = true
  try {
    const res = await hs.workspaces.rejectOwnershipTransfer(props.workspace!.id)

    if (res.ok) {
      emits('needs-refresh')
      Snackbar.success('Workspace transfer cancelled.')
    } else {
      console.error('Error cancelling workspace transfer.', res)
      Snackbar.error(res.message || 'Unable to cancel the workspace transfer.')
    }
  } catch (error) {
    console.error('Error cancelling workspace transfer.', error)
    Snackbar.error('Unable to cancel the workspace transfer.')
  } finally {
    isCancelling.value = false
  }
}
</script>

<style scoped>
.ownership-title {
  margin-bottom: 4px;
}
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

@media (max-width: 600px) {
  .ownership-card {
    padding: 16px;
  }
  .ownership-form {
    grid-template-columns: 1fr;
  }
}
</style>
