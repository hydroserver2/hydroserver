<template>
  <v-card rounded min-width="600">
    <v-card-title class="text-body-1">
      Filter by values
      <v-badge
        v-if="Object.keys(appliedFilters).length"
        :content="Object.keys(appliedFilters).length"
        inline
        color="blue"
      ></v-badge>
    </v-card-title>
    <v-divider></v-divider>
    <template v-if="Object.keys(appliedFilters).length">
      <v-card-text class="d-flex gap-1">
        <div class="d-flex gap-1">
          <v-chip
            border="double blue"
            variant="outlined"
            closable
            color="blue"
            v-for="(key, index) of Object.keys(appliedFilters)"
            :key="index"
            @click:close="removeFilter(key)"
            >{{ key }}: {{ appliedFilters[key] }}</v-chip
          >
        </div>
        <v-spacer></v-spacer>
        <v-btn
          color="blue-grey-lighten-1"
          :disabled="isUpdating"
          @click="clearFilters"
          variant="outlined"
          rounded
          >Clear</v-btn
        >
      </v-card-text>
      <v-divider></v-divider>
    </template>

    <v-card-text>
      <v-label class="mb-4">Select points where the values are</v-label>

      <v-select
        :items="filterOperators"
        class="mb-6"
        v-model="selectedFilter"
        return-object
        hide-details
      ></v-select>
      <v-text-field
        label="Value"
        v-model="filterValue"
        step="0.1"
        type="number"
        hide-details
      >
      </v-text-field>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Close</v-btn-cancel>
      <v-btn
        @click="onAddFilter(selectedFilter?.title, filterValue)"
        :disabled="isUpdating || (!filterValue && filterValue !== 0)"
        prepend-icon="mdi-plus"
        >Add Filter</v-btn
      >
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { Ref, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { EnumFilterOperations, FilterOperation } from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import { usePlotlyStore } from '@/store/plotly'

const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { dispatchSelection, clearSelected } = useDataSelection()
const emit = defineEmits(['filter', 'close'])

// FILTERS
const filterOperators = [
  ...Object.keys(FilterOperation).map((key) => ({
    value: key,
    // @ts-ignore
    title: FilterOperation[key],
  })),
]
const selectedFilter = ref(filterOperators[2])
const filterValue = ref(0)
const appliedFilters: Ref<{ [key: string]: number }> = ref({})

const clearFilters = async () => {
  appliedFilters.value = {}
  isUpdating.value = true
  setTimeout(async () => {
    const selection = await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.VALUE_THRESHOLD,
      appliedFilters.value
    )
    if (selection) {
      await dispatchSelection(selection)
    }
    isUpdating.value = false
  })
}

const onAddFilter = async (key: string, value: number) => {
  isUpdating.value = true
  setTimeout(async () => {
    await clearSelected()
    await _addFilter(key, value)
    isUpdating.value = false
  })
}

const _addFilter = async (key: string, value: number) => {
  appliedFilters.value[key] = +value
  const newSelection = await selectedSeries.value?.data.dispatchFilter(
    EnumFilterOperations.VALUE_THRESHOLD,
    appliedFilters.value
  )

  if (newSelection) {
    await dispatchSelection(newSelection)
  }
}

const removeFilter = async (key: string) => {
  isUpdating.value = true
  delete appliedFilters.value[key]
  setTimeout(async () => {
    const newSelection = await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.VALUE_THRESHOLD,
      appliedFilters.value
    )
    if (newSelection) {
      await dispatchSelection(newSelection)
    }
    isUpdating.value = false
  })
}
</script>
