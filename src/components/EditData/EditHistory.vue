<template>
  <div class="edit-history d-flex flex-column" style="min-height: 0">
    <!-- Compact header: title + edit count chip + undo/redo toolbar. -->
    <div class="edit-history__header px-3 py-2 d-flex align-center gap-2">
      <v-icon icon="mdi-history" color="primary" size="18" />
      <span class="text-body-2 font-weight-bold">Edit history</span>
      <v-chip
        size="x-small"
        :color="editCount ? 'primary' : undefined"
        :variant="editCount ? 'tonal' : 'outlined'"
        label
      >
        {{ editCount }}
      </v-chip>

      <v-spacer />

      <v-tooltip location="bottom" text="Undo (Ctrl+Z)">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-undo-variant"
            :disabled="isUpdating || !canUndo"
            @click="onUndo"
          />
        </template>
      </v-tooltip>

      <v-tooltip location="bottom" text="Redo (Ctrl+Y)">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-redo-variant"
            :disabled="isUpdating || !canRedo"
            @click="onRedo"
          />
        </template>
      </v-tooltip>
    </div>

    <v-divider />

    <!-- Scrollable list body. Each entry is a single tight row (icon,
         method, duration, actions). The timeline + nested expansion
         panel layout used to cost ~100 px per entry; this is ~32. -->
    <div
      class="flex-grow-1 overflow-y-auto"
      style="min-height: 0"
    >
      <!-- Baseline: "Data loaded" status row with its own reload action. -->
      <div class="edit-history__row edit-history__row--baseline px-3 py-2 d-flex align-center">
        <v-icon
          :icon="selectedSeries?.data.isLoading ? 'mdi-progress-download' : 'mdi-database-check'"
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
      <div
        v-if="editCount === 0"
        class="edit-history__empty pa-4 text-center"
      >
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
              :aria-label="openIndex === index ? 'Collapse' : 'Expand arguments'"
              :aria-expanded="openIndex === index"
              @click="toggle(index)"
            >
              <v-icon
                :icon="openIndex === index ? 'mdi-chevron-down' : 'mdi-chevron-right'"
                size="16"
              />
            </button>

            <v-icon
              v-if="entry.icon"
              :icon="entry.icon"
              size="16"
              color="primary"
              class="mr-2"
            />

            <span
              class="edit-history__method flex-grow-1 text-truncate font-weight-medium"
            >
              {{ formatMethod(entry.method) }}
            </span>

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
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlotlyStore } from '@/store/plotly'
import { useDataSelection } from '@/composables/useDataSelection'
import { formatDuration } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'

const { editHistory, selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { clearSelected, dispatchSelection } = useDataSelection()

/** Index of the expanded entry (for the inline arguments drawer). */
const openIndex = ref<number | null>(null)

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

  setTimeout(async () => {
    const { refreshGraphSeriesArray } = useDataVisStore()
    if (selectedSeries.value) {
      selectedSeries.value.data.history = []
      // A fresh server-side reload invalidates the redo chain.
      selectedSeries.value.data.redoStack.length = 0
    }
    await refreshGraphSeriesArray()
    await selectedSeries.value?.data.reload()
    await clearSelected()
    isUpdating.value = false
    await redraw()
  })
}

const onReloadHistory = async (index: number) => {
  if (index < editHistory.value.length) {
    isUpdating.value = true
    setTimeout(async () => {
      const newSelection = await selectedSeries.value?.data.reloadHistory(index)

      isUpdating.value = false
      await redraw()
      if (newSelection) {
        dispatchSelection(newSelection)
      }
    })
  }
}

/**
 * After an undo or redo, restore the selection to match whatever the
 * replay returned: a non-empty array becomes the new plot selection; an
 * empty array (or `undefined`) clears it. `isUpdating` stays `true`
 * across `redraw` + selection sync so Plotly's debounced relayout
 * handler bails out early and doesn't overwrite the selection mid-flight.
 * `clearSelected({ dispatchFilter: false })` wipes the plot highlight
 * without pushing an extra SELECTION entry into the history we just
 * replayed.
 */
const applyReplayedSelection = async (
  newSelection: number[] | undefined
) => {
  await redraw()
  if (newSelection && newSelection.length) {
    await dispatchSelection(newSelection)
  } else {
    await clearSelected({ dispatchFilter: false })
  }
}

const onUndo = async () => {
  if (!canUndo.value || isUpdating.value) return
  isUpdating.value = true
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
  min-height: 40px;
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
</style>
