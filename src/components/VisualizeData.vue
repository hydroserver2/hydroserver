<template>
  <div
    v-if="currentView === DrawerType.Select"
    class="select-view fill-height d-flex flex-column pa-4"
  >
    <!-- Single unified card: one header carries the QC title, the
         "Start editing" CTA, and the Plotted toggle. Below that, a split
         body: plot on the left, plotted-list on the right. -->
    <v-card class="select-view__card d-flex flex-column mb-3">
      <div
        class="select-view__header d-flex align-center flex-wrap gap-3 px-4 py-3"
      >
        <v-icon icon="mdi-chart-line" color="primary" size="24" class="mr-1" />
        <div class="d-flex flex-column" style="min-width: 0; flex: 1 1 auto">
          <span v-if="qcDatastream" class="text-subtitle-1 font-weight-bold">
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
    class="edit-view d-flex bg-background"
  >
    <aside
      class="edit-view__col edit-view__col--drawer d-flex flex-column overflow-y-auto bg-surface border-e"
    >
      <EditDrawer />
    </aside>

    <div
      class="edit-view__col edit-view__col--plot d-flex flex-column pa-3 overflow-hidden"
    >
      <v-card class="fill-height d-flex flex-column" elevation="1">
        <div class="flex-grow-1" style="min-height: 0">
          <DataVisualization />
        </div>
      </v-card>
    </div>

    <aside
      class="edit-view__col edit-view__col--aux d-flex flex-column overflow-hidden bg-surface border-s"
    >
      <div
        class="edit-view__exit-bar d-flex align-center flex-wrap px-3 py-2 border-b"
      >
        <v-btn
          data-testid="exit-save-btn"
          size="small"
          variant="flat"
          color="primary"
          prepend-icon="mdi-content-save-outline"
          :disabled="!editCount || isUpdating || isSubmitting"
          :loading="isSubmitting && exitIntent === 'save'"
          @click="requestSave"
        >
          Save
        </v-btn>
        <v-btn
          data-testid="exit-save-close-btn"
          class="ml-1"
          size="small"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-content-save-move-outline"
          :disabled="!editCount || isUpdating || isSubmitting"
          :loading="isSubmitting && exitIntent === 'save-close'"
          @click="requestSaveAndClose"
        >
          Save &amp; Close
        </v-btn>
        <v-spacer />
        <v-btn
          data-testid="exit-close-btn"
          size="small"
          variant="text"
          prepend-icon="mdi-close"
          :disabled="isSubmitting"
          @click="requestClose"
        >
          Close
        </v-btn>
      </div>

      <section class="bg-surface">
        <PlottedDatastreams section-title="Plotted Datastreams" lock-qc />
      </section>

      <div
        class="bg-background border-t border-b flex-shrink-0"
        style="height: 12px"
      />

      <section
        class="edit-view__aux-body flex-grow-1 d-flex flex-column bg-surface"
      >
        <div
          class="edit-view__history d-flex flex-column"
          :class="{ 'edit-view__history--split': selectedOperation }"
        >
          <EditHistory />
        </div>

        <div
          v-if="selectedOperation"
          class="edit-view__op-panel d-flex flex-column border-t"
        >
          <OperationPanel />
        </div>
      </section>
    </aside>

    <v-dialog v-model="showSaveConfirm" max-width="520">
      <v-card rounded="lg">
        <div class="d-flex align-center gap-3 px-6 pt-5 pb-2">
          <v-avatar color="primary" variant="tonal" size="40">
            <v-icon icon="mdi-cloud-upload-outline" size="22" />
          </v-avatar>
          <div class="d-flex flex-column">
            <div class="text-h6 font-weight-bold">Submit QC observations?</div>
            <div class="text-caption text-medium-emphasis">
              {{ editCount }} edit{{ editCount === 1 ? '' : 's' }} pending
            </div>
          </div>
        </div>
        <v-card-text class="text-body-2 pt-2 pb-4 px-6">
          This will
          <strong>overwrite existing server observations</strong> in the
          submitted time range (replace mode). This action cannot be undone.
        </v-card-text>
        <v-divider />
        <v-card-actions class="d-flex align-center gap-2 px-4 py-3">
          <v-btn variant="text" @click="showSaveConfirm = false">Cancel</v-btn>
          <v-spacer />
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-cloud-upload-outline"
            :loading="isSubmitting"
            @click="confirmSave"
          >
            Submit
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showCloseConfirm" max-width="520">
      <v-card rounded="lg">
        <div class="d-flex align-center gap-3 px-6 pt-5 pb-2">
          <v-avatar color="error" variant="tonal" size="40">
            <v-icon icon="mdi-alert-outline" size="22" />
          </v-avatar>
          <div class="d-flex flex-column">
            <div class="text-h6 font-weight-bold">Discard unsaved edits?</div>
            <div class="text-caption text-medium-emphasis">
              {{ editCount }} edit{{ editCount === 1 ? '' : 's' }} will be lost
            </div>
          </div>
        </div>
        <v-card-text class="text-body-2 pt-2 pb-4 px-6">
          Closing will leave the editor without submitting your changes.
          Discarded edits cannot be recovered.
        </v-card-text>
        <v-divider />
        <v-card-actions class="d-flex align-center gap-2 px-4 py-3">
          <v-btn variant="text" @click="showCloseConfirm = false">Cancel</v-btn>
          <v-spacer />
          <v-btn
            color="error"
            variant="flat"
            prepend-icon="mdi-delete-outline"
            @click="confirmClose"
          >
            Discard &amp; close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import DataVisDatasetsTable from '@/components/VisualizeData/DataVisDatasetsTable.vue'
import DataVisualization from '@/components/VisualizeData/DataVisualization.vue'
import EditHistory from '@/components/EditData/EditHistory.vue'
import OperationPanel from '@/components/EditData/OperationPanel.vue'
import EditDrawer from '@/components/Navigation/EditDrawer.vue'

import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { useUIStore, DrawerType } from '@/store/userInterface'
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlottedDatastreams from './VisualizeData/PlottedDatastreams.vue'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSubmission } from '@/composables/useQcSubmission'
import { useDataSelection } from '@/composables/useDataSelection'

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
const { currentView, selectedDrawer, isDrawerOpen, selectedOperation } =
  storeToRefs(useUIStore())
const { editHistory, isUpdating, isSubmitting, selectedSeries } =
  storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { refreshGraphSeriesArray } = useDataVisStore()
const { clearSelected } = useDataSelection()
const { submitQcEdits } = useQcSubmission()

const editCount = computed(() => editHistory.value?.length ?? 0)
const showSaveConfirm = ref(false)
const showCloseConfirm = ref(false)
const exitIntent = ref<'save' | 'save-close' | null>(null)

function exitToSelect() {
  currentView.value = DrawerType.Select
  selectedDrawer.value = DrawerType.Select
  isDrawerOpen.value = true
}

function requestSave() {
  exitIntent.value = 'save'
  showSaveConfirm.value = true
}

function requestSaveAndClose() {
  exitIntent.value = 'save-close'
  showSaveConfirm.value = true
}

async function confirmSave() {
  const intent = exitIntent.value
  showSaveConfirm.value = false
  await submitQcEdits()
  if (intent === 'save-close') exitToSelect()
  exitIntent.value = null
}

function requestClose() {
  if (editCount.value > 0) {
    showCloseConfirm.value = true
  } else {
    exitToSelect()
  }
}

async function discardEdits() {
  if (!editCount.value) return
  isUpdating.value = true
  try {
    if (selectedSeries.value) selectedSeries.value.data.history = []
    await refreshGraphSeriesArray()
    await selectedSeries.value?.data.reload()
    await clearSelected()
    await redraw()
  } finally {
    isUpdating.value = false
  }
}

async function confirmClose() {
  showCloseConfirm.value = false
  await discardEdits()
  exitToSelect()
}

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
    const unchanged = keys.every((k) => (current[k] ?? '') === (query[k] ?? ''))
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

/* Edit view: pinned to the viewport so the page never gets its own
   scrollbar. Sizing & overflow expressed in CSS because Vuetify has no
   utility for the calc() against v-layout offsets. Everything else
   (flex, gap, bg, borders, overflow-y) lives on the template as
   utility classes. */
.edit-view {
  height: calc(100vh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  max-height: 100vh;
  min-height: 0;
  overflow: hidden;
}

.edit-view__col {
  min-height: 0;
  min-width: 0;
  max-height: 100%;
}

.edit-view__col--drawer {
  flex: 0 0 220px;
  min-width: 200px;
  max-width: 260px;
}

.edit-view__col--plot {
  flex: 1 1 auto;
}

.edit-view__col--aux {
  flex: 0 0 25%;
  min-width: 320px;
}

/* Split the lower sidebar between Edit History and the Operation Panel
   when an operation is selected. Each half scrolls independently; the
   outer aux column already has `overflow-y-auto`, but we tighten that
   to `hidden` so the page doesn't inherit a scrollbar — each child
   owns its own scroll region. */
.edit-view__aux-body {
  min-height: 0;
  overflow: hidden;
}

.edit-view__history {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.edit-view__history--split {
  /* Keep a usable amount of history visible (~40% of the lower column)
     when the operation panel is open. */
  flex: 0 0 40%;
}

.edit-view__op-panel {
  flex: 1 1 60%;
  min-height: 0;
  overflow: hidden;
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
