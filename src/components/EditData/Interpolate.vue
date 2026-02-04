<template>
  <v-card>
    <v-card-title>Interpolate</v-card-title>
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
      <div class="d-flex gap-1">
        <v-radio-group
          hide-details
          color="primary"
          v-model="selectedInterpolationMethod"
        >
          <v-radio
            label="Linear Interpolation"
            :value="InterpolationMethods.LINEAR"
          ></v-radio>
        </v-radio-group>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn @click="onInterpolate">Interpolate</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { InterpolationMethods, useUIStore } from '@/store/userInterface'
import { useDataSelection } from '@/composables/useDataSelection'

const { selectedData } = storeToRefs(useDataVisStore())
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { selectedInterpolationMethod } = storeToRefs(useUIStore())
const { clearSelected } = useDataSelection()

const emit = defineEmits(['close'])

const onInterpolate = async () => {
  if (!selectedData.value?.length) {
    return
  }

  isUpdating.value = true

  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.INTERPOLATE,
      selectedData.value
    )

    await clearSelected()
    isUpdating.value = false
    await redraw()
    emit('close')
  })
}
</script>
