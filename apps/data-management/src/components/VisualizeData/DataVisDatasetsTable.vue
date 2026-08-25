<template>
  <section class="datastreams-panel" aria-labelledby="datastreams-heading">
    <div class="hs-table-tools datastreams-tools">
      <div class="datastreams-tools__primary">
        <div class="datastreams-heading">
          <h2 id="datastreams-heading" class="hs-subheading">Datastreams</h2>
          <span class="datastreams-count hs-text-sm">
            {{ tableItems.length }} available
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
            :disabled="detailLevel === 3"
            data-testid="show-more-datastream-details"
            @click="detailLevel++"
          >
            More detail
          </v-btn>
        </div>
      </div>

      <div class="datastreams-search">
        <HsQuerySearchInput
          v-model="search"
          placeholder="Search datastreams…"
          aria-label="Search"
          :qualifiers="searchQualifiers"
          @clear="clearSearchAndSelection"
        />
      </div>
    </div>

    <div class="hs-table-card datastreams-table-card">
      <table class="datastreams-table hs-text-sm">
        <thead>
          <tr v-if="plottedDatastreams.length">
            <th colspan="3" class="datastream-selection-header">
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
                  <span>
                    {{ plottedDatastreams.length }} of 5 selected
                  </span>
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
            </th>
          </tr>
          <tr v-else>
            <th colspan="3" class="datastream-filter-header">
              <DataVisTableFilters />
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="item in visibleTableItems"
            :key="item.id"
          >
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
              <div
                class="datastream-name"
                :title="datastreamDisplayName(item)"
              >
                <span
                  v-if="showMonitoringSiteContext && item.monitoringSiteName"
                  class="datastream-name__thing"
                >
                  {{ item.monitoringSiteName }}
                </span>
                <span
                  v-if="showMonitoringSiteContext && item.monitoringSiteName"
                  class="datastream-name__separator"
                  aria-hidden="true"
                >
                  /
                </span>
                <span class="datastream-name__primary">
                  {{ datastreamName(item) }}
                </span>
              </div>
              <div
                v-if="detailLevel >= 2"
                class="datastream-meta datastream-signature hs-text-sm"
              >
                <span
                  v-for="value in datastreamSignature(item)"
                  :key="`${item.id}-${value}`"
                  class="datastream-signature__item"
                >
                  {{ value }}
                </span>
              </div>
              <div
                v-if="detailLevel === 3"
                class="datastream-meta datastream-observation-range hs-text-sm"
              >
                {{ observationRange(item) }}
              </div>
            </td>

            <td class="datastream-actions-cell">
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
            </td>
          </tr>

          <tr v-if="!visibleTableItems.length">
            <td colspan="3" class="datastreams-empty hs-text-sm">
              No datastreams match the current filters.
            </td>
          </tr>
        </tbody>
      </table>
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
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Datastream, MonitoringSite } from '@hydroserver/client'
import { mdiChevronRight, mdiDownload } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import { useWorkspaceStore } from '@/store/workspaces'
import { downloadDatastreamsCsvZip } from '@/utils/csvExport'
import { formatTime } from '@/utils/time'
import { parseDatastreamQuery } from '@/utils/datastreamSearch'
import HsQuerySearchInput from '@/components/base/HsQuerySearchInput.vue'
import DatastreamInformationCard from './DatastreamInformationCard.vue'
import DataVisTableFilters from './DataVisTableFilters.vue'

type DatastreamTableItem = Datastream & {
  monitoringSiteName?: string
  qualityControlLevelDefinition?: string
  unitSymbol?: string
}

const dataVisStore = useDataVisStore()
const {
  filteredDatastreams,
  plottedDatastreams,
  tableSearch: search,
  datastreamDetailLevel: detailLevel,
  monitoringSites,
  selectedMonitoringSites,
  selectedWorkspaces,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
  observedProperties,
  processingLevels,
} = storeToRefs(dataVisStore)
const { workspaces } = storeToRefs(useWorkspaceStore())

const showOnlySelected = ref(false)
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
    key: 'processing-level',
    label: 'Processing levels',
    values: uniqueSorted(processingLevels.value.map((item) => item.definition)),
  },
])
const plainSearch = computed(() => parseDatastreamQuery(search.value).text)

const displayDatastreams = computed(() => {
  if (!showOnlySelected.value) return filteredDatastreams.value
  return filteredDatastreams.value.filter((datastream) =>
    plottedDatastreams.value.some((selected) => selected.id === datastream.id)
  )
})

const tableItems = computed<DatastreamTableItem[]>(() =>
  displayDatastreams.value.map((datastream) => {
    const monitoringSite = dataVisStore.monitoringSiteById.get(
      datastream.monitoringSiteId
    )
    const processingLevel = dataVisStore.processingLevelById.get(
      datastream.processingLevelId
    )

    return {
      ...datastream,
      monitoringSiteName: monitoringSite?.name,
      qualityControlLevelDefinition: processingLevel?.definition,
    }
  })
)

const visibleTableItems = computed(() => {
  const query = plainSearch.value.trim().toLocaleLowerCase()
  return tableItems.value
    .filter((item) => {
      if (!query) return true
      return [
        item.name,
        item.monitoringSiteName,
        item.qualityControlLevelDefinition,
        item.aggregationStatistic,
        item.intendedTimeSpacing,
        item.intendedTimeSpacingUnit,
        item.unitSymbol,
        item.valueCount,
        item.phenomenonEndTime,
      ].some((value) => `${value ?? ''}`.toLocaleLowerCase().includes(query))
    })
    .sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''))
})

const showMonitoringSiteContext = computed(
  () => selectedMonitoringSites.value.length !== 1
)

const datastreamName = (item: DatastreamTableItem) =>
  item.name?.trim() || 'Unnamed datastream'

const datastreamDisplayName = (item: DatastreamTableItem) => {
  const name = datastreamName(item)
  return showMonitoringSiteContext.value && item.monitoringSiteName
    ? `${item.monitoringSiteName} / ${name}`
    : name
}

type TimeSpacingUnit = NonNullable<Datastream['intendedTimeSpacingUnit']>

const formatIntendedTimeSpacing = (
  interval: number | string | null | undefined,
  unit: Datastream['intendedTimeSpacingUnit']
) => {
  if (interval === null || interval === undefined || !unit) return ''

  const numericInterval = Number(interval)
  if (!Number.isFinite(numericInterval)) return ''

  if (numericInterval === 1) {
    const namedPeriods: Record<TimeSpacingUnit, string> = {
      seconds: 'every second',
      minutes: 'every minute',
      hours: 'hourly',
      days: 'daily',
    }
    return namedPeriods[unit]
  }

  const abbreviations: Record<TimeSpacingUnit, string> = {
    seconds: 'sec',
    minutes: 'min',
    hours: 'hr',
    days: 'day',
  }
  return `every ${numericInterval} ${abbreviations[unit]}`
}

const datastreamSignature = (item: DatastreamTableItem) =>
  [
    item.qualityControlLevelDefinition,
    item.aggregationStatistic,
    formatIntendedTimeSpacing(
      item.intendedTimeSpacing,
      item.intendedTimeSpacingUnit
    ),
    item.unitSymbol,
  ]
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value))

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
  showOnlySelected.value = false
  plottedDatastreams.value = []
}

const clearSearchAndSelection = () => {
  search.value = ''
  selectedWorkspaces.value = []
  selectedMonitoringSites.value = []
  selectedObservedPropertyNames.value = []
  selectedProcessingLevelNames.value = []
  clearSelected()
}

const isChecked = (item: Datastream) =>
  plottedDatastreams.value.some((selected) => selected.id === item.id)

const openMetadata = (item: Datastream) => {
  selectedMonitoringSite.value =
    dataVisStore.monitoringSiteById.get(item.monitoringSiteId) ?? null
  selectedDatastream.value =
    filteredDatastreams.value.find((datastream) => datastream.id === item.id) ??
    null
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

.datastreams-actions {
  margin-left: auto;
}

.datastreams-table-card {
  flex: 0 1 auto;
  height: auto;
  max-height: 100%;
  min-height: 0;
  overflow: auto;
}

.datastreams-table {
  width: 100%;
  min-width: 100%;
  height: auto;
  border-collapse: collapse;
  table-layout: auto;
}

.datastreams-table thead {
  position: sticky;
  top: 0;
  z-index: 2;
}

.datastreams-table thead th {
  height: 48px;
  padding: var(--hs-space-8) var(--hs-space-12);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-regular);
  letter-spacing: 0;
  text-transform: none;
  background: var(--hs-surface-muted);
}

.datastreams-table .datastream-filter-header {
  height: auto;
  padding: var(--hs-space-12);
  text-align: left;
  background: var(--hs-surface-muted);
}

.datastream-selection-header {
  text-align: left;
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

.datastreams-table thead tr,
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

.plot-checkbox {
  display: block;
  width: 16px;
  height: 16px;
  margin: 4px 0 0;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}

.plot-checkbox:disabled {
  cursor: not-allowed;
}

.datastream-name {
  display: flex;
  gap: var(--hs-space-6);
  align-items: baseline;
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

.datastream-signature {
  gap: 0;
}

.datastream-signature__item:not(:first-child)::before {
  margin: 0 var(--hs-space-8);
  content: '·';
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

  .datastream-meta.datastream-signature {
    flex-direction: row;
    gap: 0;
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
