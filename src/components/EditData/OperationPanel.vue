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
         the panel instead of a dialog-in-a-sidebar. Sections are
         visually separated with their own padding + bottom border. -->
    <div
      v-else
      class="operation-panel__body flex-grow-1 overflow-y-auto"
      :class="{ 'operation-panel__body--multi': filterRangeToggleVisible }"
    >
      <section
        v-if="filterRangeToggleVisible"
        class="operation-panel__section"
      >
        <div class="operation-panel__section-head">
          <h3 class="operation-panel__section-title">Date range</h3>
          <v-tooltip
            v-if="filterRangeActive"
            location="start"
            text="Disable date range"
          >
            <template #activator="{ props: tp }">
              <v-btn
                v-bind="tp"
                size="x-small"
                variant="text"
                density="comfortable"
                icon="mdi-close"
                aria-label="Disable date range"
                @click="filterRangeActive = false"
              />
            </template>
          </v-tooltip>
        </div>
        <FilterRangePanel v-if="filterRangeActive" />
        <div v-else class="operation-panel__section-empty px-3 pb-3">
          <p class="text-caption text-medium-emphasis mb-2">
            Run this operation against the full datastream, or restrict it
            to a datetime window.
          </p>
          <v-btn
            size="small"
            variant="outlined"
            color="primary"
            prepend-icon="mdi-arrow-expand-horizontal"
            @click="filterRangeActive = true"
          >
            Enable date range
          </v-btn>
        </div>
      </section>
      <section class="operation-panel__section operation-panel__section--op">
        <component :is="op.component" @close="close" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '@/store/userInterface'
import { useDataVisStore } from '@/store/dataVisualization'
import { operationsById } from './operations'
import FilterRangePanel from '@/components/FilterPoints/FilterRangePanel.vue'

const { selectedOperation, filterRangeActive } = storeToRefs(useUIStore())
const { selectedData } = storeToRefs(useDataVisStore())

const op = computed(() =>
  selectedOperation.value ? operationsById[selectedOperation.value] : null
)

// `datetimeRange` brings its own picker — would duplicate the shared range UI.
const OPS_WITH_OWN_RANGE = new Set(['datetimeRange'])

const filterRangeToggleVisible = computed(
  () =>
    op.value?.group === 'filter' && !OPS_WITH_OWN_RANGE.has(op.value.id)
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
  padding: 8px;
}

.operation-panel__section + .operation-panel__section {
  margin-top: 12px;
}

.operation-panel__section {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.operation-panel__section-head {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 4px 0 0;
}

.operation-panel__section-title {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.7);
  padding: 8px 12px 4px;
  margin: 0;
  flex-grow: 1;
}

.operation-panel__section-empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

/* Normalize the embedded v-card so it doesn't look like a dialog:
   no elevation, no rounded corners, no min-width. The individual
   operation components all wrap their contents in a v-card, and we
   want that card to be visually flush with the surrounding section. */
.operation-panel__section :deep(> .v-card),
.operation-panel__section :deep(> .v-form > .v-card) {
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
.operation-panel__section--op :deep(> .v-card > .v-card-title:first-child),
.operation-panel__section--op
  :deep(> .v-form > .v-card > .v-card-title:first-child) {
  display: none !important;
}

/* Hide the leading divider that separated the now-hidden title from
   the body, if present. */
.operation-panel__section--op
  :deep(> .v-card > .v-card-title:first-child + .v-divider),
.operation-panel__section--op
  :deep(> .v-form > .v-card > .v-card-title:first-child + .v-divider) {
  display: none !important;
}
</style>
