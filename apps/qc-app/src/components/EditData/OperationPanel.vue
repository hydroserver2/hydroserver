<template>
  <div
    v-if="op"
    class="operation-panel d-flex flex-column overflow-hidden bg-surface"
    :data-testid="`operation-panel-${op.id}`"
  >
    <div class="operation-panel__header px-3 py-2 d-flex align-center ga-2">
      <v-avatar
        :color="op.requiresSelection ? 'warning' : 'primary'"
        variant="flat"
        size="24"
      >
        <v-icon :icon="op.icon" color="white" size="14" />
      </v-avatar>
      <div class="d-flex flex-column flex-grow-1" style="min-width: 0">
        <span class="text-body-medium font-weight-bold text-truncate">
          {{ op.title }}
        </span>
        <span class="text-body-small text-medium-emphasis text-truncate">
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

    <div
      v-if="op.requiresSelection && !selectedData?.length"
      class="px-3 py-4 d-flex flex-column align-center text-center"
    >
      <v-icon
        icon="mdi-selection-ellipse-arrow-inside"
        size="28"
        color="warning"
        class="mb-2"
      />
      <div class="text-body-small text-medium-emphasis">
        Select points on the plot to continue.
      </div>
    </div>

    <div
      v-else
      class="operation-panel__body flex-grow-1 overflow-y-auto pa-2"
    >
      <section
        v-if="filterRangeToggleVisible"
        class="operation-panel__section rounded border bg-surface overflow-hidden"
      >
        <div class="operation-panel__section-head d-flex align-center ga-1">
          <h3 class="operation-panel__section-title flex-grow-1">Date range mask</h3>
          <v-tooltip
            v-if="filterRangeActive"
            location="start"
            text="Disable date range mask"
          >
            <template #activator="{ props: tp }">
              <v-btn
                v-bind="tp"
                data-testid="filter-range-disable-btn"
                size="x-small"
                variant="text"
                density="comfortable"
                icon="mdi-close"
                aria-label="Disable date range mask"
                @click="filterRangeActive = false"
              />
            </template>
          </v-tooltip>
        </div>
        <FilterRangePanel v-if="filterRangeActive" />
        <div v-else class="d-flex flex-column align-start ga-1 px-3 pb-3">
          <p class="text-body-small text-medium-emphasis mb-2">
            Run this operation against the full datastream, or apply a
            date range mask to restrict it to a datetime window.
          </p>
          <v-btn
            data-testid="filter-range-enable-btn"
            size="small"
            variant="outlined"
            color="primary"
            prepend-icon="mdi-arrow-expand-horizontal"
            @click="filterRangeActive = true"
          >
            Enable date range mask
          </v-btn>
        </div>
      </section>
      <section class="operation-panel__section operation-panel__section--op rounded border bg-surface overflow-hidden">
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

// datetimeRange has its own picker that would duplicate the shared range UI.
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
}

.operation-panel__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 40px;
}

.operation-panel__body {
  min-height: 0;
}

.operation-panel__section + .operation-panel__section {
  margin-top: 12px;
}

.operation-panel__section-head {
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
}

/* Flatten the embedded v-card so the operation reads as part of the
   section instead of a dialog-in-a-sidebar. */
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

/* The panel header already names the operation: hide the embedded
   v-card-title (and the divider that followed it) to avoid duplication. */
.operation-panel__section--op :deep(> .v-card > .v-card-title:first-child),
.operation-panel__section--op
  :deep(> .v-form > .v-card > .v-card-title:first-child) {
  display: none !important;
}

.operation-panel__section--op
  :deep(> .v-card > .v-card-title:first-child + .v-divider),
.operation-panel__section--op
  :deep(> .v-form > .v-card > .v-card-title:first-child + .v-divider) {
  display: none !important;
}
</style>
