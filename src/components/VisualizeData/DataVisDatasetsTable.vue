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

            <v-divider class="my-1" />

            <v-list-item
              prepend-icon="mdi-sort-variant-remove"
              @click="resetSort"
            >
              <v-list-item-title>Reset sort</v-list-item-title>
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

    <!-- One-shot tip surfaced while nothing is plotted yet. The QC-target
         rule lives only in the right pane's empty state otherwise; users
         coming from filters into the table never see it. -->
    <div
      v-if="!plottedDatastreams.length"
      class="datasets-table__hint d-flex align-center px-3 py-1"
    >
      <v-icon icon="mdi-information-outline" size="14" class="mr-2" />
      <span class="text-caption">
        First plotted datastream becomes the
        <b>QC target</b>.
        Click a row to see its details.
      </span>
    </div>

    <div class="datasets-table__body flex-grow-1 d-flex flex-column">
      <v-data-table-virtual
        data-testid="datastreams-table"
        :headers="visibleHeaders"
        :items="tableItems"
        :sort-by="sortBy"
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
        <template #header.plot>
          <v-icon
            icon="mdi-chart-line"
            size="18"
            title="Plot"
            aria-label="Plot"
          />
        </template>

        <template v-slot:item.plot="{ item }">
          <v-tooltip
            :disabled="!isAtCap(item) && !isQc(item)"
            location="top"
            :text="
              isQc(item)
                ? 'QC target — first plotted datastream'
                : 'Maximum of 5 datastreams plotted — remove one to add another'
            "
          >
            <template #activator="{ props: tooltipProps }">
              <div class="d-flex align-center" v-bind="tooltipProps">
                <button
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
                <span v-if="isQc(item)" class="qc-pill ml-1">QC</span>
              </div>
            </template>
          </v-tooltip>
        </template>

        <template #item.siteCodeName="{ item }">
          <div class="site-cell">
            <div class="site-cell__code">{{ item.siteCodeName || '—' }}</div>
            <div v-if="item.siteName" class="site-cell__name" :title="item.siteName">
              {{ item.siteName }}
            </div>
          </div>
        </template>

        <template #item.valueCount="{ item }">
          <span class="num-cell">{{ formatCount(item.valueCount) }}</span>
        </template>

        <template #item.phenomenonEndTime="{ item }">
          <span
            class="date-cell"
            :title="item.phenomenonEndTime || ''"
          >{{ formatTableDate(item.phenomenonEndTime) }}</span>
        </template>

        <template #no-data>
          <div class="datasets-table__empty">
            <v-icon icon="mdi-database-search-outline" size="32" class="mb-2" />
            <div class="text-body-2 mb-1">No datastreams to show</div>
            <div class="text-caption text-medium-emphasis">
              Adjust the filters in the left drawer or clear the search.
            </div>
          </div>
        </template>

        <template #no-results>
          <div class="datasets-table__empty">
            <v-icon icon="mdi-magnify-close" size="32" class="mb-2" />
            <div class="text-body-2 mb-1">No matches for "{{ search }}"</div>
            <div class="text-caption text-medium-emphasis">
              Try a shorter search term or clear it to see all datastreams.
            </div>
          </div>
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
import { Datastream } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
const { hs } = storeToRefs(useHydroServer())

const { filteredDatastreams, plottedDatastreams, qcDatastream } = storeToRefs(
  useDataVisStore()
)
const { toggleDatastream, clearPlottedDatastreams } = useDataVisStore()

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
      siteName: ds.thing?.name ?? '',
      observedPropertyName: ds.observedProperty?.name ?? '',
      qualityControlLevelDefinition: ds.processingLevel?.definition ?? '',
    }
  })
})

// --- Cell formatters --------------------------------------------------------
const NUMBER_FORMATTER = new Intl.NumberFormat()
const formatCount = (n: unknown): string => {
  const v = Number(n)
  return Number.isFinite(v) ? NUMBER_FORMATTER.format(v) : '—'
}

const DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
})
const formatTableDate = (raw: unknown): string => {
  if (!raw) return '—'
  const d = new Date(raw as string)
  return Number.isNaN(d.getTime()) ? '—' : DATE_FORMATTER.format(d)
}

const clearSelected = () => {
  showOnlySelected.value = false
  void clearPlottedDatastreams()
}

const isChecked = (item: Datastream) =>
  plottedDatastreams.value.some((sds) => sds.id === item.id)

/** First-plotted datastream — the QC target. */
const isQc = (item: Datastream) => qcDatastream.value?.id === item.id

/**
 * True when the plot is at its 5-stream cap and this row is not already
 * one of the plotted streams — so its checkbox should read as disabled
 * and the whole row should dim.
 */
const isAtCap = (item: Datastream) =>
  plottedDatastreams.value.length >= 5 && !isChecked(item)

const getRowProps = ({ item }: { item: Datastream }) => ({
  class: {
    'datasets-table__row--at-cap': isAtCap(item),
    'datasets-table__row--plotted': isChecked(item),
    'datasets-table__row--qc': isQc(item),
  },
})

const search = ref()
const headers = reactive([
  { title: 'Plot', key: 'plot', visible: true, width: 64, sortable: false },
  {
    title: 'Site',
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
    title: 'Observations',
    key: 'valueCount',
    align: 'end' as const,
    cellClass: 'num-cell',
    visible: true,
  },
  {
    title: 'Last updated',
    key: 'phenomenonEndTime',
    visible: true,
  },
])

const visibleHeaders = computed(() => headers.filter((h) => h.visible))

const selectableHeaders = computed(() =>
  headers.filter((h) => !['plot'].includes(h.key))
)

// Single-sort default. Multi-sort was previously enabled but the
// priority badges Vuetify renders next to the sort caret crowded the
// header even when only one column was sorted, and the multi-column
// default (site → property → level) confused users on first paint.
const DEFAULT_SORT: Array<{ key: string; order?: 'asc' | 'desc' }> = [
  { key: 'siteCodeName', order: 'asc' },
]
const sortBy = ref<Array<{ key: string; order?: 'asc' | 'desc' }>>([
  ...DEFAULT_SORT,
])

const resetSort = () => {
  sortBy.value = [...DEFAULT_SORT]
}
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

/* Inline tip strip below the toolbar; only rendered while no
   datastreams are plotted (see template). Quiet primary tint so it
   reads as guidance, not an alert. */
.datasets-table__hint {
  background-color: rgba(var(--v-theme-primary), 0.06);
  color: rgba(var(--v-theme-on-surface), 0.75);
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.12);
}

:deep(.v-table .v-data-table__tr:nth-child(even) td) {
  background: #f7f7f7;
}

/* Plotted/QC row treatments — tint and a primary leading bar so a
   plotted row reads at a glance even when the checkbox column has
   scrolled out of view. The QC row gets a more saturated bar. */
:deep(tbody tr.datasets-table__row--plotted > td) {
  background-color: rgba(var(--v-theme-primary), 0.05);
}

:deep(tbody tr.datasets-table__row--plotted > td:first-child) {
  box-shadow: inset 3px 0 0 rgba(var(--v-theme-primary), 0.45);
}

:deep(tbody tr.datasets-table__row--qc > td) {
  background-color: rgba(var(--v-theme-primary), 0.09);
}

:deep(tbody tr.datasets-table__row--qc > td:first-child) {
  box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
}

:deep(tbody tr:hover > td) {
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
  cursor: pointer;
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
  cursor: not-allowed;
}

/* Tighten the data rows a touch. Vuetify's `density="compact"` lands
   around 40 px; trimming to ~34 px keeps headers & labels legible
   while fitting more datastreams above the fold. */
:deep(.v-table--density-compact tbody td) {
  height: 34px;
}

/* Sticky header gets a faint baseline so it stays visually distinct
   when rows scroll past. Box-shadow stacks under the existing border
   so we don't double-paint on the first paint. */
:deep(.v-table--fixed-header thead th) {
  box-shadow: 0 1px 0 rgba(var(--v-theme-on-surface), 0.08);
}

/* Two-line site cell: code on top, name below in muted tone. */
.site-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.site-cell__code {
  font-variant-numeric: tabular-nums;
}

.site-cell__name {
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-size: 0.72rem;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.num-cell {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.date-cell {
  white-space: nowrap;
}

.datasets-table__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  text-align: center;
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
  transition:
    background-color 120ms ease,
    color 120ms ease;
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

/* Compact "QC" pill rendered next to the plot checkbox on the QC row.
   Marks the quality-control target without occupying its own column. */
.qc-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 18px;
  padding: 0 6px;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #fff;
  background-color: rgb(var(--v-theme-primary));
  border-radius: 4px;
}
</style>
