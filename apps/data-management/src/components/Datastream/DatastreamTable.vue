<template>
  <section
    ref="datastreamSectionRef"
    class="site-datastreams"
    aria-labelledby="site-datastreams-heading"
  >
    <p
      v-if="monitoringSite?.dataDisclaimer"
      class="site-datastreams__disclaimer hs-text-sm"
    >
      {{ monitoringSite.dataDisclaimer }}
    </p>

    <div class="hs-table-tools site-datastreams__tools">
      <div class="site-datastreams__tools-primary">
        <div class="site-datastreams__heading">
          <h2 id="site-datastreams-heading" class="hs-subheading">
            Datastreams
          </h2>
          <span class="hs-text-sm site-datastreams__count">
            {{ tableDatastreams.length }} available
          </span>
        </div>

        <div class="hs-table-actions">
          <v-btn
            size="small"
            variant="text"
            :prepend-icon="mdiChartLine"
            :to="{
              name: 'VisualizeData',
              query: { sites: monitoringSite!.id },
            }"
          >
            Visualize
          </v-btn>
          <v-btn-page-action
            v-if="
              hasPermission(
                PermissionResource.Datastream,
                PermissionAction.Create,
                workspace
              )
            "
            size="small"
            :prepend-icon="mdiPlus"
            data-testid="add-datastream-button"
            @click="openCreate = true"
          >
            Add datastream
          </v-btn-page-action>
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

    <div class="hs-table-card site-datastreams__table-card">
      <div class="site-datastreams__table-controls">
        <div class="site-datastreams__filter-header-content">
          <div class="site-datastreams__filters">
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
                  class="site-datastreams__filter-button"
                  :class="{
                    'site-datastreams__filter-button--active':
                      filter.selectedCount > 0,
                  }"
                  :append-icon="mdiChevronDown"
                  :aria-label="`Filter by ${filter.label.toLowerCase()}`"
                >
                  {{ filter.label }}
                  <span
                    v-if="filter.selectedCount"
                    class="site-datastreams__filter-count"
                  >
                    {{ filter.selectedCount }}
                  </span>
                </v-btn>
              </template>

              <v-list class="site-datastreams__filter-menu" density="compact">
                <div class="site-datastreams__filter-menu-title">
                  Filter by {{ filter.label }}
                </div>
                <v-text-field
                  v-model="filterSearches[filter.key]"
                  class="site-datastreams__filter-search"
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
                  class="site-datastreams__clear-filter"
                  @click="clearFilter(filter.key)"
                >
                  <v-list-item-title>Clear filter</v-list-item-title>
                </v-list-item>
                <div
                  v-if="!filteredOptions(filter).length"
                  class="site-datastreams__filter-empty"
                >
                  No {{ filter.label.toLowerCase() }} found
                </div>
              </v-list>
            </v-menu>
          </div>

          <v-menu location="bottom end" attach="body">
            <template #activator="{ props: menuProps }">
              <v-btn
                v-bind="menuProps"
                variant="text"
                size="small"
                :prepend-icon="mdiSort"
                :append-icon="mdiChevronDown"
                class="site-datastreams__sort-button"
              >
                {{ sortButtonLabel }}
              </v-btn>
            </template>
            <v-list class="site-datastreams__sort-menu" density="comfortable">
              <div class="site-datastreams__sort-menu-title">Sort by</div>
              <v-list-item
                v-for="option in sortOptions"
                :key="option.key"
                @click="setSortKey(option.key)"
              >
                <template #prepend>
                  <v-icon
                    :icon="mdiCheck"
                    :class="{
                      'site-datastreams__sort-check--hidden':
                        activeSort.key !== option.key,
                    }"
                  />
                </template>
                <v-list-item-title>{{ option.label }}</v-list-item-title>
              </v-list-item>
              <v-divider class="my-1" />
              <div class="site-datastreams__sort-menu-title">Order</div>
              <v-list-item
                v-for="option in sortOrderOptions"
                :key="option.order"
                @click="setSortOrder(option.order)"
              >
                <template #prepend>
                  <v-icon :icon="option.icon" />
                </template>
                <v-list-item-title>{{ option.label }}</v-list-item-title>
                <template #append>
                  <v-icon
                    :icon="mdiCheck"
                    :class="{
                      'site-datastreams__sort-check--hidden':
                        activeSort.order !== option.order,
                    }"
                  />
                </template>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </div>
      <table class="site-datastreams__table hs-text-sm">
        <tbody>
          <tr
            v-for="(item, index) in renderedDatastreams"
            :key="item.id"
            :class="{
              'site-datastreams__row--highlighted': isTargetDatastream(item.id),
            }"
            :data-datastream-id="item.id"
            :data-load-more-trigger="
              isLoadMoreTrigger(index) ? 'true' : undefined
            "
          >
            <td class="site-datastreams__name-cell" data-label="Datastream">
              <div class="site-datastreams__name" :title="datastreamName(item)">
                {{ datastreamName(item) }}
              </div>
            </td>
            <td
              class="site-datastreams__observations-cell"
              data-label="Recent observations"
            >
              <div
                v-if="!canViewData(item)"
                class="site-datastreams__private-data"
              >
                <v-icon :icon="mdiLock" size="16" />
                Data is private
              </div>
              <div v-else class="site-datastreams__observations">
                <Sparkline
                  class="site-datastreams__sparkline"
                  :datastream="item"
                  :unit-name="item.unitName"
                  @open-chart="selectedChartDatastream = item"
                  @latest-value="
                    (value) => handleLatestValueUpdate(item.id, value)
                  "
                />
                <div
                  class="site-datastreams__latest"
                  :class="latestStatusClass(item)"
                >
                  <span v-if="Number(item.valueCount) > 0">
                    Latest observation {{ item.endDate }}
                  </span>
                  <span v-if="shouldShowLatestValue(item.id)">
                    Latest value {{ latestValueDisplay(item) }}
                  </span>
                </div>
              </div>
            </td>
            <td class="site-datastreams__actions-cell" data-label="Actions">
              <div class="site-datastreams__row-actions">
                <v-tooltip
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Edit,
                      workspace
                    )
                  "
                  bottom
                  :open-delay="500"
                  content-class="pa-0 ma-0 bg-transparent"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-btn-icon
                      v-bind="tooltipProps"
                      :icon="item.isVisible ? mdiFileEyeOutline : mdiFileRemove"
                      size="small"
                      :color="item.isVisible ? 'success' : 'error'"
                      :data-testid="`data-visibility-toggle-${item.id}`"
                      :aria-label="`${item.isVisible ? 'Hide' : 'Show'} data`"
                      @click="toggleDataVisibility(item)"
                    />
                  </template>
                  <VisibilityTooltipCard
                    title="Observations are currently"
                    :items="[
                      {
                        label: 'Clicking this will',
                        value: item.isVisible
                          ? 'Hide data for this datastream from guests of your site while keeping the datastream metadata publicly visible.'
                          : 'Make the observations and metadata for this datastream visible to guests of your site.',
                      },
                    ]"
                    :is-visible="item.isVisible"
                  />
                </v-tooltip>

                <v-tooltip
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Edit,
                      workspace
                    )
                  "
                  bottom
                  :open-delay="500"
                  content-class="pa-0 ma-0 bg-transparent"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-btn-icon
                      v-bind="tooltipProps"
                      :icon="item.isPrivate ? mdiLock : mdiLockOpenVariant"
                      size="small"
                      :color="item.isPrivate ? 'error' : 'success'"
                      :data-testid="`datastream-privacy-toggle-${item.id}`"
                      :aria-label="`Make datastream ${item.isPrivate ? 'public' : 'private'}`"
                      @click="toggleVisibility(item)"
                    />
                  </template>
                  <VisibilityTooltipCard
                    title="Datastream is currently"
                    :items="[
                      {
                        label: 'Clicking this will',
                        value: item.isPrivate
                          ? 'Make this datastream and all its metadata and observations publicly visible.'
                          : 'Hide this datastream from guests of your site along with all its metadata and observations.',
                      },
                    ]"
                    :is-visible="!item.isPrivate"
                  />
                </v-tooltip>

                <v-tooltip
                  v-if="
                    !hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.View,
                      workspace
                    ) && !item.isVisible
                  "
                  bottom
                  :open-delay="100"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-icon
                      v-bind="tooltipProps"
                      :icon="mdiLock"
                      color="error"
                    />
                  </template>
                  <span>The data for this datastream is private</span>
                </v-tooltip>

                <v-menu v-else>
                  <template #activator="{ props: menuProps }">
                    <v-btn-icon
                      v-bind="menuProps"
                      :icon="mdiDotsVertical"
                      size="small"
                      :aria-label="`Actions for ${datastreamName(item)}`"
                      :data-testid="`datastream-actions-${item.id}`"
                    />
                  </template>
                  <v-list>
                    <v-list-item
                      v-if="
                        hasPermission(
                          PermissionResource.Datastream,
                          PermissionAction.Edit,
                          workspace
                        )
                      "
                      :prepend-icon="mdiPencil"
                      title="Edit datastream metadata"
                      :data-testid="`edit-datastream-${item.id}`"
                      @click="openDialog(item, 'edit')"
                    />
                    <v-list-item
                      v-if="
                        hasPermission(
                          PermissionResource.Datastream,
                          PermissionAction.Delete,
                          workspace
                        )
                      "
                      :prepend-icon="mdiTrashCanOutline"
                      title="Delete datastream"
                      :data-testid="`delete-datastream-${item.id}`"
                      @click="openDialog(item, 'delete')"
                    />
                    <v-list-item
                      v-if="
                        hasPermission(
                          PermissionResource.Observation,
                          PermissionAction.Delete,
                          workspace
                        )
                      "
                      :prepend-icon="mdiTrashCanOutline"
                      title="Delete data from datastream"
                      :data-testid="`delete-datastream-data-${item.id}`"
                      @click="openObservationDialog(item)"
                    />
                    <v-list-item
                      :prepend-icon="mdiChartLine"
                      title="Visualize data"
                      :data-testid="`visualize-datastream-${item.id}`"
                      :to="{
                        name: 'VisualizeData',
                        query: {
                          sites: item.monitoringSiteId,
                          datastreams: item.id,
                        },
                      }"
                    />
                    <v-list-item
                      v-if="canOpenQcEditor"
                      :prepend-icon="mdiShieldCheckOutline"
                      title="Open in QC editor"
                      :data-testid="`qc-edit-datastream-${item.id}`"
                      :href="qcEditHref(item.id)"
                    />
                    <v-list-item
                      :prepend-icon="mdiDownload"
                      title="Download data"
                      :data-testid="`download-datastream-${item.id}`"
                      @click="onDownload(item.id)"
                    />
                  </v-list>
                </v-menu>
              </div>
              <v-btn
                size="small"
                variant="outlined"
                class="site-datastreams__metadata-button"
                :data-testid="`datastream-metadata-${item.id}`"
                @click="openInfoCardFor(item)"
              >
                View full metadata
              </v-btn>
              <div
                v-if="downloading[item.id]"
                class="site-datastreams__download"
              >
                <v-progress-circular
                  indeterminate
                  size="16"
                  width="2"
                  color="primary"
                />
                Preparing file…
              </div>
            </td>
          </tr>
          <tr v-if="!renderedDatastreams.length">
            <td colspan="3" class="site-datastreams__empty">
              No datastreams match the current filters.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <v-dialog
      v-if="selectedChartDatastream"
      v-model="isChartOpen"
      width="80rem"
    >
      <DatastreamPopupPlot
        :datastream="selectedChartDatastream"
        @close="isChartOpen = false"
      />
    </v-dialog>
  </section>

  <v-dialog v-model="openCreate" width="80rem">
    <DatastreamForm
      :monitoringSite="monitoringSite!"
      :workspace="workspace"
      @close="openCreate = false"
      @created="onCreated"
    />
  </v-dialog>

  <v-dialog v-model="openEdit" width="80rem">
    <DatastreamForm
      :monitoringSite="monitoringSite!"
      :workspace="workspace"
      :datastream="item"
      @close="openEdit = false"
      @updated="updateDatastream"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DatastreamDeleteCard
      :datastream="item"
      @close="openDelete = false"
      @delete="onDelete"
    />
  </v-dialog>

  <v-dialog v-model="openObservationsDelete" width="40rem">
    <ObservationsDeleteCard
      :datastream="item"
      @close="openObservationsDelete = false"
      @delete="onObservationsDelete"
    />
  </v-dialog>

  <v-dialog
    v-model="openInfoCard"
    width="50rem"
    v-if="selectedDatastream && monitoringSite"
  >
    <DatastreamTableInfoCard
      :datastream="selectedDatastream"
      :monitoringSite="monitoringSite"
      @close="openInfoCard = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import DatastreamPopupPlot from '@/components/Datastream/DatastreamPopupPlot.vue'
import DatastreamForm from '@/components/Datastream/DatastreamForm.vue'
import DatastreamDeleteCard from './DatastreamDeleteCard.vue'
import Sparkline from '@/components/Sparkline.vue'
import {
  computed,
  nextTick,
  onBeforeUnmount,
  reactive,
  ref,
  toRef,
  watch,
} from 'vue'
import { useMetadata } from '@/composables/useMetadata'
import { storeToRefs } from 'pinia'
import { useMonitoringSiteStore } from '@/store/monitoringSite'
import { useWorkspaceStore } from '@/store/workspaces'
import { Datastream, Workspace, type StatusType } from '@hydroserver/client'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useTableLogic } from '@/composables/useTableLogic'
import { Snackbar } from '@/utils/notifications'
import { downloadDatastreamCsv } from '@/utils/csvExport'
import { formatTime } from '@/utils/time'
import { buildQcEditUrl } from '@/utils/qcLinks'
import {
  parseDatastreamQuery,
  serializeDatastreamQuery,
  type DatastreamQueryFilters,
  type DatastreamSort,
  type DatastreamSortKey,
  type DatastreamSortOrder,
} from '@/utils/datastreamSearch'
import {
  countDistinctMonitoringViolationRules,
  getMonitoringRulesViolated,
  getMonitoringRunViolations,
  getTaskRunStatusText,
  getTaskStatusText,
} from '@/utils/orchestration/taskRunDetails'
import DatastreamTableInfoCard from './DatastreamTableInfoCard.vue'
import ObservationsDeleteCard from '../Observation/ObservationsDeleteCard.vue'
import VisibilityTooltipCard from '@/components/Datastream/VisibilityTooltipCard.vue'
import hs, { PermissionAction, PermissionResource } from '@hydroserver/client'
import { HsQuerySearchInput } from '@hydroserver/design-system/vue'
import {
  mdiArrowDown,
  mdiArrowUp,
  mdiCallMerge,
  mdiChartBellCurve,
  mdiChartLine,
  mdiCheck,
  mdiChevronDown,
  mdiTrashCanOutline,
  mdiDotsVertical,
  mdiDownload,
  mdiFileEyeOutline,
  mdiFileRemove,
  mdiLightningBolt,
  mdiLock,
  mdiLockOpenVariant,
  mdiMagnify,
  mdiPencil,
  mdiPlus,
  mdiShieldCheckOutline,
  mdiSigma,
  mdiSort,
} from '@mdi/js'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
  targetDatastreamId: { type: String, default: '' },
})

type LinkedDatastreamTask = {
  id: string
  name: string
  dataConnectionName: string | null
  displayName: string
  label: string
  icon: string
  iconClass: string
  status: StatusType
  paused: boolean
  lastRunAt: string | null
  route: {
    name: string
    params: { view: string }
    query: Record<string, string>
  }
}

type LinkedMonitoringTask = LinkedDatastreamTask & {
  ruleCount: number
  violationCount: number | null
  latestRunStatus: string | null
  lastRunStatus: StatusType
}

type SiteDatastreamFilterKey =
  'observed-property' | 'unit' | 'method' | 'processing-level'
type FilterOption = { value: string; label: string }
type FilterDefinition = {
  key: SiteDatastreamFilterKey
  label: string
  options: FilterOption[]
  selectedCount: number
}

const { monitoringSite } = storeToRefs(useMonitoringSiteStore())
const openCreate = ref(false)
const workspaceRef = toRef(props, 'workspace')
const monitoringSiteIdRef = computed(() => monitoringSite.value!.id)
const downloading = reactive<Record<string, boolean>>({})
const search = ref('')
const datastreamSectionRef = ref<any>(null)
const highlightedDatastreamId = ref('')
const DATASTREAM_HIGHLIGHT_DURATION_MS = 2500
const DATASTREAM_RENDER_BATCH_SIZE = 10
const DATASTREAM_PRELOAD_AHEAD_COUNT = 10
const renderedDatastreamCount = ref(DATASTREAM_RENDER_BATCH_SIZE)
let highlightTimeout: number | undefined
let loadMoreObserver: IntersectionObserver | undefined

const openObservationsDelete = ref(false)
function openObservationDialog(selectedItem: any) {
  item.value = selectedItem
  openObservationsDelete.value = true
}

const openInfoCard = ref(false)
const selectedDatastream = ref<Datastream | null>(null)
const openInfoCardFor = (datastream: Datastream) => {
  selectedDatastream.value = datastream
  openInfoCard.value = true
}

const { hasPermission } = useWorkspacePermissions(workspaceRef)
const { workspaces } = storeToRefs(useWorkspaceStore())

const canOpenQcEditor = computed(
  () =>
    hasPermission(
      PermissionResource.Observation,
      PermissionAction.Edit,
      props.workspace
    ) ||
    hasPermission(
      PermissionResource.Observation,
      PermissionAction.Create,
      props.workspace
    )
)

const qcEditHref = (datastreamId: string) =>
  buildQcEditUrl({
    workspaceId: props.workspace.id,
    datastreamId,
  })

const canViewOrchestrationInfo = computed(() => {
  return workspaces.value.some(
    (workspace) => workspace.id === props.workspace.id
  )
})

const updateDatastream = async (updatedDatastream: Datastream) => {
  await fetchMetadata(props.workspace.id)
  onUpdate(updatedDatastream)
}

const onCreated = async () => {
  await fetchMetadata(props.workspace.id)
  await loadDatastreams()
}

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  useTableLogic(
    async (monitoringSiteId: string) =>
      await hs.datastreams.listAllItems({
        monitoring_site_id: [monitoringSiteId],
      }),
    hs.datastreams.delete,
    Datastream,
    monitoringSiteIdRef
  )

const { methods, units, observedProperties, processingLevels, fetchMetadata } =
  useMetadata(toRef(props, 'workspace'))

const selectedChartDatastream = ref<Datastream | null>(null)
const isChartOpen = computed({
  get: () => Boolean(selectedChartDatastream.value),
  set: (isOpen) => {
    if (!isOpen) selectedChartDatastream.value = null
  },
})
const latestValues = reactive<
  Record<string, { text: string; showUnit: boolean; isBad: boolean }>
>({})
const rawEtlTasks = ref<any[]>([])
const rawDataProductTasks = ref<any[]>([])
const rawMonitoringTasks = ref<any[]>([])
const linkedTasksLoaded = ref(false)
const linkedTasksErrored = ref(false)
let linkedTasksRequestId = 0

const handleLatestValueUpdate = (
  datastreamId: string,
  value: { text: string; showUnit: boolean; isBad: boolean }
) => {
  latestValues[datastreamId] = value
}

const latestValueFor = (datastreamId: string) =>
  latestValues[datastreamId] || { text: '—', showUnit: false, isBad: false }

const shouldShowLatestValue = (datastreamId: string) => {
  const value = latestValueFor(datastreamId)
  return value.text !== 'No observations'
}

const latestValueDisplay = (datastream: { id: string; unitName?: string }) => {
  const value = latestValueFor(datastream.id)
  if (!value.showUnit) return value.text
  return `${value.text} ${datastream.unitName ?? ''}`.trim()
}

const latestStatusClass = (datastream: Datastream) => {
  if (isDatastreamStale(datastream)) return 'site-datastreams__latest--stale'
  const latestValue = latestValueFor(datastream.id)
  if (latestValue.isBad) return 'site-datastreams__latest--error'
  return 'site-datastreams__latest--success'
}

const visibleDatastreams = computed(() => {
  const unitsById = new Map(units.value.map((u) => [u.id, u]))
  const methodsById = new Map(
    methods.value.map((method) => [method.id, method])
  )
  const opsById = new Map(observedProperties.value.map((o) => [o.id, o]))
  const processingLevelsById = new Map(
    processingLevels.value.map((p) => [p.id, p])
  )

  return items.value
    .filter(
      (d) =>
        !d.isPrivate ||
        hasPermission(
          PermissionResource.Datastream,
          PermissionAction.View,
          props.workspace
        )
    )
    .map((d) => {
      const unit = unitsById.get(d.unitId)
      const method = methodsById.get(d.methodId)
      const op = opsById.get(d.observedPropertyId)
      const pl = processingLevelsById.get(d.processingLevelId)

      const mapped = {
        ...d,
        OPName: op ? `${op.name} (${op.code})` : '',
        observedPropertyName: op?.name ?? '',
        processingLevelCode: pl?.code ?? '',
        processingLevelName: pl?.name ?? '',
        methodName: method?.name ?? '',
        unitName: unit?.name ?? '',
        searchText: ',',
        beginDate: formatTime(d.phenomenonBeginTime),
        endDate: formatTime(d.phenomenonEndTime),
        aggregationInterval: `${d.timeAggregationInterval} ${d.timeAggregationIntervalUnit}`,
        spacingInterval: `${d.intendedTimeSpacing} ${d.intendedTimeSpacingUnit}`,
      }

      mapped.searchText = [
        mapped.name,
        mapped.OPName,
        mapped.id,
        mapped.processingLevelName,
        mapped.sampledMedium,
        mapped.methodName,
        mapped.noDataValue,
        mapped.aggregationStatistic,
        mapped.unitName,
        mapped.status,
        mapped.valueCount,
        mapped.beginDate,
        mapped.endDate,
        mapped.aggregationInterval,
        mapped.spacingInterval,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return mapped
    })
})

const parsedSearch = computed(() => parseDatastreamQuery(search.value))
const normalizedSearch = computed(() =>
  parsedSearch.value.text.toLocaleLowerCase()
)
const filterSearches = reactive<Record<SiteDatastreamFilterKey, string>>({
  'observed-property': '',
  unit: '',
  method: '',
  'processing-level': '',
})
const uniqueSorted = (values: Array<string | null | undefined>) =>
  [...new Set(values.filter((value): value is string => Boolean(value)))].sort(
    (a, b) => a.localeCompare(b)
  )
const option = (value: string): FilterOption => ({ value, label: value })
const filterDefinitions = computed<FilterDefinition[]>(() => [
  {
    key: 'observed-property',
    label: 'Observed property',
    options: uniqueSorted(
      visibleDatastreams.value.map((item) => item.observedPropertyName)
    ).map(option),
    selectedCount: parsedSearch.value.filters['observed-property'].length,
  },
  {
    key: 'unit',
    label: 'Unit',
    options: uniqueSorted(
      visibleDatastreams.value.map((item) => item.unitName)
    ).map(option),
    selectedCount: parsedSearch.value.filters.unit.length,
  },
  {
    key: 'method',
    label: 'Method',
    options: uniqueSorted(
      visibleDatastreams.value.map((item) => item.methodName)
    ).map(option),
    selectedCount: parsedSearch.value.filters.method.length,
  },
  {
    key: 'processing-level',
    label: 'Processing level',
    options: uniqueSorted(
      visibleDatastreams.value.map((item) => item.processingLevelName)
    ).map(option),
    selectedCount: parsedSearch.value.filters['processing-level'].length,
  },
])
const searchQualifiers = computed(() => [
  ...filterDefinitions.value.map((filter) => ({
    key: filter.key,
    label: filter.label,
    values: filter.options.map((item) => item.value),
  })),
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
const defaultSort: DatastreamSort = { key: 'name', order: 'asc' }
const activeSort = computed(() => parsedSearch.value.sort ?? defaultSort)
const sortOptions = [
  { key: 'name' as const, label: 'Datastream name' },
  { key: 'updated' as const, label: 'Last updated' },
  { key: 'observations' as const, label: 'Observation count' },
]
const sortButtonLabel = computed(
  () =>
    sortOptions.find((option) => option.key === activeSort.value.key)?.label ??
    'Sort'
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
const matchesFilter = (values: string[], candidate: string) =>
  !values.length ||
  values.some(
    (value) => value.toLocaleLowerCase() === candidate.toLocaleLowerCase()
  )
const compareText = (left: string, right: string) =>
  left.localeCompare(right, undefined, { numeric: true, sensitivity: 'base' })
const compareNumbers = (
  left: number | string | null | undefined,
  right: number | string | null | undefined
) => {
  const leftNumber = Number(left)
  const rightNumber = Number(right)
  if (!Number.isFinite(leftNumber) && !Number.isFinite(rightNumber)) return 0
  if (!Number.isFinite(leftNumber)) return 1
  if (!Number.isFinite(rightNumber)) return -1
  return leftNumber - rightNumber
}
const compareDatastreams = (
  left: (typeof visibleDatastreams.value)[number],
  right: (typeof visibleDatastreams.value)[number]
) => {
  const { key, order } = activeSort.value
  const multiplier = order === 'asc' ? 1 : -1
  if (key === 'name') {
    return compareText(datastreamName(left), datastreamName(right)) * multiplier
  }
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
  return comparison
    ? comparison * multiplier
    : compareText(datastreamName(left), datastreamName(right))
}
const tableDatastreams = computed(() => {
  const { filters } = parsedSearch.value
  return visibleDatastreams.value
    .filter(
      (item) =>
        matchesFilter(
          filters['observed-property'],
          item.observedPropertyName
        ) &&
        matchesFilter(filters.unit, item.unitName) &&
        matchesFilter(filters.method, item.methodName) &&
        matchesFilter(filters['processing-level'], item.processingLevelName) &&
        (!normalizedSearch.value ||
          item.searchText.includes(normalizedSearch.value))
    )
    .sort(compareDatastreams)
})

function updateSearch(value: string) {
  search.value = value
}
function clearSearch() {
  search.value = ''
}
function filteredOptions(filter: FilterDefinition) {
  const query = filterSearches[filter.key].trim().toLocaleLowerCase()
  return query
    ? filter.options.filter((item) =>
        item.label.toLocaleLowerCase().includes(query)
      )
    : filter.options
}
function isFilterSelected(key: SiteDatastreamFilterKey, value: string) {
  return parsedSearch.value.filters[key].some(
    (item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()
  )
}
function updateSearchFilters(filters: DatastreamQueryFilters) {
  search.value = serializeDatastreamQuery(
    filters,
    parsedSearch.value.text,
    parsedSearch.value.sort
  )
}
function toggleFilter(key: SiteDatastreamFilterKey, value: string) {
  const filters = structuredClone(
    parsedSearch.value.filters
  ) as DatastreamQueryFilters
  const index = filters[key].findIndex(
    (item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()
  )
  if (index >= 0) filters[key].splice(index, 1)
  else filters[key].push(value)
  updateSearchFilters(filters)
}
function clearFilter(key: SiteDatastreamFilterKey) {
  const filters = structuredClone(
    parsedSearch.value.filters
  ) as DatastreamQueryFilters
  filters[key] = []
  filterSearches[key] = ''
  updateSearchFilters(filters)
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
function datastreamName(datastream: Datastream) {
  return datastream.name?.trim() || 'Unnamed datastream'
}
function canViewData(datastream: Datastream) {
  return (
    datastream.isVisible ||
    hasPermission(
      PermissionResource.Datastream,
      PermissionAction.View,
      props.workspace
    )
  )
}

const renderedDatastreams = computed(() =>
  tableDatastreams.value.slice(0, renderedDatastreamCount.value)
)

const hasMoreDatastreams = computed(
  () => renderedDatastreams.value.length < tableDatastreams.value.length
)

const loadMoreTriggerIndex = computed(() => {
  if (!hasMoreDatastreams.value) return -1
  return Math.max(
    0,
    renderedDatastreams.value.length - DATASTREAM_PRELOAD_AHEAD_COUNT
  )
})

function isLoadMoreTrigger(index: number) {
  return index === loadMoreTriggerIndex.value
}

function loadMoreDatastreams() {
  if (!hasMoreDatastreams.value) return
  loadMoreObserver?.disconnect()
  renderedDatastreamCount.value = Math.min(
    renderedDatastreamCount.value + DATASTREAM_RENDER_BATCH_SIZE,
    tableDatastreams.value.length
  )
}

async function observeLoadMoreTrigger() {
  await nextTick()
  loadMoreObserver?.disconnect()
  if (!hasMoreDatastreams.value) return

  const trigger = datastreamSectionElement()?.querySelector<HTMLElement>(
    '[data-load-more-trigger="true"]'
  )
  if (!trigger) return

  if (!window.IntersectionObserver) {
    renderedDatastreamCount.value = tableDatastreams.value.length
    return
  }

  loadMoreObserver ??= new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadMoreDatastreams()
      }
    },
    { root: null, threshold: 0 }
  )
  loadMoreObserver.observe(trigger)
}

const deepLinkedDatastreamId = computed(() => props.targetDatastreamId.trim())

const targetDatastreamIndex = computed(() => {
  if (!deepLinkedDatastreamId.value) return -1
  return tableDatastreams.value.findIndex(
    (datastream) => String(datastream.id) === deepLinkedDatastreamId.value
  )
})

function isTargetDatastream(datastreamId: string) {
  return (
    !!highlightedDatastreamId.value &&
    String(datastreamId) === highlightedDatastreamId.value
  )
}

function findTargetDatastreamElement() {
  if (!deepLinkedDatastreamId.value) return null
  const section = datastreamSectionElement()
  const elements = Array.from(
    section?.querySelectorAll<HTMLElement>('[data-datastream-id]') ?? []
  )
  return (
    elements.find(
      (element) => element.dataset.datastreamId === deepLinkedDatastreamId.value
    ) ?? null
  )
}

function datastreamSectionElement(): HTMLElement | null {
  const section = datastreamSectionRef.value
  if (!section) return null
  if (section instanceof HTMLElement) return section
  return section.$el instanceof HTMLElement ? section.$el : null
}

function highlightTargetDatastream() {
  highlightedDatastreamId.value = deepLinkedDatastreamId.value
  if (highlightTimeout) window.clearTimeout(highlightTimeout)
  highlightTimeout = window.setTimeout(() => {
    highlightedDatastreamId.value = ''
  }, DATASTREAM_HIGHLIGHT_DURATION_MS)
}

async function scrollToTargetDatastream() {
  if (!deepLinkedDatastreamId.value) return
  const canAccessDatastream = visibleDatastreams.value.some(
    (datastream) => String(datastream.id) === deepLinkedDatastreamId.value
  )
  if (!canAccessDatastream) return

  if (targetDatastreamIndex.value === -1 && normalizedSearch.value) {
    search.value = ''
    await nextTick()
  }

  if (targetDatastreamIndex.value >= renderedDatastreamCount.value) {
    renderedDatastreamCount.value = Math.min(
      targetDatastreamIndex.value + DATASTREAM_PRELOAD_AHEAD_COUNT + 1,
      tableDatastreams.value.length
    )
    await nextTick()
  }

  await nextTick()
  datastreamSectionElement()?.scrollIntoView({
    block: 'start',
    behavior: 'smooth',
  })

  window.setTimeout(() => {
    findTargetDatastreamElement()?.scrollIntoView({
      block: 'center',
      behavior: 'smooth',
    })
    highlightTargetDatastream()
  }, 80)
}

const isDatastreamStale = (datastream: Datastream) => {
  if (!datastream.phenomenonEndTime) return true
  const endTime = new Date(datastream.phenomenonEndTime)
  const seventyTwoHoursAgo = new Date(Date.now() - 72 * 60 * 60 * 1000)
  return endTime < seventyTwoHoursAgo
}

const linkedTasksForDatastream = (datastreamId: string) =>
  linkedTasksByDatastreamId.value[datastreamId] ?? []

const monitoringTasksForDatastream = (datastreamId: string) =>
  monitoringTasksByDatastreamId.value[datastreamId] ?? []

const showTaskRow = computed(
  () => canViewOrchestrationInfo.value && linkedTasksLoaded.value
)

const showTaskSkeleton = computed(
  () =>
    canViewOrchestrationInfo.value &&
    !linkedTasksLoaded.value &&
    !linkedTasksErrored.value
)

const datastreamTaskLinkClass = (datastreamId: string) => {
  const linkedTasks = linkedTasksForDatastream(datastreamId)
  if (!linkedTasks.length) return 'datastream-task-link--none'
  if (linkedTasks.length > 1) return 'datastream-task-link--conflict'
  if (linkedTasks[0].paused) return 'datastream-task-link--none'

  const statusClass: Record<StatusType, string> = {
    OK: 'datastream-task-link--ok',
    Pending: 'datastream-task-link--pending',
    'Needs attention': 'datastream-task-link--attention',
    'Behind schedule': 'datastream-task-link--behind',
    Unknown: 'datastream-task-link--none',
    'Loading paused': 'datastream-task-link--none',
  }
  return statusClass[linkedTasks[0].status]
}

const TASK_STATUS_DOT_COLORS: Record<StatusType, string> = {
  OK: '#357a38',
  Pending: '#1769aa',
  'Needs attention': '#c62828',
  'Behind schedule': '#e65100',
  Unknown: '#546e7a',
  'Loading paused': '#546e7a',
}

const displayedTaskStatus = (task: LinkedDatastreamTask): StatusType =>
  task.paused && task.status !== 'Needs attention'
    ? 'Loading paused'
    : task.status

const taskStatusColor = (task: LinkedDatastreamTask) =>
  TASK_STATUS_DOT_COLORS[displayedTaskStatus(task)] ??
  TASK_STATUS_DOT_COLORS.Unknown

const formatRelativeTime = (iso: string | null) => {
  if (!iso) return null
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return null

  const diffSeconds = Math.round((Date.now() - then) / 1000)
  if (diffSeconds < 45) return 'just now'

  const units: [number, string][] = [
    [60, 'min'],
    [60, 'hr'],
    [24, 'day'],
    [30, 'mo'],
    [12, 'yr'],
  ]
  let value = diffSeconds / 60
  let label = 'min'
  for (let i = 1; i < units.length && value >= units[i][0]; i += 1) {
    value /= units[i][0]
    label = units[i][1]
  }
  const rounded = Math.round(value)
  return `${rounded} ${label}${rounded === 1 ? '' : 's'} ago`
}

const lastRanLabel = (task: LinkedDatastreamTask) => {
  const relative = formatRelativeTime(task.lastRunAt)
  return relative ? `Last ran ${relative}` : 'Never ran'
}

const monitoringOutcomeLabel = (task: LinkedMonitoringTask) => {
  const ruleLabel = `${task.ruleCount} rule${task.ruleCount === 1 ? '' : 's'}`
  if (!task.latestRunStatus) return `Not checked · ${ruleLabel}`
  if (
    task.latestRunStatus === 'PENDING' ||
    task.latestRunStatus === 'STARTED'
  ) {
    return `Checking ${ruleLabel}`
  }
  if (task.latestRunStatus === 'FAILURE')
    return `Results unavailable · ${ruleLabel}`
  if (task.violationCount === null) return `Results unavailable · ${ruleLabel}`
  if (task.violationCount === 0) {
    return `${task.ruleCount}/${task.ruleCount} ${
      task.ruleCount === 1 ? 'rule' : 'rules'
    } passed`
  }
  return `${task.violationCount}/${task.ruleCount} ${
    task.ruleCount === 1 ? 'rule' : 'rules'
  } violated`
}

const monitoringOutcomeClass = (task: LinkedMonitoringTask) => {
  if (task.violationCount !== null && task.violationCount > 0) {
    return 'datastream-task-link__quality-outcome--violations'
  }
  if (task.latestRunStatus === 'SUCCESS' && task.violationCount === 0) {
    return 'datastream-task-link__quality-outcome--ok'
  }
  return 'datastream-task-link__quality-outcome--unknown'
}

const monitoringLastRunStatus = (task: LinkedMonitoringTask): StatusType =>
  task.lastRunStatus

const monitoringLastRunColor = (task: LinkedMonitoringTask) =>
  TASK_STATUS_DOT_COLORS[monitoringLastRunStatus(task)]

const routeForIngestionTask = (task: any) => {
  const query: Record<string, string> = {
    workspace_id: props.workspace.id,
    task_id: String(task.id),
  }
  const dataConnectionId = task.dataConnection?.id ?? task.dataConnectionId
  if (dataConnectionId) query.data_connection_id = String(dataConnectionId)

  return {
    name: 'OrchestrationIngestionDetails',
    params: { view: 'ingestion' },
    query,
  }
}

const dataProductRouteName = (task: any) => {
  if (task.aggregationTransformations?.length) {
    return 'OrchestrationAggregationDetails'
  }
  if (task.derivationTransformations?.length) {
    return 'OrchestrationDerivationDetails'
  }
  if (task.ratingCurveTransformations?.length) {
    return 'OrchestrationRatingCurveDetails'
  }
  return 'OrchestrationAggregationDetails'
}

const siteScopedRoute = (task: any, name: string, view: string) => {
  const query: Record<string, string> = {
    workspace_id: props.workspace.id,
    task_id: String(task.id),
  }
  const siteId =
    task.monitoringSite?.id ?? task.monitoringSiteId ?? monitoringSite.value?.id
  if (siteId) query.site_id = String(siteId)

  return { name, params: { view }, query }
}

const routeForDataProductTask = (task: any) =>
  siteScopedRoute(task, dataProductRouteName(task), 'aggregation')

const routeForMonitoringTask = (task: any) =>
  siteScopedRoute(task, 'OrchestrationQualityDetails', 'quality')

const outputDatastreamId = (transformation: any) =>
  transformation?.outputDatastream?.id ?? transformation?.outputDatastreamId

const targetDatastreamId = (mapping: any) =>
  mapping?.targetDatastream?.id ?? mapping?.targetDatastreamId

const monitoredDatastreamId = (monitoredDatastream: any) =>
  monitoredDatastream?.datastream?.id ??
  monitoredDatastream?.datastreamId ??
  monitoredDatastream?.id

const monitoringViolationCount = (
  task: any,
  datastreamId: string,
  monitoredDatastreamCount: number
) => {
  const latestRun = task?.latestRun
  if (!latestRun || latestRun.status !== 'SUCCESS') return null

  const detailedViolations = getMonitoringRunViolations(latestRun)
  const totalViolations = detailedViolations.length
    ? countDistinctMonitoringViolationRules(detailedViolations)
    : getMonitoringRulesViolated(latestRun)
  if (totalViolations === 0) return 0

  const datastreamViolations = detailedViolations.filter(
    (violation) => violation.datastreamId === datastreamId
  )
  if (datastreamViolations.length) {
    return countDistinctMonitoringViolationRules(datastreamViolations)
  }

  if (detailedViolations.length && monitoredDatastreamCount === 1) {
    return countDistinctMonitoringViolationRules(detailedViolations)
  }

  return monitoredDatastreamCount === 1 ? totalViolations : null
}

const taskPaused = (task: any) =>
  task.schedule
    ? task.schedule.paused === true || task.schedule.enabled === false
    : false

const truncateTaskInfoPart = (value: unknown, maxLength = 250) => {
  const text = `${value ?? ''}`.trim()
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

const dataConnectionNameForTask = (task: any) =>
  task.dataConnection?.name ?? task.dataConnectionName ?? null

const linkedTaskDisplayName = (task: any) => {
  const taskName = truncateTaskInfoPart(task.name || task.id)
  const dataConnectionName = dataConnectionNameForTask(task)
  if (!dataConnectionName) return taskName
  return `${truncateTaskInfoPart(dataConnectionName)} · ${taskName}`
}

const addLinkedTask = (
  grouped: Record<string, LinkedDatastreamTask[]>,
  seen: Set<string>,
  datastreamId: string,
  task: any,
  config: Pick<LinkedDatastreamTask, 'label' | 'icon' | 'route'> &
    Partial<Pick<LinkedDatastreamTask, 'iconClass'>>
) => {
  const key = `${datastreamId}:${task.id}`
  if (seen.has(key)) return
  seen.add(key)
  grouped[datastreamId] ??= []
  grouped[datastreamId].push({
    id: String(task.id),
    name: task.name,
    dataConnectionName: dataConnectionNameForTask(task),
    displayName: linkedTaskDisplayName(task),
    label: config.label,
    icon: config.icon,
    iconClass: config.iconClass ?? '',
    status: getTaskStatusText(task),
    paused: taskPaused(task),
    lastRunAt: task.latestRun?.startedAt ?? task.latestRun?.finishedAt ?? null,
    route: config.route,
  })
}

const loadLinkedTasks = async () => {
  const requestId = ++linkedTasksRequestId
  linkedTasksLoaded.value = false
  linkedTasksErrored.value = false
  const site = monitoringSite.value
  if (!canViewOrchestrationInfo.value || !site || !props.workspace?.id) {
    rawEtlTasks.value = []
    rawDataProductTasks.value = []
    rawMonitoringTasks.value = []
    return
  }

  try {
    const [etlTasks, dataProductTasks, monitoringTasks] = await Promise.all([
      hs.tasks.listAllItems({
        monitoring_site_id: [site.id],
        order_by: ['name'],
        expand_related: true,
      }),
      hs.dataProductTasks.listAllItems({
        monitoring_site_id: [site.id],
        order_by: ['name'],
        expand_related: true,
      }),
      hs.monitoringTasks.listAllItems({
        monitoring_site_id: [site.id],
        order_by: ['name'],
        expand_related: true,
      }),
    ])
    if (requestId !== linkedTasksRequestId) return

    rawEtlTasks.value = etlTasks ?? []
    rawDataProductTasks.value = dataProductTasks ?? []
    rawMonitoringTasks.value = monitoringTasks ?? []
    linkedTasksLoaded.value = true
  } catch (error) {
    if (requestId !== linkedTasksRequestId) return
    console.error('Error fetching linked datastream tasks', error)
    linkedTasksErrored.value = true
    rawEtlTasks.value = []
    rawDataProductTasks.value = []
    rawMonitoringTasks.value = []
  }
}

const linkedTasksByDatastreamId = computed<
  Record<string, LinkedDatastreamTask[]>
>(() => {
  if (!linkedTasksLoaded.value) return {}
  const datastreamIds = new Set(items.value.map((d) => String(d.id)))
  const grouped: Record<string, LinkedDatastreamTask[]> = {}
  const seen = new Set<string>()

  for (const task of rawEtlTasks.value) {
    for (const mapping of (task as any).mappings ?? []) {
      const datastreamId = targetDatastreamId(mapping)
      if (!datastreamId || !datastreamIds.has(String(datastreamId))) continue
      addLinkedTask(grouped, seen, String(datastreamId), task, {
        label: 'Fed by',
        icon: mdiLightningBolt,
        iconClass: 'datastream-task-link__icon--source',
        route: routeForIngestionTask(task),
      })
    }
  }

  for (const task of rawDataProductTasks.value) {
    const transformationGroups = [
      {
        label: 'Aggregated by',
        icon: mdiCallMerge,
        iconClass: 'datastream-task-link__icon--aggregation',
        transformations: (task as any).aggregationTransformations ?? [],
      },
      {
        label: 'Derived by',
        icon: mdiSigma,
        iconClass: 'datastream-task-link__icon--derived',
        transformations: (task as any).derivationTransformations ?? [],
      },
      {
        label: 'Rating curve',
        icon: mdiChartBellCurve,
        iconClass: 'datastream-task-link__icon--rating-curve',
        transformations: (task as any).ratingCurveTransformations ?? [],
      },
    ]
    for (const group of transformationGroups) {
      for (const transformation of group.transformations) {
        const datastreamId = outputDatastreamId(transformation)
        if (!datastreamId || !datastreamIds.has(String(datastreamId))) continue
        addLinkedTask(grouped, seen, String(datastreamId), task, {
          label: group.label,
          icon: group.icon,
          iconClass: group.iconClass,
          route: routeForDataProductTask(task),
        })
      }
    }
  }

  return grouped
})

const monitoringTasksByDatastreamId = computed<
  Record<string, LinkedMonitoringTask[]>
>(() => {
  if (!linkedTasksLoaded.value) return {}
  const datastreamIds = new Set(items.value.map((d) => String(d.id)))
  const groupedMonitoring: Record<string, LinkedMonitoringTask[]> = {}
  const seenMonitoring = new Set<string>()

  for (const task of rawMonitoringTasks.value) {
    const monitoredDatastreams = (task as any).monitoredDatastreams ?? []
    for (const monitoredDatastream of monitoredDatastreams) {
      const datastreamId = monitoredDatastreamId(monitoredDatastream)
      if (!datastreamId || !datastreamIds.has(String(datastreamId))) continue

      const key = `${datastreamId}:${(task as any).id}`
      if (seenMonitoring.has(key)) continue
      seenMonitoring.add(key)
      groupedMonitoring[String(datastreamId)] ??= []
      groupedMonitoring[String(datastreamId)].push({
        id: String((task as any).id),
        name: (task as any).name,
        dataConnectionName: null,
        displayName: truncateTaskInfoPart(
          (task as any).name || (task as any).id
        ),
        label: 'Quality monitoring',
        icon: mdiShieldCheckOutline,
        iconClass: 'datastream-task-link__icon--monitoring',
        status: getTaskStatusText(task),
        paused: taskPaused(task),
        lastRunAt:
          (task as any).latestRun?.startedAt ??
          (task as any).latestRun?.finishedAt ??
          null,
        route: routeForMonitoringTask(task),
        ruleCount: ((monitoredDatastream as any).rules ?? []).length,
        violationCount: monitoringViolationCount(
          task,
          String(datastreamId),
          monitoredDatastreams.length
        ),
        latestRunStatus: (task as any).latestRun?.status ?? null,
        lastRunStatus: getTaskRunStatusText((task as any).latestRun),
      })
    }
  }

  return groupedMonitoring
})

watch(
  [
    deepLinkedDatastreamId,
    () => tableDatastreams.value.map((datastream) => datastream.id).join(','),
  ],
  () => {
    void scrollToTargetDatastream()
  },
  { immediate: true, flush: 'post' }
)

watch(
  search,
  () => {
    renderedDatastreamCount.value = Math.min(
      DATASTREAM_RENDER_BATCH_SIZE,
      tableDatastreams.value.length
    )
  },
  { flush: 'post' }
)

watch(
  [renderedDatastreamCount, () => tableDatastreams.value.length],
  () => {
    renderedDatastreamCount.value = Math.min(
      Math.max(renderedDatastreamCount.value, DATASTREAM_RENDER_BATCH_SIZE),
      tableDatastreams.value.length
    )
    void observeLoadMoreTrigger()
  },
  { immediate: true, flush: 'post' }
)

onBeforeUnmount(() => {
  if (highlightTimeout) window.clearTimeout(highlightTimeout)
  loadMoreObserver?.disconnect()
})

const onDownload = async (datastreamId: string) => {
  if (downloading[datastreamId]) return
  downloading[datastreamId] = true

  try {
    await downloadDatastreamCsv(datastreamId)
  } catch (err: any) {
    console.error('Error downloading datastream CSV', err)
    Snackbar.error(err.message)
  } finally {
    downloading[datastreamId] = false
  }
}

async function toggleDataVisibility(computedDatastream: Datastream) {
  // mutate the original
  const datastream = items.value.find((d) => d.id === computedDatastream.id)
  if (!datastream) return

  const previousIsVisible = datastream.isVisible
  const previousIsPrivate = datastream.isPrivate
  datastream.isVisible = !datastream.isVisible
  if (datastream.isVisible) datastream.isPrivate = false
  const didPersist = await patchDatastream({
    id: datastream.id,
    isPrivate: datastream.isPrivate,
    isVisible: datastream.isVisible,
  })
  if (!didPersist) {
    datastream.isVisible = previousIsVisible
    datastream.isPrivate = previousIsPrivate
  }
}

async function toggleVisibility(computedDatastream: Datastream) {
  // mutate the original
  const datastream = items.value.find((d) => d.id === computedDatastream.id)
  if (!datastream) return

  const previousIsVisible = datastream.isVisible
  const previousIsPrivate = datastream.isPrivate
  datastream.isPrivate = !datastream.isPrivate
  datastream.isVisible = !datastream.isPrivate
  const didPersist = await patchDatastream({
    id: datastream.id,
    isPrivate: datastream.isPrivate,
    isVisible: datastream.isVisible,
  })
  if (!didPersist) {
    datastream.isVisible = previousIsVisible
    datastream.isPrivate = previousIsPrivate
  }
}

const patchDatastream = async <T extends { id: string }>(patchBody: T) => {
  try {
    await hs.datastreams.update(patchBody)
    return true
  } catch (error) {
    console.error('Error updating datastream', error)
    return false
  }
}

async function onObservationsDelete() {
  try {
    await hs.datastreams.deleteObservations(item.value.id)
    items.value = []
    await loadDatastreams()
  } catch (error) {
    console.error('Failed to delete observations', error)
    Snackbar.error('Failed to delete observations')
  }
  openObservationsDelete.value = false
}

const loadDatastreams = async () => {
  try {
    items.value = await hs.datastreams.listAllItems({
      monitoring_site_id: [monitoringSite.value!.id],
    })
  } catch (e) {
    console.error('Error fetching datastreams', e)
  }
}
</script>

<style scoped>
/* Datastream list — plain card list (replaces the Vuetify data table for full
   layout control), modelled on the Claude Design "strip" prototype. */
.datastream-list {
  --datastream-list-grid: minmax(0, 1.1fr) minmax(0, 1.3fr) 10.75rem;
  --datastream-list-inline: calc(0.75rem + 1px + 0.85rem);
  padding: 0 0 0.75rem;
  background: #fafbfc;
  overflow: visible;
}

.datastream-list__head {
  position: sticky;
  top: 0;
  z-index: 1;
  display: grid;
  grid-template-columns: var(--datastream-list-grid);
  gap: 1.25rem;
  padding: 0.5rem var(--datastream-list-inline);
  background: rgb(var(--v-theme-surface));
  border-bottom: 1px solid #e2e5e9;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.56);
}

.datastream-list__head-actions {
  text-align: right;
}

.ds-card {
  margin: 0.5rem 0.75rem 0;
  background: #fff;
  border: 1px solid #e2e5e9;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.ds-card--highlighted {
  border-color: #1565c0;
  box-shadow: 0 0 0 2px rgba(21, 101, 192, 0.18);
}

.ds-card__grid {
  display: grid;
  grid-template-columns: var(--datastream-list-grid);
  gap: 1.25rem;
  padding: 0.6rem 0.85rem;
}

.ds-card__grid > .datastream-actions {
  align-items: flex-end;
}

.datastream-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  padding: 0.75rem 1rem;
  background: rgb(var(--v-theme-secondary));
  color: rgb(var(--v-theme-on-secondary));
  border-radius: 12px 12px 0 0;
}

.datastream-toolbar__left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex: 1 1 420px;
  min-width: 220px;
}

.datastream-toolbar__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-left: auto;
}

.datastream-toolbar__title {
  margin: 0;
  line-height: 1.2;
  color: inherit;
}

.datastream-toolbar :deep(.v-field__input) {
  color: rgb(var(--v-theme-on-secondary));
}

.datastream-toolbar :deep(.v-field__prepend-inner) {
  color: rgba(var(--v-theme-on-secondary), 0.8);
}

.datastream-toolbar :deep(.v-label) {
  color: rgba(var(--v-theme-on-secondary), 0.8);
}

.datastream-toolbar :deep(.v-field__outline__start),
.datastream-toolbar :deep(.v-field__outline__end) {
  border-color: rgba(var(--v-theme-on-secondary), 0.5);
}

.datastream-toolbar :deep(.v-field__outline__notch) {
  border-color: rgba(var(--v-theme-on-secondary), 0.5);
}

.datastream-toolbar :deep(.v-field__clearable) {
  color: rgba(var(--v-theme-on-secondary), 0.9);
}

.datastream-search {
  max-width: 260px;
  min-width: 200px;
  flex: 0 1 260px;
}

@media (max-width: 1200px) {
  .datastream-toolbar__left {
    flex-direction: column;
    align-items: flex-start;
  }

  .datastream-search {
    max-width: 100%;
    flex: 1 1 100%;
  }
}

.datastream-latest {
  display: flex;
  flex-direction: column;
  padding-top: 0;
}

.datastream-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.6rem;
}

.datastream-card {
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.datastream-card--highlighted {
  border-color: #1565c0;
  box-shadow: 0 0 0 2px rgba(21, 101, 192, 0.18);
}

.datastream-card__content {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.datastream-card__icons {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.datastream-card__actions {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.datastream-card__meta-btn {
  align-self: flex-start;
}

.datastream-title {
  max-width: 360px;
  overflow-wrap: anywhere;
}

.datastream-info-list,
.datastream-time-list {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding-top: 0;
}

.datastream-line {
  margin: 0;
  line-height: 1.3;
}

.datastream-id {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.datastream-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.datastream-actions__icons {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 32px;
  flex-wrap: wrap;
}

.datastream-download {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.datastream-task-link {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  width: 100%;
  margin-top: 0.75rem;
  padding: 0.55rem 0.65rem;
  border-left: 3px solid #546e7a;
  border-radius: 6px;
  background: #eceff1;
  color: rgba(0, 0, 0, 0.87);
}

/* Task strip sits flush at the bottom of each card as an integral footer. */
.datastream-task-link--card {
  margin-top: 0;
  border-radius: 0;
  width: 100%;
  padding: 0.45rem 0.85rem;
  border-top: 1px solid #eef0f3;
}

.datastream-task-link--ok {
  border-left-color: #357a38;
  background: #e8f5e9;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--attention,
.datastream-task-link--conflict {
  border-left-color: #c62828;
  background: #fdecea;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--pending {
  border-left-color: #1769aa;
  background: #e3f1fd;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--behind {
  border-left-color: #e65100;
  background: #fff3e0;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--none {
  border-left-color: #546e7a;
  background: #eceff1;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--loading {
  border-left-color: #90a4ae;
  background: #f3f6f8;
  color: rgba(0, 0, 0, 0.38);
}

.datastream-task-link__loading-icon,
.datastream-task-link__loading-bar {
  display: block;
  flex: none;
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    rgba(120, 144, 156, 0.14) 0%,
    rgba(120, 144, 156, 0.28) 42%,
    rgba(120, 144, 156, 0.14) 82%
  );
  background-size: 220% 100%;
  animation: datastream-task-skeleton 1.4s ease-in-out infinite;
}

.datastream-task-link__loading-icon {
  width: 1.1rem;
  height: 1.1rem;
}

.datastream-task-link__loading-bar {
  height: 0.48rem;
}

.datastream-task-link__loading-bar--label {
  width: 8rem;
  max-width: 38%;
}

.datastream-task-link__loading-bar--name {
  width: 20rem;
  max-width: 68%;
}

.datastream-task-link__icon--source {
  color: #2196f3 !important;
}

.datastream-task-link__icon--derived {
  color: #6a1b9a !important;
}

.datastream-task-link__icon--aggregation {
  color: #6a1b9a !important;
}

.datastream-task-link__icon--rating-curve {
  color: #283593 !important;
}

.datastream-task-link__icon--monitoring,
.datastream-task-link__monitoring-icon {
  color: #00695c !important;
}

.datastream-task-link__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.datastream-task-link__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.45rem 0.85rem;
}

.datastream-task-link__label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: rgba(0, 0, 0, 0.42);
}

.datastream-task-link__name {
  color: rgba(0, 0, 0, 0.87);
  text-decoration: none;
}

.datastream-task-link__name:hover,
.datastream-task-link__tasks a:hover {
  text-decoration: underline;
}

.datastream-task-link__status {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.datastream-task-link__dot {
  display: inline-block;
  width: 0.44rem;
  height: 0.44rem;
  border-radius: 50%;
  flex: none;
}

.datastream-task-link__last-ran {
  white-space: nowrap;
  color: rgba(0, 0, 0, 0.42);
}

.datastream-task-link__tasks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.75rem;
}

.datastream-task-link__tasks a {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.datastream-task-link__monitoring {
  display: flex;
  align-items: center;
  flex: 0 0 100%;
  gap: 0.75rem;
}

.datastream-task-link__monitoring-body {
  display: flex;
  align-items: center;
  flex: 1;
  flex-wrap: wrap;
  gap: 0.35rem 0.65rem;
  min-width: 0;
}

.datastream-task-link__monitoring-task {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.datastream-task-link__monitoring-task
  + .datastream-task-link__monitoring-task {
  padding-left: 0.65rem;
  border-left: 1px solid rgba(0, 105, 92, 0.24);
}

.datastream-task-link__quality-outcome {
  padding: 0.08rem 0.4rem;
  border-radius: 999px;
  white-space: nowrap;
}

.datastream-task-link__quality-outcome--ok {
  background: #e8f5e9;
  color: #2e7d32;
}

.datastream-task-link__quality-outcome--violations {
  background: #fdecea;
  color: #b71c1c;
}

.datastream-task-link__quality-outcome--unknown {
  background: #eceff1;
  color: #546e7a;
}

@keyframes datastream-task-skeleton {
  0% {
    background-position: 120% 0;
  }

  100% {
    background-position: -120% 0;
  }
}

@media (max-width: 960px) {
  .datastream-search {
    max-width: 100%;
    flex: 1 1 100%;
  }
}

@media (max-width: 700px) {
  .datastream-toolbar__left,
  .datastream-toolbar__actions {
    width: 100%;
  }

  .datastream-toolbar__left {
    flex-direction: column;
    align-items: stretch;
  }

  .datastream-toolbar__actions {
    justify-content: flex-start;
  }

  .datastream-toolbar__actions :deep(.v-btn) {
    width: 100%;
    justify-content: center;
  }

  .datastream-info-list,
  .datastream-time-list {
    gap: 0.35rem;
  }

  .datastream-copy-btn {
    min-width: 40px;
    min-height: 40px;
  }
}

@media (min-width: 961px) {
  .datastream-info-list,
  .datastream-time-list {
    gap: 0.2rem;
  }
}
/* Site details datastream table */
.site-datastreams {
  min-width: 0;
}
.site-datastreams__disclaimer {
  margin: 0 0 var(--hs-space-8);
  color: var(--hs-error);
}
.site-datastreams__tools {
  flex-wrap: wrap;
  align-items: flex-end;
}
.site-datastreams__tools-primary,
.site-datastreams__heading,
.site-datastreams__table-controls,
.site-datastreams__filter-header-content,
.site-datastreams__filters,
.site-datastreams__row-actions,
.site-datastreams__private-data,
.site-datastreams__latest {
  display: flex;
  align-items: center;
}
.site-datastreams__tools-primary {
  flex: 1 1 28rem;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--hs-space-12);
}
.site-datastreams__heading {
  gap: var(--hs-space-8);
  align-items: baseline;
}
.site-datastreams__heading h2 {
  margin: 0;
}
.site-datastreams__count,
.site-datastreams__latest,
.site-datastreams__details dt,
.site-datastreams__empty,
.site-datastreams__private-data {
  color: var(--hs-text-secondary);
}
.site-datastreams__tools :deep(.hs-query-search) {
  flex: 1 0 100%;
  width: 100%;
  max-width: none;
  margin-left: 0;
}
.site-datastreams__table {
  width: 100%;
  border-collapse: collapse;
}
.site-datastreams__table-controls {
  padding: var(--hs-space-6) var(--hs-space-8);
  background: var(--hs-surface-muted);
  border-bottom: 1px solid var(--hs-border);
}
.site-datastreams__filter-header-content {
  justify-content: space-between;
  gap: var(--hs-space-8);
}
.site-datastreams__filters {
  flex-wrap: wrap;
  gap: var(--hs-space-4);
}
.site-datastreams__filter-button,
.site-datastreams__sort-button {
  color: var(--hs-text-primary);
  text-transform: none;
}
.site-datastreams__filter-button--active {
  color: rgb(var(--v-theme-primary)) !important;
}
.site-datastreams__filter-count {
  min-width: var(--hs-space-16);
  padding-inline: var(--hs-space-4);
  color: rgb(var(--v-theme-on-primary));
  font-size: var(--hs-font-2xs);
  line-height: var(--hs-space-16);
  text-align: center;
  background: rgb(var(--v-theme-primary));
  border-radius: var(--hs-radius-pill);
}
.site-datastreams__table tbody tr {
  border-bottom: 1px solid var(--hs-border);
}
.site-datastreams__table tbody tr:hover {
  background: var(--hs-surface-muted);
}
.site-datastreams__row--highlighted {
  background: rgb(var(--v-theme-primary) / 0.08) !important;
}
.site-datastreams__table td {
  padding: var(--hs-space-12);
  vertical-align: top;
}
.site-datastreams__name-cell {
  width: 24%;
  min-width: 11rem;
}
.site-datastreams__name {
  overflow: hidden;
  color: var(--hs-text-primary);
  font-weight: var(--hs-font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.site-datastreams__observations-cell {
  min-width: 16rem;
}
.site-datastreams__sparkline {
  min-width: 13rem;
}
.site-datastreams__latest {
  flex-wrap: wrap;
  gap: var(--hs-space-8);
  margin-top: var(--hs-space-4);
  font-family: var(--hs-font-data);
  font-size: var(--hs-font-2xs);
}
.site-datastreams__latest--stale {
  color: var(--hs-text-muted);
}
.site-datastreams__latest--error {
  color: var(--hs-error);
}
.site-datastreams__latest--success {
  color: var(--hs-success);
}
.site-datastreams__private-data {
  gap: var(--hs-space-6);
  min-height: var(--hs-space-32);
}
.site-datastreams__actions-cell {
  width: 1%;
  white-space: nowrap;
}
.site-datastreams__row-actions {
  justify-content: flex-end;
  gap: var(--hs-space-2);
}
.site-datastreams__metadata-button {
  width: 100%;
  margin-top: var(--hs-space-6);
}
.site-datastreams__download {
  display: flex;
  gap: var(--hs-space-6);
  align-items: center;
  margin-top: var(--hs-space-6);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-2xs);
}
.site-datastreams__empty {
  padding: var(--hs-space-16) !important;
  text-align: center;
}
.site-datastreams__filter-menu,
.site-datastreams__sort-menu {
  min-width: 17rem;
  max-height: 20rem;
  padding-block: var(--hs-space-8);
  overflow-y: auto;
}
.site-datastreams__filter-menu-title,
.site-datastreams__sort-menu-title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-semibold);
}
.site-datastreams__filter-search {
  margin: 0 var(--hs-space-12) var(--hs-space-8);
}
.site-datastreams__clear-filter {
  color: rgb(var(--v-theme-primary));
  border-top: 1px solid var(--hs-border);
}
.site-datastreams__filter-empty {
  padding: var(--hs-space-12) var(--hs-space-16);
  color: var(--hs-text-secondary);
}
.site-datastreams__sort-check--hidden {
  visibility: hidden;
}
@media (max-width: 60rem) {
  .site-datastreams__table,
  .site-datastreams__table tbody,
  .site-datastreams__table tr,
  .site-datastreams__table td {
    display: block;
    width: 100%;
  }
  .site-datastreams__table tbody tr {
    padding: var(--hs-space-12);
  }
  .site-datastreams__table td {
    padding: var(--hs-space-6) 0;
  }
  .site-datastreams__name-cell {
    padding-top: 0 !important;
  }
  .site-datastreams__actions-cell {
    padding-bottom: 0 !important;
  }
  .site-datastreams__row-actions {
    justify-content: flex-start;
  }
}
@media (max-width: 40rem) {
  .site-datastreams__tools-primary,
  .site-datastreams__filter-header-content {
    align-items: flex-start;
    flex-direction: column;
  }
  .site-datastreams__sparkline {
    min-width: 0;
  }
}
</style>
