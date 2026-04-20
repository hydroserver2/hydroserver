<template>
  <div class="time-filters d-flex flex-column gap-2">
    <!-- Range presets as a 3×2 grid so they fit the drawer width without
         a horizontal scrollbar. -->
    <div class="time-filters__presets">
      <v-btn
        v-for="option in dateOptions"
        :key="option.id"
        :variant="selectedDateBtnId === option.id ? 'flat' : 'outlined'"
        :color="selectedDateBtnId === option.id ? 'primary' : undefined"
        size="x-small"
        :title="(option as any).title ?? option.label"
        class="time-filters__preset-btn"
        @click="onDateBtnClick(option.id)"
      >
        {{ option.label }}
      </v-btn>
    </div>

    <DatePickerField
      :model-value="beginDate"
      placeholder="Start"
      @update:model-value="setDateRange({ begin: $event })"
    />
    <DatePickerField
      :model-value="endDate"
      placeholder="End"
      @update:model-value="setDateRange({ end: $event })"
    />
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

.time-filters__preset-btn {
  min-width: 0;
  letter-spacing: 0;
  text-transform: none;
  font-weight: 500;
  height: 28px !important;
  font-size: 0.75rem;
}
</style>
