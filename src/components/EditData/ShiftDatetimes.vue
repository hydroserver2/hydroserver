<template>
  <v-card>
    <v-card-title>Shift Datetimes</v-card-title>
    <v-card-subtitle class="mb-4">
      <div>
        {{ selectedData?.length }} Data Point{{
          selectedData?.length === 1 ? '' : 's'
        }}
        selected
      </div>
    </v-card-subtitle>

    <v-divider></v-divider>

    <v-card-text>
      <v-row>
        <v-col>
          <v-text-field label="Amount" type="number" v-model="shiftAmount" />
        </v-col>
        <v-col>
          <v-select
            label="Time Unit"
            :items="shiftUnits"
            v-model="selectedShiftUnit"
          />
        </v-col>
      </v-row>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn :disabled="isUpdating" @click="onShiftDatetimes"
        >Shift Datetimes</v-btn
      >
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
