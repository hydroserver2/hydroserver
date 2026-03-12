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
            class="preset-chip"
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
    <div class="time-filters__actions">
      <v-btn
        color="primary"
        :append-icon="mdiContentCopy"
        class="copy-state-btn"
        @click="copyStateToClipboard"
      >
        Copy State as URL
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { mdiContentCopy } from '@mdi/js'

const { setDateRange, onDateBtnClick } = useDataVisStore()
const emit = defineEmits(['copy-state'])

const { beginDate, endDate, dateOptions, selectedDateBtnId } = storeToRefs(
  useDataVisStore()
)

const isCustomRangeActive = computed(() => selectedDateBtnId.value < 0)

const handlePresetChange = (value: number | null) => {
  if (typeof value === 'number') {
    onDateBtnClick(value)
  }
}

const copyStateToClipboard = () => {
  emit('copy-state')
}
</script>

<style scoped>
.time-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 8px 8px 0;
}

.time-filters__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  flex: 1 1 auto;
  min-width: 0;
}

.time-filters__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 0 0 auto;
  gap: 8px;
}

.preset-filters {
  display: flex;
  align-items: center;
  padding-left: 8px;
}

.preset-chips {
  gap: 4px;
}

.preset-chip {
  border-radius: 4px;
  padding-inline: 6px;
  min-height: 24px;
  font-size: 0.75rem;
}

.date-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
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

  .time-filters__actions {
    justify-content: center;
    width: 100%;
  }

  .copy-state-btn {
    width: 100%;
    max-width: 260px;
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
