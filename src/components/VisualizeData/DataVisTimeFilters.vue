<template>
  <div class="time-filters d-flex flex-column gap-2">
    <!-- Section header -->
    <div>
      <div class="text-caption text-medium-emphasis font-weight-medium text-uppercase mb-1">
        Loaded time window
      </div>
      <div class="text-caption text-medium-emphasis" style="line-height: 1.4">
        Changing the range re-fetches observations from the server.
      </div>
    </div>

    <!-- Date inputs — the source of truth -->
    <div class="d-flex flex-column gap-1">
      <div>
        <div class="text-caption text-medium-emphasis mb-1">From</div>
        <DatePickerField
          :model-value="beginDate"
          placeholder="Start date"
          @update:model-value="setDateRange({ begin: $event })"
        />
      </div>
      <div>
        <div class="text-caption text-medium-emphasis mb-1">To</div>
        <DatePickerField
          :model-value="endDate"
          placeholder="End date"
          @update:model-value="setDateRange({ end: $event })"
        />
      </div>
    </div>

    <!-- Preset quick-selects -->
    <div>
      <div class="time-filters__presets">
        <v-chip
          v-for="option in dateOptions"
          :key="option.id"
          :color="selectedDateBtnId === option.id ? 'primary' : undefined"
          :variant="selectedDateBtnId === option.id ? 'tonal' : 'outlined'"
          size="small"
          :title="(option as any).title ?? option.label"
          class="time-filters__preset-chip"
          @click="onDateBtnClick(option.id)"
        >
          {{ option.label }}
        </v-chip>
        <v-chip
          v-if="selectedDateBtnId === -1"
          color="secondary"
          variant="tonal"
          size="small"
          class="time-filters__preset-chip"
          title="Date range set manually"
        >
          Custom
        </v-chip>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'

const { setDateRange, onDateBtnClick } = useDataVisStore()
const { dateOptions, beginDate, endDate, selectedDateBtnId } =
  storeToRefs(useDataVisStore())
</script>

<style scoped>
.time-filters {
  width: 100%;
}

.time-filters__presets {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
}

.time-filters__preset-chip {
  min-width: 0;
  justify-content: center;
  font-size: 0.75rem !important;
  height: 26px !important;
}
</style>
