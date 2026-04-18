<template>
  <v-card>
    <v-card-title class="text-body-1">Filter by values</v-card-title>

    <template v-if="Object.keys(appliedFilters).length">
      <v-card-text class="pt-2 pb-0">
        <div class="text-caption text-medium-emphasis mb-2 d-flex align-center">
          <span class="flex-grow-1">
            Applied ({{ Object.keys(appliedFilters).length }})
          </span>
          <v-btn
            size="x-small"
            variant="text"
            :disabled="isUpdating"
            @click="clearFilters"
          >
            Clear all
          </v-btn>
        </div>
        <div class="d-flex flex-wrap gap-1">
          <v-chip
            v-for="(key, index) of Object.keys(appliedFilters)"
            :key="index"
            size="small"
            variant="tonal"
            color="primary"
            closable
            @click:close="removeFilter(key)"
          >
            {{ key }} {{ appliedFilters[key] }}
          </v-chip>
        </div>
      </v-card-text>
    </template>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">
        Select points where the value is
      </div>
      <v-select
        :items="filterOperators"
        class="mb-3"
        v-model="selectedFilter"
        return-object
        hide-details
        density="comfortable"
        variant="outlined"
      />
      <v-text-field
        label="Value"
        v-model="filterValue"
        step="0.1"
        type="number"
        hide-details
        density="comfortable"
        variant="outlined"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        prepend-icon="mdi-plus"
        :disabled="isUpdating || (!filterValue && filterValue !== 0)"
        @click="onAddFilter(selectedFilter?.title, filterValue)"
      >
        Add filter
      </v-btn>
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
