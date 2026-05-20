<template>
  <!-- Loading: skeleton/spinner over the full plot area instead of the
       instructional empty state. -->
  <div
    v-if="isUpdating"
    class="data-vis-state fill-height d-flex flex-column align-center justify-center pa-6 text-center"
    data-testid="data-loading-indicator"
  >
    <v-progress-circular
      color="primary"
      :size="56"
      :width="4"
      indeterminate
      class="mb-4"
    />
    <div class="text-subtitle-1 font-weight-bold mb-1">
      Loading observations…
    </div>
    <div class="text-caption text-medium-emphasis">
      Fetching data for
      {{ plottedDatastreams.length }}
      datastream{{ plottedDatastreams.length === 1 ? '' : 's' }}
    </div>
  </div>

  <!-- Plot: render when data is ready. -->
  <div v-else-if="isDataAvailable" class="fill-height">
    <Plot class="fill-height" :preview="preview" />
  </div>

  <!-- No data available for selected range (something is plotted but
       the query came back empty). Keep this concise and actionable. -->
  <div
    v-else-if="plottedDatastreams.length"
    class="data-vis-state fill-height d-flex flex-column align-center justify-center pa-6 text-center"
  >
    <v-icon
      icon="mdi-calendar-remove-outline"
      size="56"
      color="warning"
      class="mb-3"
    />
    <div class="text-subtitle-1 font-weight-bold mb-1">
      No observations in this range
    </div>
    <div class="text-body-2 text-medium-emphasis" style="max-width: 360px">
      The selected datastream{{ plottedDatastreams.length === 1 ? '' : 's' }}
      returned no data for the current time window. Try a different range from
      the drawer on the left.
    </div>
  </div>

  <!-- Empty state (no datastream selected yet). A short headline above
       the three "how to" cards reminds the user what to do. -->
  <div
    v-else
    class="data-vis-state data-vis-state--empty fill-height d-flex flex-column justify-center align-center pa-6"
  >
    <div class="data-vis-state__steps">
      <div class="data-vis-state__step">
        <div class="data-vis-state__step-num">1</div>
        <v-icon
          icon="mdi-filter-variant"
          size="24"
          color="primary"
          class="data-vis-state__step-icon"
        />
        <div class="data-vis-state__step-body">
          <div class="text-subtitle-2 font-weight-bold">Find a datastream</div>
          <div class="text-caption text-medium-emphasis">
            Use the filters on the left drawer and the search bar at the top of
            the table to narrow the list.
          </div>
        </div>
      </div>

      <div class="data-vis-state__step">
        <div class="data-vis-state__step-num">2</div>
        <v-icon
          icon="mdi-radiobox-marked"
          size="24"
          color="primary"
          class="data-vis-state__step-icon"
        />
        <div class="data-vis-state__step-body">
          <div class="text-subtitle-2 font-weight-bold">Pick the QC target</div>
          <div class="text-caption text-medium-emphasis">
            Click the <b>Plot</b> checkbox on a row. The first one becomes the
            quality-control target, shown in primary blue.
          </div>
        </div>
      </div>

      <div class="data-vis-state__step">
        <div class="data-vis-state__step-num">3</div>
        <v-icon
          icon="mdi-calendar-range"
          size="24"
          color="primary"
          class="data-vis-state__step-icon"
        />
        <div class="data-vis-state__step-body">
          <div class="text-subtitle-2 font-weight-bold">Set the time range</div>
          <div class="text-caption text-medium-emphasis">
            Adjust <b>Time filters</b> from the left drawer to cover the period
            you want to inspect.
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

defineProps<{
  preview?: boolean
}>()

const { plotlyOptions } = storeToRefs(usePlotlyStore())

const { loadingStates, plottedDatastreams } = storeToRefs(useDataVisStore())

const isUpdating = computed(() =>
  Array.from(loadingStates.value.values()).some((isLoading) => isLoading)
)

const isDataAvailable = computed(() => {
  return plotlyOptions.value.traces?.length && plottedDatastreams.value?.length
})
</script>

<style scoped>
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: rgb(var(--v-theme-primary));
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 999px;
  line-height: 1;
}

@media (max-width: 720px) {
  .data-vis-state__steps {
    grid-template-columns: 1fr;
  }
}
</style>
