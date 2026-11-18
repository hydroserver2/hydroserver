<template>
  <div ref="container" class="datavis-header-filters">
    <!-- Filters that don't fit move into the "More filters" menu; their own
         menus then open from that button. -->
    <HsTableFilterMenu
      v-for="(filter, index) in filterDefinitions"
      :key="filter.key"
      v-model="openFilters[filter.key]"
      v-model:search="filterSearches[filter.key]"
      :target="index >= visibleCount ? '.datavis-filter-overflow' : undefined"
      :location="index >= visibleCount ? 'bottom end' : 'bottom start'"
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
    </HsTableFilterMenu>

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
          @click="openFilters[filter.key] = true"
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
import { mdiChevronDown, mdiDotsVertical } from '@mdi/js'
import { HsTableFilterMenu } from '@hydroserver/design-system/vue'
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
  workspaces,
} = storeToRefs(useDataVisStore())

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

const openFilters = reactive<Partial<Record<FilterKey, boolean>>>({})
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
</style>
