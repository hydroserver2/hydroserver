<template>
  <div
    v-if="op"
    class="operation-panel d-flex flex-column bg-surface"
    :data-testid="`operation-panel-${op.id}`"
  >
    <!-- Header mirrors the edit-history header so the two panels read as
         siblings in the sidebar. Close button dismisses the panel; the
         operation itself decides when to auto-close on a successful
         action via its own `close` emit. -->
    <div
      class="operation-panel__header px-3 py-2 d-flex align-center gap-2"
    >
      <v-avatar
        :color="op.requiresSelection ? 'warning' : 'primary'"
        variant="flat"
        size="24"
      >
        <v-icon :icon="op.icon" color="white" size="14" />
      </v-avatar>
      <div class="d-flex flex-column flex-grow-1" style="min-width: 0">
        <span class="text-body-2 font-weight-bold text-truncate">
          {{ op.title }}
        </span>
        <span class="text-caption text-medium-emphasis text-truncate">
          {{ op.description }}
        </span>
      </div>
      <v-tooltip location="start" text="Close">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-close"
            @click="close"
          />
        </template>
      </v-tooltip>
    </div>

    <v-divider />

    <!-- Selection-required guard. Shown inline rather than replacing the
         body so the user keeps the panel open while they go back to the
         plot and brush a range. -->
    <div
      v-if="op.requiresSelection && !selectedData?.length"
      class="operation-panel__empty px-3 py-4 d-flex flex-column align-center text-center"
    >
      <v-icon
        icon="mdi-selection-ellipse-arrow-inside"
        size="28"
        color="warning"
        class="mb-2"
      />
      <div class="text-caption text-medium-emphasis">
        Select points on the plot to continue.
      </div>
    </div>

    <!-- Dynamic body. Each operation renders its own v-card; scoped
         overrides below flatten the nested card so it looks native to
         the panel instead of a dialog-in-a-sidebar. -->
    <div v-else class="operation-panel__body flex-grow-1 overflow-y-auto">
      <component :is="op.component" @close="close" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '@/store/userInterface'
import { useDataVisStore } from '@/store/dataVisualization'
import { operationsById } from './operations'

const { selectedOperation } = storeToRefs(useUIStore())
const { selectedData } = storeToRefs(useDataVisStore())

const op = computed(() =>
  selectedOperation.value ? operationsById[selectedOperation.value] : null
)

function close() {
  selectedOperation.value = null
}
</script>

<style scoped>
.operation-panel {
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
}

.operation-panel__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 40px;
}

.operation-panel__body {
  min-height: 0;
  padding-inline: 8px;
}

/* Normalize the embedded v-card so it doesn't look like a dialog:
   no elevation, no rounded corners, no min-width. The individual
   operation components all wrap their contents in a v-card, and we
   want that card to be visually flush with the surrounding panel. */
.operation-panel__body :deep(> .v-card),
.operation-panel__body :deep(> .v-form > .v-card) {
  box-shadow: none !important;
  border-radius: 0 !important;
  min-width: 0 !important;
  width: 100% !important;
  background: transparent !important;
}

.operation-panel__body :deep(.v-card-title) {
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  padding: 8px 12px !important;
}

.operation-panel__body :deep(.v-card-subtitle) {
  padding: 0 12px 8px !important;
  font-size: 0.75rem !important;
}

.operation-panel__body :deep(.v-card-text) {
  padding: 12px !important;
  height: auto !important;
  resize: none !important;
}

.operation-panel__body :deep(.v-card-actions) {
  padding: 8px 12px !important;
  min-height: 0 !important;
}

/* The operation components redundantly repeat their titles in
   v-card-title. The panel header already names the operation, so
   hide the internal one. */
.operation-panel__body :deep(> .v-card > .v-card-title:first-child),
.operation-panel__body :deep(> .v-form > .v-card > .v-card-title:first-child) {
  display: none !important;
}

/* Hide the leading divider that separated the now-hidden title from
   the body, if present. */
.operation-panel__body
  :deep(> .v-card > .v-card-title:first-child + .v-divider),
.operation-panel__body
  :deep(> .v-form > .v-card > .v-card-title:first-child + .v-divider) {
  display: none !important;
}
</style>
