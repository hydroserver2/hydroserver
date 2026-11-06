<template>
  <section class="datastreams-panel" aria-labelledby="datastreams-heading">
    <div class="hs-table-tools datastreams-tools">
      <div class="datastreams-tools__primary">
        <div class="datastreams-heading">
          <h2 id="datastreams-heading" class="hs-subheading">Datastreams</h2>
          <span v-if="total !== null" class="datastreams-count hs-text-sm">
            {{ total }} available
          </span>
        </div>

        <div class="hs-table-actions datastreams-actions">
          <v-btn
            size="small"
            variant="text"
            :disabled="detailLevel === 1"
            data-testid="show-less-datastream-details"
            @click="detailLevel--"
          >
            Less detail
          </v-btn>
          <v-btn
            size="small"
            variant="text"
            :disabled="detailLevel === 2"
            data-testid="show-more-datastream-details"
            @click="detailLevel++"
          >
            More detail
          </v-btn>
        </div>
      </div>

      <div class="datastreams-search">
        <HsQuerySearchInput
          :model-value="search"
          placeholder="Search datastreams…"
          aria-label="Search"
          :qualifiers="searchQualifiers"
          @update:model-value="updateSearch"
          @clear="clearSearch"
        />
      </div>
    </div>

    <div class="hs-table-card datastreams-table-card">
      <v-data-table-virtual
        ref="table"
        class="datastreams-table hs-text-sm"
        :headers="columns"
        :items="tableItems"
        item-value="id"
        hide-default-header
        hide-no-data
      >
        <template #top>
          <div class="datastream-filter-header">
            <div class="datastream-filter-header__content">
              <DataVisTableFilters />

              <v-menu location="bottom end" attach="body">
                <template #activator="{ props: menuProps }">
                  <v-btn
                    v-bind="menuProps"
                    variant="text"
                    size="small"
                    class="datastream-sort-button"
                    :prepend-icon="mdiSort"
                    :append-icon="mdiChevronDown"
                    aria-label="Sort datastreams"
                    data-testid="datastream-sort-menu"
                  >
                    {{ sortButtonLabel }}
                  </v-btn>
                </template>

                <v-list class="datastream-sort-menu" density="comfortable">
                  <div class="datastream-sort-menu__title">Sort by</div>
                  <v-list-item
                    v-for="option in sortOptions"
                    :key="option.key"
                    :class="{
                      'datastream-sort-menu__item--selected':
                        activeSort.key === option.key,
                    }"
                    @click="setSortKey(option.key)"
                  >
                    <template #prepend>
                      <v-icon
                        :icon="mdiCheck"
                        :class="{
                          'datastream-sort-menu__check--hidden':
                            activeSort.key !== option.key,
                        }"
                      />
                    </template>
                    <v-list-item-title>{{ option.label }}</v-list-item-title>
                  </v-list-item>

                  <v-divider class="my-1" />

                  <div class="datastream-sort-menu__title">Order</div>
                  <v-list-item
                    v-for="option in sortOrderOptions"
                    :key="option.order"
                    :class="{
                      'datastream-sort-menu__item--selected':
                        activeSort.order === option.order,
                    }"
                    @click="setSortOrder(option.order)"
                  >
                    <template #prepend>
                      <v-icon
                        :icon="option.icon"
                        class="datastream-sort-menu__order-icon"
                      />
                    </template>
                    <v-list-item-title>{{ option.label }}</v-list-item-title>
                    <template #append>
                      <v-icon
                        :icon="mdiCheck"
                        :class="{
                          'datastream-sort-menu__check--hidden':
                            activeSort.order !== option.order,
                        }"
                      />
                    </template>
                  </v-list-item>
                </v-list>
              </v-menu>
            </div>
          </div>
          <div
            v-if="plottedDatastreams.length"
            class="datastream-selection-header"
            data-testid="datastream-selection-bar"
          >
            <div class="datastream-selection-header__content">
              <div class="datastream-selection-summary">
                <input
                  type="checkbox"
                  class="plot-checkbox datastreams-clear-selection-checkbox"
                  :indeterminate="true"
                  aria-label="Clear selected datastreams"
                  data-testid="clear-selected-datastreams"
                  @change="clearSelected"
                />
                <span> {{ plottedDatastreams.length }} of 5 selected </span>
              </div>

              <div class="datastream-selection-actions">
                <v-btn
                  size="small"
                  variant="text"
                  data-testid="toggle-selected-datastreams"
                  @click="showOnlySelected = !showOnlySelected"
                >
                  {{ showOnlySelected ? 'Show all' : 'Show selected' }}
                </v-btn>

                <v-btn
                  size="small"
                  variant="text"
                  :loading="downloading"
                  :prepend-icon="mdiDownload"
                  data-testid="download-selected-datastreams"
                  @click="downloadSelected(plottedDatastreams)"
                >
                  Download selected
                </v-btn>
              </div>
            </div>
          </div>
        </template>

        <template #item="{ item, itemRef }">
          <tr :ref="itemRef">
            <td class="datastream-plot-cell">
              <input
                type="checkbox"
                class="plot-checkbox"
                :checked="isChecked(item)"
                :disabled="plottedDatastreams.length >= 5 && !isChecked(item)"
                :aria-label="`Plot ${item.name || 'datastream'}`"
                :data-testid="`plot-datastream-${item.id}`"
                @click.stop
                @change="onPlotChange(item, $event)"
              />
            </td>

            <td class="datastream-summary-cell">
              <div class="datastream-name" :title="datastreamDisplayName(item)">
                <span class="datastream-name__primary">
                  {{ datastreamName(item) }}
                </span>
                <span
                  v-if="showMonitoringSiteContext && item.monitoringSiteName"
                  class="datastream-name__separator"
                  aria-hidden="true"
                >
                  @
                </span>
                <span
                  v-if="showMonitoringSiteContext && item.monitoringSiteName"
                  class="datastream-name__thing"
                >
                  {{ item.monitoringSiteName }}
                </span>
              </div>
              <div
                v-if="detailLevel >= 2"
                class="datastream-meta datastream-observation-range hs-text-sm"
              >
                {{ observationRange(item) }}
              </div>
            </td>

            <td class="datastream-actions-cell">
              <div class="datastream-row-actions">
                <v-btn
                  variant="text"
                  size="small"
                  color="primary"
                  :append-icon="mdiChevronRight"
                  class="datastream-details-button"
                  :aria-label="`View details for ${item.name || 'datastream'}`"
                  :data-testid="`datavis-metadata-${item.id}`"
                  @click.stop="openMetadata(item)"
                >
                  <span class="datastream-details-button__label">Details</span>
                </v-btn>

                <v-menu location="bottom end" attach="body">
                  <template #activator="{ props: menuProps }">
                    <v-btn-icon
                      v-bind="menuProps"
                      :icon="mdiDotsVertical"
                      size="small"
                      :aria-label="`Actions for ${datastreamName(item)}`"
                      :data-testid="`datavis-actions-${item.id}`"
                    />
                  </template>

                  <v-list>
                    <v-list-item
                      :prepend-icon="mdiMapMarkerOutline"
                      title="View on site details page"
                      :data-testid="`datavis-view-site-${item.id}`"
                      :to="{
                        name: 'SiteDetails',
                        params: { id: item.monitoringSiteId },
                        query: { datastream: item.id },
                      }"
                    />
                  </v-list>
                </v-menu>
              </div>
            </td>
          </tr>
        </template>

        <template #tbody="{ columns }">
          <LoadMoreRow
            v-if="!showOnlySelected"
            :colspan="columns.length"
            :has-more="hasMore"
            :loading="loading"
            :error="error"
            @load="loadMore"
            @retry="retry"
          />
          <tbody v-if="total === 0 && !showOnlySelected">
            <tr>
              <td colspan="3" class="datastreams-empty hs-text-sm">
                No datastreams match the current filters.
              </td>
            </tr>
          </tbody>
        </template>
      </v-data-table-virtual>
    </div>

    <v-dialog
      v-if="selectedDatastream && selectedMonitoringSite"
      v-model="openInfoCard"
      width="50rem"
    >
      <DatastreamInformationCard
        :datastream="selectedDatastream"
        :monitoringSite="selectedMonitoringSite"
        @close="openInfoCard = false"
      />
    </v-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import hs, { Datastream, MonitoringSite } from '@hydroserver/client'
import {
  mdiArrowDown,
  mdiArrowUp,
  mdiCheck,
  mdiChevronDown,
  mdiChevronRight,
  mdiDownload,
  mdiDotsVertical,
  mdiMapMarkerOutline,
  mdiSort,
} from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import { useWorkspaceStore } from '@/store/workspaces'
import { downloadDatastreamsCsvZip } from '@/utils/csvExport'
import { formatTime } from '@/utils/time'
import {
  parseDatastreamQuery,
  serializeDatastreamQuery,
  type DatastreamQueryFilters,
  type DatastreamSort,
  type DatastreamSortKey,
  type DatastreamSortOrder,
} from '@/utils/datastreamSearch'
import { HsQuerySearchInput } from '@hydroserver/design-system/vue'
import LoadMoreRow from '@/components/base/LoadMoreRow.vue'
import { usePagedList } from '@/composables/usePagedList'
import DatastreamInformationCard from './DatastreamInformationCard.vue'
import DataVisTableFilters from './DataVisTableFilters.vue'

type DatastreamTableItem = Datastream & { monitoringSiteName?: string }

const dataVisStore = useDataVisStore()
const {
  plottedDatastreams,
  datastreamFilters,
  tableSearch: search,
  datastreamDetailLevel: detailLevel,
  monitoringSites,
  selectedMonitoringSites,
  selectedWorkspaces,
  selectedObservedPropertyNames,
  selectedUnitNames,
  selectedMethodNames,
  selectedProcessingLevelNames,
  observedProperties,
  processingLevels,
  units,
  methods,
} = storeToRefs(dataVisStore)
const { workspaces } = storeToRefs(useWorkspaceStore())

const initialFilters: DatastreamQueryFilters = {
  workspace: selectedWorkspaces.value.map((item) => item.name),
  site: selectedMonitoringSites.value.map((item) => item.name),
  'observed-property': [...selectedObservedPropertyNames.value],
  unit: [...selectedUnitNames.value],
  method: [...selectedMethodNames.value],
  'processing-level': [...selectedProcessingLevelNames.value],
}
if (!search.value.trim()) {
  search.value = serializeDatastreamQuery(initialFilters, '')
}

const openInfoCard = ref(false)
const downloading = ref(false)
const selectedDatastream = ref<Datastream | null>(null)
const selectedMonitoringSite = ref<MonitoringSite | null>(null)

const uniqueSorted = (values: Array<string | null | undefined>) =>
  [...new Set(values.filter((value): value is string => Boolean(value)))].sort(
    (a, b) => a.localeCompare(b)
  )
const searchQualifiers = computed(() => [
  {
    key: 'workspace',
    label: 'Workspaces',
    values: uniqueSorted(workspaces.value.map((item) => item.name)),
  },
  {
    key: 'site',
    label: 'Sites',
    values: uniqueSorted(monitoringSites.value.map((item) => item.name)),
  },
  {
    key: 'observed-property',
    label: 'Observed properties',
    values: uniqueSorted(observedProperties.value.map((item) => item.name)),
  },
  {
    key: 'unit',
    label: 'Units',
    values: uniqueSorted(units.value.map((item) => item.name)),
  },
  {
    key: 'method',
    label: 'Methods',
    values: uniqueSorted(methods.value.map((item) => item.name)),
  },
  {
    key: 'processing-level',
    label: 'Processing levels',
    values: uniqueSorted(processingLevels.value.map((item) => item.name)),
  },
  {
    key: 'sort',
    label: 'Sort',
    values: [
      'name-asc',
      'name-desc',
      'updated-asc',
      'updated-desc',
      'observations-asc',
      'observations-desc',
    ],
  },
])
const parsedSearch = computed(() =>
  parseDatastreamQuery(search.value, searchQualifiers.value)
)
const plainSearch = computed(() => parsedSearch.value.text)

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

// The filter controls are replaced by the selection summary while a
// datastream is plotted, so keep query hydration in this always-mounted table.
watch(
  search,
  () => {
    const { filters } = parsedSearch.value
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
    selectedUnitNames.value = canonicalValues(
      units.value.map((item) => item.name),
      filters.unit
    )
    selectedMethodNames.value = canonicalValues(
      methods.value.map((item) => item.name),
      filters.method
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

const defaultSort: DatastreamSort = { key: 'name', order: 'asc' }
const activeSort = computed(() => parsedSearch.value.sort ?? defaultSort)
const sortOptions = computed(() => [
  {
    key: 'name' as const,
    label: 'Datastream name',
  },
  { key: 'updated' as const, label: 'Last updated' },
  { key: 'observations' as const, label: 'Observation count' },
])
const sortButtonLabel = computed(() => {
  const option = sortOptions.value.find(
    (candidate) => candidate.key === activeSort.value.key
  )
  return option?.label ?? 'Sort'
})
const sortOrderOptions = computed(() => {
  if (activeSort.value.key === 'name') {
    return [
      { order: 'asc' as const, label: 'A–Z', icon: mdiArrowUp },
      { order: 'desc' as const, label: 'Z–A', icon: mdiArrowDown },
    ]
  }

  if (activeSort.value.key === 'updated') {
    return [
      { order: 'asc' as const, label: 'Oldest', icon: mdiArrowUp },
      { order: 'desc' as const, label: 'Newest', icon: mdiArrowDown },
    ]
  }

  return [
    { order: 'asc' as const, label: 'Least observations', icon: mdiArrowUp },
    { order: 'desc' as const, label: 'Most observations', icon: mdiArrowDown },
  ]
})

const defaultSortOrder = (key: DatastreamSortKey): DatastreamSortOrder =>
  key === 'name' ? 'asc' : 'desc'

const updateSort = (sort: DatastreamSort) => {
  search.value = serializeDatastreamQuery(
    parsedSearch.value.filters,
    parsedSearch.value.text,
    sort
  )
}

const setSortKey = (key: DatastreamSortKey) => {
  updateSort({
    key,
    order:
      activeSort.value.key === key
        ? activeSort.value.order
        : defaultSortOrder(key),
  })
}

const setSortOrder = (order: DatastreamSortOrder) => {
  updateSort({ key: activeSort.value.key, order })
}

const sortFields = {
  name: 'name',
  updated: 'phenomenonEndTime',
  observations: 'valueCount',
} as const

const { items, total, loading, error, hasMore, loadMore, retry } = usePagedList(
  () => ({
    ...datastreamFilters.value,
    q: plainSearch.value || undefined,
    sortby: [
      `${activeSort.value.order === 'desc' ? '-' : ''}${sortFields[activeSort.value.key]}` as const,
    ],
  }),
  (query, page) => hs.datastreams.list({ ...query, ...page })
)

// Selected datastreams are pinned above the results each time the results
// restart, so they survive filter changes without jumping when checked.
const pinned = ref([...plottedDatastreams.value])
const table = useTemplateRef('table')
watch(total, (value) => {
  if (value !== null) return
  pinned.value = [...plottedDatastreams.value]
  table.value?.scrollToIndex(0)
})
// "Show selected" hides every row that isn't currently selected.
const showOnlySelected = ref(false)
watch(showOnlySelected, () => table.value?.scrollToIndex(0))
watch(
  () => plottedDatastreams.value.length,
  (count) => {
    if (!count) showOnlySelected.value = false
  }
)
const tableItems = computed<DatastreamTableItem[]>(() => {
  const pinnedIds = new Set(pinned.value.map((item) => item.id))
  const rows = showOnlySelected.value
    ? plottedDatastreams.value
    : [
        ...pinned.value,
        ...items.value.filter((item) => !pinnedIds.has(item.id)),
      ]
  return rows.map((datastream) => ({
    ...datastream,
    monitoringSiteName: dataVisStore.monitoringSiteById.get(
      datastream.monitoringSiteId
    )?.name,
  }))
})

const columns = [{ key: 'plot' }, { key: 'summary' }, { key: 'actions' }]

const showMonitoringSiteContext = computed(
  () => selectedMonitoringSites.value.length !== 1
)

const datastreamName = (item: DatastreamTableItem) =>
  item.name?.trim() || 'Unnamed datastream'

const datastreamDisplayName = (item: DatastreamTableItem) => {
  const name = datastreamName(item)
  return showMonitoringSiteContext.value && item.monitoringSiteName
    ? `${name} @ ${item.monitoringSiteName}`
    : name
}

const downloadSelected = async (datastreams: Datastream[]) => {
  downloading.value = true
  try {
    await downloadDatastreamsCsvZip(datastreams)
  } catch (error) {
    console.error('Error downloading selected datastreams', error)
  } finally {
    downloading.value = false
  }
}

const clearSelected = () => {
  plottedDatastreams.value = []
}

const updateSearch = (value: string) => {
  search.value = value
}

const clearSearch = () => {
  search.value = ''
  selectedWorkspaces.value = []
  selectedMonitoringSites.value = []
  selectedObservedPropertyNames.value = []
  selectedUnitNames.value = []
  selectedMethodNames.value = []
  selectedProcessingLevelNames.value = []
}

const isChecked = (item: Datastream) =>
  plottedDatastreams.value.some((selected) => selected.id === item.id)

const openMetadata = (item: Datastream) => {
  selectedMonitoringSite.value =
    dataVisStore.monitoringSiteById.get(item.monitoringSiteId) ?? null
  selectedDatastream.value = item
  openInfoCard.value = Boolean(
    selectedDatastream.value && selectedMonitoringSite.value
  )
}

const formatObservationCount = (value: number | string | null | undefined) => {
  const count = Number(value)
  return Number.isFinite(count) ? count.toLocaleString() : '—'
}

const observationRange = (item: DatastreamTableItem) => {
  const count = Number(item.valueCount)
  const observationLabel = count === 1 ? 'observation' : 'observations'
  if (count === 0) return '0 observations'
  return [
    `${formatObservationCount(item.valueCount)} ${observationLabel} between`,
    formatTime(item.phenomenonBeginTime),
    'and',
    formatTime(item.phenomenonEndTime),
  ].join(' ')
}

const onPlotChange = (datastream: Datastream, event: Event) => {
  updatePlottedDatastreams(
    datastream,
    (event.target as HTMLInputElement).checked
  )
}

function updatePlottedDatastreams(
  datastream: Datastream,
  selected: boolean | null
) {
  const index = plottedDatastreams.value.findIndex(
    (item) => item.id === datastream.id
  )
  if (selected && index === -1) {
    if (plottedDatastreams.value.length >= 5) return
    plottedDatastreams.value.push(datastream)
  } else if (!selected && index !== -1) {
    plottedDatastreams.value.splice(index, 1)
  }
}
</script>

<style scoped>
.datastreams-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.datastreams-tools {
  flex-direction: column;
  align-items: stretch;
  margin: 0 0 var(--hs-space-10);
}

.datastreams-tools__primary {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.datastreams-heading {
  display: flex;
  flex-shrink: 0;
  gap: var(--hs-space-8);
  align-items: baseline;
}

.datastreams-heading h2 {
  margin: 0;
  color: var(--hs-text-primary);
}

.datastreams-count {
  color: var(--hs-text-secondary);
  white-space: nowrap;
}

.datastreams-search {
  width: 100%;
  margin-left: 0 !important;
}

.datastreams-search :deep(.hs-query-search) {
  width: 100%;
  max-width: none;
}

.datastream-sort-button {
  color: var(--hs-text-primary);
  text-transform: none;
}

.datastream-sort-menu {
  min-width: 270px;
  padding: var(--hs-space-8) 0;
  border: 1px solid var(--hs-border);
}

.datastream-sort-menu__title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-semibold);
}

.datastream-sort-menu :deep(.v-list-item) {
  min-height: 40px;
  padding-inline: var(--hs-space-16);
}

.datastream-sort-menu__item--selected :deep(.v-list-item-title) {
  font-weight: var(--hs-font-weight-semibold);
}

.datastream-sort-menu__check--hidden {
  visibility: hidden;
}

.datastream-sort-menu__order-icon {
  color: var(--hs-text-secondary);
}

.datastreams-actions {
  margin-left: auto;
}

/* Sized to its rows, scrolling only once they outgrow the panel. */
.datastreams-table-card,
.datastreams-table {
  display: flex;
  flex: 0 1 auto;
  flex-direction: column;
  min-height: 0;
}

.datastreams-table-card {
  overflow: hidden;
}

.datastreams-table {
  background: transparent;
}

.datastreams-table :deep(.v-table__wrapper) {
  flex: 0 1 auto;
  min-height: 0;
}

.datastream-filter-header,
.datastream-selection-header {
  padding: var(--hs-space-8) var(--hs-space-12);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  background: var(--hs-surface-muted);
  border-bottom: 1px solid var(--hs-border);
}

.datastream-filter-header {
  padding: var(--hs-space-12);
}

.datastream-filter-header__content {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
  justify-content: space-between;
}

.datastream-selection-header__content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--hs-text-primary);
  font-weight: var(--hs-font-weight-semibold);
}

.datastream-selection-summary,
.datastream-selection-actions {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
}

.datastream-selection-actions {
  font-weight: var(--hs-font-weight-regular);
}

.datastreams-clear-selection-checkbox {
  flex: 0 0 auto;
  margin: 0;
}

.datastreams-table tbody tr {
  border-bottom: 1px solid var(--hs-border);
}

.datastreams-table tbody tr {
  cursor: default;
}

.datastreams-table tbody tr:hover {
  background: var(--hs-surface-muted);
}

.datastream-plot-cell {
  width: 32px;
  padding: var(--hs-space-12) 0 var(--hs-space-12) var(--hs-space-12);
  vertical-align: top;
}

.datastream-summary-cell {
  padding: var(--hs-space-12) var(--hs-space-12) var(--hs-space-12) 4px;
  vertical-align: top;
}

.datastream-actions-cell {
  width: 1%;
  padding: var(--hs-space-12);
  vertical-align: top;
  text-align: right;
  white-space: nowrap;
}

.datastream-row-actions {
  display: flex;
  gap: var(--hs-space-4);
  align-items: center;
  justify-content: flex-end;
}

.plot-checkbox {
  display: block;
  width: 16px;
  height: 16px;
  margin: var(--hs-space-6) 0 0;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}

.plot-checkbox:disabled {
  cursor: not-allowed;
}

.datastream-name {
  display: flex;
  gap: var(--hs-space-6);
  align-items: center;
  min-height: 28px;
  max-width: 100%;
  padding: 0;
  overflow: hidden;
  color: var(--hs-text-primary);
  font-family: inherit;
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
  line-height: 1.3;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: transparent;
  border: 0;
}

.datastream-name__thing {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 40%;
  overflow: hidden;
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-regular);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.datastream-name__separator {
  flex: 0 0 auto;
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-regular);
}

.datastream-name__primary {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.datastream-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-4) var(--hs-space-12);
  align-items: center;
  margin-top: var(--hs-space-4);
  color: var(--hs-text-secondary);
}

.datastream-observation-range {
  font-family: var(--hs-font-data);
  line-height: 1.4;
}

.datastream-details-button {
  min-height: 28px;
  text-transform: none;
}

.datastreams-empty {
  padding: var(--hs-space-24);
  color: var(--hs-text-secondary);
  text-align: center;
}

@media (max-width: 600px) {
  .datastreams-panel {
    min-height: 520px;
  }

  .datastreams-heading {
    justify-content: space-between;
  }

  .datastreams-tools__primary {
    flex-direction: column;
    align-items: stretch;
  }

  .datastream-plot-cell {
    width: 28px;
    padding-left: var(--hs-space-8);
  }

  .datastream-actions-cell {
    width: 48px;
    padding-right: var(--hs-space-8);
  }

  .datastream-details-button {
    min-width: 32px;
    width: 32px;
    padding: 0;
  }

  .datastream-details-button__label {
    display: none;
  }

  .datastream-meta {
    flex-direction: column;
    gap: var(--hs-space-2);
    align-items: flex-start;
  }

  .datastream-name {
    white-space: normal;
  }

  .datastream-name__thing,
  .datastream-name__primary {
    white-space: normal;
  }

  .datastream-selection-header__content {
    gap: var(--hs-space-8);
  }

  .datastream-selection-actions {
    gap: var(--hs-space-4);
  }

  .datastream-selection-actions :deep(.v-btn) {
    min-width: auto;
    padding: 0 var(--hs-space-8);
  }
}
</style>
