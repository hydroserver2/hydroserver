<template>
  <v-card>
    <v-card-title class="text-body-1">Filter by rate of change</v-card-title>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">
        Select points where the rate of change is
      </div>
      <v-select
        label="Comparator"
        :items="logicalComparators"
        v-model="selectedRateOfChangeComparator"
        return-object
        density="comfortable"
        variant="outlined"
        hide-details
        class="mb-3"
      />
      <v-text-field
        label="Rate of change"
        type="number"
        step="1"
        clearable
        append-inner-icon="mdi-percent-outline"
        v-model="rateOfChangeValue"
        density="comfortable"
        variant="outlined"
        hide-details
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating || rateOfChangeValue == null"
        @click="
          onFilter(selectedRateOfChangeComparator?.title, rateOfChangeValue)
        "
      >
        Apply filter
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useDataSelection } from '@/composables/useDataSelection'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore } from '@/store/userInterface'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { storeToRefs } from 'pinia'
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { dispatchSelection, clearSelected } = useDataSelection()
const emit = defineEmits(['filter', 'close'])
const { selectedRateOfChangeComparator, rateOfChangeValue } =
  storeToRefs(useUIStore())

const { logicalComparators } = useUIStore()

const onFilter = async (key: string, value: number) => {
  isUpdating.value = true
  setTimeout(async () => {
    await clearSelected()
    const selection = await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.RATE_OF_CHANGE,
      key,
      +value / 100
    )

    await dispatchSelection(selection)
    isUpdating.value = false
    emit('close')
  })
}
</script>
