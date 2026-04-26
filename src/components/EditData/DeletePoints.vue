<template>
  <v-card>
    <v-card-title>Delete points</v-card-title>
    <v-card-subtitle>
      <span class="selected-count-badge">
        <v-icon icon="mdi-vector-selection" size="14" />
        <span class="text-error font-weight-bold">
          {{ selectedData?.length }}
        </span>
        point{{ selectedData?.length === 1 ? '' : 's' }} selected
      </span>
    </v-card-subtitle>

    <v-card-text>
      <v-alert
        type="warning"
        density="compact"
        variant="tonal"
        class="text-body-2"
      >
        This removes
        <b>{{ selectedData?.length }}</b>
        selected point{{ selectedData?.length === 1 ? '' : 's' }} from the
        series. The step is recorded in the edit history and can be undone
        from there.
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="error"
        variant="flat"
        prepend-icon="mdi-trash-can-outline"
        :disabled="isUpdating || !selectedData?.length"
        @click="onDeleteDataPoints"
      >
        Delete
      </v-btn>
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
    // No indices arg — qc-utils' dispatch reads the target indices
    // off the preceding SELECTION in history.
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.DELETE_POINTS
    )

    await clearSelected()
    isUpdating.value = false
    await redraw(true)
    emit('close')
  })
}
</script>
