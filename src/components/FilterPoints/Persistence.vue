<template>
  <v-card>
    <v-card-title class="text-body-1">Find persistent values</v-card-title>

    <v-card-text>
      <div
        v-if="selectedData?.length"
        class="mb-3 pa-2 rounded bg-info-lighten-5"
        style="
          background-color: rgba(var(--v-theme-primary), 0.04);
          border-left: 2px solid rgb(var(--v-theme-primary));
        "
      >
        <div class="text-caption text-medium-emphasis">Within selection</div>
        <div class="text-body-2 font-weight-medium">
          {{ startDateString }} → {{ endDateString }}
        </div>
      </div>

      <div class="text-caption text-medium-emphasis mb-2">
        Flag runs of identical values that repeat at least
      </div>
      <v-text-field
        v-model.number="times"
        type="number"
        suffix="times in a row"
        min="2"
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
        :disabled="isUpdating"
        @click="onPersistence"
      >
        Apply filter
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import { usePlotlyStore } from '@/store/plotly'

const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const { dispatchSelection, startDateString, endDateString } = useDataSelection()

const emit = defineEmits(['close'])
const times = ref(2)
const onPersistence = async () => {
  isUpdating.value = true

  setTimeout(async () => {
    const selection = await selectedSeries.value.data.dispatchFilter(
      EnumFilterOperations.PERSISTENCE,
      times.value,
      selectedData.value
        ? [
            selectedData.value[0],
            selectedData.value[selectedData.value.length - 1],
          ]
        : undefined
    )

    await dispatchSelection(selection)

    isUpdating.value = false
    emit('close')
  })
}
</script>
