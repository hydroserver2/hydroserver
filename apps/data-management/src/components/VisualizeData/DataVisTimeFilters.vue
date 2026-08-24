<template>
  <div class="time-filters">
    <div class="time-filters__controls">
      <div class="preset-filters">
        <v-chip-group
          class="preset-chips"
          :model-value="selectedDateBtnId"
          selected-class="bg-primary text-white"
          @update:model-value="handlePresetChange"
        >
          <v-chip
            v-for="option in dateOptions"
            :key="option.id"
            :value="option.id"
            class="preset-chip hs-text-sm"
            size="small"
            label
          >
            {{ option.label }}
          </v-chip>
        </v-chip-group>
      </div>
      <div class="date-fields">
        <DatePickerField
          :active="isCustomRangeActive"
          :model-value="beginDate"
          placeholder="Begin Date"
          @update:model-value="setDateRange({ begin: $event })"
        />
        <DatePickerField
          :active="isCustomRangeActive"
          :model-value="endDate"
          placeholder="End Date"
          @update:model-value="setDateRange({ end: $event })"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'

const { setDateRange, onDateBtnClick } = useDataVisStore()

const { beginDate, endDate, dateOptions, selectedDateBtnId } =
  storeToRefs(useDataVisStore())

const isCustomRangeActive = computed(() => selectedDateBtnId.value < 0)

const handlePresetChange = (value: number | null) => {
  if (typeof value === 'number') {
    onDateBtnClick(value)
  }
}
</script>

<style scoped>
.time-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--hs-space-8);
  padding: 0 var(--hs-space-8) var(--hs-space-8) 0;
}

.time-filters__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--hs-space-12);
  flex: 1 1 auto;
  min-width: 0;
}

.preset-filters {
  display: flex;
  align-items: center;
  padding-left: var(--hs-space-8);
}

.preset-chips {
  gap: var(--hs-space-4);
}

.preset-chip {
  border-radius: var(--hs-radius-sm);
  padding-inline: var(--hs-space-6);
  min-height: 24px;
}

.date-fields {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-12);
}

.date-fields :deep(.v-input) {
  min-width: 160px;
}

@media (max-width: 600px) {
  .time-filters {
    flex-direction: column;
    align-items: stretch;
    justify-content: stretch;
    width: 100%;
  }

  .time-filters__controls {
    width: 100%;
  }

  .preset-filters {
    width: 100%;
    justify-content: center;
  }

  .preset-chips :deep(.v-slide-group__content) {
    justify-content: center;
  }

  .date-fields {
    flex-direction: column;
    width: 100%;
  }

  .date-fields :deep(.v-input) {
    min-width: 0;
    width: 100%;
  }
}
</style>
