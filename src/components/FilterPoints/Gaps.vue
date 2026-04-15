<template>
  <v-card>
    <v-card-title class="text-body-1">Find time gaps in the data</v-card-title>

    <v-divider></v-divider>

    <v-card-text>
      <div class="mb-4">
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
      </div>

      <p class="text-body-1 mb-4"><b>Find</b> gaps of at least:</p>
      <div class="d-flex gap-1">
        <v-text-field
          width="30"
          label="Amount"
          type="number"
          v-model="gapAmount"
        >
        </v-text-field>

        <v-select
          label="Gap Unit"
          :items="gapUnits"
          v-model="selectedGapUnit"
        ></v-select>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn :disabled="isUpdating" @click="onFindGaps">Find Gaps</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useDataSelection } from '@/composables/useDataSelection'
import { EnumFilterOperations, TimeUnit } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore } from '@/store/userInterface'
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'

const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { gapAmount, gapUnits, selectedGapUnit } = storeToRefs(useUIStore())
const { selectedData } = storeToRefs(useDataVisStore())
const { dispatchSelection, startDate, endDate, selectDateRange } =
  useDataSelection()

const emit = defineEmits(['close'])

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

const onFindGaps = async () => {
  isUpdating.value = true

  setTimeout(async () => {
    const newSelection = await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.FIND_GAPS,
      +gapAmount.value,
      // @ts-ignore
      TimeUnit[selectedGapUnit.value],
      // TODO: this operation should now receive datetimes instead of indexes, so that it can be represented as such in histories
      selectedData.value
        ? [
            selectedData.value[0],
            selectedData.value[selectedData.value.length - 1],
          ]
        : undefined
    )

    if (newSelection) {
      await dispatchSelection(newSelection)
    }

    isUpdating.value = false
    emit('close')
  })
}
</script>
