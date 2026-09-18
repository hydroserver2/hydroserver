<template>
  <div class="plotted-wrapper d-flex flex-column">
    <div
      v-if="!qcDatastream"
      class="plotted-toolbar d-flex align-center px-3 py-2"
    >
      <v-spacer></v-spacer>
      <v-btn
        :disabled="!plottedDatastreams.length"
        size="x-small"
        variant="text"
        prepend-icon="mdi-close-circle-outline"
        @click="clearAll"
      >
        Unplot all
      </v-btn>
    </div>
    <v-divider />
    <ul class="plotted-list pa-0 ma-0">
      <li
        v-for="(datastream, index) of seriesDatastreams"
        :key="datastream.id"
        class="plotted-item"
        :class="{
          'plotted-item--qc': isEdit(datastream),
          'plotted-item--source': isSource(datastream),
          'plotted-item--hidden': visibleDict[datastream.id] === false,
          'plotted-item--drop-before':
            dragIndex !== null &&
            dropIndex === index &&
            dropIndex !== dragIndex &&
            (dragIndex as number) > index,
          'plotted-item--drop-after':
            dragIndex !== null &&
            dropIndex === index &&
            dropIndex !== dragIndex &&
            (dragIndex as number) < index,
        }"
        :data-testid="`plotted-item-${datastream.id}`"
        :draggable="!isPinned(datastream)"
        @dragstart="onDragStart(index, $event)"
        @dragover.prevent="onDragOver(index, $event)"
        @dragleave="onDragLeave(index)"
        @drop.prevent="onDrop(index)"
        @dragend="onDragEnd"
      >
        <v-icon
          v-if="!isPinned(datastream)"
          class="plotted-item__drag cursor-grab"
          icon="mdi-drag-vertical"
          size="16"
          :color="contextCount > 1 ? 'grey' : 'grey-lighten-2'"
          title="Drag to reorder"
        />
        <span v-else />

        <button
          type="button"
          class="plotted-item__visibility d-inline-flex align-center justify-center cursor-pointer rounded-sm"
          :title="
            visibleDict[datastream.id] === false
              ? 'Show on plot'
              : 'Hide from plot'
          "
          :disabled="isUpdating"
          @click="toggleVisibility(datastream)"
        >
          <v-icon
            :icon="
              visibleDict[datastream.id] === false ? 'mdi-eye-off' : 'mdi-eye'
            "
            size="16"
            :color="
              visibleDict[datastream.id] === false
                ? 'grey'
                : labelColorForDatastream(datastream.id)
            "
          />
        </button>

        <!-- Primary rows sit on the always-rendered left axis. -->
        <button
          v-if="!isPrimary(datastream, index)"
          type="button"
          class="plotted-item__axis-toggle d-inline-flex align-center justify-center cursor-pointer rounded-sm"
          :title="
            hiddenAxisIds.has(datastream.id) ? 'Show Y axis' : 'Hide Y axis'
          "
          :disabled="isUpdating"
          @click="toggleAxisVisibility(datastream.id)"
        >
          <v-icon
            :icon="
              hiddenAxisIds.has(datastream.id)
                ? 'mdi-toggle-switch-off-outline'
                : 'mdi-toggle-switch'
            "
            size="16"
            :color="
              hiddenAxisIds.has(datastream.id)
                ? 'grey'
                : labelColorForDatastream(datastream.id)
            "
          />
        </button>
        <span v-else />

        <!-- Darker companion of the line colour: ties the row to its
             axis while staying legible at body-text weight. -->
        <div
          class="plotted-item__text"
          :style="{ color: labelColorForDatastream(datastream.id) }"
        >
          <div
            class="plotted-item__title d-flex align-center ga-1"
            :title="datastream.name"
          >
            <v-icon
              v-if="snapshotFor(datastream.id)"
              icon="mdi-history"
              size="14"
              class="flex-shrink-0"
            />
            <span>{{ datastream.name }}</span>
            <v-chip
              v-if="isSource(datastream)"
              size="x-small"
              variant="tonal"
              label
              class="flex-shrink-0"
            >
              raw source
            </v-chip>
            <v-chip
              v-if="snapshotFor(datastream.id)"
              size="x-small"
              variant="tonal"
              label
              class="flex-shrink-0"
            >
              snapshot
            </v-chip>
            <v-tooltip
              v-if="
                !snapshotFor(datastream.id) &&
                !loadStatus(datastream.id).loading &&
                loadStatus(datastream.id).count === 0
              "
              location="top"
              text="No observations in the current time window"
            >
              <template #activator="{ props: tp }">
                <v-icon
                  v-bind="tp"
                  class="plotted-item__empty-flag flex-shrink-0"
                  icon="mdi-database-off-outline"
                  size="14"
                  color="warning"
                  aria-label="No data in window"
                />
              </template>
            </v-tooltip>
          </div>
          <div class="plotted-item__subtitle">
            <template v-if="snapshotFor(datastream.id)">
              {{ snapshotSubtitle(datastream.id) }}
            </template>
            <template v-else-if="loadStatus(datastream.id).loading">
              loading…
            </template>
            <template v-else>
              {{ loadStatus(datastream.id).count.toLocaleString() }} pt{{
                loadStatus(datastream.id).count === 1 ? '' : 's'
              }}
              loaded
            </template>
          </div>
        </div>

        <button
          v-if="!isPinned(datastream)"
          type="button"
          class="plotted-item__close d-inline-flex align-center justify-center cursor-pointer rounded-sm"
          :title="`Remove ${datastream.name} from plot`"
          aria-label="Remove from plot"
          @click="toggleDatastream(datastream)"
        >
          <v-icon icon="mdi-close" size="14" />
        </button>
        <span v-else />
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import {
  handleNewPlot,
  toggleAxisVisibility,
  toggleTraceVisibility,
} from '@/utils/plotting/plotly'
import type { AppPlotlyTrace } from '@/utils/plotting/plotly'
import type { GraphSeries } from '@/types'
import { usePlotlyStore } from '@/store/plotly'
import { ref, computed } from 'vue'
import { Datastream } from '@hydroserver/client'
import { formatDayStamp } from '@/utils/time'

const { updateOptions, labelColorForDatastream } = usePlotlyStore()
const {
  plotlyRef,
  graphSeriesArray,
  hiddenAxisIds,
  hiddenTraceIds,
  plotlyOptions,
} = storeToRefs(usePlotlyStore())

const {
  plottedDatastreams,
  seriesDatastreams,
  qcDatastream,
  sourceContextDatastream,
  loadingStates,
} = storeToRefs(useDataVisStore())
const { toggleDatastream, clearPlottedDatastreams } = useDataVisStore()

const isEdit = (ds: Datastream) => qcDatastream.value?.id === ds.id
const isSource = (ds: Datastream) =>
  sourceContextDatastream.value?.id === ds.id
/** Edit target and its source: always shown, never removed or reordered. */
const isPinned = (ds: Datastream) => isEdit(ds) || isSource(ds)
const isPrimary = (ds: Datastream, index: number) =>
  isPinned(ds) || (!qcDatastream.value && index === 0)

const contextCount = computed(
  () => seriesDatastreams.value.filter((ds) => !isPinned(ds)).length
)

// Template treats `visibleDict[id] === false` as "hidden"; source of
// truth lives in the store so the share URL can read it.
const visibleDict = computed<Record<string, boolean>>(() => {
  const out: Record<string, boolean> = {}
  for (const ds of seriesDatastreams.value) {
    out[ds.id] = !hiddenTraceIds.value.has(ds.id)
  }
  return out
})

const isUpdating = computed(() =>
  Array.from(loadingStates.value.values()).some((isLoading) => isLoading)
)

const loadStatusById = computed<
  Record<string, { loading: boolean; count: number }>
>(() => {
  const countById = new Map<string, number>()
  for (const t of plotlyOptions.value?.traces ?? []) {
    const trace = t as AppPlotlyTrace
    if (trace.id != null) {
      const x = trace.x as ArrayLike<unknown> | undefined
      countById.set(trace.id, x?.length ?? 0)
    }
  }
  const out: Record<string, { loading: boolean; count: number }> = {}
  for (const series of graphSeriesArray.value) {
    out[series.id] = {
      loading: series.data.isLoading,
      count: countById.get(series.id) ?? 0,
    }
  }
  return out
})

const loadStatus = (id: string) =>
  loadStatusById.value[id] ?? { loading: true, count: 0 }

const snapshotFor = (id: string) =>
  graphSeriesArray.value.find((s) => s.id === id)?.snapshot

/** `step 3 of 7: Fill Gaps - by Alice - Mar 14, 2026` */
const snapshotSubtitle = (id: string): string => {
  const meta = snapshotFor(id)
  if (!meta) return ''
  const parts = [
    meta.opIndex < 0
      ? 'session start'
      : `step ${meta.opIndex + 1} of ${meta.opCount}: ${meta.opName}`,
  ]
  if (meta.performedBy) parts.push(`by ${meta.performedBy}`)
  parts.push(formatDayStamp(meta.createdAt))
  return parts.join(' - ')
}

async function clearAll() {
  hiddenTraceIds.value = new Set()
  await clearPlottedDatastreams()
}

const toggleVisibility = async (datastream: Datastream) => {
  const traces = plotlyRef.value?.data ?? []
  const mainIndex = traces.findIndex(
    (trace) => (trace as AppPlotlyTrace).id == datastream.id
  )
  if (mainIndex < 0) return

  const mainTrace = traces[mainIndex] as AppPlotlyTrace | undefined
  const isVisible = (
    mainTrace as { visible?: boolean | 'legendonly' } | undefined
  )?.visible
  const nextVisible = !(isVisible === true || isVisible == undefined)

  // Mutate a fresh Set instance so pinia notifies deep watchers (URL share).
  const next = new Set(hiddenTraceIds.value)
  if (nextVisible) next.delete(datastream.id)
  else next.add(datastream.id)
  hiddenTraceIds.value = next

  // Gap overlays carry only `_gapOverlayFor`; toggle alongside the main
  // trace so hiding a datastream removes both its line and its markers.
  for (let i = 0; i < traces.length; i++) {
    const t = traces[i] as AppPlotlyTrace
    if (i === mainIndex || t._gapOverlayFor === datastream.id) {
      await toggleTraceVisibility(plotlyRef.value, i, nextVisible)
    }
  }
}

// Drag indices are row positions in `seriesDatastreams`. Firefox needs
// `setData` for a drag to actually start, hence the payload.
const dragIndex = ref<number | null>(null)
const dropIndex = ref<number | null>(null)

const isPinnedAt = (index: number) => {
  const ds = seriesDatastreams.value[index]
  return !ds || isPinned(ds)
}

function onDragStart(index: number, ev: DragEvent) {
  if (isPinnedAt(index)) return
  dragIndex.value = index
  ev.dataTransfer?.setData('text/plain', String(index))
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = 'move'
}

function onDragOver(index: number, ev: DragEvent) {
  if (dragIndex.value === null || isPinnedAt(index)) return
  dropIndex.value = index
  if (ev.dataTransfer) ev.dataTransfer.dropEffect = 'move'
}

function onDragLeave(index: number) {
  if (dropIndex.value === index) dropIndex.value = null
}

async function onDrop(index: number) {
  const from = dragIndex.value
  dragIndex.value = null
  dropIndex.value = null
  if (from === null || from === index || isPinnedAt(index)) return
  if (!reorder(from, index)) return
  updateOptions()
  await handleNewPlot(undefined, { preserveZoom: true })
}

function onDragEnd() {
  dragIndex.value = null
  dropIndex.value = null
}

// Moves the dragged row to the target row's place in `plottedDatastreams`,
// then re-sorts `graphSeriesArray` so trace order (and the colours derived
// from it) follows `seriesDatastreams`.
function reorder(from: number, to: number): boolean {
  const movedId = seriesDatastreams.value[from]?.id
  const targetId = seriesDatastreams.value[to]?.id
  const list = plottedDatastreams.value
  const fromPos = list.findIndex((d) => d.id === movedId)
  const toPos = list.findIndex((d) => d.id === targetId)
  if (fromPos < 0 || toPos < 0) return false
  const moved = list.splice(fromPos, 1)[0]!
  list.splice(toPos, 0, moved)

  const order = new Map(seriesDatastreams.value.map((d, i) => [d.id, i]))
  ;(graphSeriesArray.value as GraphSeries[]).sort(
    (a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0)
  )
  return true
}
</script>

<style scoped>
.plotted-wrapper {
  min-height: 0;
}

.plotted-toolbar {
  background-color: rgba(var(--v-theme-primary), 0.02);
}

.plotted-list {
  list-style: none;
}

.plotted-item {
  display: grid;
  grid-template-columns: 16px 22px 22px 1fr 22px;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  transition: background-color 120ms ease;
  position: relative;
}

.plotted-item:last-child {
  border-bottom: none;
}

.plotted-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.plotted-item--qc {
  background-color: rgba(var(--v-theme-primary), 0.06);
}

.plotted-item--hidden {
  opacity: 0.45;
}

.plotted-item--hidden .plotted-item__title,
.plotted-item--hidden .plotted-item__subtitle {
  text-decoration: line-through;
}

.plotted-item--hidden:hover {
  opacity: 0.7;
}

.plotted-item--drop-before::before,
.plotted-item--drop-after::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background-color: rgb(var(--v-theme-primary));
  pointer-events: none;
}

.plotted-item--drop-before::before {
  top: -1px;
}

.plotted-item--drop-after::after {
  bottom: -1px;
}

.plotted-item__drag {
  opacity: 0.75;
}

.plotted-item__drag:active {
  cursor: grabbing;
}

.plotted-item__visibility,
.plotted-item__axis-toggle,
.plotted-item__close {
  width: 22px;
  height: 22px;
  padding: 0;
  background: transparent;
  border: none;
}

.plotted-item__visibility:hover:not(:disabled),
.plotted-item__axis-toggle:hover:not(:disabled),
.plotted-item__close:hover {
  background-color: rgba(0, 0, 0, 0.06);
}

.plotted-item__visibility:disabled,
.plotted-item__axis-toggle:disabled {
  cursor: default;
  opacity: 0.5;
}

.plotted-item__text {
  min-width: 0;
  font-size: 0.8125rem;
  line-height: 1.2;
}

.plotted-item__title {
  font-weight: 600;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.plotted-item__subtitle {
  font-size: 0.7rem;
  opacity: 0.65;
  margin-top: 1px;
}
</style>
