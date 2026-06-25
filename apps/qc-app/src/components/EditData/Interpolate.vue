<template>
  <v-card>
    <v-card-title>Interpolate</v-card-title>
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
      <div class="text-body-small text-medium-emphasis mb-2">Method</div>
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
import { useFilterDispatch } from '@/composables/useFilterDispatch'

const { selectedData } = storeToRefs(useDataVisStore())
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { selectedInterpolationMethod } = storeToRefs(useUIStore())
const { recordPostActionSelection } = useFilterDispatch()

const emit = defineEmits(['close'])

const onInterpolate = async () => {
  if (!selectedData.value?.length) {
    return
  }

  const indices = [...selectedData.value]

  isUpdating.value = true

  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.INTERPOLATE
    )

    isUpdating.value = false
    await redraw()
    await recordPostActionSelection(indices)
    emit('close')
  })
}
</script>
