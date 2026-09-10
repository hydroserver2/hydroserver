<template>
  <v-card class="datastream-selector-card">
    <v-toolbar color="primary-darken-2"
      ><v-card-title>{{ cardTitle }}</v-card-title></v-toolbar
    >
    <v-card-text class="datastream-selector-card__content">
      <div class="hs-table-tools datastream-selector-tools">
        <div class="datastream-selector-tools__primary">
          <div class="datastream-selector-heading">
            <h2 class="hs-subheading">Datastreams</h2>
            <span class="hs-text-sm datastream-selector-count"
              >{{ visibleDatastreams.length }} available</span
            >
          </div>
          <div class="hs-table-actions">
            <v-checkbox
              v-if="enforceUniqueSelections"
              v-model="showLinkedDatastreams"
              color="primary"
              label="Show already linked"
              hide-details
              density="compact"
            />
            <v-btn
              size="small"
              variant="text"
              :disabled="detailLevel === 1"
              @click="detailLevel--"
              >Less detail</v-btn
            >
            <v-btn
              size="small"
              variant="text"
              :disabled="detailLevel === 2"
              @click="detailLevel++"
              >More detail</v-btn
            >
          </div>
        </div>
        <HsQuerySearchInput
          :model-value="search"
          placeholder="Search datastreams…"
          aria-label="Search datastreams"
          :qualifiers="searchQualifiers"
          @update:model-value="updateSearch"
          @clear="clearSearch"
        />
      </div>
      <div class="hs-table-card datastream-selector-table-card">
        <table class="datastream-selector-table hs-text-sm">
          <thead>
            <tr>
              <th colspan="2" class="datastream-filter-header">
                <div class="datastream-filter-header__content">
                  <div class="datastream-header-filters">
                    <v-menu
                      v-for="filter in filterDefinitions"
                      :key="filter.key"
                      :close-on-content-click="false"
                      location="bottom start"
                      attach="body"
                    >
                      <template #activator="{ props: menuProps }"
                        ><v-btn
                          v-bind="menuProps"
                          variant="text"
                          size="small"
                          :class="{
                            'datastream-filter-button--active':
                              filter.selectedCount > 0,
                          }"
                          :append-icon="mdiChevronDown"
                          >{{ filter.label }}
                          <span
                            v-if="filter.selectedCount"
                            class="filter-count"
                            >{{ filter.selectedCount }}</span
                          ></v-btn
                        ></template
                      >
                      <v-list class="datastream-filter-menu" density="compact">
                        <div class="datastream-filter-title">
                          Filter by {{ filter.label }}
                        </div>
                        <v-text-field
                          v-model="filterSearches[filter.key]"
                          class="datastream-filter-search"
                          :placeholder="`Filter ${filter.label.toLowerCase()}`"
                          :prepend-inner-icon="mdiMagnify"
                          density="compact"
                          hide-details
                          clearable
                        />
                        <v-list-item
                          v-for="option in filteredOptions(filter)"
                          :key="option.value"
                          @click="toggleFilter(filter.key, option.value)"
                        >
                          <template #prepend
                            ><v-checkbox
                              :model-value="
                                isFilterSelected(filter.key, option.value)
                              "
                              hide-details
                              density="compact"
                              @click.stop="
                                toggleFilter(filter.key, option.value)
                              "
                          /></template>
                          <v-list-item-title>{{
                            option.label
                          }}</v-list-item-title>
                        </v-list-item>
                        <v-list-item
                          v-if="filter.selectedCount"
                          class="filter-clear-item"
                          @click="clearFilter(filter.key)"
                          ><v-list-item-title
                            >Clear filter</v-list-item-title
                          ></v-list-item
                        >
                        <div
                          v-if="!filteredOptions(filter).length"
                          class="filter-empty"
                        >
                          No {{ filter.label.toLowerCase() }} found
                        </div>
                      </v-list>
                    </v-menu>
                  </div>
                  <v-menu location="bottom end" attach="body">
                    <template #activator="{ props: menuProps }"
                      ><v-btn
                        v-bind="menuProps"
                        variant="text"
                        size="small"
                        :prepend-icon="mdiSort"
                        :append-icon="mdiChevronDown"
                        class="datastream-sort-button"
                        >{{ sortButtonLabel }}</v-btn
                      ></template
                    >
                    <v-list class="datastream-sort-menu" density="comfortable">
                      <div class="datastream-sort-menu__title">Sort by</div>
                      <v-list-item
                        v-for="option in sortOptions"
                        :key="option.key"
                        @click="setSortKey(option.key)"
                        ><template #prepend
                          ><v-icon
                            :icon="mdiCheck"
                            :class="{
                              'datastream-sort-menu__check--hidden':
                                activeSort.key !== option.key,
                            }" /></template
                        ><v-list-item-title>{{
                          option.label
                        }}</v-list-item-title></v-list-item
                      >
                      <v-divider class="my-1" />
                      <div class="datastream-sort-menu__title">Order</div>
                      <v-list-item
                        v-for="option in sortOrderOptions"
                        :key="option.order"
                        @click="setSortOrder(option.order)"
                        ><template #prepend
                          ><v-icon :icon="option.icon" /></template
                        ><v-list-item-title>{{
                          option.label
                        }}</v-list-item-title
                        ><template #append
                          ><v-icon
                            :icon="mdiCheck"
                            :class="{
                              'datastream-sort-menu__check--hidden':
                                activeSort.order !== option.order,
                            }" /></template
                      ></v-list-item>
                    </v-list>
                  </v-menu>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="datastream in visibleDatastreams"
              :key="datastream.id"
              :class="{
                'datastream-selector-row--linked': isLinked(datastream),
              }"
              @click="onDatastreamClick(datastream)"
            >
              <td class="datastream-summary-cell">
                <div
                  class="datastream-name"
                  :title="datastreamDisplayName(datastream)"
                >
                  <span class="datastream-name__primary">{{
                    datastreamName(datastream)
                  }}</span>
                  <template
                    v-if="
                      showMonitoringSiteContext &&
                      monitoringSiteName(datastream)
                    "
                    ><span class="datastream-name__separator" aria-hidden="true"
                      >@</span
                    ><span class="datastream-name__thing">{{
                      monitoringSiteName(datastream)
                    }}</span></template
                  >
                </div>
                <div
                  v-if="detailLevel >= 2"
                  class="datastream-observation-range hs-text-sm"
                >
                  {{ observationRange(datastream) }}
                </div>
              </td>
              <td class="datastream-actions-cell">
                <v-btn
                  variant="text"
                  size="small"
                  color="primary"
                  :append-icon="mdiChevronRight"
                  @click.stop="openDetails(datastream)"
                  >Details</v-btn
                >
              </td>
            </tr>
            <tr v-if="!visibleDatastreams.length">
              <td colspan="2" class="datastreams-empty hs-text-sm">
                No datastreams match the current filters.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </v-card-text>
    <v-card-actions
      ><v-spacer /><v-btn-cancel @click="$emit('close')"
        >Cancel</v-btn-cancel
      ></v-card-actions
    >
  </v-card>
  <v-dialog v-if="selectedDatastream" v-model="detailsOpen" width="50rem"
    ><v-card
      ><v-toolbar flat color="surface-subtle"
        ><v-card-title class="datastream-details-title">{{
          datastreamDisplayName(selectedDatastream)
        }}</v-card-title
        ><v-spacer /><v-btn-icon
          :icon="mdiClose"
          aria-label="Close datastream details"
          @click="detailsOpen = false" /></v-toolbar
      ><DatastreamInformationPanels
        :datastream-id="selectedDatastream.id"
      /><v-card-actions
        ><v-spacer /><v-btn-cancel @click="detailsOpen = false"
          >Close</v-btn-cancel
        ></v-card-actions
      ></v-card
    ></v-dialog
  >
  <v-dialog width="40rem" v-model="openLinkConflictModal"
    ><v-card
      ><v-toolbar color="yellow-darken-2"
        ><v-card-title class="text-medium-emphasis"
          ><v-icon :icon="mdiAlert" class="mr-2" /> Conflicting
          links</v-card-title
        ></v-toolbar
      ><v-card-text
        >This datastream is already being linked to another data connection in
        the Task form.</v-card-text
      ><v-card-actions
        ><v-spacer /><v-btn-cancel @click="openLinkConflictModal = false"
          >Cancel</v-btn-cancel
        ></v-card-actions
      ></v-card
    ></v-dialog
  >
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import type {
  Datastream,
  DatastreamExtended,
  MonitoringSite,
  Workspace,
} from '@hydroserver/client'
import hs from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import {
  mdiAlert,
  mdiArrowDown,
  mdiArrowUp,
  mdiCheck,
  mdiChevronDown,
  mdiChevronRight,
  mdiClose,
  mdiMagnify,
  mdiSort,
} from '@mdi/js'
import { HsQuerySearchInput } from '@hydroserver/design-system/vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'
import { formatTime } from '@/utils/time'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'
import {
  parseDatastreamQuery,
  serializeDatastreamQuery,
  type DatastreamQualifierKey,
  type DatastreamQueryFilters,
  type DatastreamSort,
  type DatastreamSortKey,
  type DatastreamSortOrder,
} from '@/utils/datastreamSearch'
import DatastreamInformationPanels from './DatastreamInformationPanels.vue'

type SelectorDatastream = Datastream & Record<string, any>
type FilterOption = { value: string; label: string }
type FilterDefinition = {
  key: DatastreamQualifierKey
  label: string
  options: FilterOption[]
  selectedCount: number
}
const props = withDefaults(
  defineProps<{
    cardTitle: string
    workspace?: Workspace
    datastreams?: Datastream[]
    monitoringSites?: MonitoringSite[]
    workspaceId?: string | null
    monitoringSiteId?: string | null
    enforceUniqueSelections?: boolean
    draftDatastreams?: DatastreamExtended[]
  }>(),
  {
    datastreams: undefined,
    monitoringSites: undefined,
    workspaceId: null,
    monitoringSiteId: null,
    enforceUniqueSelections: false,
    draftDatastreams: undefined,
  }
)
const emit = defineEmits<{
  (e: 'selectedDatastream', datastream: DatastreamExtended): void
  (e: 'close'): void
}>()
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const { linkedDatastreamIds } = storeToRefs(useOrchestrationStore())
const fetchedDatastreams = ref<Datastream[]>([]),
  fetchedMonitoringSites = ref<MonitoringSite[]>([]),
  search = ref(''),
  detailLevel = ref(1),
  showLinkedDatastreams = ref(!props.enforceUniqueSelections),
  detailsOpen = ref(false),
  selectedDatastream = ref<Datastream | null>(null),
  openLinkConflictModal = ref(false)
const filterSearches = reactive<Record<DatastreamQualifierKey, string>>({
  workspace: '',
  site: '',
  'observed-property': '',
  'processing-level': '',
})
const activeWorkspaceId = computed(
  () =>
    props.workspaceId ??
    props.workspace?.id ??
    selectedWorkspace.value?.id ??
    null
)
const availableDatastreams = computed(
  () => props.datastreams ?? fetchedDatastreams.value
)
const availableMonitoringSites = computed(
  () => props.monitoringSites ?? fetchedMonitoringSites.value
)
const monitoringSiteById = computed(
  () => new Map(availableMonitoringSites.value.map((site) => [site.id, site]))
)
const parsedSearch = computed(() => parseDatastreamQuery(search.value)),
  plainSearch = computed(() => parsedSearch.value.text.toLocaleLowerCase())
const scopedDatastreams = computed(() =>
  availableDatastreams.value.filter(
    (datastream) =>
      (!props.monitoringSiteId ||
        datastreamMonitoringSiteId(datastream) === props.monitoringSiteId) &&
      (!props.workspaceId ||
        datastreamWorkspaceId(datastream) === props.workspaceId)
  )
)
const filteredDatastreams = computed(() =>
  scopedDatastreams.value.filter((datastream) => {
    const filters = parsedSearch.value.filters
    return (
      !(
        props.enforceUniqueSelections &&
        !showLinkedDatastreams.value &&
        isLinked(datastream)
      ) &&
      matchesFilter(filters.workspace, workspaceName(datastream)) &&
      matchesFilter(filters.site, monitoringSiteName(datastream)) &&
      matchesFilter(
        filters['observed-property'],
        observedPropertyName(datastream)
      ) &&
      matchesFilter(
        filters['processing-level'],
        processingLevelName(datastream)
      )
    )
  })
)
const showMonitoringSiteContext = computed(
  () =>
    new Set(
      filteredDatastreams.value.map(datastreamMonitoringSiteId).filter(Boolean)
    ).size !== 1
)
const visibleDatastreams = computed(() =>
  filteredDatastreams.value
    .filter((datastream) => matchesPlainSearch(datastream, plainSearch.value))
    .sort(compareDatastreams)
)
const uniqueSorted = (values: Array<string | null | undefined>) =>
  [...new Set(values.filter((value): value is string => Boolean(value)))].sort(
    (a, b) => a.localeCompare(b)
  )
const searchQualifiers = computed(() => [
  {
    key: 'workspace',
    label: 'Workspaces',
    values: uniqueSorted(scopedDatastreams.value.map(workspaceName)),
  },
  {
    key: 'site',
    label: 'Sites',
    values: uniqueSorted(scopedDatastreams.value.map(monitoringSiteName)),
  },
  {
    key: 'observed-property',
    label: 'Observed properties',
    values: uniqueSorted(scopedDatastreams.value.map(observedPropertyName)),
  },
  {
    key: 'processing-level',
    label: 'Processing levels',
    values: uniqueSorted(scopedDatastreams.value.map(processingLevelName)),
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
const filterDefinitions = computed<FilterDefinition[]>(() => [
  {
    key: 'workspace',
    label: 'Workspaces',
    options: uniqueSorted(scopedDatastreams.value.map(workspaceName)).map(
      option
    ),
    selectedCount: parsedSearch.value.filters.workspace.length,
  },
  {
    key: 'site',
    label: 'Sites',
    options: uniqueSorted(scopedDatastreams.value.map(monitoringSiteName)).map(
      option
    ),
    selectedCount: parsedSearch.value.filters.site.length,
  },
  {
    key: 'observed-property',
    label: 'Observed properties',
    options: uniqueSorted(
      scopedDatastreams.value.map(observedPropertyName)
    ).map(option),
    selectedCount: parsedSearch.value.filters['observed-property'].length,
  },
  {
    key: 'processing-level',
    label: 'Processing levels',
    options: uniqueSorted(scopedDatastreams.value.map(processingLevelName)).map(
      option
    ),
    selectedCount: parsedSearch.value.filters['processing-level'].length,
  },
])
const defaultSort: DatastreamSort = { key: 'name', order: 'asc' }
const activeSort = computed(() => parsedSearch.value.sort ?? defaultSort)
const sortOptions = computed(() => [
  {
    key: 'name' as const,
    label: showMonitoringSiteContext.value
      ? 'Site name, datastream name'
      : 'Datastream name',
  },
  { key: 'updated' as const, label: 'Last updated' },
  { key: 'observations' as const, label: 'Observation count' },
])
const sortButtonLabel = computed(
  () =>
    sortOptions.value.find((option) => option.key === activeSort.value.key)
      ?.label ?? 'Sort'
)
const sortOrderOptions = computed(() =>
  activeSort.value.key === 'name'
    ? [
        { order: 'asc' as const, label: 'A–Z', icon: mdiArrowUp },
        { order: 'desc' as const, label: 'Z–A', icon: mdiArrowDown },
      ]
    : activeSort.value.key === 'updated'
      ? [
          { order: 'asc' as const, label: 'Oldest', icon: mdiArrowUp },
          { order: 'desc' as const, label: 'Newest', icon: mdiArrowDown },
        ]
      : [
          {
            order: 'asc' as const,
            label: 'Least observations',
            icon: mdiArrowUp,
          },
          {
            order: 'desc' as const,
            label: 'Most observations',
            icon: mdiArrowDown,
          },
        ]
)
function option(value: string): FilterOption {
  return { value, label: value }
}
function monitoringSiteName(datastream: Datastream): string {
  return (
    (datastream as SelectorDatastream).monitoringSite?.name ??
    monitoringSiteById.value.get(datastreamMonitoringSiteId(datastream))
      ?.name ??
    ''
  )
}
function workspaceName(datastream: Datastream): string {
  const ds = datastream as SelectorDatastream
  return (
    ds.workspace?.name ??
    (
      monitoringSiteById.value.get(datastreamMonitoringSiteId(datastream)) as
        (MonitoringSite & Record<string, any>) | undefined
    )?.workspace?.name ??
    selectedWorkspace.value?.name ??
    ''
  )
}
function datastreamWorkspaceId(datastream: Datastream): string {
  const ds = datastream as SelectorDatastream
  return (
    ds.workspaceId ??
    ds.workspace?.id ??
    ds.monitoringSite?.workspaceId ??
    monitoringSiteById.value.get(datastreamMonitoringSiteId(datastream))
      ?.workspaceId ??
    activeWorkspaceId.value ??
    ''
  )
}
function observedPropertyName(datastream: Datastream): string {
  return (datastream as SelectorDatastream).observedProperty?.name ?? ''
}
function processingLevelName(datastream: Datastream): string {
  return (datastream as SelectorDatastream).processingLevel?.name ?? ''
}
function datastreamName(datastream: Datastream): string {
  return datastream.name?.trim() || 'Unnamed datastream'
}
function datastreamDisplayName(datastream: Datastream): string {
  const siteName = monitoringSiteName(datastream)
  return showMonitoringSiteContext.value && siteName
    ? `${datastreamName(datastream)} @ ${siteName}`
    : datastreamName(datastream)
}
function observationRange(datastream: Datastream): string {
  const count = Number(datastream.valueCount),
    formattedCount = Number.isFinite(count) ? count.toLocaleString() : '—'
  if (count === 0) return '0 observations'
  return `${formattedCount} ${count === 1 ? 'observation' : 'observations'} between ${formatTime(datastream.phenomenonBeginTime)} and ${formatTime(datastream.phenomenonEndTime)}`
}
function matchesFilter(values: string[], candidate: string) {
  return (
    !values.length ||
    values.some(
      (value) => value.toLocaleLowerCase() === candidate.toLocaleLowerCase()
    )
  )
}
function matchesPlainSearch(datastream: Datastream, query: string) {
  if (!query) return true
  return [datastream.name, monitoringSiteName(datastream)].some((value) =>
    `${value ?? ''}`.toLocaleLowerCase().includes(query)
  )
}
function compareText(left: string, right: string) {
  return left.localeCompare(right, undefined, {
    numeric: true,
    sensitivity: 'base',
  })
}
function compareNumbers(
  left: number | string | null | undefined,
  right: number | string | null | undefined
) {
  const leftNumber = Number(left),
    rightNumber = Number(right)
  if (!Number.isFinite(leftNumber) && !Number.isFinite(rightNumber)) return 0
  if (!Number.isFinite(leftNumber)) return 1
  if (!Number.isFinite(rightNumber)) return -1
  return leftNumber - rightNumber
}
function compareNames(left: Datastream, right: Datastream) {
  const sites = showMonitoringSiteContext.value
    ? compareText(monitoringSiteName(left), monitoringSiteName(right))
    : 0
  return sites || compareText(datastreamName(left), datastreamName(right))
}
function compareDatastreams(left: Datastream, right: Datastream) {
  const { key, order } = activeSort.value,
    multiplier = order === 'asc' ? 1 : -1
  if (key === 'name') return compareNames(left, right) * multiplier
  const comparison =
    key === 'updated'
      ? compareNumbers(
          left.phenomenonEndTime
            ? new Date(left.phenomenonEndTime).getTime()
            : null,
          right.phenomenonEndTime
            ? new Date(right.phenomenonEndTime).getTime()
            : null
        )
      : compareNumbers(left.valueCount, right.valueCount)
  return comparison ? comparison * multiplier : compareNames(left, right)
}
function isLinked(datastream: Datastream) {
  const id = String(datastream.id)
  return (
    props.draftDatastreams?.some((item) => String(item.id) === id) ||
    linkedDatastreamIds.value.has(id)
  )
}
function onDatastreamClick(datastream: Datastream) {
  if (props.enforceUniqueSelections && isLinked(datastream)) {
    openLinkConflictModal.value = true
    return
  }
  emit('selectedDatastream', datastream as unknown as DatastreamExtended)
  emit('close')
}
function openDetails(datastream: Datastream) {
  selectedDatastream.value = datastream
  detailsOpen.value = true
}
function updateSearch(value: string) {
  search.value = value
}
function clearSearch() {
  search.value = ''
}
function updateSort(sort: DatastreamSort) {
  search.value = serializeDatastreamQuery(
    parsedSearch.value.filters,
    parsedSearch.value.text,
    sort
  )
}
function setSortKey(key: DatastreamSortKey) {
  updateSort({
    key,
    order:
      activeSort.value.key === key
        ? activeSort.value.order
        : key === 'name'
          ? 'asc'
          : 'desc',
  })
}
function setSortOrder(order: DatastreamSortOrder) {
  updateSort({ key: activeSort.value.key, order })
}
function filteredOptions(filter: FilterDefinition) {
  const query = filterSearches[filter.key].trim().toLocaleLowerCase()
  return query
    ? filter.options.filter((item) =>
        item.label.toLocaleLowerCase().includes(query)
      )
    : filter.options
}
function isFilterSelected(key: DatastreamQualifierKey, value: string) {
  return parsedSearch.value.filters[key].some(
    (item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()
  )
}
function toggleFilter(key: DatastreamQualifierKey, value: string) {
  const filters = structuredClone(
      parsedSearch.value.filters
    ) as DatastreamQueryFilters,
    index = filters[key].findIndex(
      (item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()
    )
  if (index >= 0) filters[key].splice(index, 1)
  else filters[key].push(value)
  search.value = serializeDatastreamQuery(
    filters,
    parsedSearch.value.text,
    parsedSearch.value.sort
  )
}
function clearFilter(key: DatastreamQualifierKey) {
  const filters = structuredClone(
    parsedSearch.value.filters
  ) as DatastreamQueryFilters
  filters[key] = []
  filterSearches[key] = ''
  search.value = serializeDatastreamQuery(
    filters,
    parsedSearch.value.text,
    parsedSearch.value.sort
  )
}
async function loadFallbackData() {
  if (props.datastreams) return
  const workspaceId = activeWorkspaceId.value
  if (!workspaceId) return
  const [datastreams, sites] = await Promise.all([
    hs.datastreams.listAllItems({
      workspace_id: [workspaceId],
      expand_related: true,
    } as any),
    props.monitoringSites
      ? Promise.resolve([])
      : hs.monitoringSites.listAllItems({
          workspace_id: [workspaceId],
          order_by: ['name'],
        } as any),
  ])
  fetchedDatastreams.value = datastreams as Datastream[]
  if (!props.monitoringSites)
    fetchedMonitoringSites.value = sites as MonitoringSite[]
}
watch(activeWorkspaceId, loadFallbackData)
onMounted(loadFallbackData)
</script>

<style scoped>
.datastream-selector-card__content {
  padding-block: var(--hs-space-16);
}
.datastream-selector-tools {
  flex-direction: column;
  align-items: stretch;
  margin: 0 0 var(--hs-space-10);
}
.datastream-selector-tools__primary,
.datastream-selector-heading,
.datastream-filter-header__content,
.datastream-header-filters,
.datastream-name {
  display: flex;
  align-items: center;
}
.datastream-selector-tools__primary {
  justify-content: space-between;
  gap: var(--hs-space-12);
}
.datastream-selector-heading {
  gap: var(--hs-space-8);
  align-items: baseline;
}
.datastream-selector-heading h2 {
  margin: 0;
  color: var(--hs-text-primary);
}
.datastream-selector-count,
.datastream-observation-range,
.datastreams-empty {
  color: var(--hs-text-secondary);
}
.datastream-selector-tools :deep(.hs-query-search) {
  width: 100%;
  max-width: none;
}
.datastream-selector-table {
  width: 100%;
  border-collapse: collapse;
}
.datastream-filter-header {
  padding: var(--hs-space-6) var(--hs-space-8);
  text-align: left;
  background: var(--hs-surface-muted);
  border-bottom: 1px solid var(--hs-border);
}
.datastream-filter-header__content {
  justify-content: space-between;
  gap: var(--hs-space-8);
}
.datastream-header-filters {
  flex-wrap: wrap;
  gap: var(--hs-space-8);
}
.datastream-header-filters :deep(.v-btn),
.datastream-sort-button {
  color: var(--hs-text-primary);
  text-transform: none;
}
.datastream-filter-button--active {
  color: rgb(var(--v-theme-primary)) !important;
}
.filter-count {
  min-width: var(--hs-space-16);
  padding-inline: var(--hs-space-4);
  color: rgb(var(--v-theme-on-primary));
  font-size: var(--hs-font-2xs);
  line-height: var(--hs-space-16);
  text-align: center;
  background: rgb(var(--v-theme-primary));
  border-radius: var(--hs-radius-pill);
}
.datastream-selector-table tbody tr {
  cursor: pointer;
  border-bottom: 1px solid var(--hs-border);
}
.datastream-selector-table tbody tr:hover {
  background: var(--hs-surface-muted);
}
.datastream-selector-table tbody tr.datastream-selector-row--linked,
.datastream-selector-table tbody tr.datastream-selector-row--linked:hover {
  color: var(--hs-text-secondary);
  background: var(--hs-danger-bg);
}
.datastream-summary-cell {
  padding: var(--hs-space-12) var(--hs-space-16);
}
.datastream-actions-cell {
  width: 1%;
  padding: var(--hs-space-8) var(--hs-space-12);
  white-space: nowrap;
}
.datastream-name {
  flex-wrap: wrap;
  gap: var(--hs-space-4);
  color: var(--hs-text-primary);
}
.datastream-name__primary {
  font-weight: var(--hs-font-weight-semibold);
}
.datastream-name__thing,
.datastream-name__separator {
  color: var(--hs-text-secondary);
}
.datastream-observation-range {
  margin-top: var(--hs-space-4);
  font-family: var(--hs-font-data);
}
.datastreams-empty {
  padding: var(--hs-space-16);
  text-align: center;
}
.datastream-details-title {
  min-width: 0;
  overflow: hidden;
  color: var(--hs-text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.datastream-filter-menu {
  min-width: 18rem;
  max-height: 20rem;
  padding-block: var(--hs-space-8);
  overflow-y: auto;
}
.datastream-filter-title,
.datastream-sort-menu__title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-semibold);
}
.datastream-filter-search {
  margin: 0 var(--hs-space-12) var(--hs-space-8);
}
.filter-clear-item {
  color: rgb(var(--v-theme-primary));
  border-top: 1px solid var(--hs-border);
}
.filter-empty {
  padding: var(--hs-space-12) var(--hs-space-16);
  color: var(--hs-text-secondary);
}
.datastream-sort-menu {
  min-width: 17rem;
  padding-block: var(--hs-space-8);
  border: 1px solid var(--hs-border);
}
.datastream-sort-menu__check--hidden {
  visibility: hidden;
}
@media (max-width: 40rem) {
  .datastream-selector-tools__primary,
  .datastream-filter-header__content {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
