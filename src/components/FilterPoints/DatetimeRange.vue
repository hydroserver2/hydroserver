<template>
  <v-card>
    <v-card-title class="text-body-1">Filter by datetime range</v-card-title>

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

      <v-alert
        v-if="!isRangeValid"
        type="error"
        density="compact"
        variant="tonal"
        class="mt-3"
      >
        End datetime must be after the start datetime.
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating || !isRangeValid"
        @click="onApply"
      >
        Apply filter
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useDataSelection } from '@/composables/useDataSelection'
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'

const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { dispatchSelection, clearSelected, startDate, endDate } =
  useDataSelection()
const emit = defineEmits(['close'])

const fromDate = ref<Date>(startDate.value)
const toDate = ref<Date>(endDate.value)

const isRangeValid = computed(
  () => fromDate.value.getTime() <= toDate.value.getTime()
)

const onFromDateChange = (date: Date) => {
  fromDate.value = date
}
const onToDateChange = (date: Date) => {
  toDate.value = date
}

const onApply = async () => {
  isUpdating.value = true
  setTimeout(async () => {
    await clearSelected()
    const selection = await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.DATETIME_RANGE,
      fromDate.value.getTime(),
      toDate.value.getTime()
    )
    if (selection) {
      await dispatchSelection(selection)
    }
    isUpdating.value = false
    emit('close')
  })
}
</script>
