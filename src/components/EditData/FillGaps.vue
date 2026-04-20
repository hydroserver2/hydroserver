<template>
  <v-card>
    <v-card-title>Fill gaps</v-card-title>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">Date range</div>
      <DatePickerField
        placeholder="From"
        :modelValue="fromDate"
        @update:modelValue="onFromDateChange"
        class="mb-2"
      />
      <DatePickerField
        placeholder="To"
        :modelValue="toDate"
        @update:modelValue="onToDateChange"
      />

      <div class="text-caption text-medium-emphasis mt-4 mb-2">
        Find gaps of at least
      </div>
      <div class="d-flex gap-2">
        <v-text-field
          label="Amount"
          type="number"
          v-model="gapAmount"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
        <v-select
          label="Unit"
          :items="gapUnits"
          v-model="selectedGapUnit"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
      </div>

      <div class="text-caption text-medium-emphasis mt-4 mb-2">
        Fill with a value every
      </div>
      <div class="d-flex gap-2">
        <v-text-field
          label="Amount"
          type="number"
          v-model="fillAmount"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
        <v-select
          label="Unit"
          :items="fillUnits"
          v-model="selectedFillUnit"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
      </div>

      <v-checkbox
        v-model="interpolateValues"
        label="Interpolate fill values"
        :hint="
          interpolateValues
            ? 'Values between endpoints will be linearly interpolated.'
            : 'NoData values (e.g. -9999) will be inserted.'
        "
        persistent-hint
        density="compact"
        class="mt-2"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating"
        @click="onFillGaps"
      >
        Fill gaps
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUIStore } from '@/store/userInterface'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
const { fillUnits, gapUnits } = useUIStore()
const {
  interpolateValues,
  gapAmount,
  selectedGapUnit,
  selectedFillUnit,
  fillAmount,
} = storeToRefs(useUIStore())
import { EnumEditOperations, TimeUnit } from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'

import { usePlotlyStore } from '@/store/plotly'
const { redraw } = usePlotlyStore()
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const { clearSelected, startDate, endDate, selectDateRange } =
  useDataSelection()

const fromDate = ref<Date>(startDate.value)
const toDate = ref<Date>(endDate.value)

const onFromDateChange = async (date: Date) => {
  fromDate.value = date
  await selectDateRange(date, toDate.value)
}

const onToDateChange = async (date: Date) => {
  toDate.value = date
  await selectDateRange(fromDate.value, date)
}

const emit = defineEmits(['close'])
const onFillGaps = async () => {
  isUpdating.value = true

  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.FILL_GAPS,
      // @ts-ignore
      [+gapAmount.value, TimeUnit[selectedGapUnit.value]],
      // @ts-ignore
      [+fillAmount.value, TimeUnit[selectedFillUnit.value]],
      interpolateValues.value,
      selectedData.value
        ? [
            selectedData.value[0],
            selectedData.value[selectedData.value.length - 1],
          ]
        : undefined
    )

    await clearSelected()
    isUpdating.value = false
    await redraw()
    emit('close')
  })
}
</script>
