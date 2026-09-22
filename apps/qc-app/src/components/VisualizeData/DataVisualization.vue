<template>
  <!-- Stays mounted while loading so a refresh keeps the plot and its zoom. -->
  <Plot v-if="isUpdating || isDataAvailable" class="fill-height">
    <template #body-overlay>
      <div
        v-if="isUpdating"
        class="data-vis-loading position-absolute d-flex flex-column align-center justify-center pa-6 text-center"
        data-testid="data-loading-indicator"
      >
        <v-progress-circular
          color="primary"
          :size="56"
          :width="4"
          indeterminate
          class="mb-4"
        />
        <div class="text-title-medium font-weight-bold mb-1">
          Loading observations…
        </div>
        <div class="text-body-small text-medium-emphasis">
          Fetching data for
          {{ loadingCount }}
          datastream{{ loadingCount === 1 ? '' : 's' }}
        </div>
      </div>
    </template>
  </Plot>

  <!-- Nothing drawn yet: keep the range control where the plot toolbar puts
       it, so a window can be set before any data is pulled. -->
  <div v-else class="fill-height d-flex flex-column">
    <div class="data-vis-toolbar d-flex align-center px-3 py-1">
      <v-spacer />
      <TimeRangeMenu />
    </div>
    <v-divider />

    <div
      v-if="seriesDatastreams.length"
      class="data-vis-state flex-grow-1 d-flex flex-column align-center justify-center pa-6 text-center"
    >
      <v-icon
        icon="mdi-calendar-remove-outline"
        size="56"
        color="warning"
        class="mb-3"
      />
      <div class="text-title-medium font-weight-bold mb-1">
        No observations in this range
      </div>
      <div class="text-body-medium text-medium-emphasis" style="max-width: 360px">
        The selected datastream{{ seriesDatastreams.length === 1 ? '' : 's' }}
        returned no data for the current time window. Try a different range
        from the <b>Time range</b> menu above.
      </div>
    </div>

    <div
      v-else
      class="data-vis-state flex-grow-1 d-flex flex-column justify-center align-center pa-6"
    >
      <div class="data-vis-state__steps">
        <div class="data-vis-state__step">
          <div class="data-vis-state__step-num d-inline-flex align-center justify-center rounded-pill text-white">1</div>
          <v-icon
            icon="mdi-filter-variant"
            size="24"
            color="primary"
            class="data-vis-state__step-icon"
          />
          <div class="data-vis-state__step-body">
            <div class="text-title-small font-weight-bold">Find a datastream</div>
            <div class="text-body-small text-medium-emphasis">
              Use the filters on the left drawer and the search bar at the top of
              the table to narrow the list.
            </div>
          </div>
        </div>

        <div class="data-vis-state__step">
          <div class="data-vis-state__step-num d-inline-flex align-center justify-center rounded-pill text-white">2</div>
          <v-icon
            icon="mdi-checkbox-marked-outline"
            size="24"
            color="primary"
            class="data-vis-state__step-icon"
          />
          <div class="data-vis-state__step-body">
            <div class="text-title-small font-weight-bold">Plot datastreams</div>
            <div class="text-body-small text-medium-emphasis">
              Click the <b>Plot</b> checkbox on rows to preview them together.
            </div>
          </div>
        </div>

        <div class="data-vis-state__step">
          <div class="data-vis-state__step-num d-inline-flex align-center justify-center rounded-pill text-white">3</div>
          <v-icon
            icon="mdi-calendar-range"
            size="24"
            color="primary"
            class="data-vis-state__step-icon"
          />
          <div class="data-vis-state__step-body">
            <div class="text-title-small font-weight-bold">Set the time range</div>
            <div class="text-body-small text-medium-emphasis">
              Pick the period to inspect from the <b>Time range</b> menu
              above, before or after plotting.
            </div>
          </div>
        </div>

        <div class="data-vis-state__step">
          <div class="data-vis-state__step-num d-inline-flex align-center justify-center rounded-pill text-white">4</div>
          <v-icon
            icon="mdi-pencil"
            size="24"
            color="primary"
            class="data-vis-state__step-icon"
          />
          <div class="data-vis-state__step-body">
            <div class="text-title-small font-weight-bold">Edit one</div>
            <div class="text-body-small text-medium-emphasis">
              Click the <b>pencil</b> on a row to pick or create its QC datastream
              and start a session.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlotlyStore } from '@/store/plotly'
import Plot from '@/components/VisualizeData/Plot.vue'
import TimeRangeMenu from '@/components/VisualizeData/TimeRangeMenu.vue'

const { plotlyOptions } = storeToRefs(usePlotlyStore())

const { loadingStates, seriesDatastreams } = storeToRefs(useDataVisStore())

// Only what is fetching: the edit target never is.
const loadingCount = computed(
  () => Array.from(loadingStates.value.values()).filter(Boolean).length
)
const isUpdating = computed(() => loadingCount.value > 0)

// The editor draws its target and source even with nothing else plotted.
const isDataAvailable = computed(() => {
  return plotlyOptions.value.traces?.length && seriesDatastreams.value?.length
})
</script>

<style scoped>
.data-vis-loading {
  inset: 0;
  z-index: 1;
  background-color: rgba(var(--v-theme-surface), 0.75);
}

.data-vis-toolbar {
  background-color: rgba(var(--v-theme-primary), 0.02);
  min-height: 40px;
}

.data-vis-state {
  background-color: rgba(var(--v-theme-primary), 0.02);
}

.data-vis-state__steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.data-vis-state__step {
  position: relative;
  display: grid;
  grid-template-columns: 32px 1fr;
  column-gap: 10px;
  align-items: start;
  padding: 12px 14px;
  background-color: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-primary), 0.15);
  border-radius: 8px;
}

.data-vis-state__step-icon {
  grid-row: 1;
  grid-column: 1;
  align-self: start;
  margin-top: 2px;
}

.data-vis-state__step-body {
  grid-row: 1;
  grid-column: 2;
  min-width: 0;
  line-height: 1.35;
}

.data-vis-state__step-num {
  position: absolute;
  top: -9px;
  left: 12px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  background-color: rgb(var(--v-theme-primary));
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1;
}

@media (max-width: 720px) {
  .data-vis-state__steps {
    grid-template-columns: 1fr;
  }
}
</style>
