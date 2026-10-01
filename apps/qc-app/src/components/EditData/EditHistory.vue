<template>
  <div class="edit-history d-flex flex-column" style="min-height: 0">
    <div
      class="edit-history__header px-3 d-flex align-center ga-2"
      :class="{ 'edit-history__header--collapsible': collapsible }"
      :role="collapsible ? 'button' : undefined"
      :tabindex="collapsible ? 0 : undefined"
      @click="onHeaderClick"
      @keydown.enter.prevent="collapsible && toggleCollapsed()"
      @keydown.space.prevent="collapsible && toggleCollapsed()"
    >
      <v-icon
        v-if="collapsible"
        size="16"
        :icon="isCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-down'"
      />
      <v-icon icon="mdi-history" color="primary" size="16" />
      <span class="text-body-small font-weight-medium">Edit history</span>
      <v-chip
        v-if="editCount"
        size="x-small"
        color="primary"
        variant="tonal"
        label
      >
        {{ editCount }}
      </v-chip>

      <v-spacer />

      <v-tooltip location="bottom" text="Undo (Ctrl+Z)">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            data-testid="history-undo-btn"
            aria-label="Undo"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-undo-variant"
            :disabled="isUpdating || isReadOnly || !canUndo"
            @click.stop="onUndo"
          />
        </template>
      </v-tooltip>

      <v-tooltip location="bottom" text="Redo (Ctrl+Y)">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            data-testid="history-redo-btn"
            aria-label="Redo"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-redo-variant"
            :disabled="isUpdating || isReadOnly || !canRedo"
            @click.stop="onRedo"
          />
        </template>
      </v-tooltip>

      <v-tooltip location="bottom" text="Save QC History">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            data-testid="history-save-btn"
            aria-label="Save QC History"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-tray-arrow-down"
            :disabled="isUpdating || !editCount"
            @click.stop="onSaveHistory"
          />
        </template>
      </v-tooltip>

      <v-tooltip v-if="popOutEnabled" location="bottom" text="Open in window">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            aria-label="Open history in a modal window"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-open-in-new"
            @click.stop="emit('pop-out')"
          />
        </template>
      </v-tooltip>
    </div>

    <v-divider />

    <div
      v-show="!isCollapsed"
      class="flex-grow-1 overflow-y-auto pa-2"
      style="min-height: 0"
    >
      <SessionList @view="emit('view-session', $event)">
        <template #operations>
          <div class="rounded border bg-surface overflow-hidden">
            <!-- Row clicks are a mouse shortcut. The step button is the real control,
                 so the row's other buttons are not nested inside a button. -->
            <div
              class="edit-history__row edit-history__row--baseline px-3 py-2 d-flex align-center"
              :class="{ 'edit-history__row--clickable': canStepTo }"
              data-testid="history-reload-step-baseline"
              :title="canStepTo ? `Preview the session's starting state` : undefined"
              @click="onRowReload(SNAPSHOT_BASELINE_INDEX)"
            >
              <v-icon
                :icon="
                  selectedSeries?.data.isLoading
                    ? 'mdi-progress-download'
                    : 'mdi-database-check'
                "
                size="16"
                :color="selectedSeries?.data.isLoading ? 'grey' : 'success'"
                class="mr-2"
              />
              <button
                type="button"
                class="edit-history__step text-body-small font-weight-medium flex-grow-1 text-truncate"
                data-testid="history-step-btn-baseline"
                :disabled="!canStepTo"
                :title="canStepTo ? `Preview the session's starting state` : undefined"
                @click.stop="onRowReload(SNAPSHOT_BASELINE_INDEX)"
              >
                {{ selectedSeries?.data.isLoading ? 'Loading data…' : 'Data loaded' }}
              </button>
              <v-chip
                v-if="shownStepIndex === SNAPSHOT_BASELINE_INDEX"
                size="x-small"
                color="primary"
                variant="tonal"
                label
                class="mr-1 flex-shrink-0"
                data-testid="history-loaded-baseline"
              >
                Showing
              </v-chip>

              <span
                v-if="selectedSeries?.data.loadingTime"
                class="text-body-small text-medium-emphasis mr-1 flex-shrink-0"
              >
                {{ formatDuration(selectedSeries?.data.loadingTime) }}
              </span>
              <v-progress-circular
                v-if="selectedSeries?.data.isLoading"
                size="14"
                width="2"
                color="primary"
                indeterminate
              />
              <v-tooltip
                location="start"
                :text="
                  snapshotShown(SNAPSHOT_BASELINE_INDEX)
                    ? 'Remove this comparison line'
                    : `Plot the session's starting state`
                "
              >
                <template #activator="{ props: tp }">
                  <v-btn
                    v-bind="tp"
                    data-testid="history-snapshot-baseline"
                    aria-label="Plot the session's starting state"
                    size="x-small"
                    variant="text"
                    density="comfortable"
                    :icon="
                      snapshotShown(SNAPSHOT_BASELINE_INDEX)
                        ? 'mdi-chart-line-variant'
                        : 'mdi-chart-line'
                    "
                    :color="
                      snapshotShown(SNAPSHOT_BASELINE_INDEX) ? 'primary' : undefined
                    "
                    :disabled="isBuilding"
                    @click.stop="onToggleSnapshot(SNAPSHOT_BASELINE_INDEX)"
                  />
                </template>
              </v-tooltip>

              <!-- Refetches from the server; the step reload above replays the
                   in-memory raw. Hidden on a committed session. -->
              <v-tooltip
                v-if="!selectedSeries?.data.isLoading && !isReadOnly"
                location="start"
                text="Discard edits and reload from server"
              >
                <template #activator="{ props: tp }">
                  <v-btn
                    v-bind="tp"
                    data-testid="history-reload-btn"
                    aria-label="Discard edits and reload from server"
                    size="x-small"
                    variant="text"
                    density="comfortable"
                    icon="mdi-cloud-download-outline"
                    :disabled="isUpdating"
                    @click.stop="onReload"
                  />
                </template>
              </v-tooltip>
            </div>

            <v-divider />

            <div
              v-if="previewIndex !== null && !isSwitchingSession"
              class="edit-history__preview d-flex align-center ga-2 px-3 py-2"
              data-testid="history-preview-banner"
            >
              <v-icon icon="mdi-eye-outline" size="16" color="primary" />
              <span class="text-body-small flex-grow-1">
                Previewing
                {{
                  previewIndex < 0
                    ? 'the starting state'
                    : `step ${previewIndex + 1} of ${editCount}`
                }}. Editing waits until you are back on the latest step.
              </span>
              <v-btn
                data-testid="history-back-to-latest-btn"
                size="small"
                variant="flat"
                color="primary"
                :disabled="isUpdating"
                @click.stop="onBackToLatest"
              >
                Back to latest
              </v-btn>
            </div>

            <!-- Or the outgoing session's operations linger as if they were these. -->
            <div
              v-if="isSwitchingSession"
              class="pa-4 text-center"
              data-testid="history-loading"
            >
              <v-progress-circular indeterminate color="primary" size="24" />
              <div class="text-body-small text-medium-emphasis mt-2">
                Loading session…
              </div>
            </div>

            <div v-else-if="editCount === 0" class="pa-4 text-center">
              <v-icon icon="mdi-clock-outline" size="28" color="grey" class="mb-2" />
              <div class="text-body-small text-medium-emphasis">
                Edit operations will appear here.
              </div>
            </div>

            <div v-else>
              <div
                v-for="(entry, index) of editHistory"
                :key="index"
                :data-testid="`history-item-${index}`"
              >
                <div
                  class="edit-history__row px-3 py-1 d-flex align-center"
                  :class="{
                    'edit-history__row--loading': entry.execution?.inFlight,
                    'edit-history__row--open': openIndex === index,
                    'edit-history__row--loaded': shownStepIndex === index,
                    'edit-history__row--unapplied': !isApplied(index),
                    'edit-history__row--clickable': canStepTo,
                  }"
                  :title="stepTitle(index)"
                  @click="onRowReload(index)"
                >
                  <button
                    type="button"
                    class="edit-history__expand mr-1 d-inline-flex align-center justify-center cursor-pointer rounded-sm"
                    :title="openIndex === index ? 'Collapse' : 'Expand arguments'"
                    :aria-label="
                      openIndex === index ? 'Collapse' : 'Expand arguments'
                    "
                    :aria-expanded="openIndex === index"
                    @click.stop="toggle(index)"
                  >
                    <v-icon
                      :icon="
                        openIndex === index ? 'mdi-chevron-down' : 'mdi-chevron-right'
                      "
                      size="16"
                    />
                  </button>

                  <v-icon
                    :icon="iconForMethod(entry.method)"
                    size="16"
                    :color="
                      entry.execution?.status === 'failed'
                        ? 'error'
                        : colorForMethod(entry.method)
                    "
                    class="mr-2"
                  />

                  <!-- Grows as one unit so the badge sits against the title text. -->
                  <button
                    type="button"
                    class="edit-history__step edit-history__title flex-grow-1 d-flex flex-column align-start"
                    :data-testid="`history-step-btn-${index}`"
                    :disabled="!canStepTo || entry.execution?.inFlight"
                    :title="stepTitle(index)"
                    @click.stop="onRowReload(index)"
                  >
                    <span class="d-flex align-center ga-1 w-100">
                      <span class="edit-history__method text-truncate font-weight-medium">
                        {{ formatMethod(entry.method) }}
                      </span>

                      <v-tooltip v-if="entry.comment" location="start" :text="entry.comment">
                        <template #activator="{ props: tp }">
                          <v-icon
                            v-bind="tp"
                            :data-testid="`history-comment-badge-${index}`"
                            icon="mdi-comment-text-outline"
                            size="14"
                            color="primary"
                            class="flex-shrink-0"
                          />
                        </template>
                      </v-tooltip>
                    </span>

                    <span
                      v-if="stepExtent(entry)"
                      class="edit-history__extent text-medium-emphasis text-truncate w-100"
                      :data-testid="`history-extent-${index}`"
                    >
                      {{ stepExtent(entry) }}
                    </span>
                  </button>

                  <v-chip
                    v-if="shownStepIndex === index"
                    size="x-small"
                    color="primary"
                    variant="tonal"
                    label
                    class="mr-1 flex-shrink-0"
                    :data-testid="`history-loaded-${index}`"
                  >
                    Showing
                  </v-chip>

                  <div class="d-flex align-center ga-2 flex-shrink-0">
                    <v-tooltip
                      v-if="isApplied(index) && entry.execution?.status === 'failed'"
                      location="start"
                      text="Operation failed: see console for details"
                    >
                      <template #activator="{ props: tp }">
                        <v-icon
                          v-bind="tp"
                          :data-testid="`history-failed-${index}`"
                          icon="mdi-alert-circle"
                          size="14"
                          color="error"
                        />
                      </template>
                    </v-tooltip>

                    <!-- `!= null` so a replay that measures 0ms still reads as
                         having run. -->
                    <span
                      v-if="isApplied(index) && entry.execution?.durationMs != null"
                      :data-testid="`history-duration-${index}`"
                      class="text-body-small text-medium-emphasis"
                    >
                      {{ formatDuration(entry.execution.durationMs) }}
                    </span>

                    <v-progress-circular
                      v-if="entry.execution?.inFlight"
                      size="14"
                      width="2"
                      color="primary"
                      indeterminate
                    />

                    <v-tooltip
                      location="start"
                      :text="
                        snapshotShown(index)
                          ? 'Remove this comparison line'
                          : 'Plot this step as a comparison line'
                      "
                    >
                      <template #activator="{ props: tp }">
                        <v-btn
                          v-bind="tp"
                          :data-testid="`history-snapshot-${index}`"
                          aria-label="Plot this step as a comparison line"
                          size="x-small"
                          variant="text"
                          density="comfortable"
                          :icon="
                            snapshotShown(index)
                              ? 'mdi-chart-line-variant'
                              : 'mdi-chart-line'
                          "
                          :color="snapshotShown(index) ? 'primary' : undefined"
                          :disabled="isBuilding || entry.execution?.inFlight"
                          @click.stop="onToggleSnapshot(index)"
                        />
                      </template>
                    </v-tooltip>

                    <!-- Trailing entry only: earlier steps are previewed, not
                         undone. Never on a committed session. -->
                    <v-tooltip
                      v-if="index === editHistory.length - 1 && !isReadOnly"
                      location="start"
                      text="Undo this step"
                    >
                      <template #activator="{ props: tp }">
                        <v-btn
                          v-bind="tp"
                          :data-testid="`history-undo-${index}`"
                          aria-label="Undo this step"
                          size="x-small"
                          variant="text"
                          density="comfortable"
                          icon="mdi-undo-variant"
                          color="error"
                          :disabled="isUpdating"
                          @click.stop="onUndo"
                        />
                      </template>
                    </v-tooltip>
                  </div>
                </div>

                <EditHistoryStepDetails
                  v-if="openIndex === index"
                  :entry="entry"
                  :index="index"
                  :applied="isApplied(index)"
                  :read-only="isReadOnly"
                  @update:comment="entry.comment = $event"
                />

                <v-divider />
              </div>
            </div>
          </div>
        </template>
      </SessionList>
    </div>

    <!-- Sits outside the collapsible body, so it stays visible when
         collapsed. -->
    <div
      v-if="$slots.footer"
      class="edit-history__footer flex-shrink-0 px-2 pb-2"
      :class="isCollapsed ? 'pt-2' : 'pt-0'"
    >
      <!-- Same container treatment as the session rows above. -->
      <div
        class="rounded border bg-surface d-flex align-center flex-wrap ga-2 px-2 py-2"
      >
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlotlyStore } from '@/store/plotly'
import { useDataSelection } from '@/composables/useDataSelection'
import { formatDuration } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { useUIStore } from '@/store/userInterface'
import { iconForMethod, colorForMethod } from '@/components/EditData/operations'
import SessionList from '@/components/EditData/SessionList.vue'
import EditHistoryStepDetails from '@/components/EditData/EditHistoryStepDetails.vue'
import { useQcHistory } from '@/composables/useQcHistory'
import { useQcSessionStore } from '@/store/qcSession'
import { useHistorySnapshots } from '@/composables/useHistorySnapshots'
import { SNAPSHOT_BASELINE_INDEX } from '@/utils/snapshotId'
import { Snackbar } from '@uwrl/qc-utils'
import type { HistoryItem } from '@uwrl/qc-utils'
import { formatDateRange, formatStamp } from '@/utils/time'

const props = withDefaults(
  defineProps<{
    collapsible?: boolean
    collapsed?: boolean
    popOutEnabled?: boolean
  }>(),
  {
    collapsible: true,
    collapsed: false,
    popOutEnabled: true,
  }
)

defineSlots<{
  /** Session actions pinned below the history, shown collapsed or not. */
  footer?: () => any
}>()

const emit = defineEmits<{
  (e: 'update:collapsed', value: boolean): void
  (e: 'pop-out'): void
  (e: 'view-session', sessionId: string): void
}>()

const isCollapsed = computed(() => props.collapsible && !!props.collapsed)
const toggleCollapsed = () => {
  if (!props.collapsible) return
  emit('update:collapsed', !props.collapsed)
}

// Bail when the click landed on a descendant button. Firefox sometimes
// hit-tests the header div instead of the v-btn even with @click.stop,
// which would otherwise collapse the panel under the user's cursor.
const onHeaderClick = (e: MouseEvent) => {
  if (!props.collapsible) return
  const target = e.target as HTMLElement | null
  if (target?.closest('button')) return
  toggleCollapsed()
}

const { editHistory, selectedSeries, isUpdating, previewIndex } =
  storeToRefs(usePlotlyStore())
const { selectedOperation } = storeToRefs(useUIStore())
const { redraw } = usePlotlyStore()
const { clearSelected, setPlotSelection } = useDataSelection()
const { exportHistory } = useQcHistory()

const openIndex = ref<number | null>(null)

/** The step the plot reflects: the one previewed, else the last entry. */
const shownStepIndex = computed<number | null>(() => {
  const last = editHistory.value.length - 1
  if (last < 0) return null
  return previewIndex.value ?? last
})

// Committed sessions are immutable server-side, so their comments are shown
// but not editable.
const { isReadOnly, isSwitchingSession, viewedSessionId } =
  storeToRefs(useQcSessionStore())

const { toggleSnapshot, isSnapshotPlotted, isBuilding } = useHistorySnapshots()

// Not gated on isReadOnly: plotting a comparison line is a read action.
const onToggleSnapshot = async (opIndex: number) => {
  const sessionId = viewedSessionId.value
  if (!sessionId) return
  await toggleSnapshot(sessionId, opIndex)
}

const snapshotShown = (opIndex: number) =>
  !!viewedSessionId.value && isSnapshotPlotted(viewedSessionId.value, opIndex)

const editCount = computed(() => editHistory.value?.length ?? 0)

const canUndo = computed(
  () => !!selectedSeries.value?.data && (editHistory.value?.length ?? 0) > 0
)
const canRedo = computed(
  () => (selectedSeries.value?.data.redoStack?.length ?? 0) > 0
)

/** Stepping needs something to replay and a settled dispatch. */
const canStepTo = computed(() => !isUpdating.value && editCount.value > 0)

/** Row click / Enter / Space: preview that step. */
const onRowReload = (index: number) => {
  if (!canStepTo.value) return
  if (index >= 0 && editHistory.value[index]?.execution?.inFlight) return
  onReloadHistory(index)
}

function toggle(index: number) {
  openIndex.value = openIndex.value === index ? null : index
}

/** Steps past the one on screen were not replayed, so their execution
 *  record describes a run that no longer holds in this view. */
const isApplied = (index: number) =>
  shownStepIndex.value === null || index <= shownStepIndex.value

const stepTitle = (index: number) =>
  isApplied(index)
    ? 'Preview this step'
    : 'Not applied in the step currently shown. Click to preview it.'

/** The period a step touched and how many points, from the datetimes qc-utils
 *  read when it ran. Indices would drift with later edits. */
function stepExtent(entry: HistoryItem): string {
  const extent = entry.execution?.extent
  if (!extent) return ''
  const begin = new Date(extent.begin)
  const end = new Date(extent.end)
  const period =
    extent.begin === extent.end
      ? formatStamp(begin)
      : formatDateRange(begin.toISOString(), end.toISOString())
  const n = entry.execution?.selectionSize
  return n ? `${period} · ${n.toLocaleString()} pt${n === 1 ? '' : 's'}` : period
}

function formatMethod(method: string) {
  if (!method) return ''
  return method
    .toLowerCase()
    .split('_')
    .map((w) => (w ? w[0]!.toUpperCase() + w.slice(1) : ''))
    .join(' ')
}

const onReload = async () => {
  if (isReadOnly.value || isUpdating.value) return
  isUpdating.value = true
  closeStaleStagingPanel()

  setTimeout(async () => {
    const { refreshGraphSeriesArray } = useDataVisStore()
    if (selectedSeries.value) {
      // In-place clear: reassigning history = [] would detach
      // the editHistory ref from the array the store watches.
      selectedSeries.value.data.history.length = 0
      selectedSeries.value.data.redoStack.length = 0
    }
    await refreshGraphSeriesArray()
    // Restores the raw values when the refetch above failed and left the
    // edited record in place.
    await selectedSeries.value?.data.reload()
    // reload() already wiped history; don't push an empty SELECTION.
    await clearSelected({ recordHistory: false })
    isUpdating.value = false
    await redraw()
  })
}

// Previewing only shows a step: every step stays in the history, and only
// undo and redo change it. The last step is the whole history again.
const onReloadHistory = async (index: number) => {
  if (index >= editHistory.value.length) return
  const record = selectedSeries.value?.data
  if (!record) return
  isUpdating.value = true
  closeStaleStagingPanel()
  setTimeout(async () => {
    try {
      await applyReplayedSelection(await record.previewHistory(index))
    } finally {
      isUpdating.value = false
    }
  })
}

const onBackToLatest = () => {
  const last = editHistory.value.length - 1
  if (last >= 0) void onReloadHistory(last)
}

const onSaveHistory = async () => {
  try {
    await exportHistory()
    Snackbar.success('QC history saved.')
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    Snackbar.error(`Couldn't save QC history: ${msg}`)
  }
}

// Pass recordHistory: false on the clear path because the replay is
// authoritative; dispatching an empty SELECTION could pop a filter the
// replay just restored.
const applyReplayedSelection = async (newSelection: number[] | undefined) => {
  await redraw()
  if (newSelection && newSelection.length) {
    await setPlotSelection(newSelection)
  } else {
    await clearSelected({ recordHistory: false })
  }
}

// Drop the Fill Gaps panel before an undo/redo so its
// onBeforeUnmount clears the ghost-marker trace before the replay
// shifts the underlying gaps.
const closeStaleStagingPanel = () => {
  if (selectedOperation.value === 'fillGaps') {
    selectedOperation.value = null
  }
}

const onUndo = async () => {
  // Also guards the Ctrl+Z shortcut, which bypasses the disabled button.
  if (isReadOnly.value || !canUndo.value || isUpdating.value) return
  isUpdating.value = true
  closeStaleStagingPanel()
  setTimeout(async () => {
    try {
      const newSelection = await selectedSeries.value?.data.undo()
      await applyReplayedSelection(newSelection)
    } finally {
      isUpdating.value = false
    }
  })
}

const onRedo = async () => {
  if (isReadOnly.value || !canRedo.value || isUpdating.value) return
  isUpdating.value = true
  closeStaleStagingPanel()
  setTimeout(async () => {
    try {
      const newSelection = await selectedSeries.value?.data.redo()
      await applyReplayedSelection(newSelection)
    } finally {
      isUpdating.value = false
    }
  })
}

// Ctrl/Cmd+Z undo, Ctrl+Y or Ctrl/Cmd+Shift+Z redo.
// Bail on inputs so native field undo still wins.
const onKeydown = (e: KeyboardEvent) => {
  const mod = e.ctrlKey || e.metaKey
  if (!mod) return

  const target = e.target as HTMLElement | null
  if (
    target &&
    (target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable)
  ) {
    return
  }

  const key = e.key.toLowerCase()
  if (key === 'z' && !e.shiftKey) {
    e.preventDefault()
    onUndo()
  } else if (key === 'y' || (key === 'z' && e.shiftKey)) {
    e.preventDefault()
    onRedo()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.edit-history__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 32px;
}

.edit-history__header--collapsible {
  cursor: pointer;
}
.edit-history__header--collapsible:hover,
.edit-history__header--collapsible:focus {
  outline: none;
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.edit-history__row {
  min-height: 32px;
  transition: background-color 120ms ease;
}

.edit-history__row:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.edit-history__row--clickable {
  cursor: pointer;
}

/* Size and weight come from the typography utility classes. */
.edit-history__step {
  min-width: 0;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font-family: inherit;
  text-align: start;
  cursor: inherit;
}

.edit-history__step:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.edit-history__row--loaded {
  background-color: rgba(var(--v-theme-primary), 0.1);
  box-shadow: inset 3px 0 0 0 rgb(var(--v-theme-primary));
}

.edit-history__row--open {
  background-color: rgba(var(--v-theme-primary), 0.06);
}

.edit-history__row--baseline {
  background-color: rgba(var(--v-theme-success, 76 175 80), 0.04);
}

.edit-history__row--loading {
  opacity: 0.75;
}

/* Steps past the one on screen were not replayed, so they are dimmed to
   separate what the plot reflects from what is merely recorded. */
.edit-history__preview {
  background-color: rgba(var(--v-theme-primary), 0.06);
}

.edit-history__row--unapplied {
  opacity: 0.45;
}

.edit-history__expand {
  width: 20px;
  height: 20px;
  padding: 0;
  background: transparent;
  border: none;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.edit-history__expand:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.edit-history__title {
  min-width: 0;
  line-height: inherit;
}

.edit-history__method {
  font-size: 0.8125rem;
  min-width: 0;
}

.edit-history__extent {
  font-size: 0.6875rem;
  line-height: 1.2;
}
</style>
