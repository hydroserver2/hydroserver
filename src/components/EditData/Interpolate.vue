<template>
  <v-card>
    <v-card-title>Interpolate</v-card-title>
    <v-card-subtitle>
      <v-icon icon="mdi-selection-ellipse" size="14" class="mr-1" />
      {{ selectedData?.length }} point{{
        selectedData?.length === 1 ? '' : 's'
      }}
      selected
    </v-card-subtitle>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">Method</div>
      <v-radio-group
        hide-details
        color="primary"
        v-model="selectedInterpolationMethod"
        density="compact"
      >
        <v-radio
          label="Linear interpolation"
          :value="InterpolationMethods.LINEAR"
        />
      </v-radio-group>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating || !selectedData?.length"
        @click="onInterpolate"
      >
        Interpolate
      </v-btn>
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
