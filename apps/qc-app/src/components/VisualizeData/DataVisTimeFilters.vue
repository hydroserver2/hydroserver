<template>
  <div class="d-flex flex-column ga-2 w-100">
    <div>
      <div class="text-body-small text-medium-emphasis">
        <template v-if="description">{{ description }}</template>
        <template v-else>
          <strong>Loaded time window.</strong>
          Presets count back from the plotted data's last observation.
        </template>
      </div>
    </div>

    <div class="d-flex flex-column ga-1">
      <div>
        <div class="text-body-small text-medium-emphasis mb-1">From</div>
        <DatePickerField
          data-testid="date-range-from"
          :model-value="beginDate"
          placeholder="Start date"
          @update:model-value="setDateRange({ begin: $event })"
        />
      </div>
      <div>
        <div class="text-body-small text-medium-emphasis mb-1">To</div>
        <DatePickerField
          data-testid="date-range-to"
          :model-value="endDate"
          placeholder="End date"
          @update:model-value="setDateRange({ end: $event })"
        />
      </div>
    </div>

    <div class="time-filters__presets">
      <v-chip
        v-for="option in presets"
        :key="option.id"
        :data-testid="`date-preset-${option.label}`"
        :color="shownId === option.id ? 'primary' : undefined"
        :variant="shownId === option.id ? 'tonal' : 'outlined'"
        size="small"
        :title="option.title"
        class="time-filters__preset-chip justify-center"
        @click="onDateBtnClick(option.id)"
      >
        {{ option.label }}
      </v-chip>
      <v-chip
        v-if="activePresetId === CUSTOM_PRESET_ID"
        data-testid="date-preset-custom"
        color="secondary"
        variant="tonal"
        size="small"
        class="time-filters__preset-chip justify-center"
        title="Date range set manually"
      >
        Custom
      </v-chip>
    </div>
  </div>
</template>

<script setup lang="ts">
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'
import { useDataVisStore } from '@/store/dataVisualization'
import {
  CUSTOM_PRESET_ID,
  TIME_RANGE_PRESETS,
  shownPresetId,
  type TimeRangePreset,
} from '@/utils/timeRangePresets'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    description?: string
    /** Preset chips to offer; the editor leaves out YTD. */
    presets?: readonly TimeRangePreset[]
  }>(),
  { description: undefined, presets: () => TIME_RANGE_PRESETS }
)

const { setDateRange, onDateBtnClick } = useDataVisStore()
const { beginDate, endDate, activePresetId } = storeToRefs(useDataVisStore())

const shownId = computed(() =>
  shownPresetId(activePresetId.value, props.presets)
)
</script>

<style scoped>
.time-filters__presets {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
}

.time-filters__preset-chip {
  min-width: 0;
  font-size: 0.75rem !important;
  height: 26px !important;
}
</style>
