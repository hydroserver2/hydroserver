<template>
  <div class="edit-history d-flex flex-column" style="min-height: 0">
    <!-- Header. Mirrors the section-header pattern used by Plotted
         Datastreams in the parent (chevron + caption) so the
         sidebar reads as a consistent stack of collapsible panels.
         The undo / redo / pop-out actions trail on the right; they
         stop propagation so clicking them doesn't also toggle the
         collapse. -->
    <div
      class="edit-history__header px-3 d-flex align-center gap-1"
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
      <span class="text-caption font-weight-medium">Edit history</span>
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

      <v-tooltip location="bottom" text="Save QC script">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            data-testid="history-save-btn"
            aria-label="Save QC script"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-tray-arrow-down"
            :disabled="isUpdating || !editCount"
            @click.stop="onSaveScript"
          />
        </template>
      </v-tooltip>

      <v-tooltip location="bottom" text="Load QC script">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            data-testid="history-load-btn"
            aria-label="Load QC script"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-tray-arrow-up"
            :disabled="isUpdating"
            @click.stop="onLoadScriptClick"
          />
        </template>
      </v-tooltip>
      <!-- Hidden file input the load button forwards to. Reset
           `value` after each pick so picking the same file twice
           still triggers `change`. -->
      <input
        ref="fileInputRef"
        type="file"
        accept="application/json,.json"
        style="display: none"
        @click.stop
        @change="onLoadScriptFile"
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
      class="edit-history__body flex-grow-1 overflow-y-auto"
      style="min-height: 0"
    >
     <div class="edit-history__card">
      <!-- Baseline: "Data loaded" status row with its own reload action. -->
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
        <span class="text-caption font-weight-medium flex-grow-1 text-truncate">
          {{ selectedSeries?.data.isLoading ? 'Loading data…' : 'Data loaded' }}
        </span>
        <span
          v-if="selectedSeries?.data.loadingTime"
          class="text-caption text-medium-emphasis mr-1 flex-shrink-0"
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

      <!-- Empty state (no edits yet). -->
      <div v-if="editCount === 0" class="edit-history__empty pa-4 text-center">
        <v-icon icon="mdi-clock-outline" size="28" color="grey" class="mb-2" />
        <div class="text-caption text-medium-emphasis">
          Edit operations will appear here.
        </div>
      </div>

      <!-- Edit entries. The chevron on the left toggles the details
           drawer (arguments list) inline so users can peek without
           pushing adjacent rows around. -->
      <div v-else>
        <div
          v-for="(entry, index) of editHistory"
          :key="index"
          :data-testid="`history-item-${index}`"
          class="edit-history__entry"
        >
          <div
            class="edit-history__row px-3 py-1 d-flex align-center"
            :class="{
              'edit-history__row--loading': entry.isLoading,
              'edit-history__row--open': openIndex === index,
            }"
          >
            <button
              type="button"
              class="edit-history__expand mr-1"
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
                entry.status === 'failed'
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

            <!-- Failure badge — surfaces ops that threw at author
                 time so the user knows the entry didn't actually
                 apply. The same flag round-trips through
                 save/load via `HistoryItem.status`. -->
            <v-tooltip
              v-if="entry.status === 'failed'"
              location="start"
              text="Operation failed — see console for details"
            >
              <template #activator="{ props: tp }">
                <v-icon
                  v-bind="tp"
                  icon="mdi-alert-circle"
                  size="14"
                  color="error"
                  class="mr-1 flex-shrink-0"
                />
              </template>
            </v-tooltip>

            <!-- Dev-only execution mode badge. Surfaces whether the
                 calibration layer routed this dispatch to a worker or
                 inline main-thread path — quick feedback for tuning
                 thresholds without opening devtools. Hidden in prod
                 via `import.meta.env.DEV`. -->
            <v-chip
              v-if="isDev && entry.executionMode"
              size="x-small"
              variant="tonal"
              :color="entry.executionMode === 'inline' ? 'success' : 'primary'"
              class="mr-1 flex-shrink-0 edit-history__mode-chip"
              :title="
                entry.executionMode === 'inline'
                  ? 'Ran on the main thread (inline)'
                  : 'Ran on a web worker'
              "
            >
              {{ entry.executionMode }}
            </v-chip>

            <span
              v-if="entry.duration"
              class="text-caption text-medium-emphasis flex-shrink-0 mr-1"
            >
              {{ formatDuration(entry.duration) }}
            </span>

            <v-progress-circular
              v-if="entry.isLoading"
              size="14"
              width="2"
              color="primary"
              indeterminate
              class="mr-1"
            />

            <v-tooltip location="start" text="Reload from this step">
              <template #activator="{ props: tp }">
                <v-btn
                  v-bind="tp"
                  size="x-small"
                  variant="text"
                  density="comfortable"
                  icon="mdi-reload"
                  :disabled="isUpdating || entry.isLoading"
                  @click="onReloadHistory(index)"
                />
              </template>
            </v-tooltip>

            <!-- Per-item undo is only exposed on the trailing entry —
                 undoing a middle entry is handled via "Reload from this
                 step". The toolbar button above drives global Ctrl+Z. -->
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

          <div v-if="openIndex === index" class="edit-history__args px-3 py-2">
            <div class="text-caption text-medium-emphasis mb-1">Arguments</div>
            <ul class="edit-history__args-list pa-0 ma-0">
              <li
                v-for="(arg, argIdx) of entry.args"
                :key="argIdx"
                class="text-caption px-1 py-1"
                style="word-break: break-all"
              >
                <code class="text-caption">{{ formatArg(arg) }}</code>
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
import { useQcScript } from '@/composables/useQcScript'
import { Snackbar } from '@uwrl/qc-utils'

const props = withDefaults(
  defineProps<{
    /** When true (default) the header shows a chevron and the body
     *  hides while `collapsed`. Pass `false` inside the pop-out
     *  modal — the modal IS the expanded view, so a second collapse
     *  control would be redundant. */
    collapsible?: boolean
    /** Controlled collapse state. Pair with `@update:collapsed` for
     *  v-model. Ignored when `collapsible` is false. */
    collapsed?: boolean
    /** Show the "open in window" icon button in the header. Hidden
     *  inside the pop-out modal so the modal doesn't offer to open
     *  itself. */
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

/**
 * Header-bar click handler. Toggle the collapse only when the click
 * landed outside any interactive descendant (the undo / redo /
 * pop-out buttons). The buttons themselves use `@click.stop`, but
 * Firefox's hit-test occasionally lands on the header `<div>`
 * instead of the v-btn (Vuetify wraps the button in a tooltip
 * activator + ripple overlay), and the resulting bubbled click
 * would collapse the panel out from under the user — and break
 * the e2e flow that tries to click the button immediately after.
 * Bailing on `target.closest('button')` here is the cheap, robust
 * fix that doesn't require restructuring the header layout.
 */
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
const { exportScript, importScript } = useQcScript()
const fileInputRef = ref<HTMLInputElement | null>(null)

/** Index of the expanded entry (for the inline arguments drawer). */
const openIndex = ref<number | null>(null)

/** Dev-only execution-mode badge is gated on Vite's DEV flag. */
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

/** Replace ALL_CAPS_SNAKE with Title Case for display. */
function formatMethod(method: string) {
  if (!method) return ''
  return method
    .toLowerCase()
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : ''))
    .join(' ')
}

/** Render argument values in a compact inspector-style form. Arrays get
 *  length + first/last hint; plain objects get JSON; everything else
 *  falls through as string. */
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
      // In-place clear; reassigning `history = []` would detach the
      // `editHistory` ref (which stores the original array reference)
      // and downstream dispatches would mutate the new array while
      // the UI watched the old empty one.
      selectedSeries.value.data.history.length = 0
      // A fresh server-side reload invalidates the redo chain.
      selectedSeries.value.data.redoStack.length = 0
    }
    await refreshGraphSeriesArray()
    await selectedSeries.value?.data.reload()
    // `recordHistory: false` — `reload()` already wiped history;
    // dispatching a SELECTION on top would just push and self-pop.
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

/**
 * Save the current QC history as a JSON file. The button is
 * disabled when there's nothing to save (`editCount === 0`), so the
 * try/catch is just defense in depth against an unexpected
 * `selectedSeries` race.
 */
const onSaveScript = async () => {
  try {
    await exportScript()
    Snackbar.success('QC script saved.')
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    Snackbar.error(`Couldn't save QC script: ${msg}`)
  }
}

/**
 * Forward to the hidden file input. Vuetify's icon-only `<v-btn>`
 * doesn't accept a `type="file"` shortcut, so we use a sibling
 * `<input>` and proxy the click.
 */
const onLoadScriptClick = () => {
  fileInputRef.value?.click()
}

/**
 * File-input change handler. Hands the picked file to the
 * composable, surfaces the per-op apply report through Snackbars,
 * and resets the input value so re-picking the same file fires
 * `change` again.
 */
const onLoadScriptFile = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // Reset early so a thrown apply doesn't leave the picker stuck.
  input.value = ''
  if (!file) return

  isUpdating.value = true
  try {
    const report = await importScript(file)
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
    Snackbar.error(`Couldn't load QC script: ${msg}`)
  } finally {
    isUpdating.value = false
  }
}

/**
 * After an undo or redo, restore the selection to match whatever the
 * replay returned: a non-empty array becomes the new plot selection;
 * an empty array (or `undefined`) clears it. `isUpdating` stays
 * `true` across `redraw` + selection sync so Plotly's debounced
 * relayout handler bails out early. The clear path passes
 * `recordHistory: false` because the replay is already authoritative
 * — dispatching a SELECTION([]) here would risk popping a filter
 * the replay just restored.
 */
const applyReplayedSelection = async (newSelection: number[] | undefined) => {
  await redraw()
  if (newSelection && newSelection.length) {
    await setPlotSelection(newSelection)
  } else {
    await clearSelected({ recordHistory: false })
  }
}

// The Fill Gaps panel paints a ghost-marker preview over detected
// gaps. When an undo/redo mutates the underlying data, those gaps
// shift (a FILL_GAPS being undone re-opens its filled region) and
// the panel's reactive watcher would re-stage ghost markers across
// whatever the new gap landscape looks like — visually a "ghost
// points everywhere" regression. Drop the staging panel first so
// its `onBeforeUnmount` clears the ghost trace before the replay.
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

/**
 * Keyboard: Ctrl/Cmd+Z = undo, Ctrl+Y or Ctrl/Cmd+Shift+Z = redo.
 * Attached to `window` so the shortcuts work regardless of what has
 * focus inside the app, but we bail when the user is typing into an
 * input/textarea/contenteditable so native browser undo on text fields
 * still wins.
 */
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
/* Tinted backgrounds, transitions, and the left-accent border on the
   args panel don't have Vuetify utility equivalents. Layout,
   overflow, and spacing have all been moved into utility classes on
   the template. */
.edit-history__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 32px;
}

.edit-history__body {
  padding: 8px;
}

/* Bordered card wrapper around the history rows. Matches the
   `.operation-panel__section` and Plotted-Datastreams treatments
   so all right-sidebar section bodies read as a contained group
   instead of resting flush against the chrome. */
.edit-history__card {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

/* Matches the section-header treatment used by Plotted
   Datastreams in the parent so both collapsible sidebar panels
   have the same hover + focus affordance when the chevron is
   available. */
.edit-history__header--collapsible {
  cursor: pointer;
}
.edit-history__header--collapsible:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 3px;
  cursor: pointer;
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
  overflow-y: auto;
}

/* Keep the dev execution-mode chip compact so it doesn't push the
   duration/actions out of the row. */
.edit-history__mode-chip {
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  height: 16px;
  padding-inline: 6px;
}
</style>
