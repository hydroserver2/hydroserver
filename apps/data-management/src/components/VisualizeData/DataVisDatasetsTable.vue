<template>
  <section class="datastreams-panel" aria-labelledby="datastreams-heading">
    <div class="hs-table-tools datastreams-tools">
      <div class="datastreams-tools__primary">
        <div class="datastreams-heading">
          <h2 id="datastreams-heading" class="hs-subheading">Datastreams</h2>
          <span class="datastreams-count hs-text-sm">
            {{ tableItems.length }} available ·
            {{ plottedDatastreams.length }}/5 selected
          </span>
        </div>

        <div class="hs-table-actions datastreams-actions">
          <v-btn
            size="small"
            variant="text"
            :disabled="!plottedDatastreams.length"
            data-testid="clear-selected-datastreams"
            @click="clearSelected"
          >
            Clear selected
          </v-btn>

          <v-btn
            size="small"
            variant="outlined"
            data-testid="toggle-selected-datastreams"
            @click="showOnlySelected = !showOnlySelected"
          >
            {{ showOnlySelected ? 'Show all' : 'Show selected' }}
          </v-btn>

          <v-btn-primary
            size="small"
            :loading="downloading"
            :disabled="!plottedDatastreams.length"
            :prepend-icon="mdiDownload"
            data-testid="download-selected-datastreams"
            @click="downloadSelected(plottedDatastreams)"
          >
            Download selected
          </v-btn-primary>

          <v-menu :close-on-content-click="false" location="bottom end">
            <template #activator="{ props: menuProps }">
              <v-tooltip
                text="Choose row details"
                location="top"
                :open-delay="0"
                :close-delay="0"
              >
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="{ ...menuProps, ...tooltipProps }"
                    :icon="mdiTableColumnWidth"
                    variant="text"
                    size="small"
                    class="hs-table-icon-action"
                    aria-label="Choose row details"
                  />
                </template>
              </v-tooltip>
            </template>

            <v-card class="datastream-details-menu">
              <div class="datastream-details-menu__title hs-text-sm">
                Row details
              </div>
              <v-list density="compact" class="py-1">
                <v-list-item
                  v-for="header in selectableHeaders"
                  :key="header.key"
                  @click="toggleHeader(header.key)"
                >
                  <template #prepend>
                    <v-checkbox-btn
                      :model-value="selectedHeaders.includes(header.key)"
                      :aria-label="`Toggle ${header.title}`"
                      color="primary"
                      @update:model-value="toggleHeader(header.key)"
                      @click.stop
                    />
                  </template>
                  <v-list-item-title>{{ header.title }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-card>
          </v-menu>
        </div>
      </div>

      <div class="datastreams-search">
        <HsQuerySearchInput
          v-model="search"
          placeholder="Search datastreams…"
          aria-label="Search"
          :qualifiers="searchQualifiers"
        />
      </div>
    </div>

    <div class="hs-table-card datastreams-table-card">
      <table class="datastreams-table hs-text-sm">
        <thead>
          <tr>
            <th colspan="3" class="datastream-filter-header">
              <DataVisTableFilters />
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="item in visibleTableItems"
            :key="item.id"
            @click="openMetadata(item)"
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
              <button
                type="button"
                class="datastream-name"
                @click.stop="openMetadata(item)"
              >
                {{ item.name || 'Unnamed datastream' }}
              </button>
              <div class="datastream-meta hs-text-sm">
                <span
                  v-if="isDetailVisible('siteCodeName')"
                  class="datastream-meta__item"
                >
                  <span class="datastream-meta__label hs-label">Site</span>
                  {{ item.siteCodeName || '—' }}
                </span>
                <span
                  v-if="isDetailVisible('observedPropertyName')"
                  class="datastream-meta__item"
                >
                  <span class="datastream-meta__label hs-label">Property</span>
                  {{ item.observedPropertyName || '—' }}
                </span>
                <span
                  v-if="isDetailVisible('qualityControlLevelDefinition')"
                  class="datastream-meta__item"
                >
                  <span class="datastream-meta__label hs-label"
                    >Processing</span
                  >
                  {{ item.qualityControlLevelDefinition || '—' }}
                </span>
                <span
                  v-if="isDetailVisible('valueCount')"
                  class="datastream-meta__item datastream-meta__item--data"
                >
                  <span class="datastream-meta__label hs-label"
                    >Observations</span
                  >
                  {{ formatObservationCount(item.valueCount) }}
                </span>
                <span
                  v-if="isDetailVisible('phenomenonEndTime')"
                  class="datastream-meta__item datastream-meta__item--data"
                >
                  <span class="datastream-meta__label hs-label">Updated</span>
                  {{ formatTime(item.phenomenonEndTime) }}
                </span>
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
import { mdiChevronRight, mdiDownload, mdiTableColumnWidth } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import { useWorkspaceStore } from '@/store/workspaces'
import { downloadDatastreamsCsvZip } from '@/utils/csvExport'
import { formatTime } from '@/utils/time'
import { parseDatastreamQuery } from '@/utils/datastreamSearch'
import HsQuerySearchInput from '@/components/base/HsQuerySearchInput.vue'
import DatastreamInformationCard from './DatastreamInformationCard.vue'
import DataVisTableFilters from './DataVisTableFilters.vue'

type DatastreamTableItem = Datastream & {
  siteCodeName?: string
  observedPropertyName?: string
  qualityControlLevelDefinition?: string
}

const dataVisStore = useDataVisStore()
const {
  filteredDatastreams,
  plottedDatastreams,
  tableHeaders: headers,
  tableSearch: search,
  monitoringSites,
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
    label: 'Workspace',
    values: uniqueSorted(workspaces.value.map((item) => item.name)),
  },
  {
    key: 'site',
    label: 'Site',
    values: uniqueSorted(monitoringSites.value.map((item) => item.name)),
  },
  {
    key: 'property',
    label: 'Observed property',
    values: uniqueSorted(observedProperties.value.map((item) => item.name)),
  },
  {
    key: 'processing',
    label: 'Processing level',
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
    const observedProperty = dataVisStore.observedPropertyById.get(
      datastream.observedPropertyId
    )
    const observedPropertyCode = observedProperty?.code?.trim() ?? ''
    const observedPropertyName = observedProperty?.name?.trim() ?? ''
    const processingLevel = dataVisStore.processingLevelById.get(
      datastream.processingLevelId
    )

    return {
      ...datastream,
      siteCodeName: monitoringSite?.code,
      observedPropertyName: observedPropertyCode
        ? `${observedPropertyName} (${observedPropertyCode})`
        : observedPropertyName,
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
        item.siteCodeName,
        item.observedPropertyName,
        item.qualityControlLevelDefinition,
        item.valueCount,
        item.phenomenonEndTime,
      ].some((value) => `${value ?? ''}`.toLocaleLowerCase().includes(query))
    })
    .sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''))
})

const selectableHeaders = computed(() =>
  headers.value.filter((header) => header.key !== 'plot')
)

const selectedHeaders = computed({
  get: () =>
    headers.value
      .filter((header) => header.visible)
      .map((header) => header.key),
  set: (keys: string[]) => {
    headers.value.forEach((header) => {
      header.visible = header.key === 'plot' || keys.includes(header.key)
    })
  },
})

const isDetailVisible = (key: string) =>
  headers.value.find((header) => header.key === key)?.visible ?? true

const toggleHeader = (key: string) => {
  const keys = [...selectedHeaders.value]
  const index = keys.indexOf(key)
  if (index >= 0) keys.splice(index, 1)
  else keys.push(key)
  selectedHeaders.value = keys
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
  showOnlySelected.value = false
  plottedDatastreams.value = []
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
  flex-wrap: wrap;
  justify-content: flex-end;
}

.datastream-details-menu {
  min-width: 260px;
  padding: var(--hs-space-4) 0;
  background: var(--hs-surface);
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-md);
}

.datastream-details-menu__title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-secondary);
  font-weight: var(--hs-font-weight-semibold);
}

.datastreams-table-card {
  flex: 1;
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
  padding: var(--hs-space-8) var(--hs-space-12) var(--hs-space-10);
  text-align: left;
  background: var(--hs-surface-muted);
}

.datastreams-table thead tr,
.datastreams-table tbody tr {
  border-bottom: 1px solid var(--hs-border);
}

.datastreams-table tbody tr {
  cursor: pointer;
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
  margin: 2px 0 0;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}

.plot-checkbox:disabled {
  cursor: not-allowed;
}

.datastream-name {
  display: block;
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
  cursor: pointer;
  background: transparent;
  border: 0;
}

.datastream-name:hover {
  text-decoration: underline;
}

.datastream-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-4) var(--hs-space-12);
  align-items: center;
  margin-top: var(--hs-space-4);
  color: var(--hs-text-secondary);
}

.datastream-meta__item {
  display: inline-flex;
  gap: var(--hs-space-4);
  align-items: baseline;
  min-width: 0;
}

.datastream-meta__label {
  color: var(--hs-text-secondary);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.datastream-meta__item--data {
  font-family: var(--hs-font-data);
  white-space: nowrap;
}

.datastream-meta__item--data .datastream-meta__label {
  font-family: inherit;
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

  .datastreams-actions {
    justify-content: flex-start;
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
}
</style>
