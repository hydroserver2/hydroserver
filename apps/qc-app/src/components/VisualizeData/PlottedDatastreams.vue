<template>
  <div class="plotted-wrapper d-flex flex-column">
    <div v-if="!lockQc" class="plotted-toolbar d-flex align-center px-3 py-2">
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
        v-for="(datastream, index) of plottedDatastreams"
        :key="datastream.id"
        class="plotted-item"
        :class="{
          'plotted-item--qc': qcDatastream === datastream,
          'plotted-item--locked': lockQc,
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
        draggable="true"
        @dragstart="onDragStart(index, $event)"
        @dragover.prevent="onDragOver(index, $event)"
        @dragleave="onDragLeave(index)"
        @drop.prevent="onDrop(index)"
        @dragend="onDragEnd"
      >
        <v-icon
          class="plotted-item__drag cursor-grab"
          icon="mdi-drag-vertical"
          size="16"
          :color="plottedDatastreams.length > 1 ? 'grey' : 'grey-lighten-2'"
          title="Drag to reorder"
        />

        <button
          v-if="!lockQc"
          type="button"
          class="plotted-item__dot cursor-pointer rounded-circle"
          :class="{ 'plotted-item__dot--active': qcDatastream === datastream }"
          :style="{
            color: colorForDatastream(datastream.id),
          }"
          :disabled="isUpdating"
          :title="
            qcDatastream === datastream
              ? 'Current QC target'
              : 'Set as QC target'
          "
          :aria-pressed="qcDatastream === datastream"
          @click="setQcDatastream(datastream)"
        />

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

        <!-- QC rows sit on the always-rendered primary left axis, so
             the Y-axis toggle is only for non-QC rows. -->
        <button
          v-if="qcDatastream !== datastream"
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
            <span>{{ datastream.name }}</span>
            <v-tooltip
              v-if="
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
            <template v-if="loadStatus(datastream.id).loading">
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
          v-if="!(lockQc && qcDatastream === datastream)"
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
defineProps<{ sectionTitle?: string; lockQc?: boolean }>()

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
const { updateOptions, colorForDatastream, labelColorForDatastream } =
  usePlotlyStore()
const {
  plotlyRef,
  graphSeriesArray,
  hiddenAxisIds,
  hiddenTraceIds,
  plotlyOptions,
} = storeToRefs(usePlotlyStore())
import { ref, computed } from 'vue'
import { Datastream } from '@hydroserver/client'

const { plottedDatastreams, qcDatastream, loadingStates } =
  storeToRefs(useDataVisStore())
const {
  toggleDatastream,
  setQcDatastream: setQcInStore,
  clearPlottedDatastreams,
} = useDataVisStore()

// Template treats `visibleDict[id] === false` as "hidden"; source of
// truth lives in the store so the share URL can read it.
const visibleDict = computed<Record<string, boolean>>(() => {
  const out: Record<string, boolean> = {}
  for (const ds of plottedDatastreams.value) {
    out[ds.id] = !hiddenTraceIds.value.has(ds.id)
  }
  return out
})

const setQcDatastream = async (datastream: Datastream) => {
  await setQcInStore(datastream.id)
}

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

// Firefox needs `setData` for a drag to actually start, hence the payload.
const dragIndex = ref<number | null>(null)
const dropIndex = ref<number | null>(null)

function onDragStart(index: number, ev: DragEvent) {
  dragIndex.value = index
  ev.dataTransfer?.setData('text/plain', String(index))
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = 'move'
}

function onDragOver(index: number, ev: DragEvent) {
  if (dragIndex.value === null) return
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
  if (from === null || from === index) return
  reorder(from, index)
  updateOptions()
  await handleNewPlot(undefined, { preserveZoom: true })
}

function onDragEnd() {
  dragIndex.value = null
  dropIndex.value = null
}

// Mirrors the reorder onto `graphSeriesArray` so plot trace order (and
// the colour assignments derived from it) stays in sync.
function reorder(from: number, to: number) {
  const list = plottedDatastreams.value
  const moved = list.splice(from, 1)[0]
  if (!moved) return
  list.splice(to, 0, moved)

  const series = graphSeriesArray.value as GraphSeries[]
  const fromSeries = series.findIndex((s) => s.id === moved.id)
  if (fromSeries >= 0) {
    const movedSeries = series.splice(fromSeries, 1)[0]
    if (!movedSeries) return
    const ids = list.map((d) => d.id)
    const newIdx = ids.indexOf(moved.id)
    series.splice(Math.max(0, newIdx), 0, movedSeries)
  }
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
  grid-template-columns: 16px 18px 22px 22px 1fr 22px;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  transition: background-color 120ms ease;
  position: relative;
}

.plotted-item--locked {
  grid-template-columns: 16px 22px 22px 1fr 22px;
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

/* Compact QC-target radio. currentColor picks up the inline series
   colour per row; v-radio was too tall for the rail. */
.plotted-item__dot {
  width: 14px;
  height: 14px;
  padding: 0;
  border: 2px solid currentColor;
  background: transparent;
  transition:
    background-color 120ms ease,
    box-shadow 120ms ease;
}

.plotted-item__dot:hover:not(:disabled) {
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}

.plotted-item__dot--active {
  background: currentColor;
  box-shadow: inset 0 0 0 2px #fff;
}

.plotted-item__dot:disabled {
  cursor: default;
  opacity: 0.5;
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
