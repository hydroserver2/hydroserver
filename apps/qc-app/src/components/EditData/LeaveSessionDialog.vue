<template>
  <v-dialog :model-value="!!leavePrompt" max-width="520" persistent>
    <v-card v-if="leavePrompt" rounded="lg" data-testid="leave-session-dialog">
      <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
        <v-avatar :color="copy.color" variant="tonal" size="40">
          <v-icon :icon="copy.icon" size="22" />
        </v-avatar>
        <div class="d-flex flex-column">
          <div class="text-title-large font-weight-bold">{{ copy.title }}</div>
          <div class="text-body-small text-medium-emphasis">
            {{ copy.subtitle }}
          </div>
        </div>
      </div>

      <v-card-text class="text-body-medium pt-2 pb-4 px-6">
        {{ copy.body }}
      </v-card-text>

      <v-divider />

      <v-card-actions class="d-flex align-center ga-2 px-4 py-3">
        <v-btn
          variant="text"
          data-testid="leave-cancel-btn"
          :disabled="!!leaveWork"
          @click="cancelLeave"
        >
          Cancel
        </v-btn>
        <v-spacer />

        <template v-if="leavePrompt.kind === 'unsaved'">
          <v-btn
            color="error"
            variant="tonal"
            prepend-icon="mdi-backup-restore"
            data-testid="leave-discard-edits-btn"
            :disabled="!!leaveWork"
            :loading="leaveWork === 'discard-edits'"
            @click="discardEditsAndLeave"
          >
            Discard changes and close
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-content-save-outline"
            data-testid="leave-save-btn"
            :disabled="!!leaveWork || !leavePrompt.canSave"
            :loading="leaveWork === 'save'"
            @click="saveAndLeave"
          >
            Save and close
          </v-btn>
        </template>

        <template v-else-if="leavePrompt.kind === 'empty'">
          <v-btn
            color="error"
            variant="tonal"
            prepend-icon="mdi-delete-outline"
            data-testid="leave-discard-session-btn"
            :disabled="!!leaveWork"
            :loading="leaveWork === 'discard-session'"
            @click="discardSessionAndLeave"
          >
            Discard session
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-pause-circle-outline"
            data-testid="leave-keep-btn"
            :disabled="!!leaveWork"
            @click="keepSession"
          >
            Keep session
          </v-btn>
        </template>

        <template v-else>
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-close"
            data-testid="leave-close-btn"
            :disabled="!!leaveWork"
            @click="closeSession"
          >
            Close
          </v-btn>
        </template>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * The one dialog for leaving an edit session. Every exit routes through
 * `useLeaveSession`, which decides which of the three cases applies and
 * carries out the answer; this component only shows it.
 */

import { computed } from 'vue'
import { useLeaveSession } from '@/composables/useLeaveSession'

const {
  leavePrompt,
  leaveWork,
  cancelLeave,
  keepSession,
  closeSession,
  saveAndLeave,
  discardEditsAndLeave,
  discardSessionAndLeave,
} = useLeaveSession()

const RESUME = "Resume it any time from the datastream's Edit button."

const copy = computed(() => {
  const prompt = leavePrompt.value
  const on = prompt?.datastreamName ? ` on ${prompt.datastreamName}` : ''
  if (prompt?.kind === 'unsaved') {
    const count = prompt.unsavedCount
    return {
      color: 'warning',
      icon: 'mdi-content-save-alert-outline',
      title: `Unsaved edits${on}`,
      subtitle: count
        ? `${count} edit${count === 1 ? '' : 's'} not yet saved to the session`
        : 'You have changes that are not in the session',
      body: prompt.canSave
        ? `Save them to the session, or discard them for good. Either way the session stays in progress. ${RESUME}`
        : `No session is open, so these edits cannot be saved. Discarding them closes the editor.`,
    }
  }
  if (prompt?.kind === 'empty') {
    return {
      color: 'error',
      icon: 'mdi-help-circle-outline',
      title: `Your session${on} has no edits`,
      subtitle: 'Nothing saved, nothing unsaved',
      body: `Keep it and it stays in progress. ${RESUME} Discard it and it is deleted from the server.`,
    }
  }
  return {
    color: 'primary',
    icon: 'mdi-pause-circle-outline',
    title: `Close your session${on}?`,
    subtitle: 'Every edit is saved to the session',
    body: `Your work stays where it is. The session stays in progress. ${RESUME}`,
  }
})
</script>
