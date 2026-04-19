<template>
  <div class="datasets-table d-flex flex-column">
    <v-toolbar flat density="compact" class="datasets-table__toolbar px-2">
      <div class="d-flex align-center gap-2" style="min-width: 0;">
        <v-icon icon="mdi-database" color="primary" size="18" />
        <span class="text-body-2 font-weight-bold">Datastreams</span>
        <v-chip
          size="x-small"
          :color="plottedDatastreams.length ? 'primary' : undefined"
          :variant="plottedDatastreams.length ? 'tonal' : 'outlined'"
          label
        >
          {{ plottedDatastreams.length }}/5 plotted
        </v-chip>
      </div>

      <v-text-field
        class="datasets-table__search mx-3 flex-grow-1"
        clearable
        v-model="search"
        prepend-inner-icon="mdi-magnify"
        placeholder="Search datastreams…"
        hide-details
        density="compact"
        variant="outlined"
      />

      <v-menu location="bottom end" :close-on-content-click="false">
        <template #activator="{ props: menuProps }">
          <v-btn
            v-bind="menuProps"
            icon="mdi-dots-vertical"
            size="small"
            variant="text"
            aria-label="Table options"
            title="Table options"
          />
        </template>

        <v-card min-width="260" class="py-1">
          <v-list density="compact" nav>
            <v-list-item
              prepend-icon="mdi-close-circle-outline"
              :disabled="!plottedDatastreams.length"
              @click="clearSelected"
            >
              <v-list-item-title>Clear selected</v-list-item-title>
            </v-list-item>

            <v-list-item
              :prepend-icon="
                showOnlySelected ? 'mdi-filter' : 'mdi-filter-outline'
              "
              @click="showOnlySelected = !showOnlySelected"
            >
              <v-list-item-title>
                {{ showOnlySelected ? 'Show all' : 'Show selected only' }}
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              prepend-icon="mdi-download"
              :disabled="!plottedDatastreams.length || downloading"
              @click="downloadSelected(plottedDatastreams)"
            >
              <v-list-item-title>
                {{ downloading ? 'Downloading…' : 'Download selected' }}
              </v-list-item-title>
            </v-list-item>
          </v-list>

          <v-divider />

          <div class="pa-3">
            <div class="text-caption text-medium-emphasis mb-1">
              Visible columns
            </div>
            <v-checkbox
              v-for="h in selectableHeaders"
              :key="h.key"
              density="compact"
              hide-details
              :label="h.title"
              :model-value="h.visible"
              @update:model-value="h.visible = !!$event"
            />
          </div>
        </v-card>
      </v-menu>
    </v-toolbar>

    <v-divider />

    <div class="datasets-table__body flex-grow-1 d-flex flex-column">
      <v-data-table-virtual
        data-testid="datastreams-table"
        :headers="headers.filter((header) => header.visible)"
        :items="tableItems"
        :sort-by="sortBy"
        multi-sort
        :search="search"
        style="height: 0"
        class="datasets-table__table flex-grow-1"
        fixed-header
        color="secondary"
        density="compact"
        :row-props="getRowProps"
        @click:row="onRowClick"
        hover
      >
        <template #item.status="{ item }">
          <v-progress-circular
            v-if="loadingStates.get(item.id)"
            color="primary"
            size="small"
            indeterminate
          ></v-progress-circular>
          <template v-else-if="!!observationsRaw[item.id]">
            <v-icon
              color="primary"
              :title="`${observationsRaw[item.id].datetimes.length} observation(s)`"
              >mdi-database-check</v-icon
            >
          </template>
        </template>
        <template v-slot:item.plot="{ item }">
          <v-tooltip
            :disabled="!isAtCap(item)"
            location="top"
            text="Maximum of 5 datastreams plotted — remove one to add another"
          >
            <template #activator="{ props: tooltipProps }">
              <button
                v-bind="tooltipProps"
                type="button"
                class="plot-check"
                :class="{
                  'plot-check--checked': isChecked(item),
                  'plot-check--disabled': isAtCap(item),
                }"
                :data-testid="`plot-checkbox-${item.id}`"
                :aria-disabled="isAtCap(item)"
                :aria-pressed="isChecked(item)"
                :aria-label="
                  isChecked(item) ? 'Remove from plot' : 'Add to plot'
                "
                @click.stop="!isAtCap(item) && toggleDatastream(item)"
              >
                <v-icon
                  :icon="
                    isChecked(item)
                      ? 'mdi-checkbox-marked'
                      : 'mdi-checkbox-blank-outline'
                  "
                  size="20"
                />
              </button>
            </template>
          </v-tooltip>
        </template>
      </v-data-table-virtual>
    </div>

    <v-dialog v-model="openInfoCard" width="50rem" v-if="selectedDatastream">
      <DatastreamInformationCard
        :datastream="selectedDatastream"
        @close="openInfoCard = false"
      />
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { computed, reactive, ref } from 'vue'
import DatastreamInformationCard from './DatastreamInformationCard.vue'
import { useObservationStore } from '@/store/observations'
import { Datastream } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
const { observationsRaw } = storeToRefs(useObservationStore())
const { loadingStates } = storeToRefs(useDataVisStore())
const { hs } = storeToRefs(useHydroServer())

const {
  things,
  filteredDatastreams,
  plottedDatastreams,
  observedProperties,
  processingLevels,
} = storeToRefs(useDataVisStore())
const { toggleDatastream } = useDataVisStore()

const showOnlySelected = ref(false)
const openInfoCard = ref(false)
const downloading = ref(false)
const selectedDatastream = ref<Datastream | null>(null)

const downloadSelected = async (plottedDatastreams: Datastream[]) => {
  downloading.value = true
  try {
    await hs.value.datastreams.downloadCsvBatchZip(plottedDatastreams)
  } catch (error) {
    console.error('Error downloading selected datastreams', error)
  }
  downloading.value = false
}

const onRowClick = (event: Event, item: any) => {
  // If the click came from a checkbox, do nothing.
  const targetElement = event.target as HTMLElement
  if (targetElement.id && targetElement.id.startsWith('checkbox-')) return

  const selectedDatastreamId = item.item.id
  const foundDatastream = filteredDatastreams.value.find(
    (d) => d.id === selectedDatastreamId
  )
  if (foundDatastream) {
    selectedDatastream.value = foundDatastream
    openInfoCard.value = true
  } else selectedDatastream.value = null
}

const displayDatastreams = computed(() => {
  // Guard against `filteredDatastreams` being momentarily undefined
  // (workspace-switch transition, store-reset race) — `.map` on
  // undefined throws during render.
  const rows = filteredDatastreams.value ?? []
  if (showOnlySelected.value) {
    return rows.filter((ds) =>
      plottedDatastreams.value.some((sds) => sds.id === ds.id)
    )
  }
  return rows
})

const tableItems = computed(() => {
  // Defensive optional-chaining: these nested fields come from
  // `expand_related: true` on the datastream fetch. During a catalog
  // refresh (workspace switch, re-fetch after plot changes) the store
  // can briefly hold rows whose related objects haven't landed yet —
  // dereferencing `ds.thing.samplingFeatureCode` then threw, which
  // surfaced as an error during table render and tore the whole
  // `v-data-table-virtual` out of the DOM. Falling back to an empty
  // string keeps the row visible (and sort-stable).
  return displayDatastreams.value.map((ds) => {
    return {
      ...ds,
      siteCodeName: ds.thing?.samplingFeatureCode ?? '',
      observedPropertyName: ds.observedProperty?.name ?? '',
      qualityControlLevelDefinition: ds.processingLevel?.definition ?? '',
    }
  })
})

function clearSelected() {
  showOnlySelected.value = false
  plottedDatastreams.value = []
}

const isChecked = (item: Datastream) =>
  plottedDatastreams.value.some((sds) => sds.id === item.id)

/**
 * True when the plot is at its 5-stream cap and this row is not already
 * one of the plotted streams — so its checkbox should read as disabled
 * and the whole row should dim.
 */
const isAtCap = (item: Datastream) =>
  plottedDatastreams.value.length >= 5 && !isChecked(item)

const getRowProps = ({ item }: { item: Datastream }) => ({
  class: { 'datasets-table__row--at-cap': isAtCap(item) },
})

const search = ref()
const headers = reactive([
  { title: '', key: 'status', visible: true, width: 1 },
  { title: 'Plot', key: 'plot', visible: true, width: 1 },
  // { title: 'Select', key: 'select', visible: true, width: 1 },
  {
    title: 'Site code',
    key: 'siteCodeName',
    visible: true,
  },
  {
    title: 'Observed property',
    key: 'observedPropertyName',
    visible: true,
  },
  {
    title: 'Processing level',
    key: 'qualityControlLevelDefinition',
    visible: true,
  },
  {
    title: 'Number observations',
    key: 'valueCount',
    visible: true,
  },
  {
    title: 'Date last updated',
    key: 'phenomenonEndTime',
    visible: true,
  },
])

const selectableHeaders = computed(() => {
  return headers.filter(
    (header) => !['plot', 'select', 'status'].includes(header.key)
  )
})

const sortBy = [
  { key: 'siteCodeName' },
  { key: 'observedPropertyName' },
  { key: 'qualityControlLevelDefinition' },
  // { key: 'valueCount', order: 'desc' },
]
</script>

<style scoped lang="scss">
.datasets-table {
  min-height: 0;
}

.datasets-table__toolbar {
  background-color: rgb(var(--v-theme-surface));
}

.datasets-table__body {
  min-height: 0;
}

:deep(.v-table .v-data-table__tr:nth-child(even) td) {
  background: #f7f7f7;
}

:deep(tbody tr:hover > td) {
  background-color: rgba(var(--v-theme-primary), 0.05) !important;
}

/* When the 5/5 plot cap is hit, make rows whose checkbox is disabled
   read as clearly unavailable — dim all row content and switch the
   cursor away from the row-level click affordance. The checkbox's own
   styling is amplified below. */
:deep(tbody tr.datasets-table__row--at-cap > td) {
  opacity: 0.45;
  cursor: not-allowed;
}

:deep(tbody tr.datasets-table__row--at-cap:hover > td) {
  background-color: transparent !important;
}

/* Custom plot-column "checkbox" — rendered as a button + icon so we
   have complete control over its visual states (Vuetify's
   `.v-selection-control` internals changed between minor versions and
   were fighting the previous override). */
.plot-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: rgba(var(--v-theme-on-surface), 0.6);
  transition: background-color 120ms ease, color 120ms ease;
}

.plot-check:hover {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.plot-check--checked {
  color: rgb(var(--v-theme-primary));
}

.plot-check--disabled,
.plot-check--disabled:hover {
  color: rgba(var(--v-theme-on-surface), 0.25);
  background-color: transparent;
  cursor: not-allowed;
}
</style>
