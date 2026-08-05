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

      <v-tooltip location="bottom" text="Load QC History">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            data-testid="history-load-btn"
            aria-label="Load QC History"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-tray-arrow-up"
            :disabled="isUpdating || isReadOnly"
            @click.stop="onLoadHistoryClick"
          />
        </template>
      </v-tooltip>
      <input
        ref="fileInputRef"
        type="file"
        accept="application/json,.json"
        class="d-none"
        @click.stop
        @change="onLoadHistoryFile"
      />

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
      <div
        class="edit-history__row edit-history__row--baseline px-3 py-2 d-flex align-center"
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
        <span class="text-body-small font-weight-medium flex-grow-1 text-truncate">
          {{ selectedSeries?.data.isLoading ? 'Loading data…' : 'Data loaded' }}
        </span>
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
              @click="onToggleSnapshot(SNAPSHOT_BASELINE_INDEX)"
            />
          </template>
        </v-tooltip>

        <v-tooltip v-if="!selectedSeries?.data.isLoading" location="start" text="Reload from server">
          <template #activator="{ props: tp }">
            <v-btn
              v-bind="tp"
              data-testid="history-reload-btn"
              size="x-small"
              variant="text"
              density="comfortable"
              icon="mdi-reload"
              :disabled="isUpdating || isReadOnly"
              @click="onReload"
            />
          </template>
        </v-tooltip>
      </div>

      <v-divider />

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
            }"
          >
            <button
              type="button"
              class="edit-history__expand mr-1 d-inline-flex align-center justify-center cursor-pointer rounded-sm"
              :title="openIndex === index ? 'Collapse' : 'Expand arguments'"
              :aria-label="
                openIndex === index ? 'Collapse' : 'Expand arguments'
              "
              :aria-expanded="openIndex === index"
              @click="toggle(index)"
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

            <span
              class="edit-history__method flex-grow-1 text-truncate font-weight-medium"
            >
              {{ formatMethod(entry.method) }}
            </span>

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
                v-if="entry.performedBy"
                location="start"
                :text="`Applied by ${entry.performedBy}`"
              >
                <template #activator="{ props: tp }">
                  <span
                    v-bind="tp"
                    class="edit-history__author text-body-small text-medium-emphasis text-truncate"
                    :data-testid="`history-author-${index}`"
                  >
                    {{ entry.performedBy }}
                  </span>
                </template>
              </v-tooltip>

              <v-tooltip v-if="entry.comment" location="start" :text="entry.comment">
                <template #activator="{ props: tp }">
                  <v-icon
                    v-bind="tp"
                    :data-testid="`history-comment-badge-${index}`"
                    icon="mdi-comment-text-outline"
                    size="14"
                    color="primary"
                  />
                </template>
              </v-tooltip>

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
                    @click="onToggleSnapshot(index)"
                  />
                </template>
              </v-tooltip>

              <v-tooltip location="start" text="Reload from this step">
                <template #activator="{ props: tp }">
                  <v-btn
                    v-bind="tp"
                    size="x-small"
                    variant="text"
                    density="comfortable"
                    icon="mdi-reload"
                    :disabled="isUpdating || entry.execution?.inFlight"
                    @click="onReloadHistory(index)"
                  />
                </template>
              </v-tooltip>

              <!-- Trailing entry only; middle entries use "Reload from this
                   step". Never on a committed session. -->
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
                    @click="onUndo"
                  />
                </template>
              </v-tooltip>
            </div>
          </div>

          <div v-if="openIndex === index" class="edit-history__args px-3 py-2">
            <div class="text-body-small text-medium-emphasis mb-1">Arguments</div>
            <ul class="edit-history__args-list pa-0 ma-0 overflow-y-auto">
              <li
                v-for="(arg, argIdx) of entry.args"
                :key="argIdx"
                class="text-body-small px-1 py-1"
                style="word-break: break-all"
              >
                <code class="text-body-small">{{ formatArg(arg) }}</code>
              </li>
            </ul>

            <div
              v-if="isApplied(index) && isDev && entry.execution?.mode"
              class="text-body-small text-medium-emphasis mt-3 d-flex align-center ga-2"
              :data-testid="`history-execution-${index}`"
            >
              <!-- Dev-only: whether the dispatch ran on a worker or inline. -->
              <v-chip
                v-if="isDev && entry.execution?.mode"
                size="x-small"
                variant="tonal"
                :color="entry.execution.mode === 'inline' ? 'success' : 'primary'"
                class="edit-history__mode-chip"
                :title="
                  entry.execution.mode === 'inline'
                    ? 'Ran on the main thread (inline)'
                    : 'Ran on a web worker'
                "
              >
                {{ entry.execution.mode }}
              </v-chip>
            </div>

            <div
              v-if="entry.performedBy"
              class="text-body-small text-medium-emphasis mt-3"
              :data-testid="`history-author-detail-${index}`"
            >
              Applied by {{ entry.performedBy }}
            </div>

            <div class="text-body-small text-medium-emphasis mt-3 mb-1">
              Comment
            </div>
            <v-textarea
              v-if="!isReadOnly"
              :model-value="entry.comment ?? ''"
              :data-testid="`history-comment-${index}`"
              placeholder="Why was this operation applied?"
              variant="outlined"
              density="compact"
              rows="2"
              auto-grow
              hide-details
              class="text-body-small"
              @update:model-value="setComment(entry, $event)"
            />
            <div
              v-else
              class="text-body-small"
              :class="{ 'text-medium-emphasis font-italic': !entry.comment }"
              :data-testid="`history-comment-readonly-${index}`"
            >
              {{ entry.comment || 'No comment.' }}
            </div>
          </div>

          <v-divider />
        </div>
      </div>
          </div>
        </template>
      </SessionList>
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
import { useQcHistory } from '@/composables/useQcHistory'
import { useQcSessionStore } from '@/store/qcSession'
import { useHistorySnapshots } from '@/composables/useHistorySnapshots'
import { SNAPSHOT_BASELINE_INDEX } from '@/utils/snapshotId'
import { Snackbar } from '@uwrl/qc-utils'
import type { HistoryItem } from '@uwrl/qc-utils'

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

const { editHistory, selectedSeries, isUpdating } =
  storeToRefs(usePlotlyStore())
const { selectedOperation } = storeToRefs(useUIStore())
const { redraw } = usePlotlyStore()
const { clearSelected, setPlotSelection } = useDataSelection()
const { exportHistory, importHistory } = useQcHistory()
const fileInputRef = ref<HTMLInputElement | null>(null)

const openIndex = ref<number | null>(null)

/** Invalidated by any mutation of the history. */
const loadedStepIndex = ref<number | null>(null)

/** The step the plot reflects: the explicit choice, else the last entry. */
const shownStepIndex = computed<number | null>(() => {
  const last = editHistory.value.length - 1
  if (last < 0) return null
  const chosen = loadedStepIndex.value
  return chosen !== null && chosen <= last ? chosen : last
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

function setComment(entry: HistoryItem, value: string) {
  entry.comment = value
}

const isDev = import.meta.env.DEV

const editCount = computed(() => editHistory.value?.length ?? 0)

const canUndo = computed(
  () => !!selectedSeries.value?.data && (editHistory.value?.length ?? 0) > 0
)
const canRedo = computed(
  () => (selectedSeries.value?.data.redoStack?.length ?? 0) > 0
)

function toggle(index: number) {
  openIndex.value = openIndex.value === index ? null : index
}

/** Steps past the one on screen were not replayed, so their execution
 *  record describes a run that no longer holds in this view. */
const isApplied = (index: number) =>
  shownStepIndex.value === null || index <= shownStepIndex.value

function formatMethod(method: string) {
  if (!method) return ''
  return method
    .toLowerCase()
    .split('_')
    .map((w) => (w ? w[0]!.toUpperCase() + w.slice(1) : ''))
    .join(' ')
}

function formatArg(arg: unknown): string {
  if (Array.isArray(arg)) {
    const len = arg.length
    if (!len) return '[]'
    const preview = arg
      .slice(0, 5)
      .map((v) => (typeof v === 'number' ? v : JSON.stringify(v)))
      .join(', ')
    return len <= 5 ? `[${preview}]` : `[${preview}, … (${len} items)]`
  }
  if (arg && typeof arg === 'object') {
    try {
      return JSON.stringify(arg)
    } catch {
      return String(arg)
    }
  }
  return String(arg)
}

const onReload = async () => {
  loadedStepIndex.value = null
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
    await selectedSeries.value?.data.reload()
    // reload() already wiped history; don't push an empty SELECTION.
    await clearSelected({ recordHistory: false })
    isUpdating.value = false
    await redraw()
  })
}

const onReloadHistory = async (index: number) => {
  if (index < editHistory.value.length) {
    isUpdating.value = true
    closeStaleStagingPanel()
    // `reloadHistory` truncates to `0..index`; a committed session's
    // operations must survive stepping through them.
    const record = selectedSeries.value?.data
    const preserved = isReadOnly.value ? [...(record?.history ?? [])] : null
    loadedStepIndex.value = index
    setTimeout(async () => {
      const newSelection = await record?.reloadHistory(index)
      if (preserved && record) {
        // Append only what the replay dropped. Restoring `preserved`
        // wholesale would put the pre-replay timings back.
        const tail = preserved.slice(index + 1)
        record.history.push(...tail)
        loadedStepIndex.value = record.history.length - tail.length - 1
      }

      isUpdating.value = false
      await applyReplayedSelection(newSelection)
    })
  }
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

const onLoadHistoryClick = () => {
  fileInputRef.value?.click()
}

const onLoadHistoryFile = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // Reset early so re-picking the same file fires change again.
  input.value = ''
  if (!file) return

  isUpdating.value = true
  try {
    const report = await importHistory(file)
    if (report.failed.length === 0) {
      Snackbar.success(
        `Loaded ${report.applied} operation${report.applied === 1 ? '' : 's'}.`
      )
    } else {
      Snackbar.warn(
        `Loaded ${report.applied} operation${report.applied === 1 ? '' : 's'}; ` +
          `${report.failed.length} failed (see history badges).`
      )
    }
    await redraw()
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    Snackbar.error(`Couldn't load QC history: ${msg}`)
  } finally {
    isUpdating.value = false
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
  loadedStepIndex.value = null
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
  loadedStepIndex.value = null
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

.edit-history__author {
  max-width: 8rem;
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

.edit-history__method {
  font-size: 0.8125rem;
  min-width: 0;
}

.edit-history__args {
  background-color: rgba(var(--v-theme-primary), 0.03);
  border-left: 2px solid rgb(var(--v-theme-primary));
}

.edit-history__args-list {
  list-style: none;
  max-height: 12rem;
}

.edit-history__mode-chip {
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  height: 16px;
  padding-inline: 6px;
}
</style>
