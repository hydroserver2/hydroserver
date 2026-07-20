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
            :disabled="isUpdating || !canUndo"
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
            :disabled="isUpdating || !canRedo"
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
            :disabled="isUpdating"
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
        <v-tooltip v-else location="start" text="Reload from server">
          <template #activator="{ props: tp }">
            <v-btn
              v-bind="tp"
              size="x-small"
              variant="text"
              density="comfortable"
              icon="mdi-reload"
              :disabled="isUpdating"
              @click="onReload"
            />
          </template>
        </v-tooltip>
      </div>

      <v-divider />

      <div v-if="editCount === 0" class="pa-4 text-center">
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

            <div class="d-flex align-center ga-2 flex-shrink-0">
              <v-tooltip
                v-if="entry.execution?.status === 'failed'"
                location="start"
                text="Operation failed: see console for details"
              >
                <template #activator="{ props: tp }">
                  <v-icon
                    v-bind="tp"
                    icon="mdi-alert-circle"
                    size="14"
                    color="error"
                  />
                </template>
              </v-tooltip>

              <!-- Dev-only badge showing whether the dispatch ran on a
                   worker or inline; gated on import.meta.env.DEV. -->
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

              <span
                v-if="entry.execution?.durationMs"
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

              <!-- Per-item undo only on the trailing entry; middle
                   entries use "Reload from this step". -->
              <v-tooltip
                v-if="index === editHistory.length - 1"
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
          </div>

          <v-divider />
        </div>
      </div>
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
import { useQcHistory } from '@/composables/useQcHistory'
import { Snackbar } from '@uwrl/qc-utils'

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
    setTimeout(async () => {
      const newSelection = await selectedSeries.value?.data.reloadHistory(index)

      isUpdating.value = false
      await redraw()
      if (newSelection) {
        setPlotSelection(newSelection)
      }
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
  if (!canUndo.value || isUpdating.value) return
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
  if (!canRedo.value || isUpdating.value) return
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
