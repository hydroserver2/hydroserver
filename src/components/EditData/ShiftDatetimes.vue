<template>
  <v-card>
    <v-card-title>Shift datetimes</v-card-title>
    <v-card-subtitle>
      <span class="selected-count-badge">
        <v-icon icon="mdi-vector-selection" size="14" />
        {{ selectedData?.length }} point{{
          selectedData?.length === 1 ? '' : 's'
        }}
        selected
      </span>
    </v-card-subtitle>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">
        Shift selected timestamps by
      </div>
      <div class="d-flex gap-2">
        <v-text-field
          label="Amount"
          type="number"
          v-model="shiftAmount"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
        <v-select
          label="Unit"
          :items="shiftUnits"
          v-model="selectedShiftUnit"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating || !selectedData?.length"
        @click="onShiftDatetimes"
      >
        Shift
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations, TimeUnit } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore } from '@/store/userInterface'
import { useDataSelection } from '@/composables/useDataSelection'

const { selectedData } = storeToRefs(useDataVisStore())
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedShiftUnit, shiftAmount } = storeToRefs(useUIStore())
const { redraw } = usePlotlyStore()
const { shiftUnits } = useUIStore()
const { clearSelected } = useDataSelection()

const emit = defineEmits(['close'])

const onShiftDatetimes = async () => {
  if (!selectedData.value?.length) {
    return
  }

  isUpdating.value = true

  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.SHIFT_DATETIMES,
      selectedData.value,
      +shiftAmount.value,
      // @ts-ignore
      TimeUnit[selectedShiftUnit.value]
    )

    await clearSelected()
    isUpdating.value = false
    await redraw(true)
    emit('close')
  })
}
</script>
