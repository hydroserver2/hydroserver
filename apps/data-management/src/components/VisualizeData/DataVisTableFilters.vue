<template>
  <div class="datavis-header-filters">
    <v-menu
      v-for="filter in filterDefinitions"
      :key="filter.key"
      :close-on-content-click="false"
      location="bottom start"
      attach="body"
    >
      <template #activator="{ props: menuProps }">
        <v-btn
          v-bind="menuProps"
          variant="text"
          size="small"
          class="datavis-filter-button"
          :class="{
            'datavis-filter-button--active': filter.selectedCount > 0,
          }"
          :append-icon="mdiChevronDown"
          :aria-label="`Filter by ${filter.label.toLowerCase()}${
            filter.selectedCount ? ` (${filter.selectedCount} selected)` : ''
          }`"
        >
          {{ filter.label }}
          <span v-if="filter.selectedCount" class="filter-count">
            {{ filter.selectedCount }}
          </span>
        </v-btn>
      </template>

      <v-list class="datavis-filter-menu" density="compact">
        <div class="datavis-filter-title">Filter by {{ filter.label }}</div>
        <v-text-field
          v-model="filterSearches[filter.key]"
          class="datavis-filter-search"
          :placeholder="`Filter ${filter.label.toLowerCase()}`"
          :prepend-inner-icon="mdiMagnify"
          variant="outlined"
          density="compact"
          hide-details
          clearable
        />
        <v-list-item
          v-for="option in filteredOptions(filter)"
          :key="option.value"
          @click="toggleFilter(filter.key, option.value)"
        >
          <template #prepend>
            <v-checkbox
              :model-value="isFilterSelected(filter.key, option.value)"
              hide-details
              density="compact"
              :aria-label="`${filter.label}: ${option.label}`"
              @click.stop="toggleFilter(filter.key, option.value)"
            />
          </template>
          <v-list-item-title>{{ option.label }}</v-list-item-title>
        </v-list-item>
        <v-list-item
          v-if="filter.selectedCount"
          class="filter-clear-item"
          @click="clearFilter(filter.key)"
        >
          <v-list-item-title>Clear filter</v-list-item-title>
        </v-list-item>
        <div v-if="!filteredOptions(filter).length" class="filter-empty">
          No {{ filter.label.toLowerCase() }} found
        </div>
      </v-list>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiChevronDown, mdiMagnify } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import { useWorkspaceStore } from '@/store/workspaces'
import {
  parseDatastreamQuery,
  serializeDatastreamQuery,
  type DatastreamQueryFilters,
  type DatastreamQualifierKey,
} from '@/utils/datastreamSearch'

type FilterKey = DatastreamQualifierKey
type FilterOption = { value: string; label: string }
type FilterDefinition = {
  key: FilterKey
  label: string
  options: FilterOption[]
  selectedCount: number
}

const dataVisStore = useDataVisStore()
const {
  matchesSelectedObservedProperty,
  matchesSelectedProcessingLevel,
  matchesSelectedMonitoringSite,
  matchesSelectedWorkspace,
} = dataVisStore
const {
  monitoringSites,
  datastreams,
  observedProperties,
  processingLevels,
  selectedMonitoringSites,
  selectedWorkspaces,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
  tableSearch,
} = storeToRefs(dataVisStore)
const { workspaces } = storeToRefs(useWorkspaceStore())

const filterSearches = reactive<Record<FilterKey, string>>({
  workspace: '',
  site: '',
  'observed-property': '',
  'processing-level': '',
})

const initialFilters: DatastreamQueryFilters = {
  workspace: selectedWorkspaces.value.map((item) => item.name),
  site: selectedMonitoringSites.value.map((item) => item.name),
  'observed-property': [...selectedObservedPropertyNames.value],
  'processing-level': [...selectedProcessingLevelNames.value],
}
if (!tableSearch.value.trim()) {
  tableSearch.value = serializeDatastreamQuery(initialFilters, '')
}

const parsedQuery = computed(() => parseDatastreamQuery(tableSearch.value))

const canonicalValues = (candidates: string[], requested: string[]) => {
  const requestedSet = new Set(
    requested.map((value) => value.toLocaleLowerCase())
  )
  return candidates.filter((value, index) => {
    const normalized = value.toLocaleLowerCase()
    return (
      requestedSet.has(normalized) &&
      candidates.findIndex(
        (candidate) => candidate.toLocaleLowerCase() === normalized
      ) === index
    )
  })
}

watch(
  tableSearch,
  () => {
    const { filters } = parsedQuery.value
    selectedWorkspaces.value = workspaces.value.filter((item) =>
      filters.workspace.some(
        (value) => value.toLocaleLowerCase() === item.name.toLocaleLowerCase()
      )
    )
    selectedMonitoringSites.value = monitoringSites.value.filter((item) =>
      filters.site.some(
        (value) => value.toLocaleLowerCase() === item.name.toLocaleLowerCase()
      )
    )
    selectedObservedPropertyNames.value = canonicalValues(
      observedProperties.value
        .map((item) => item.name)
        .filter((value): value is string => Boolean(value)),
      filters['observed-property']
    )
    selectedProcessingLevelNames.value = canonicalValues(
      processingLevels.value
        .map((item) => item.name)
        .filter((value): value is string => Boolean(value)),
      filters['processing-level']
    )
  },
  { immediate: true }
)

const sortedWorkspaces = computed(() => {
  const workspaceIds = new Set<string>()
  datastreams.value.forEach((datastream) => {
    if (
      !matchesSelectedMonitoringSite(datastream) ||
      !matchesSelectedObservedProperty(datastream) ||
      !matchesSelectedProcessingLevel(datastream)
    )
      return

    const workspaceId = dataVisStore.monitoringSiteById.get(
      datastream.monitoringSiteId
    )?.workspaceId
    if (workspaceId) workspaceIds.add(workspaceId)
  })
  return workspaces.value
    .filter((workspace) => workspaceIds.has(workspace.id))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const sortedMonitoringSites = computed(() => {
  const ids = new Set<string>()
  datastreams.value.forEach((datastream) => {
    if (
      !matchesSelectedObservedProperty(datastream) ||
      !matchesSelectedProcessingLevel(datastream) ||
      !matchesSelectedWorkspace(datastream)
    )
      return
    ids.add(datastream.monitoringSiteId)
  })
  return monitoringSites.value
    .filter((site) => ids.has(site.id))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const sortedObservedPropertyNames = computed(() => {
  const names = new Set<string>()
  datastreams.value.forEach((datastream) => {
    if (
      !matchesSelectedMonitoringSite(datastream) ||
      !matchesSelectedProcessingLevel(datastream) ||
      !matchesSelectedWorkspace(datastream)
    )
      return
    const name = dataVisStore.observedPropertyById.get(
      datastream.observedPropertyId
    )?.name
    if (name) names.add(name)
  })
  return [...names].sort()
})

const sortedProcessingLevelNames = computed(() => {
  const names = new Set<string>()
  datastreams.value.forEach((datastream) => {
    if (
      !matchesSelectedMonitoringSite(datastream) ||
      !matchesSelectedObservedProperty(datastream) ||
      !matchesSelectedWorkspace(datastream)
    )
      return
    const name = dataVisStore.processingLevelById.get(
      datastream.processingLevelId
    )?.name
    if (name) names.add(name)
  })
  return [...names].sort()
})

const filterDefinitions = computed<FilterDefinition[]>(() => [
  {
    key: 'workspace',
    label: 'Workspaces',
    options: sortedWorkspaces.value.map((item) => ({
      value: item.name,
      label: item.name,
    })),
    selectedCount: selectedWorkspaces.value.length,
  },
  {
    key: 'site',
    label: 'Sites',
    options: sortedMonitoringSites.value.map((item) => ({
      value: item.name,
      label: item.name,
    })),
    selectedCount: selectedMonitoringSites.value.length,
  },
  {
    key: 'observed-property',
    label: 'Observed properties',
    options: sortedObservedPropertyNames.value.map((item) => ({
      value: item,
      label: item,
    })),
    selectedCount: selectedObservedPropertyNames.value.length,
  },
  {
    key: 'processing-level',
    label: 'Processing levels',
    options: sortedProcessingLevelNames.value.map((item) => ({
      value: item,
      label: item,
    })),
    selectedCount: selectedProcessingLevelNames.value.length,
  },
])

const filteredOptions = (filter: FilterDefinition) => {
  const query = filterSearches[filter.key].trim().toLocaleLowerCase()
  if (!query) return filter.options
  return filter.options.filter((option) =>
    option.label.toLocaleLowerCase().includes(query)
  )
}

const isFilterSelected = (key: FilterKey, value: string) => {
  const normalized = value.toLocaleLowerCase()
  return parsedQuery.value.filters[key].some(
    (item) => item.toLocaleLowerCase() === normalized
  )
}

const toggleFilter = (key: FilterKey, value: string) => {
  const filters = Object.fromEntries(
    Object.entries(parsedQuery.value.filters).map(([filterKey, values]) => [
      filterKey,
      [...values],
    ])
  ) as DatastreamQueryFilters
  const normalized = value.toLocaleLowerCase()
  const index = filters[key].findIndex(
    (item) => item.toLocaleLowerCase() === normalized
  )
  if (index >= 0) filters[key].splice(index, 1)
  else filters[key].push(value)
  tableSearch.value = serializeDatastreamQuery(
    filters,
    parsedQuery.value.text,
    parsedQuery.value.sort
  )
}

const clearFilter = (key: FilterKey) => {
  const filters = Object.fromEntries(
    Object.entries(parsedQuery.value.filters).map(([filterKey, values]) => [
      filterKey,
      filterKey === key ? [] : [...values],
    ])
  ) as DatastreamQueryFilters
  tableSearch.value = serializeDatastreamQuery(
    filters,
    parsedQuery.value.text,
    parsedQuery.value.sort
  )
  filterSearches[key] = ''
}
</script>

<style scoped>
.datavis-header-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-8);
  align-items: center;
}

.datavis-filter-button {
  min-width: auto;
  color: var(--hs-text-primary);
  text-transform: none;
}

.datavis-filter-button--active {
  color: rgb(var(--v-theme-primary));
}

.filter-count {
  min-width: 18px;
  margin-left: var(--hs-space-2);
  padding: 0 5px;
  color: rgb(var(--v-theme-on-primary));
  font-size: var(--hs-font-2xs);
  line-height: 18px;
  text-align: center;
  background: rgb(var(--v-theme-primary));
  border-radius: var(--hs-radius-pill);
}

.datavis-filter-menu {
  min-width: 280px;
  max-width: 360px;
  max-height: 320px;
  padding: var(--hs-space-8) 0;
  overflow-y: auto;
}

.datavis-filter-title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
}

.datavis-filter-search {
  height: 30px;
  margin: 0 var(--hs-space-12) var(--hs-space-8);
}

.datavis-filter-search :deep(.v-field) {
  height: 30px;
  min-height: 30px;
  padding-inline-start: 0;
  background: var(--hs-surface);
  border-radius: var(--hs-radius-sm);
}

.datavis-filter-search :deep(.v-field__outline) {
  color: var(--hs-input-border);
  --v-field-border-opacity: 1;
}

.datavis-filter-search :deep(.v-field--focused) {
  box-shadow: none;
}

.datavis-filter-search :deep(.v-field--focused .v-field__outline) {
  color: rgb(var(--v-theme-primary));
  --v-field-border-width: 2px;
  --v-field-border-opacity: 1;
}

.datavis-filter-search :deep(.v-field__input) {
  min-height: 30px;
  padding-top: 0;
  padding-bottom: 0;
  font-size: var(--hs-font-sm);
}

.datavis-filter-search :deep(.v-field__prepend-inner) {
  padding-right: 0;
  padding-left: var(--hs-space-8);
}

.datavis-filter-search :deep(.v-field__prepend-inner > .v-icon) {
  width: 16px;
  color: var(--hs-input-border);
  font-size: var(--hs-font-md);
  opacity: 1;
}

.datavis-filter-search :deep(.v-field__append-inner) {
  padding-right: var(--hs-space-8);
}

.datavis-filter-search :deep(input::placeholder) {
  color: var(--hs-text-secondary);
  opacity: 1;
}

.filter-empty {
  padding: var(--hs-space-12) var(--hs-space-16);
  color: var(--hs-text-secondary);
}

.filter-clear-item {
  color: rgb(var(--v-theme-primary));
  border-top: 1px solid var(--hs-border);
}
</style>
