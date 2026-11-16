<template>
  <div class="datavis-header-filters">
    <HsTableFilterMenu
      v-for="filter in filterDefinitions"
      :key="filter.key"
      v-model:search="filterSearches[filter.key]"
      :title="`Filter by ${filter.label}`"
      :label="filter.label"
      :options="filter.options"
      :selected="parsedQuery.filters[filter.key]"
      case-insensitive
      :empty-text="`No ${filter.label.toLowerCase()} found`"
      @toggle="toggleFilter(filter.key, $event)"
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
    </HsTableFilterMenu>
  </div>
</template>

<script setup lang="ts">
import { HsTableFilterMenu } from '@hydroserver/design-system/vue'
import { computed, reactive } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiChevronDown } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
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
  matchesSelectedUnit,
  matchesSelectedMethod,
  matchesSelectedProcessingLevel,
  matchesSelectedMonitoringSite,
  matchesSelectedWorkspace,
} = dataVisStore
const { monitoringSites, datastreams, tableSearch, workspaces } =
  storeToRefs(dataVisStore)

const filterSearches = reactive<Record<FilterKey, string>>({
  workspace: '',
  site: '',
  'observed-property': '',
  unit: '',
  method: '',
  'processing-level': '',
})

const parsedQuery = computed(() => parseDatastreamQuery(tableSearch.value))

const sortedWorkspaces = computed(() => {
  const workspaceIds = new Set<string>()
  datastreams.value.forEach((datastream) => {
    if (
      !matchesSelectedMonitoringSite(datastream) ||
      !matchesSelectedObservedProperty(datastream) ||
      !matchesSelectedUnit(datastream) ||
      !matchesSelectedMethod(datastream) ||
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
      !matchesSelectedUnit(datastream) ||
      !matchesSelectedMethod(datastream) ||
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
      !matchesSelectedUnit(datastream) ||
      !matchesSelectedMethod(datastream) ||
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
      !matchesSelectedUnit(datastream) ||
      !matchesSelectedMethod(datastream) ||
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

const sortedUnitNames = computed(() => {
  const names = new Set<string>()
  datastreams.value.forEach((datastream) => {
    if (
      !matchesSelectedMonitoringSite(datastream) ||
      !matchesSelectedObservedProperty(datastream) ||
      !matchesSelectedMethod(datastream) ||
      !matchesSelectedProcessingLevel(datastream) ||
      !matchesSelectedWorkspace(datastream)
    )
      return
    const name = (datastream as typeof datastream & { unitName?: string })
      .unitName
    if (name) names.add(name)
  })
  return [...names].sort()
})

const sortedMethodNames = computed(() => {
  const names = new Set<string>()
  datastreams.value.forEach((datastream) => {
    if (
      !matchesSelectedMonitoringSite(datastream) ||
      !matchesSelectedObservedProperty(datastream) ||
      !matchesSelectedUnit(datastream) ||
      !matchesSelectedProcessingLevel(datastream) ||
      !matchesSelectedWorkspace(datastream)
    )
      return
    const name = (datastream as typeof datastream & { methodName?: string })
      .methodName
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
    selectedCount: parsedQuery.value.filters.workspace.length,
  },
  {
    key: 'site',
    label: 'Sites',
    options: sortedMonitoringSites.value.map((item) => ({
      value: item.name,
      label: item.name,
    })),
    selectedCount: parsedQuery.value.filters.site.length,
  },
  {
    key: 'observed-property',
    label: 'Observed properties',
    options: sortedObservedPropertyNames.value.map((item) => ({
      value: item,
      label: item,
    })),
    selectedCount: parsedQuery.value.filters['observed-property'].length,
  },
  {
    key: 'unit',
    label: 'Units',
    options: sortedUnitNames.value.map((item) => ({
      value: item,
      label: item,
    })),
    selectedCount: parsedQuery.value.filters.unit.length,
  },
  {
    key: 'method',
    label: 'Methods',
    options: sortedMethodNames.value.map((item) => ({
      value: item,
      label: item,
    })),
    selectedCount: parsedQuery.value.filters.method.length,
  },
  {
    key: 'processing-level',
    label: 'Processing levels',
    options: sortedProcessingLevelNames.value.map((item) => ({
      value: item,
      label: item,
    })),
    selectedCount: parsedQuery.value.filters['processing-level'].length,
  },
])

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
</style>
