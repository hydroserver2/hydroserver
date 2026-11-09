<template>
  <v-card>
    <v-card-title class="text-body-large">Filter by values</v-card-title>

    <template v-if="appliedFilters.length">
      <v-card-text class="pt-2 pb-0">
        <div class="text-body-small text-medium-emphasis mb-2 d-flex align-center">
          <span class="flex-grow-1">
            Applied ({{ appliedFilters.length }})
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
        <div class="d-flex flex-wrap ga-1">
          <v-chip
            v-for="(filter, index) of appliedFilters"
            :key="`${filter.operator}:${filter.value}`"
            size="small"
            variant="tonal"
            color="primary"
            closable
            @click:close="removeFilter(index)"
          >
            {{ filter.operator }} {{ filter.value }}
          </v-chip>
        </div>
        <v-btn-toggle
          v-if="appliedFilters.length > 1"
          v-model="match"
          color="primary"
          variant="outlined"
          divided
          mandatory
          density="compact"
          class="mt-3 d-flex"
          data-testid="value-threshold-match"
          :disabled="isUpdating"
        >
          <v-btn value="any" class="flex-grow-1">Match any</v-btn>
          <v-btn value="all" class="flex-grow-1">Match all</v-btn>
        </v-btn-toggle>
      </v-card-text>
    </template>

    <v-card-text>
      <div class="text-body-small text-medium-emphasis mb-2">
        Select points where the value is
      </div>
      <v-select
        :items="filterOperators"
        class="mb-3"
        v-model="selectedOperator"
        data-testid="value-threshold-operator"
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
        @keyup.enter="canAdd && onAddFilter()"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="tonal"
        prepend-icon="mdi-plus"
        :disabled="isUpdating || !canAdd"
        @click="onAddFilter"
      >
        Add filter
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        data-testid="value-threshold-apply"
        :disabled="isUpdating || !appliedFilters.length"
        @click="reapply"
      >
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import {
  EnumFilterOperations,
  FilterMatch,
  FilterOperation,
  ValueFilter,
} from '@uwrl/qc-utils'
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { usePlotlyStore } from '@/store/plotly'

const { isUpdating } = storeToRefs(usePlotlyStore())
const { dispatchFilter, getActiveFilterRange } = useFilterDispatch()
defineEmits(['filter', 'close'])

const filterOperators = Object.values(FilterOperation)
const selectedOperator = ref<FilterOperation>(FilterOperation.GT)
const filterValue = ref<number | string>(0)
const appliedFilters = ref<ValueFilter[]>([])
const match = ref<FilterMatch>('any')

const canAdd = computed(
  () => filterValue.value !== '' && Number.isFinite(+filterValue.value)
)

// Copy the filters so later panel edits don't rewrite a dispatched history entry.
const reapply = () =>
  dispatchFilter(
    EnumFilterOperations.VALUE_THRESHOLD,
    { filters: appliedFilters.value.map((f) => ({ ...f })), match: match.value },
    getActiveFilterRange()
  )

watch(match, reapply)

const clearFilters = async () => {
  appliedFilters.value = []
  await reapply()
}

const onAddFilter = async () => {
  const filter = { operator: selectedOperator.value, value: +filterValue.value }
  const exists = appliedFilters.value.some(
    (f) => f.operator === filter.operator && f.value === filter.value
  )
  if (exists) return
  appliedFilters.value.push(filter)
  await reapply()
}

const removeFilter = async (index: number) => {
  appliedFilters.value.splice(index, 1)
  await reapply()
}
</script>
