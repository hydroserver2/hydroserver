<template>
  <div
    v-if="qcDatastream"
    data-testid="edit-target-panel"
    class="edit-target-panel"
  >
    <div class="edit-target-panel__header d-flex align-center ga-1 px-3 py-1">
      <v-icon icon="mdi-pencil" color="primary" size="16" />
      <span class="text-body-small font-weight-medium">Editing</span>
    </div>

    <v-divider />

    <div class="d-flex flex-column ga-2 pa-3">
      <div style="min-width: 0">
        <div
          class="text-body-medium font-weight-medium"
          :title="qcDatastream.name"
        >
          {{ qcDatastream.name }}
        </div>
        <div class="text-body-small text-medium-emphasis">
          Session {{ sessionWindow }}
        </div>
      </div>

      <div class="d-flex align-center ga-2">
        <v-icon
          :icon="unsavedEditCount ? 'mdi-content-save-alert-outline' : 'mdi-check-circle-outline'"
          :color="unsavedEditCount ? 'warning' : 'success'"
          size="16"
        />
        <span class="text-body-small" data-testid="edit-target-unsaved">
          <template v-if="unsavedEditCount">
            {{ unsavedEditCount }} unsaved
            edit{{ unsavedEditCount === 1 ? '' : 's' }}
          </template>
          <template v-else>All edits saved</template>
        </span>
      </div>

      <div class="text-body-small text-medium-emphasis">
        Plot other datastreams around this session, then go back to edit it.
      </div>

      <v-btn
        data-testid="back-to-editor-btn"
        size="small"
        variant="flat"
        color="primary"
        prepend-icon="mdi-arrow-left"
        block
        @click="openEditor"
      >
        Back to editor
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * What the Select view says about an open edit session: the managed
 * datastream, its session window, whether anything is unsaved, and the way
 * back. Editing itself stays in the editor.
 */

import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQcSessionStore } from '@/store/qcSession'
import { useEditSession } from '@/composables/useEditSession'
import { useEditEntry } from '@/composables/useEditEntry'
import { formatDateRange } from '@/utils/time'

const { qcDatastream } = storeToRefs(useDataVisStore())
const { inProgressSession, viewedSession } = storeToRefs(useQcSessionStore())
const { unsavedEditCount } = useEditSession()
const { openEditor } = useEditEntry()

// Viewing history overrides the live session, matching the plot's band.
const sessionWindow = computed(() => {
  const session = viewedSession.value ?? inProgressSession.value
  return session
    ? formatDateRange(
        session.phenomenonTimeStart,
        session.phenomenonTimeEnd
      )
    : 'not started'
})
</script>

<style scoped>
.edit-target-panel__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 28px;
}
</style>
