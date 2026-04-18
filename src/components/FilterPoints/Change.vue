<template>
  <v-card>
    <v-card-title class="text-body-1">Filter by change</v-card-title>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">
        Select points where the change between consecutive samples is
      </div>
      <v-select
        label="Comparator"
        :items="logicalComparators"
        v-model="selectedChangeComparator"
        return-object
        density="comfortable"
        variant="outlined"
        hide-details
        class="mb-3"
      />
      <v-text-field
        label="Change"
        type="number"
        step="1"
        clearable
        v-model="changeValue"
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
        :disabled="isUpdating || changeValue == null"
        @click="onFilter(selectedChangeComparator?.title, changeValue)"
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
const { selectedChangeComparator, changeValue } = storeToRefs(useUIStore())

const { logicalComparators } = useUIStore()

const onFilter = async (key: string, value: number) => {
  isUpdating.value = true
  setTimeout(async () => {
    await clearSelected()
    const newSelection = await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.CHANGE,
      key,
      +value
    )

    if (newSelection) {
      await dispatchSelection(newSelection)
    }
    isUpdating.value = false
    emit('close')
  })
}
</script>
