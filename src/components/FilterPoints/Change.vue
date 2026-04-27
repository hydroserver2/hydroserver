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
        @keyup.enter="
          changeValue != null &&
          !isUpdating &&
          onFilter(selectedChangeComparator?.title, changeValue)
        "
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
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore } from '@/store/userInterface'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { storeToRefs } from 'pinia'

const { isUpdating } = storeToRefs(usePlotlyStore())
const { dispatchFilter, getActiveFilterRange } = useFilterDispatch()
defineEmits(['filter', 'close'])
const { selectedChangeComparator, changeValue } = storeToRefs(useUIStore())
const { logicalComparators } = useUIStore()

const onFilter = async (key: string, value: number) => {
  await dispatchFilter(
    EnumFilterOperations.CHANGE,
    key,
    +value,
    getActiveFilterRange()
  )
}
</script>
