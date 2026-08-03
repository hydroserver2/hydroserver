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

        <v-chip
          v-if="qcDatastream"
          size="small"
          variant="tonal"
          :color="canEditWorkspace ? 'primary' : 'grey'"
          :prepend-icon="canEditWorkspace ? 'mdi-pencil' : 'mdi-eye-outline'"
          class="mr-2 align-self-center"
          :title="`Your role on this workspace: ${workspaceRole}`"
        >
          {{ workspaceRole }}
        </v-chip>

        <v-tooltip
          v-if="!qcDatastream"
          location="start"
          text="Pick a datastream below (radio button) to enable editing"
        >
          <template #activator="{ props: tooltipProps }">
            <div v-bind="tooltipProps" class="ml-auto">
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

        <v-tooltip
          v-else
          location="start"
          :disabled="canEditWorkspace"
          :text="`Your role on this workspace (${workspaceRole}) is read-only. Ask a workspace owner for an editor role to make edits.`"
        >
          <template #activator="{ props: tooltipProps }">
            <div v-bind="tooltipProps" class="ml-auto">
              <v-btn
                color="primary"
                variant="flat"
                prepend-icon="mdi-pencil"
                append-icon="mdi-arrow-right"
                :loading="isCreating"
                :disabled="!canEditWorkspace"
                @click="openEditChooser"
              >
                Start editing
              </v-btn>
            </div>
          </template>
        </v-tooltip>
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

    <v-dialog v-model="showChooser" max-width="640">
      <StartEditingDialog
        v-if="chooserSource"
        :source="chooserSource"
        :options="chooserOptions"
        :loading="chooserLoading"
        @edit="editManaged"
        @delete="onChooserDelete"
        @delete-session="onChooserDeleteSession"
        @create="onChooserCreate"
        @cancel="showChooser = false"
      />
    </v-dialog>

    <v-dialog v-model="showCreateDatastream" max-width="560" persistent>
      <v-card v-if="qcDatastream" rounded="lg">
        <CreateDatastreamForm
          :source="qcDatastream"
          :processing-levels="processingLevels"
          :default-processing-level-id="qcPreferences.processingLevelId"
          :on-create-processing-level="onCreateProcessingLevel"
          :permission-error="
            canCreateDatastreamHere
              ? ''
              : `Your role on this workspace (${workspaceRole}) can't create datastreams. Ask a workspace owner for an editor role.`
          "
          @cancel="onCreateCancel"
          @confirm="onCreateDatastream"
        />
      </v-card>
    </v-dialog>
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
            :disabled="saveDisabled"
            :loading="isSavingDraft"
            @click="onSaveDraft"
          >
            Save
          </v-btn>
          <v-btn
            data-testid="exit-commit-btn"
            class="ml-1"
            size="small"
            variant="flat"
            color="success"
            prepend-icon="mdi-cloud-check-outline"
            :disabled="commitDisabled"
            :loading="isCommitting"
            @click="openCommit"
          >
            Commit
          </v-btn>
          <v-spacer />
          <v-btn
            data-testid="exit-close-btn"
            size="small"
            variant="text"
            prepend-icon="mdi-close"
            :disabled="isSavingDraft || isCommitting"
            @click="requestClose"
          >
            Close
          </v-btn>
        </div>

        <section class="bg-surface">
          <div
            class="edit-view__section-header d-flex align-center ga-2 px-3 py-1"
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
              @view-session="onViewSession"
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
        <EditHistory
          :collapsible="false"
          :pop-out-enabled="false"
          @view-session="onViewSession"
        />
      </v-card>
    </v-dialog>

    <v-dialog v-model="showCommitConfirm" max-width="520">
      <v-card rounded="lg">
        <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
          <v-avatar color="success" variant="tonal" size="40">
            <v-icon icon="mdi-cloud-check-outline" size="22" />
          </v-avatar>
          <div class="d-flex flex-column">
            <div class="text-title-large font-weight-bold">Commit session to datastream?</div>
            <div class="text-body-small text-medium-emphasis">
              Materializes this session into the managed datastream
            </div>
          </div>
        </div>
        <v-card-text class="text-body-medium pt-2 pb-4 px-6">
          The source data's integrity is verified, then the edited observations
          <strong>replace</strong> the managed datastream over this session's
          range and the session is locked into the history.
        </v-card-text>
        <div class="px-6 pb-2">
          <v-textarea
            v-model="commitDescription"
            data-testid="commit-description"
            label="Session description (optional)"
            rows="2"
            auto-grow
            density="compact"
            hide-details="auto"
          />
        </div>
        <v-divider />
        <v-card-actions class="d-flex align-center ga-2 px-4 py-3">
          <v-btn variant="text" @click="showCommitConfirm = false">Cancel</v-btn>
          <v-spacer />
          <v-btn
            color="success"
            variant="flat"
            prepend-icon="mdi-cloud-check-outline"
            :loading="isCommitting"
            @click="onCommit"
          >
            Commit
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showCloseConfirm" max-width="520">
      <v-card rounded="lg">
        <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
          <v-avatar color="primary" variant="tonal" size="40">
            <v-icon icon="mdi-content-save-outline" size="22" />
          </v-avatar>
          <div class="d-flex flex-column">
            <div class="text-title-large font-weight-bold">Save before closing?</div>
            <div class="text-body-small text-medium-emphasis">
              <template v-if="unsavedEditCount > 0">
                {{ unsavedEditCount }} edit{{ unsavedEditCount === 1 ? '' : 's' }}
                not yet saved to the session
              </template>
              <template v-else> You have unsaved changes </template>
            </div>
          </div>
        </div>
        <v-card-text class="text-body-medium pt-2 pb-4 px-6">
          Save your edits to the in-progress session before closing, or close
          without saving (unsaved changes are dropped; previously-saved draft
          operations stay in the session).
        </v-card-text>
        <v-divider />
        <v-card-actions class="d-flex align-center ga-2 px-4 py-3">
          <v-btn variant="text" @click="showCloseConfirm = false">Cancel</v-btn>
          <v-spacer />
          <v-btn variant="text" @click="closeWithoutSaving">Close without saving</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-content-save-outline"
            @click="saveDraftAndClose"
          >
            Save &amp; close
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
import { useEditSession } from '@/composables/useEditSession'
import { useUnsavedChangesWarning } from '@/composables/useUnsavedChangesWarning'
import { useResumeEditSession } from '@/composables/useResumeEditSession'
import { useQcSessionStore } from '@/store/qcSession'
import { useQcPreferencesStore } from '@/store/qcPreferences'
import CreateDatastreamForm from '@/components/EditData/CreateDatastreamForm.vue'
import StartEditingDialog from '@/components/EditData/StartEditingDialog.vue'
import {
  useCreateManagedDatastream,
  type CreateManagedDatastreamSpec,
} from '@/composables/useCreateManagedDatastream'
import {
  useManagedDatastreams,
  type ManagedDatastreamOption,
} from '@/composables/useManagedDatastreams'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useProcessingLevels } from '@/composables/useProcessingLevels'
import type { Datastream } from '@hydroserver/client'
import { Snackbar } from '@uwrl/qc-utils'
import {
  decodeShareState,
  encodeShareState,
  type ShareState,
} from '@/utils/share'
import { useWorkspaceStore } from '@/store/workspaces'
import { useResizable, usePersistedFlag } from '@/composables/useResizable'

const { resetState } = useDataVisStore()
const {
  plottedDatastreams,
  qcDatastream,
  datastreams,
  processingLevels,
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
const {
  setPlottedDatastreams,
  adoptManagedDatastream,
  releaseManagedDatastream,
  addQcHistory,
  removeManagedDatastream,
} = useDataVisStore()

const {
  beginEditing,
  startSession,
  saveDraft,
  commit,
  needsSession,
  needsHistory,
  hasUnsavedChanges,
  unsavedEditCount,
  viewSession,
} = useEditSession()
useUnsavedChangesWarning(hasUnsavedChanges)

// Selecting a session in the list loads the data as that session left it,
// plus its own operations. Guarded so unsaved edits aren't dropped silently.
const isViewingSession = ref(false)
async function onViewSession(sessionId: string) {
  if (isViewingSession.value) return
  if (
    hasUnsavedChanges.value &&
    !window.confirm(
      'You have unsaved edits. Viewing another session will discard them. Continue?'
    )
  ) {
    return
  }
  isViewingSession.value = true
  try {
    await viewSession(sessionId)
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not load that session.'
    )
  } finally {
    isViewingSession.value = false
  }
}
const qcSessionStore = useQcSessionStore()
const { isReadOnly, inProgressSession, resumeDatastreamId } =
  storeToRefs(qcSessionStore)
const { create: createManaged } = useCreateManagedDatastream()
const qcPreferences = useQcPreferencesStore()
const { canEdit, canCreateDatastream, roleName } = useWorkspacePermissions()
const { createProcessingLevel } = useProcessingLevels()
const { loadForSource, deleteManaged, deleteSession } = useManagedDatastreams()

// Permission gating: QC editing writes to the selected workspace (creates
// the managed datastream, pushes observations). Gate the editor entry
// points so a read-only collaborator gets a clear disabled state and an
// explanation instead of a 403 mid-flow.
const canEditWorkspace = computed(() => canEdit())
const canCreateDatastreamHere = computed(() => canCreateDatastream())
const workspaceRole = computed(() => roleName())

const editCount = computed(() => editHistory.value?.length ?? 0)
const showCommitConfirm = ref(false)
const showCloseConfirm = ref(false)
const showCreateDatastream = ref(false)
const commitDescription = ref('')
const showChooser = ref(false)
const chooserLoading = ref(false)
const chooserOptions = ref<ManagedDatastreamOption[]>([])
const chooserSource = ref<Datastream | null>(null)
const isSavingDraft = ref(false)
const isCommitting = ref(false)
const isCreating = ref(false)

const saveDisabled = computed(
  () =>
    !canEditWorkspace.value ||
    isReadOnly.value ||
    !inProgressSession.value ||
    !editCount.value ||
    isUpdating.value ||
    isSavingDraft.value ||
    isCommitting.value
)
const commitDisabled = computed(
  () =>
    !canEditWorkspace.value ||
    isReadOnly.value ||
    !inProgressSession.value ||
    isUpdating.value ||
    isSavingDraft.value ||
    isCommitting.value
)

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
  // Leaving the editor deliberately, so a later reload shouldn't reopen it.
  resumeDatastreamId.value = null
  // Put the source back in the plot so the catalog table shows the row the
  // user had selected; the managed datastream it was swapped for is hidden
  // from that table.
  void releaseManagedDatastream()
}

// No in-progress session yet: open one over the window already chosen by the
// time-range controls in the Select view, rather than prompting for it again.
async function startSessionForWindow() {
  try {
    await startSession({
      phenomenonTimeStart: beginDate.value.toISOString(),
      phenomenonTimeEnd: endDate.value.toISOString(),
    })
    await redraw()
    Snackbar.success('Edit session started.')
  } catch (e) {
    Snackbar.error(e instanceof Error ? e.message : 'Could not start the session.')
  }
}

async function onCreateProcessingLevel(input: {
  code: string
  definition?: string
  explanation?: string
}) {
  try {
    const level = await createProcessingLevel(input)
    // Add to the catalog so it shows in the picker and is immediately valid.
    processingLevels.value = [...processingLevels.value, level]
    Snackbar.success('Processing level added.')
    return level
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not add the processing level.'
    )
    return null
  }
}

async function onCreateDatastream(spec: CreateManagedDatastreamSpec) {
  showCreateDatastream.value = false
  qcPreferences.processingLevelId = spec.processingLevelId
  isCreating.value = true
  try {
    const { managedDatastream, history } = await createManaged(spec)
    // Register the new history + datastream so it's hidden from the catalog
    // and the chooser can resolve it (by its name, not id) without a reload.
    addQcHistory(history)
    datastreams.value = [...datastreams.value, managedDatastream]
    // Reuse the source's already-loaded series as the managed datastream's
    // working copy instead of adding a second, empty plotted item.
    await adoptManagedDatastream(managedDatastream, spec.source.id)
    Snackbar.success('Managed datastream created.')
    await enterEdit()
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not create the datastream.'
    )
  } finally {
    isCreating.value = false
  }
}

async function onSaveDraft(): Promise<boolean> {
  isSavingDraft.value = true
  try {
    await saveDraft()
    Snackbar.success('Draft saved.')
    return true
  } catch (e) {
    Snackbar.error(e instanceof Error ? e.message : 'Could not save the draft.')
    return false
  } finally {
    isSavingDraft.value = false
  }
}

async function onSaveAndClose() {
  if (await onSaveDraft()) exitToSelect()
}

// Prefill the description with the session's current one so committing
// preserves/edits it rather than blanking it.
function openCommit() {
  commitDescription.value = inProgressSession.value?.description ?? ''
  showCommitConfirm.value = true
}

async function onCommit() {
  showCommitConfirm.value = false
  isCommitting.value = true
  try {
    await commit(commitDescription.value)
    await redraw()
    Snackbar.success('Session committed.')
  } catch (e) {
    Snackbar.error(e instanceof Error ? e.message : 'Could not commit the session.')
  } finally {
    isCommitting.value = false
  }
}

function requestClose() {
  // Only prompt to save when there are edits not yet persisted to the
  // session; otherwise close straight back to the select view.
  if (hasUnsavedChanges.value) {
    showCloseConfirm.value = true
  } else {
    exitToSelect()
  }
}

async function saveDraftAndClose() {
  showCloseConfirm.value = false
  await onSaveAndClose()
}

function closeWithoutSaving() {
  showCloseConfirm.value = false
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

// "Start editing" opens a chooser of the source's managed datastreams and
// their sessions, rather than editing the raw datastream directly.
async function openEditChooser() {
  const source = qcDatastream.value
  if (!source) return
  chooserSource.value = source
  chooserOptions.value = []
  chooserLoading.value = true
  showChooser.value = true
  try {
    chooserOptions.value = await loadForSource(source.id)
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not load QC datastreams.'
    )
  } finally {
    chooserLoading.value = false
  }
}

// Edit a chosen managed datastream: reuse the source's loaded series as its
// working copy, then resume its in-progress session (or start a new one).
async function editManaged(option: ManagedDatastreamOption) {
  showChooser.value = false
  const source = chooserSource.value
  if (!source) return
  try {
    await adoptManagedDatastream(option.managed, source.id)
    await enterEdit()
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not open the datastream for editing.'
    )
  }
}

function onChooserCreate() {
  showChooser.value = false
  showCreateDatastream.value = true
}

// Cancelling create returns to the chooser it was opened from.
function onCreateCancel() {
  showCreateDatastream.value = false
  if (chooserSource.value) showChooser.value = true
}

async function onChooserDelete(option: ManagedDatastreamOption) {
  try {
    await deleteManaged(option.historyId, option.managed.id)
    removeManagedDatastream(option.historyId, option.managed.id)
    chooserOptions.value = chooserOptions.value.filter(
      (o) => o.historyId !== option.historyId
    )
    Snackbar.success('Managed datastream deleted.')
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not delete the managed datastream.'
    )
  }
}

// Discard an in-progress session from the chooser, dropping its draft edits.
// Only that session goes; the managed datastream and its commits remain.
async function onChooserDeleteSession(
  option: ManagedDatastreamOption,
  sessionId: string
) {
  try {
    await deleteSession(option.historyId, sessionId)
    chooserOptions.value = chooserOptions.value.map((o) =>
      o.historyId === option.historyId
        ? { ...o, sessions: o.sessions.filter((s) => s.id !== sessionId) }
        : o
    )
    Snackbar.success('Session discarded.')
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not discard the session.'
    )
  }
}

// Enter the editor on the current QC-target managed datastream: resume its
// in-progress session, or start a new one over the selected time range.
async function enterEdit() {
  await beginEditing()
  if (needsHistory.value) {
    Snackbar.error('This datastream is not set up for QC editing.')
    return
  }
  currentView.value = DrawerType.Edit
  selectedDrawer.value = DrawerType.Edit
  isDrawerOpen.value = true
  // Remember the target so a page reload can come back to this session.
  resumeDatastreamId.value = qcDatastream.value?.id ?? null
  if (needsSession.value) await startSessionForWindow()
}

// Reopens the editor after a page reload; waits for the catalog to land.
useResumeEditSession(enterEdit)
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
