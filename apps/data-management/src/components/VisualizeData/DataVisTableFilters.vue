<template>
  <div ref="container" class="datavis-header-filters">
    <!-- Filters that don't fit move into the "More filters" menu; their own
         menus then open from that button. -->
    <v-menu
      v-for="(filter, index) in filterDefinitions"
      :key="filter.key"
      :model-value="openFilter === filter.key"
      :target="index >= visibleCount ? '.datavis-filter-overflow' : undefined"
      :close-on-content-click="false"
      :location="index >= visibleCount ? 'bottom end' : 'bottom start'"
      attach="body"
      @update:model-value="openFilter = $event ? filter.key : null"
    >
      <template #activator="{ props: menuProps }">
        <v-btn
          v-bind="menuProps"
          variant="text"
          size="small"
          class="datavis-filter-button"
          :class="{
            'datavis-filter-button--active': filter.selectedCount > 0,
            'datavis-filter--hidden': index >= visibleCount,
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

    <v-menu location="bottom end" attach="body">
      <template #activator="{ props: menuProps }">
        <v-btn-icon
          v-bind="menuProps"
          :icon="mdiDotsVertical"
          size="small"
          class="datavis-filter-overflow"
          :class="{ 'datavis-filter--hidden': !overflowFilters.length }"
          aria-label="More filters"
        />
      </template>
      <v-list density="compact">
        <v-list-item
          v-for="filter in overflowFilters"
          :key="filter.key"
          :title="filter.label"
          @click="openFilter = filter.key"
        >
          <template v-if="filter.selectedCount" #append>
            <span class="filter-count">{{ filter.selectedCount }}</span>
          </template>
        </v-list-item>
      </v-list>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  useTemplateRef,
} from 'vue'
import { storeToRefs } from 'pinia'
import { mdiChevronDown, mdiDotsVertical, mdiMagnify } from '@mdi/js'
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

const {
  monitoringSites,
  observedProperties,
  processingLevels,
  units,
  methods,
  selectedMonitoringSites,
  selectedWorkspaces,
  selectedObservedPropertyNames,
  selectedUnitNames,
  selectedMethodNames,
  selectedProcessingLevelNames,
  tableSearch,
} = storeToRefs(useDataVisStore())
const { workspaces } = storeToRefs(useWorkspaceStore())

const filterSearches = reactive<Record<FilterKey, string>>({
  workspace: '',
  site: '',
  'observed-property': '',
  unit: '',
  method: '',
  'processing-level': '',
})

const parsedQuery = computed(() => parseDatastreamQuery(tableSearch.value))

const uniqueNames = (items: { name?: string | null }[]) =>
  [...new Set(items.map((item) => item.name).filter(Boolean) as string[])]
    .sort((a, b) => a.localeCompare(b))
    .map((name) => ({ value: name, label: name }))

// Sites are narrowed to the selected workspaces.
const siteOptions = computed(() => {
  const workspaceIds = new Set(selectedWorkspaces.value.map((item) => item.id))
  return uniqueNames(
    monitoringSites.value.filter(
      (site) => !workspaceIds.size || workspaceIds.has(site.workspaceId)
    )
  )
})

const filterDefinitions = computed<FilterDefinition[]>(() => [
  {
    key: 'workspace',
    label: 'Workspaces',
    options: uniqueNames(workspaces.value),
    selectedCount: selectedWorkspaces.value.length,
  },
  {
    key: 'site',
    label: 'Sites',
    options: siteOptions.value,
    selectedCount: selectedMonitoringSites.value.length,
  },
  {
    key: 'observed-property',
    label: 'Observed properties',
    options: uniqueNames(observedProperties.value),
    selectedCount: selectedObservedPropertyNames.value.length,
  },
  {
    key: 'unit',
    label: 'Units',
    options: uniqueNames(units.value),
    selectedCount: selectedUnitNames.value.length,
  },
  {
    key: 'method',
    label: 'Methods',
    options: uniqueNames(methods.value),
    selectedCount: selectedMethodNames.value.length,
  },
  {
    key: 'processing-level',
    label: 'Processing levels',
    options: uniqueNames(processingLevels.value),
    selectedCount: selectedProcessingLevelNames.value.length,
  },
])

const openFilter = ref<FilterKey | null>(null)
const container = useTemplateRef('container')
const visibleCount = ref(filterDefinitions.value.length)
const overflowFilters = computed(() =>
  filterDefinitions.value.slice(visibleCount.value)
)

// Show as many filters as fit, in order; the rest go in the overflow menu.
// Hidden buttons stay rendered (but invisible) so they can still be measured.
function fitFilters() {
  const element = container.value
  if (!element?.clientWidth) return
  const gap = parseFloat(getComputedStyle(element).columnGap) || 0
  const widths = [
    ...element.querySelectorAll<HTMLElement>('.datavis-filter-button'),
  ].map((button) => button.offsetWidth + gap)
  const fitsAll =
    widths.reduce((sum, width) => sum + width, 0) - gap <= element.clientWidth
  let room = fitsAll
    ? Infinity
    : element.clientWidth -
      (element.querySelector<HTMLElement>('.datavis-filter-overflow')
        ?.offsetWidth ?? 0)
  let count = 0
  for (const width of widths) {
    if (width > room) break
    room -= width
    count++
  }
  visibleCount.value = count
}

let observer: ResizeObserver | undefined
onMounted(() => {
  fitFilters()
  observer = new ResizeObserver(fitFilters)
  if (!container.value) return
  observer.observe(container.value)
  container.value
    .querySelectorAll('.datavis-filter-button')
    .forEach((button) => observer!.observe(button))
})
onBeforeUnmount(() => observer?.disconnect())

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
  position: relative;
  display: flex;
  flex: 1 1 0;
  gap: var(--hs-space-8);
  align-items: center;
  min-width: 0;
}

.datavis-filter-button {
  flex: 0 0 auto;
}

.datavis-filter-overflow {
  margin-left: auto;
}

/* Out of the layout and accessibility tree, but still measurable. */
.datavis-filter--hidden {
  position: absolute;
  visibility: hidden;
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
