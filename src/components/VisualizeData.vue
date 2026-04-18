<template>
  <div
    v-if="currentView === DrawerType.Select"
    class="select-view fill-height d-flex flex-column pa-4"
  >
    <!-- Single unified card: one header carries the QC title, the
         "Start editing" CTA, and the Plotted toggle. Below that, a split
         body: plot on the left, plotted-list on the right. -->
    <v-card class="select-view__card d-flex flex-column mb-3">
      <div class="select-view__header d-flex align-center flex-wrap gap-3 px-4 py-3">
        <v-icon icon="mdi-chart-line" color="primary" size="24" class="mr-1" />
        <div class="d-flex flex-column" style="min-width: 0; flex: 1 1 auto;">
          <span
            v-if="qcDatastream"
            class="text-subtitle-1 font-weight-bold"
          >
            {{ qcDatastream.name }}
          </span>
          <span v-else class="text-subtitle-1 font-weight-bold">
            No datastream plotted
          </span>
          <span class="text-caption text-medium-emphasis">
            <template v-if="qcDatastream">
              Quality-control target — preview ready
            </template>
            <template v-else>
              Select one from the table below to preview its data here
            </template>
          </span>
        </div>

        <v-tooltip
          v-if="!qcDatastream"
          location="start"
          text="Pick a datastream below (radio button) to enable editing"
        >
          <template #activator="{ props: tooltipProps }">
            <div v-bind="tooltipProps">
              <v-btn
                color="primary"
                variant="flat"
                prepend-icon="mdi-pencil"
                append-icon="mdi-arrow-right"
                disabled
              >
                Start editing
              </v-btn>
            </div>
          </template>
        </v-tooltip>

        <v-btn
          v-else
          color="primary"
          variant="flat"
          prepend-icon="mdi-pencil"
          append-icon="mdi-arrow-right"
          @click="goToEdit"
        >
          Start editing
        </v-btn>
      </div>

      <v-divider />

      <div class="select-view__card-body d-flex flex-grow-1">
        <div class="select-view__plot-body flex-grow-1">
          <DataVisualization preview />
        </div>

        <template v-if="plottedDatastreams.length">
          <v-divider vertical class="select-view__divider-vertical" />
          <v-divider class="select-view__divider-horizontal" />
          <div class="select-view__plotted d-flex flex-column">
            <div class="select-view__plotted-body flex-grow-1 overflow-y-auto">
              <PlottedDatastreams />
            </div>
          </div>
        </template>
      </div>
    </v-card>

    <!-- Datastreams table: always visible, flex-basis sets its proportional
         share so it doesn't crowd the plot on small screens. -->
    <v-card class="select-view__table d-flex flex-column">
      <DataVisDatasetsTable class="fill-height" />
    </v-card>
  </div>

  <div
    v-else-if="currentView === DrawerType.Edit"
    class="edit-view pa-4"
  >
    <div class="edit-view__col edit-view__col--drawer edit-view__scroll">
      <v-card class="fill-height">
        <EditDrawer />
      </v-card>
    </div>
    <div class="edit-view__col edit-view__col--plot">
      <v-card class="fill-height d-flex flex-column">
        <div class="flex-grow-1" style="min-height: 0;">
          <DataVisualization />
        </div>
      </v-card>
    </div>
    <div class="edit-view__col edit-view__col--aux edit-view__scroll">
      <v-card>
        <v-card-title class="text-body-1">Plotted Datastreams</v-card-title>
        <v-divider></v-divider>
        <PlottedDatastreams></PlottedDatastreams>
      </v-card>
      <EditHistory />
    </div>
  </div>
</template>

<script setup lang="ts">
import DataVisDatasetsTable from '@/components/VisualizeData/DataVisDatasetsTable.vue'
import DataVisualization from '@/components/VisualizeData/DataVisualization.vue'
import EditHistory from '@/components/EditData/EditHistory.vue'
import EditDrawer from '@/components/Navigation/EditDrawer.vue'

import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { useUIStore, DrawerType } from '@/store/userInterface'
import { onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlottedDatastreams from './VisualizeData/PlottedDatastreams.vue'

const { resetState } = useDataVisStore()
const {
  plottedDatastreams,
  qcDatastream,
  datastreams,
  things,
  beginDate,
  endDate,
  selectedDateBtnId,
  selectedThings,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
} = storeToRefs(useDataVisStore())
const { currentView, selectedDrawer, isDrawerOpen } = storeToRefs(useUIStore())

const route = useRoute()
const router = useRouter()

// Hydrate state from the URL once datastream metadata is available.
const hydrateFromUrl = () => {
  const mode = String(route.query.mode ?? '').toLowerCase()
  if (mode === 'edit') {
    currentView.value = DrawerType.Edit
    selectedDrawer.value = DrawerType.Edit
    isDrawerOpen.value = true
  } else if (mode === 'select') {
    currentView.value = DrawerType.Select
    selectedDrawer.value = DrawerType.Select
  }

  const splitCsv = (v: unknown) =>
    typeof v === 'string' && v.length ? v.split(',').filter(Boolean) : []

  // Filters first — the store's filteredDatastreams watcher prunes
  // plottedDatastreams whose thing/op/pl is filtered out, so we need these
  // set before we assign plottedDatastreams below.
  const thingIds = splitCsv(route.query.things)
  selectedThings.value = thingIds
    .map((id) => things.value.find((t) => t.id === id))
    .filter((t): t is NonNullable<typeof t> => !!t)
  selectedObservedPropertyNames.value = splitCsv(route.query.observedProperties)
  selectedProcessingLevelNames.value = splitCsv(route.query.processingLevels)

  const ids = splitCsv(route.query.datastreams)
  const resolved = ids
    .map((id) => datastreams.value.find((ds) => ds.id === id))
    .filter((ds): ds is NonNullable<typeof ds> => !!ds)

  plottedDatastreams.value = resolved

  const qcId = typeof route.query.qc === 'string' ? route.query.qc : ''
  const qcMatch = resolved.find((ds) => ds.id === qcId)
  qcDatastream.value = qcMatch ?? resolved[0] ?? null

  const parseDate = (v: unknown) => {
    if (typeof v !== 'string' || !v) return null
    const d = new Date(v)
    return isNaN(d.getTime()) ? null : d
  }
  const begin = parseDate(route.query.begin)
  const end = parseDate(route.query.end)
  if (begin) beginDate.value = begin
  if (end) endDate.value = end

  const btn = Number(route.query.dateBtn)
  if (Number.isFinite(btn)) selectedDateBtnId.value = btn
  else if (begin || end) selectedDateBtnId.value = -1
}

if (datastreams.value.length) {
  hydrateFromUrl()
} else {
  const stop = watch(
    () => datastreams.value.length,
    (n) => {
      if (n > 0) {
        hydrateFromUrl()
        stop()
      }
    }
  )
}

// Push URL updates when the user changes plotted datastreams, qc target, or
// mode — using replace so we don't spam browser history on every toggle.
watch(
  [
    plottedDatastreams,
    qcDatastream,
    currentView,
    beginDate,
    endDate,
    selectedDateBtnId,
    selectedThings,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
  ],
  () => {
    const ids = plottedDatastreams.value.map((ds) => ds.id)
    const query: Record<string, string> = {}
    if (currentView.value === DrawerType.Edit) query.mode = 'edit'
    else if (currentView.value === DrawerType.Select) query.mode = 'select'
    if (ids.length) query.datastreams = ids.join(',')
    if (qcDatastream.value?.id) query.qc = qcDatastream.value.id
    if (beginDate.value) query.begin = beginDate.value.toISOString()
    if (endDate.value) query.end = endDate.value.toISOString()
    if (Number.isFinite(selectedDateBtnId.value))
      query.dateBtn = String(selectedDateBtnId.value)
    if (selectedThings.value.length)
      query.things = selectedThings.value.map((t) => t.id).join(',')
    if (selectedObservedPropertyNames.value.length)
      query.observedProperties = selectedObservedPropertyNames.value.join(',')
    if (selectedProcessingLevelNames.value.length)
      query.processingLevels = selectedProcessingLevelNames.value.join(',')

    const current = route.query
    const keys = [
      'mode',
      'datastreams',
      'qc',
      'begin',
      'end',
      'dateBtn',
      'things',
      'observedProperties',
      'processingLevels',
    ]
    const unchanged = keys.every(
      (k) => (current[k] ?? '') === (query[k] ?? '')
    )
    if (unchanged) return

    router.replace({ query })
  },
  { deep: true }
)

onUnmounted(() => {
  resetState()
})

function goToEdit() {
  currentView.value = DrawerType.Edit
  selectedDrawer.value = DrawerType.Edit
  isDrawerOpen.value = true
}
</script>

<style scoped>
.select-view {
  min-height: 0;
  overflow: hidden;
}

.select-view__card {
  /* ~50% of the viewport so plot and table share space. min-height:0 so
     children can shrink below their content height. */
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

.select-view__card-body,
.select-view__plot-body,
.select-view__plotted,
.select-view__table {
  min-height: 0;
}

.select-view__card-body {
  /* Inner row: plot + vertical divider + plotted list. */
  overflow: hidden;
}

.select-view__plot-body {
  min-width: 0;
}

.select-view__plot-header,
.select-view__plotted-header {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.select-view__divider-horizontal {
  display: none;
}

.select-view__plotted {
  width: 280px;
  flex: 0 0 auto;
  overflow: hidden;
}

.select-view__plotted-body {
  max-height: 100%;
}

.select-view__table {
  flex: 1 1 0;
  min-height: 260px;
  overflow: hidden;
}

/* Stack vertically on narrower viewports — plot gets full width, plotted
   section folds under it with a horizontal divider instead of a vertical
   one. */
@media (max-width: 960px) {
  .select-view__card-body {
    flex-direction: column;
  }
  .select-view__plotted {
    width: 100%;
    max-height: 240px;
  }
  .select-view__divider-vertical {
    display: none;
  }
  .select-view__divider-horizontal {
    display: block;
  }
}

/* Edit view layout: pinned to the viewport so the page never gets its
   own scrollbar. Each column scrolls internally when its content
   overflows. Using a bespoke flex div (instead of v-row/v-col) because
   the Vuetify classes wrap each column in their own stacking context
   whose `height:100%` wasn't resolving against v-main's `min-height`. */
.edit-view {
  display: flex;
  flex-direction: row;
  gap: 8px;
  height: calc(
    100vh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px)
  );
  max-height: 100vh;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.edit-view__col {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  min-width: 0;
  max-height: 100%;
}

.edit-view__col--drawer {
  /* Reasonable fixed width for the Data-Tools list. Description text
     wraps inside the list items (see EditDrawer.vue `:deep()` rules)
     so the column doesn't need to grow to fit long labels. */
  flex: 0 0 220px;
  min-width: 200px;
  max-width: 260px;
}

.edit-view__col--plot {
  flex: 1 1 auto;
  /* Plot column: no internal scroll. The DataVisualization component
     fills the fixed height of the column via its own flex layout. */
  overflow: hidden;
}

.edit-view__col--aux {
  flex: 0 0 25%;
}

.edit-view__scroll {
  overflow-y: auto;
}

@media (max-width: 960px) {
  .edit-view {
    flex-direction: column;
    height: auto;
    max-height: none;
    overflow: visible;
  }
  .edit-view__col--drawer,
  .edit-view__col--aux {
    flex: 0 0 auto;
  }
  .edit-view__col--plot {
    min-height: 420px;
  }
}
</style>
