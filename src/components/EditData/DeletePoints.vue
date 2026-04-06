<template>
  <v-card>
    <v-card-title>Delete Points</v-card-title>
    <v-card-subtitle class="mb-4">
      <div>
        <b class="text-red">{{ selectedData?.length }}</b> Data Point{{
          selectedData?.length === 1 ? '' : 's'
        }}
        selected
      </div>
    </v-card-subtitle>

    <v-divider></v-divider>

    <v-card-text>
      <p class="text-body-1">
        Are you sure you want to delete
        <b class="text-red">{{ selectedData?.length }}</b> selected Data Point{{
          selectedData?.length !== 1 ? 's' : ''
        }}?
      </p>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn :disabled="isUpdating" @click="onDeleteDataPoints"
        >Delete Data Points</v-btn
      >
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations } from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import { usePlotlyStore } from '@/store/plotly'

const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { clearSelected } = useDataSelection()
const { selectedData } = storeToRefs(useDataVisStore())

const emit = defineEmits(['close'])

const onDeleteDataPoints = async () => {
  if (!selectedData.value?.length) {
    return
  }

  isUpdating.value = true

  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.DELETE_POINTS,
      selectedData.value
    )

    await clearSelected()
    isUpdating.value = false
    await redraw(true)
    emit('close')
  })
}
</script>
