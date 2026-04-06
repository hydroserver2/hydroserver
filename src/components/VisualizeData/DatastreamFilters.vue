<template>
  <v-btn
    color="primary-lighten-2"
    @click="clearFilters"
    variant="outlined"
    rounded
    append-icon="mdi-close"
    class="mb-4"
    >Clear filters</v-btn
  >

  <v-expansion-panels color="blue-grey-darken-2" multiple v-model="panels">
    <v-expansion-panel title="Sites">
      <v-expansion-panel-text class="bg-blue-grey-darken-4">
        <v-text-field
          class="my-4"
          clearable
          @click:clear="searchThing = ''"
          v-model="searchThing"
          prepend-inner-icon="mdi-magnify"
          label="Search"
          density="compact"
          hide-details
        />

        <v-virtual-scroll
          :items="sortedThings"
          :height="sortedThings.length < 6 ? 'auto' : 250"
        >
          <template #default="{ item }">
            <v-checkbox
              :key="item.id"
              v-model="selectedThings"
              :label="item.name"
              :value="item"
              hide-details
              density="compact"
            />
          </template>
        </v-virtual-scroll>
      </v-expansion-panel-text>
    </v-expansion-panel>

    <v-expansion-panel title="Observed properties">
      <v-expansion-panel-text class="bg-blue-grey-darken-4">
        <v-text-field
          class="my-4"
          clearable
          @click:clear="searchObservedProperty = ''"
          v-model="searchObservedProperty"
          prepend-inner-icon="mdi-magnify"
          label="Search"
          density="compact"
          hide-details
        />

        <v-virtual-scroll
          :items="sortedObservedPropertyNames"
          :height="sortedObservedPropertyNames.length < 6 ? 'auto' : 250"
        >
          <template #default="{ item }">
            <v-checkbox
              v-model="selectedObservedPropertyNames"
              :label="item"
              :value="item"
              hide-details
              density="compact"
            />
          </template>
        </v-virtual-scroll>
      </v-expansion-panel-text>
    </v-expansion-panel>

    <v-expansion-panel title="Processing levels">
      <v-expansion-panel-text class="bg-blue-grey-darken-4">
        <v-text-field
          class="my-4"
          clearable
          @click:clear="searchProcessingLevel = ''"
          v-model="searchProcessingLevel"
          prepend-inner-icon="mdi-magnify"
          label="Search"
          density="compact"
          hide-details
        />

        <v-virtual-scroll
          :items="sortedProcessingLevelNames"
          :height="sortedProcessingLevelNames.length < 6 ? 'auto' : 250"
        >
          <template #default="{ item }">
            <v-checkbox
              v-model="selectedProcessingLevelNames"
              :label="item"
              :value="item"
              hide-details
              density="compact"
            />
          </template>
        </v-virtual-scroll>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'

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

const clearFilters = () => {
  selectedThings.value = []
  selectedObservedPropertyNames.value = []
  selectedProcessingLevelNames.value = []

  searchThing.value = ''
  searchObservedProperty.value = ''
  searchProcessingLevel.value = ''
}

const panels = ref([])
</script>

<style scoped>
:deep(.v-selection-control),
:deep(.v-label) {
  align-items: start;
}
</style>
