<template>
  <div class="ds-filters">
    <!-- Inline strip with count + clear, collapsed to a single row. -->
    <div
      v-if="appliedCount"
      class="d-flex align-center justify-space-between text-caption text-medium-emphasis mb-1"
    >
      <span>
        {{ appliedCount }} filter{{ appliedCount === 1 ? '' : 's' }} applied
      </span>
      <v-btn
        size="x-small"
        variant="text"
        density="compact"
        prepend-icon="mdi-close-circle-outline"
        @click="clearFilters"
      >
        Clear
      </v-btn>
    </div>

    <v-expansion-panels
      v-model="panels"
      multiple
      variant="accordion"
      class="ds-filters__panels"
    >
      <FilterPanel
        icon="mdi-map-marker-outline"
        label="Sites"
        :total="sortedThings.length"
        :selected-count="selectedThings.length"
        v-model:search="searchThing"
      >
        <template #default>
          <v-virtual-scroll
            :items="sortedThings"
            :height="sortedThings.length < 6 ? 'auto' : 180"
            item-height="28"
          >
            <template #default="{ item }">
              <v-checkbox
                :key="item.id"
                v-model="selectedThings"
                :label="item.name"
                :value="item"
                hide-details
                density="compact"
                color="primary"
                class="ds-filters__checkbox"
              />
            </template>
          </v-virtual-scroll>
        </template>
      </FilterPanel>

      <FilterPanel
        icon="mdi-chart-bell-curve-cumulative"
        label="Observed properties"
        :total="sortedObservedPropertyNames.length"
        :selected-count="selectedObservedPropertyNames.length"
        v-model:search="searchObservedProperty"
      >
        <template #default>
          <v-virtual-scroll
            :items="sortedObservedPropertyNames"
            :height="sortedObservedPropertyNames.length < 6 ? 'auto' : 180"
            item-height="28"
          >
            <template #default="{ item }">
              <v-checkbox
                v-model="selectedObservedPropertyNames"
                :label="item"
                :value="item"
                hide-details
                density="compact"
                color="primary"
                class="ds-filters__checkbox"
              />
            </template>
          </v-virtual-scroll>
        </template>
      </FilterPanel>

      <FilterPanel
        icon="mdi-layers-triple-outline"
        label="Processing levels"
        :total="sortedProcessingLevelNames.length"
        :selected-count="selectedProcessingLevelNames.length"
        v-model:search="searchProcessingLevel"
      >
        <template #default>
          <v-virtual-scroll
            :items="sortedProcessingLevelNames"
            :height="sortedProcessingLevelNames.length < 6 ? 'auto' : 180"
            item-height="28"
          >
            <template #default="{ item }">
              <v-checkbox
                v-model="selectedProcessingLevelNames"
                :label="item"
                :value="item"
                hide-details
                density="compact"
                color="primary"
                class="ds-filters__checkbox"
              />
            </template>
          </v-virtual-scroll>
        </template>
      </FilterPanel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import FilterPanel from '@/components/VisualizeData/FilterPanel.vue'
import { usePersistedFlag } from '@/composables/useResizable'

const {
  matchesSelectedObservedProperty,
  matchesSelectedProcessingLevel,
  matchesSelectedThing,
} = useDataVisStore()
const {
  things,
  datastreams,
  processingLevels,
  observedProperties,
  selectedThings,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
} = storeToRefs(useDataVisStore())

const searchThing = ref('')
const searchObservedProperty = ref('')
const searchProcessingLevel = ref('')

// Only show list items that are referenced by at least one datastream
// Then mutually filter the lists by selected filters.
const sortedProcessingLevelNames = computed(() => {
  const filteredPLs = processingLevels.value.filter(
    (pl) =>
      pl.definition
        ?.toLowerCase()
        .includes(searchProcessingLevel.value.toLowerCase()) &&
      datastreams.value.some(
        (ds) =>
          ds.processingLevel.id === pl.id &&
          matchesSelectedThing(ds) &&
          matchesSelectedObservedProperty(ds)
      )
  )
  const names = filteredPLs.map((pl) => pl.definition)
  return [...new Set(names)].sort()
})

const sortedThings = computed(() => {
  return things.value
    .filter(
      (thing) =>
        thing.name.toLowerCase().includes(searchThing.value.toLowerCase()) &&
        datastreams.value.some(
          (ds) =>
            ds.thing.id === thing.id &&
            matchesSelectedObservedProperty(ds) &&
            matchesSelectedProcessingLevel(ds)
        )
    )
    .sort((a, b) => a.name.localeCompare(b.name))
})

const sortedObservedPropertyNames = computed(() => {
  const filteredProperties = observedProperties.value.filter((op) => {
    return (
      op.name
        .toLowerCase()
        .includes(searchObservedProperty.value.toLowerCase()) &&
      datastreams.value.some(
        (ds) =>
          ds.observedProperty.id === op.id &&
          matchesSelectedThing(ds) &&
          matchesSelectedProcessingLevel(ds)
      )
    )
  })

  const names = filteredProperties.map((pl) => pl.name)
  return [...new Set(names)].sort()
})

// Watchers to handle deselection of hidden items
watch(sortedThings, (newVal, oldVal) => {
  if (newVal.length < oldVal.length) {
    selectedThings.value = selectedThings.value.filter((selectedThing) =>
      newVal.some((thing) => thing.id === selectedThing.id)
    )
  }
})

watch(sortedObservedPropertyNames, (newVal, oldVal) => {
  if (newVal.length < oldVal.length) {
    selectedObservedPropertyNames.value =
      selectedObservedPropertyNames.value.filter((name) =>
        newVal.includes(name)
      )
  }
})

watch(sortedProcessingLevelNames, (newVal, oldVal) => {
  if (newVal.length < oldVal.length) {
    selectedProcessingLevelNames.value =
      selectedProcessingLevelNames.value.filter((name) => newVal.includes(name))
  }
})

const appliedCount = computed(
  () =>
    selectedThings.value.length +
    selectedObservedPropertyNames.value.length +
    selectedProcessingLevelNames.value.length
)

const clearFilters = () => {
  selectedThings.value = []
  selectedObservedPropertyNames.value = []
  selectedProcessingLevelNames.value = []

  searchThing.value = ''
  searchObservedProperty.value = ''
  searchProcessingLevel.value = ''
}

const sitesOpen = usePersistedFlag('qc:dsFilters:sites', true)
const observedPropsOpen = usePersistedFlag('qc:dsFilters:observedProps', false)
const processingLevelsOpen = usePersistedFlag('qc:dsFilters:processingLevels', false)

const panels = computed<number[]>({
  get() {
    const open: number[] = []
    if (sitesOpen.value) open.push(0)
    if (observedPropsOpen.value) open.push(1)
    if (processingLevelsOpen.value) open.push(2)
    return open
  },
  set(val: number[]) {
    sitesOpen.value = val.includes(0)
    observedPropsOpen.value = val.includes(1)
    processingLevelsOpen.value = val.includes(2)
  },
})
</script>

<style scoped>
.ds-filters :deep(.v-expansion-panel) {
  background: transparent;
}

.ds-filters :deep(.v-expansion-panel-title) {
  min-height: 32px;
  padding: 2px 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  border-radius: 6px;
  transition: background-color 120ms ease;
}

.ds-filters :deep(.v-expansion-panel-title--active) {
  min-height: 32px;
}

.ds-filters :deep(.v-expansion-panel-title:hover),
.ds-filters :deep(.v-expansion-panel-title--active) {
  background-color: rgba(var(--v-theme-primary), 0.06);
}

.ds-filters :deep(.v-expansion-panel-text__wrapper) {
  padding: 4px 2px 8px;
}

/* Tight checkbox rows so the 180 px virtual viewport fits more items. */
.ds-filters__checkbox {
  min-height: 24px;
}

.ds-filters__checkbox :deep(.v-selection-control) {
  min-height: 24px;
}

.ds-filters__checkbox :deep(.v-label) {
  font-size: 0.8125rem;
  line-height: 1.2;
  opacity: 0.92;
  padding-top: 2px;
}

.ds-filters__checkbox :deep(.v-selection-control__wrapper),
.ds-filters__checkbox :deep(.v-selection-control__input) {
  width: 1.25rem;
  height: 1.25rem;
}

.ds-filters__checkbox :deep(.v-selection-control__input > .v-icon) {
  font-size: 1.125rem;
}

:deep(.v-selection-control),
:deep(.v-label) {
  align-items: start;
}
</style>
