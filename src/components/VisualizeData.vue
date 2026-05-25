<template>
  <div
    v-if="currentView === DrawerType.Select"
    class="select-view fill-height d-flex flex-column pa-4"
  >
    <v-card class="select-view__card d-flex flex-column mb-3">
      <div
        class="d-flex align-center flex-wrap ga-3 px-4 py-3"
      >
        <v-icon icon="mdi-chart-line" color="primary" size="24" class="mr-1" />
        <div class="d-flex flex-column flex-1-1-auto" style="min-width: 0">
          <span v-if="qcDatastream" class="text-title-medium font-weight-bold">
            {{ qcDatastream.name }}
          </span>
          <span v-else class="text-title-medium font-weight-bold">
            No datastream plotted
          </span>
          <span class="text-body-small text-medium-emphasis">
            <template v-if="qcDatastream">
              Quality-control target: preview ready
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
        <div class="select-view__plot-body flex-grow-1 pa-2">
          <DataVisualization preview />
        </div>

        <template v-if="plottedDatastreams.length">
          <v-divider vertical class="select-view__divider-vertical" />
          <v-divider class="select-view__divider-horizontal" />
          <div class="select-view__plotted d-flex flex-column flex-grow-0 flex-shrink-0 overflow-hidden">
            <div class="select-view__plotted-body flex-grow-1 overflow-y-auto">
              <PlottedDatastreams />
            </div>
          </div>
        </template>
      </div>
    </v-card>

    <v-card class="select-view__table d-flex flex-column flex-1-1-0 overflow-hidden">
      <DataVisDatasetsTable class="fill-height" />
    </v-card>
  </div>

  <div
    v-else-if="currentView === DrawerType.Edit"
    class="edit-view d-flex bg-background"
  >
    <aside
      class="edit-view__col edit-view__col--drawer d-flex flex-column flex-grow-0 flex-shrink-0 bg-surface border-e"
      :class="{ 'edit-view__col--collapsed': drawerCollapsed }"
      :style="drawerCollapsed ? undefined : { width: drawerWidth + 'px' }"
    >
      <div
        class="edit-view__sidebar-bar d-flex align-center px-1 py-1 border-b"
        :class="{ 'justify-center': drawerCollapsed }"
      >
        <span
          v-if="!drawerCollapsed"
          class="text-body-small text-medium-emphasis pl-2"
        >
          Operations
        </span>
        <v-spacer v-if="!drawerCollapsed" />
        <v-btn
          size="x-small"
          variant="text"
          density="comfortable"
          :icon="drawerCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          :title="drawerCollapsed ? 'Expand operations' : 'Collapse operations'"
          @click="drawerCollapsed = !drawerCollapsed"
        />
      </div>
      <div v-if="!drawerCollapsed" class="flex-grow-1 overflow-y-auto">
        <EditDrawer />
      </div>
    </aside>

    <div
      v-if="!drawerCollapsed"
      class="edit-view__grip edit-view__grip--vertical"
      :class="{ 'edit-view__grip--active': drawerDragging }"
      title="Drag to resize"
      @mousedown="startDrawerDrag"
    />

    <div
      class="edit-view__col edit-view__col--plot d-flex flex-column flex-fill pa-3 overflow-hidden"
    >
      <v-card class="fill-height d-flex flex-column" elevation="1">
        <div class="flex-grow-1 pa-2" style="min-height: 0">
          <DataVisualization />
        </div>
      </v-card>
    </div>

    <div
      v-if="!auxCollapsed"
      class="edit-view__grip edit-view__grip--vertical"
      :class="{ 'edit-view__grip--active': auxDragging }"
      title="Drag to resize"
      @mousedown="startAuxDrag"
    />

    <aside
      class="edit-view__col edit-view__col--aux d-flex flex-column flex-grow-0 flex-shrink-0 overflow-hidden bg-surface border-s"
      :class="{ 'edit-view__col--collapsed': auxCollapsed }"
      :style="auxCollapsed ? undefined : { width: auxWidth + 'px' }"
    >
      <template v-if="auxCollapsed">
        <div
          class="edit-view__sidebar-bar d-flex justify-center align-center py-1"
        >
          <v-btn
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-chevron-left"
            title="Expand panel"
            @click="auxCollapsed = false"
          />
        </div>
      </template>

      <template v-else>
        <div
          class="d-flex align-center flex-wrap px-3 py-2 border-b"
        >
          <v-btn
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-chevron-right"
            title="Collapse panel"
            class="mr-1"
            @click="auxCollapsed = true"
          />
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
          <div
            class="edit-view__section-header d-flex align-center ga-1 px-3 py-1"
            role="button"
            tabindex="0"
            @click="plottedCollapsed = !plottedCollapsed"
            @keydown.enter.prevent="plottedCollapsed = !plottedCollapsed"
            @keydown.space.prevent="plottedCollapsed = !plottedCollapsed"
          >
            <v-icon
              size="16"
              :icon="
                plottedCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-down'
              "
            />
            <v-icon icon="mdi-chart-line" color="primary" size="16" />
            <span class="text-body-small font-weight-medium">
              Plotted Datastreams
            </span>
          </div>
          <div
            v-show="!plottedCollapsed"
            class="edit-view__plotted-body pa-2 overflow-y-auto"
            :style="{ height: plottedHeight + 'px' }"
          >
            <div class="rounded border bg-surface overflow-hidden">
              <PlottedDatastreams lock-qc />
            </div>
          </div>
        </section>

        <!-- Drag grip between Plotted Datastreams and Edit history.
             Hidden while Plotted is collapsed because there's no
             body height to adjust. -->
        <div
          v-if="!plottedCollapsed"
          class="edit-view__grip edit-view__grip--horizontal"
          :class="{ 'edit-view__grip--active': plottedDragging }"
          title="Drag to resize"
          @mousedown="startPlottedDrag"
        />

        <section
          ref="auxBodyEl"
          class="edit-view__aux-body flex-grow-1 d-flex flex-column overflow-y-auto bg-surface"
        >
          <!-- History + OperationPanel split. When an operation is
               staged we give the user a drag grip to rebalance the
               vertical share between the two. The history pane
               uses a flex-basis in percent so the grip location
               tracks the slider. -->
          <div
            class="edit-view__history d-flex flex-column overflow-hidden"
            :style="historyPaneStyle"
          >
            <EditHistory
              v-model:collapsed="historyCollapsed"
              @pop-out="historyModalOpen = true"
            />
          </div>

          <!-- Only show the split grip when BOTH sides are actually
               expanded. If the history is collapsed there's nothing
               to rebalance; the op panel naturally takes the
               remaining space. -->
          <div
            v-if="selectedOperation && !historyCollapsed"
            class="edit-view__grip edit-view__grip--horizontal"
            :class="{ 'edit-view__grip--active': auxSplitDragging }"
            title="Drag to resize"
            @mousedown="startAuxSplitDrag"
          />

          <div
            v-if="selectedOperation"
            class="edit-view__op-panel d-flex flex-column flex-grow-1 overflow-hidden border-t"
          >
            <OperationPanel />
          </div>
        </section>
      </template>
    </aside>

    <!-- Pop-out view of EditHistory. Same component, rendered with
         `:collapsible="false"` so the modal isn't offering its own
         collapse control, and `:pop-out-enabled="false"` so the
         header doesn't show an "open in window" button that would
         ask to open the modal we're already in. -->
    <v-dialog v-model="historyModalOpen" max-width="720">
      <v-card class="d-flex flex-column" style="max-height: 80vh">
        <EditHistory :collapsible="false" :pop-out-enabled="false" />
      </v-card>
    </v-dialog>

    <v-dialog v-model="showSaveConfirm" max-width="520">
      <v-card rounded="lg">
        <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
          <v-avatar color="primary" variant="tonal" size="40">
            <v-icon icon="mdi-cloud-upload-outline" size="22" />
          </v-avatar>
          <div class="d-flex flex-column">
            <div class="text-title-large font-weight-bold">Submit QC observations?</div>
            <div class="text-body-small text-medium-emphasis">
              {{ editCount }} edit{{ editCount === 1 ? '' : 's' }} pending
            </div>
          </div>
        </div>
        <v-card-text class="text-body-medium pt-2 pb-4 px-6">
          This will
          <strong>overwrite existing server observations</strong> in the
          submitted time range (replace mode). This action cannot be undone.
        </v-card-text>
        <v-divider />
        <v-card-actions class="d-flex align-center ga-2 px-4 py-3">
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
        <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
          <v-avatar color="error" variant="tonal" size="40">
            <v-icon icon="mdi-alert-outline" size="22" />
          </v-avatar>
          <div class="d-flex flex-column">
            <div class="text-title-large font-weight-bold">Discard unsaved edits?</div>
            <div class="text-body-small text-medium-emphasis">
              {{ editCount }} edit{{ editCount === 1 ? '' : 's' }} will be lost
            </div>
          </div>
        </div>
        <v-card-text class="text-body-medium pt-2 pb-4 px-6">
          Closing will leave the editor without submitting your changes.
          Discarded edits cannot be recovered.
        </v-card-text>
        <v-divider />
        <v-card-actions class="d-flex align-center ga-2 px-4 py-3">
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
import { computed, onUnmounted, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlottedDatastreams from './VisualizeData/PlottedDatastreams.vue'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSubmission } from '@/composables/useQcSubmission'
import {
  decodeShareState,
  encodeShareState,
  type ShareState,
} from '@/utils/share'
import { useDataSelection } from '@/composables/useDataSelection'
import { useWorkspaceStore } from '@/store/workspaces'
import { useResizable, usePersistedFlag } from '@/composables/useResizable'

const { resetState } = useDataVisStore()
const {
  plottedDatastreams,
  qcDatastream,
  datastreams,
  things,
  beginDate,
  endDate,
  selectedDateBtnId,
  dateOptions,
  selectedThings,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
} = storeToRefs(useDataVisStore())
const { currentView, selectedDrawer, isDrawerOpen, selectedOperation } =
  storeToRefs(useUIStore())
const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())
const {
  editHistory,
  isUpdating,
  isSubmitting,
  selectedSeries,
  activeTab,
  hiddenTraceIds,
  hiddenAxisIds,
  currentZoom,
  pendingShareZoom,
  tooltipsMode,
  tooltipsManualEnabled,
  tooltipsMaxDataPoints,
} = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { refreshGraphSeriesArray, setPlottedDatastreams } = useDataVisStore()
const { clearSelected } = useDataSelection()
const { submitQcEdits } = useQcSubmission()

const editCount = computed(() => editHistory.value?.length ?? 0)
const showSaveConfirm = ref(false)
const showCloseConfirm = ref(false)
const exitIntent = ref<'save' | 'save-close' | null>(null)

// --- Editor layout: sidebar sizes + collapse flags ------------------
// Persisted to localStorage so the user's preferred layout survives
// reloads. Widths / percentages share the same `qc:editorLayout`
// namespace; flags are boolean keys alongside.
const {
  size: drawerWidth,
  onStart: startDrawerDrag,
  dragging: drawerDragging,
} = useResizable({
  initial: 220,
  min: 180,
  max: 420,
  storageKey: 'qc:editorLayout:drawerWidth',
})
const {
  size: auxWidth,
  onStart: startAuxDrag,
  dragging: auxDragging,
} = useResizable({
  initial: 360,
  min: 280,
  max: 720,
  // Right sidebar: the drag grip is on its LEFT (plot-facing)
  // edge, so dragging the grip LEFT should grow the sidebar. That
  // means the x-delta needs to be inverted.
  invert: true,
  storageKey: 'qc:editorLayout:auxWidth',
})
// Template ref used by `useResizable` to convert pixel deltas into
// percent-of-container during the History / OperationPanel split
// drag. Without the conversion a small pointer move would add raw
// pixels onto the percent value, making the panel lunge.
const auxBodyEl = useTemplateRef<HTMLElement>('auxBodyEl')
const {
  size: historyPercent,
  onStart: startAuxSplitDrag,
  dragging: auxSplitDragging,
} = useResizable({
  initial: 40,
  min: 20,
  max: 80,
  direction: 'vertical',
  storageKey: 'qc:editorLayout:historyPercent',
  getContainerPx: () => auxBodyEl.value?.clientHeight ?? 0,
})
const drawerCollapsed = usePersistedFlag(
  'qc:editorLayout:drawerCollapsed',
  false
)
const auxCollapsed = usePersistedFlag('qc:editorLayout:auxCollapsed', false)
const plottedCollapsed = usePersistedFlag(
  'qc:editorLayout:plottedCollapsed',
  false
)
const {
  size: plottedHeight,
  onStart: startPlottedDrag,
  dragging: plottedDragging,
} = useResizable({
  initial: 200,
  min: 80,
  max: 600,
  direction: 'vertical',
  storageKey: 'qc:editorLayout:plottedHeight',
})
const historyCollapsed = usePersistedFlag(
  'qc:editorLayout:historyCollapsed',
  false
)
const historyModalOpen = ref(false)

const historyPaneStyle = computed(() => {
  if (historyCollapsed.value) return { flex: '0 0 auto' }
  if (selectedOperation.value) return { flex: `0 0 ${historyPercent.value}%` }
  return { flex: '1 1 auto' }
})

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
    // In-place clear so the `editHistory` ref keeps tracking the
    // same array (reassigning `history = []` detaches it).
    if (selectedSeries.value) selectedSeries.value.data.history.length = 0
    await refreshGraphSeriesArray()
    await selectedSeries.value?.data.reload()
    await clearSelected({ recordHistory: false })
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
  const state = decodeShareState(route.query as Record<string, unknown>)

  if (state.editView) {
    currentView.value = DrawerType.Edit
    selectedDrawer.value = DrawerType.Edit
    isDrawerOpen.value = true
  } else {
    currentView.value = DrawerType.Select
    selectedDrawer.value = DrawerType.Select
  }

  if (state.tableTab) activeTab.value = 'table'
  else activeTab.value = 'plot'

  // Filters first; the store's filteredDatastreams watcher prunes
  // plottedDatastreams whose thing/op/pl is filtered out, so we
  // need these set before we assign plottedDatastreams below.
  const thingIds = state.thingIds ?? []
  selectedThings.value = thingIds
    .map((id) => things.value.find((t) => t.id === id))
    .filter((t): t is NonNullable<typeof t> => !!t)
  selectedObservedPropertyNames.value = state.observedPropertyNames ?? []
  selectedProcessingLevelNames.value = state.processingLevelNames ?? []

  const ids = state.datastreamIds ?? []
  const resolved = ids
    .map((id) => datastreams.value.find((ds) => ds.id === id))
    .filter((ds): ds is NonNullable<typeof ds> => !!ds)
  // QC target is the first id by convention.
  const qcId = resolved[0]?.id ?? null

  // Apply the date window BEFORE loading datastreams so the first
  // fetch uses the correct range.
  if (state.datePresetId != null && state.datePresetId >= 0) {
    selectedDateBtnId.value = state.datePresetId
    const option = dateOptions.value.find((o) => o.id === state.datePresetId)
    if (option) {
      endDate.value = new Date()
      beginDate.value = option.calculateBeginDate()
    }
  } else if (state.beginMs != null || state.endMs != null) {
    selectedDateBtnId.value = -1
    if (state.beginMs != null) beginDate.value = new Date(state.beginMs)
    if (state.endMs != null) endDate.value = new Date(state.endMs)
  }

  // Visibility: translate the boolean lists back into the store's
  // hidden-id sets so the eye / axis toggles match the sender's view.
  if (state.traceVisibility) {
    hiddenTraceIds.value = new Set(
      ids.filter((_, i) => state.traceVisibility?.[i] === false)
    )
  } else {
    hiddenTraceIds.value = new Set()
  }
  if (state.axisVisibility) {
    hiddenAxisIds.value = new Set(
      ids.filter((_, i) => state.axisVisibility?.[i] === false)
    )
  } else {
    hiddenAxisIds.value = new Set()
  }

  // Data points marker mode + threshold.
  if (state.dataPointsMode === 'manualOn') {
    tooltipsMode.value = 'manual'
    tooltipsManualEnabled.value = true
  } else if (state.dataPointsMode === 'manualOff') {
    tooltipsMode.value = 'manual'
    tooltipsManualEnabled.value = false
  } else {
    tooltipsMode.value = 'auto'
  }
  if (state.dataPointsThreshold != null) {
    tooltipsMaxDataPoints.value = state.dataPointsThreshold
  }

  // Park the URL-supplied zoom so the Plot's mount hook can apply it
  // after `handleNewPlot` finishes the default-fit render.
  // Carry `source: 'user'` so the zoom-history recorder treats this
  // as a deliberate viewport choice (URL share is an intentional user
  // action), matching the ZoomState contract.
  pendingShareZoom.value = state.zoom
    ? {
        xRange: state.zoom.xRange,
        yRanges: state.zoom.yRanges,
        source: 'user',
      }
    : null

  void setPlottedDatastreams(resolved, qcId)
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

// Push URL updates whenever any piece of share-relevant state moves.
// `router.replace` keeps the browser history clean (no entry per
// click). Heavy lifting (key choice, default-elision, compaction)
// lives in `share.ts` so this watcher reads as a plain assembly of
// inputs.
const SHARE_KEYS = [
  'ws', 'm', 'tab', 'ds', 'r', 'from', 'to',
  't', 'op', 'pl', 'h', 'ya', 'z', 'yz', 'dp', 'th',
] as const

watch(
  [
    plottedDatastreams,
    qcDatastream,
    currentView,
    activeTab,
    beginDate,
    endDate,
    selectedDateBtnId,
    selectedThings,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
    selectedWorkspaceId,
    hiddenTraceIds,
    hiddenAxisIds,
    currentZoom,
    tooltipsMode,
    tooltipsManualEnabled,
    tooltipsMaxDataPoints,
  ],
  () => {
    const ids = plottedDatastreams.value.map((ds) => ds.id)
    const isEdit = currentView.value === DrawerType.Edit

    const state: ShareState = {
      workspaceId: selectedWorkspaceId.value || null,
      editView: isEdit,
      tableTab: activeTab.value === 'table',
      datastreamIds: ids,
      datePresetId: Number.isFinite(selectedDateBtnId.value)
        ? selectedDateBtnId.value
        : null,
      beginMs: beginDate.value ? beginDate.value.getTime() : null,
      endMs: endDate.value ? endDate.value.getTime() : null,
      // Sidebar filters only matter on the Select view (they drive
      // the datastreams table, not the plot). Skip them in Edit
      // links to keep URLs short.
      thingIds: isEdit ? [] : selectedThings.value.map((t) => t.id),
      observedPropertyNames: isEdit
        ? []
        : selectedObservedPropertyNames.value,
      processingLevelNames: isEdit ? [] : selectedProcessingLevelNames.value,
      traceVisibility: ids.map((id) => !hiddenTraceIds.value.has(id)),
      axisVisibility: ids.map((id) => !hiddenAxisIds.value.has(id)),
      zoom: currentZoom.value ?? undefined,
      dataPointsMode:
        tooltipsMode.value === 'auto'
          ? 'auto'
          : tooltipsManualEnabled.value
            ? 'manualOn'
            : 'manualOff',
      dataPointsThreshold: tooltipsMaxDataPoints.value,
    }

    const query = encodeShareState(state)
    const current = route.query
    const unchanged = SHARE_KEYS.every(
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

.select-view__divider-horizontal {
  display: none;
}

.select-view__plotted {
  width: 280px;
}

.select-view__plotted-body {
  max-height: 100%;
}

.select-view__table {
  min-height: 260px;
}

/* Stack vertically on narrower viewports: plot gets full width, plotted
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

.edit-view__col--collapsed {
  flex: 0 0 36px !important;
  width: 36px !important;
  min-width: 36px !important;
  max-width: 36px !important;
}

.edit-view__sidebar-bar {
  min-height: 32px;
}

/* Column resize grip. Renders as a 4px hit target with a subtle
   center rule so it's discoverable but not heavy. `--active` keeps
   the primary tint on throughout a drag even when the cursor leaves
   the grip element (drag listeners live on the window). */
.edit-view__grip {
  flex: 0 0 auto;
  position: relative;
  user-select: none;
}
.edit-view__grip--vertical {
  width: 4px;
  cursor: col-resize;
}
.edit-view__grip--vertical::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 1px;
  width: 2px;
  background: rgba(var(--v-theme-on-surface), 0.08);
}
.edit-view__grip--vertical:hover::after,
.edit-view__grip--active.edit-view__grip--vertical::after {
  background: rgba(var(--v-theme-primary), 0.55);
}
.edit-view__grip--horizontal {
  height: 4px;
  cursor: row-resize;
}
.edit-view__grip--horizontal::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 1px;
  height: 2px;
  background: rgba(var(--v-theme-on-surface), 0.08);
}
.edit-view__grip--horizontal:hover::after,
.edit-view__grip--active.edit-view__grip--horizontal::after {
  background: rgba(var(--v-theme-primary), 0.55);
}

/* Clickable section header (Plotted Datastreams, etc.). Subtle
   hover so the affordance reads without competing with the
   surrounding chrome. */
.edit-view__section-header {
  cursor: pointer;
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 28px;
}
.edit-view__section-header:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
.edit-view__section-header:focus {
  outline: none;
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.edit-view__plotted-body,
.edit-view__aux-body,
.edit-view__history,
.edit-view__op-panel {
  min-height: 0;
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
