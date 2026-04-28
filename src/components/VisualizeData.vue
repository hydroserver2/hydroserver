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
        <div class="select-view__plot-body flex-grow-1 pa-2">
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
    <!-- Left sidebar. Width is driven by the persisted
         `drawerWidth`; the handle to the right of the aside drags
         it. Collapsed state swaps in a narrow rail whose only
         affordance is the expand toggle. -->
    <aside
      class="edit-view__col edit-view__col--drawer d-flex flex-column bg-surface border-e"
      :class="{ 'edit-view__col--collapsed': drawerCollapsed }"
      :style="drawerCollapsed ? undefined : { width: drawerWidth + 'px' }"
    >
      <div
        class="edit-view__sidebar-bar d-flex align-center px-1 py-1 border-b"
        :class="{ 'justify-center': drawerCollapsed }"
      >
        <span
          v-if="!drawerCollapsed"
          class="text-caption text-medium-emphasis pl-2"
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

    <!-- Resize grip between drawer and plot. Hidden while the
         drawer is collapsed (no width to change). -->
    <div
      v-if="!drawerCollapsed"
      class="edit-view__grip edit-view__grip--vertical"
      :class="{ 'edit-view__grip--active': drawerDragging }"
      title="Drag to resize"
      @mousedown="startDrawerDrag"
    />

    <div
      class="edit-view__col edit-view__col--plot d-flex flex-column pa-3 overflow-hidden"
    >
      <v-card class="fill-height d-flex flex-column" elevation="1">
        <div class="flex-grow-1 pa-2" style="min-height: 0">
          <DataVisualization />
        </div>
      </v-card>
    </div>

    <!-- Resize grip between plot and aux. -->
    <div
      v-if="!auxCollapsed"
      class="edit-view__grip edit-view__grip--vertical"
      :class="{ 'edit-view__grip--active': auxDragging }"
      title="Drag to resize"
      @mousedown="startAuxDrag"
    />

    <aside
      class="edit-view__col edit-view__col--aux d-flex flex-column overflow-hidden bg-surface border-s"
      :class="{ 'edit-view__col--collapsed': auxCollapsed }"
      :style="auxCollapsed ? undefined : { width: auxWidth + 'px' }"
    >
      <!-- Collapsed rail: single expand toggle, nothing else. -->
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
          class="edit-view__exit-bar d-flex align-center flex-wrap px-3 py-2 border-b"
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

        <!-- Plotted Datastreams: collapsible by itself so the user
             can reclaim vertical room for history / operation
             details without losing the sidebar. -->
        <section class="bg-surface">
          <div
            class="edit-view__section-header d-flex align-center gap-1 px-3 py-1"
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
            <!-- Matches the Edit History header treatment (small
                 primary-tinted section icon between the chevron and
                 the title) so both collapsible panels read as the
                 same family of controls. -->
            <v-icon icon="mdi-chart-line" color="primary" size="16" />
            <span class="text-caption font-weight-medium">
              Plotted Datastreams
            </span>
          </div>
          <!-- Body height is a persisted `plottedHeight` ref driven
               by the grip below. `overflow-y: auto` means long
               plotted lists scroll inside their allocation rather
               than pushing the edit history off-screen. -->
          <div
            v-show="!plottedCollapsed"
            class="edit-view__plotted-body"
            :style="{ height: plottedHeight + 'px' }"
          >
            <div class="edit-view__section-card">
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
          class="edit-view__aux-body flex-grow-1 d-flex flex-column bg-surface"
        >
          <!-- History + OperationPanel split. When an operation is
               staged we give the user a drag grip to rebalance the
               vertical share between the two. The history pane
               uses a flex-basis in percent so the grip location
               tracks the slider. -->
          <div
            class="edit-view__history d-flex flex-column"
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
            class="edit-view__op-panel d-flex flex-column flex-grow-1 border-t"
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
import { computed, onUnmounted, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlottedDatastreams from './VisualizeData/PlottedDatastreams.vue'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSubmission } from '@/composables/useQcSubmission'
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
const { editHistory, isUpdating, isSubmitting, selectedSeries } =
  storeToRefs(usePlotlyStore())
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
  // Right sidebar — the drag grip is on its LEFT (plot-facing)
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

  const qcId = typeof route.query.qc === 'string' ? route.query.qc : ''

  const parseDate = (v: unknown) => {
    if (typeof v !== 'string' || !v) return null
    const d = new Date(v)
    return isNaN(d.getTime()) ? null : d
  }
  const begin = parseDate(route.query.begin)
  const end = parseDate(route.query.end)

  const btn = Number(route.query.dateBtn)
  if (Number.isFinite(btn)) selectedDateBtnId.value = btn
  else if (begin || end) selectedDateBtnId.value = -1

  // Apply the date window BEFORE loading datastreams so the first fetch
  // uses the correct range.
  if (begin || end) {
    if (begin) beginDate.value = begin
    if (end) endDate.value = end
  } else if (Number.isFinite(btn)) {
    const option = dateOptions.value.find((o) => o.id === btn)
    if (option) {
      endDate.value = new Date()
      beginDate.value = option.calculateBeginDate()
    }
  }

  void setPlottedDatastreams(resolved, qcId || null)
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
    selectedWorkspaceId,
  ],
  () => {
    const ids = plottedDatastreams.value.map((ds) => ds.id)
    const query: Record<string, string> = {}
    // Workspace goes in the query so a shared link lands the recipient
    // in the same HydroServer context the sender had. The workspace
    // router guard (`guards.ts`) consumes this on incoming navigation
    // and switches the active workspace when it differs from the
    // recipient's current selection.
    if (selectedWorkspaceId.value) query.workspace = selectedWorkspaceId.value
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
      'workspace',
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
  /* Width is driven inline via `drawerWidth`; flex settings here
     just prevent the sidebar from growing past its set width. */
  flex: 0 0 auto;
}

.edit-view__col--plot {
  flex: 1 1 auto;
}

.edit-view__col--aux {
  flex: 0 0 auto;
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
   the grip element — important because the drag listeners live on
   the window. */
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

.edit-view__plotted-body {
  overflow-y: auto;
  min-height: 0;
  padding: 8px;
}

/* Bordered card wrapper for section bodies. Matches the
   `.operation-panel__section` treatment so plotted-datastreams,
   edit-history, and operation-panel content all read as the same
   family of contained groups. */
.edit-view__section-card {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.edit-view__aux-body {
  min-height: 0;
  overflow-y: auto;
}

.edit-view__history {
  min-height: 0;
  overflow: hidden;
}

.edit-view__op-panel {
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
