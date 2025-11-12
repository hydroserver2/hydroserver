<template>
  <v-card rounded>
    <v-card-title class="text-body-1">Filter by change</v-card-title>
    <v-divider></v-divider>

    <v-card-text>
      <v-label class="mb-4"
        >Select points where the change threshold is</v-label
      >
      <v-select
        label="Comparison operator"
        :items="logicalComparators"
        v-model="selectedChangeComparator"
        return-object
      ></v-select>
      <v-text-field
        label="Change"
        type="number"
        clearable
        step="1"
        v-model="changeValue"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn
        @click="onFilter(selectedChangeComparator?.title, changeValue)"
        :disabled="isUpdating || changeValue == null"
        >Filter</v-btn
      >
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
    const selection = await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.CHANGE,
      key,
      +value
    )

    await dispatchSelection(selection)
    isUpdating.value = false
    emit('close')
  })
}
</script>
