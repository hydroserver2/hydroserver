<template>
  <div class="plotted-wrapper d-flex flex-column">
    <div
      class="plotted-toolbar d-flex align-center gap-2 px-3 py-2"
      :class="{ 'plotted-toolbar--section': sectionTitle }"
    >
      <template v-if="sectionTitle">
        <v-icon icon="mdi-chart-multiple" color="primary" size="18" />
        <span class="text-body-2 font-weight-bold">{{ sectionTitle }}</span>
      </template>
      <v-spacer />
      <v-btn
        v-if="!lockQc"
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
        class="plotted-item__drag"
        icon="mdi-drag-vertical"
        size="16"
        :color="plottedDatastreams.length > 1 ? 'grey' : 'grey-lighten-2'"
        title="Drag to reorder"
      />

      <button
        v-if="!lockQc"
        type="button"
        class="plotted-item__dot"
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
        class="plotted-item__visibility"
        :title="
          visibleDict[datastream.id] === false ? 'Show on plot' : 'Hide from plot'
        "
        :disabled="isUpdating"
        @click="toggleVisibility(datastream)"
      >
        <v-icon
          :icon="
            visibleDict[datastream.id] === false ? 'mdi-eye-off' : 'mdi-eye'
          "
          size="16"
          :color="colorForDatastream(datastream.id)"
        />
      </button>

      <!-- Text uses the darker companion of the line colour so the
           row reads as "tied to this axis" while staying legible; the
           raw pastel is too washed out at body-text weight. -->
      <div
        class="plotted-item__text"
        :style="{ color: labelColorForDatastream(datastream.id) }"
      >
        <div class="plotted-item__title" :title="datastream.name">
          {{ datastream.name }}
        </div>
        <div class="plotted-item__subtitle">
          {{
            datastream.valueCount?.toLocaleString?.() ?? datastream.valueCount
          }}
          obs
        </div>
      </div>

      <button
        v-if="!(lockQc && qcDatastream === datastream)"
        type="button"
        class="plotted-item__close"
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
  toggleTraceVisibility,
} from '@/utils/plotting/plotly'
import type { AppPlotlyTrace } from '@/utils/plotting/plotly'
import { usePlotlyStore } from '@/store/plotly'
const { updateOptions, colorForDatastream, labelColorForDatastream } =
  usePlotlyStore()
const { plotlyRef, graphSeriesArray } = storeToRefs(usePlotlyStore())
import { Ref, ref, computed } from 'vue'
import { Datastream } from '@hydroserver/client'

const { plottedDatastreams, qcDatastream, loadingStates } =
  storeToRefs(useDataVisStore())
const {
  toggleDatastream,
  setQcDatastream: setQcInStore,
  clearPlottedDatastreams,
} = useDataVisStore()
const visibleDict: Ref<{ [key: string]: boolean }> = ref({})

const setQcDatastream = async (datastream: Datastream) => {
  await setQcInStore(datastream.id)
}

const isUpdating = computed(() =>
  Array.from(loadingStates.value.values()).some((isLoading) => isLoading)
)

/**
 * Remove every plotted datastream at once. The store action handles
 * clearing graph series, zoom history, and QC in one step.
 */
async function clearAll() {
  visibleDict.value = {}
  await clearPlottedDatastreams()
}

const toggleVisibility = async (datastream: Datastream) => {
  const traceIndex = plotlyRef.value?.data.findIndex(
    (trace) => (trace as AppPlotlyTrace).id == datastream.id
  )
  if (traceIndex !== undefined && traceIndex >= 0) {
    const isVisible = plotlyRef.value?.data[traceIndex].visible
    visibleDict.value[datastream.id] = !(
      isVisible === true || isVisible == undefined
    )
    await toggleTraceVisibility(
      plotlyRef.value,
      traceIndex,
      visibleDict.value[datastream.id]
    )
  }
}

// --- Native HTML5 drag-and-drop reordering ---
// Keeping this tight instead of pulling in a dependency. Firefox needs
// `setData` for a drag to actually start, hence the payload.
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

/**
 * Move the plotted datastream at `from` to the position `to`. Also
 * reorders the matching entry in `graphSeriesArray` so the plot trace
 * order (and the colour assignments derived from it) stays in sync.
 */
function reorder(from: number, to: number) {
  const list = plottedDatastreams.value
  const moved = list.splice(from, 1)[0]
  list.splice(to, 0, moved)

  const series = graphSeriesArray.value
  const fromSeries = series.findIndex((s) => s.id === moved.id)
  if (fromSeries >= 0) {
    const movedSeries = series.splice(fromSeries, 1)[0]
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

.plotted-toolbar--section {
  background-color: rgba(var(--v-theme-primary), 0.06);
  min-height: 40px;
}

.plotted-list {
  list-style: none;
}

.plotted-item {
  display: grid;
  grid-template-columns: 16px 18px 22px 1fr 22px;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  transition: background-color 120ms ease;
  position: relative;
}

.plotted-item--locked {
  grid-template-columns: 16px 22px 1fr 22px;
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

/* When the user hides this series from the plot via the eye button,
   dim the whole row so its hidden state is clear at a glance. The drag
   handle and the eye/close/dot controls stay fully interactive — only
   the visual content (title, subtitle, dot, eye icon) fades. */
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
  cursor: grab;
  opacity: 0.75;
}

.plotted-item__drag:active {
  cursor: grabbing;
}

/* Custom compact radio: a 14px circle that's filled when this row is
   the QC target. `currentColor` picks up the inline `color:` style so
   each row uses its series colour. v-radio was too tall/wide for the
   rail. */
.plotted-item__dot {
  width: 14px;
  height: 14px;
  padding: 0;
  border: 2px solid currentColor;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  transition: background-color 120ms ease, box-shadow 120ms ease;
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
.plotted-item__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.plotted-item__visibility:hover:not(:disabled),
.plotted-item__close:hover {
  background-color: rgba(0, 0, 0, 0.06);
}

.plotted-item__visibility:disabled {
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
  /* Wrap long names instead of truncating. */
  word-break: break-word;
  overflow-wrap: anywhere;
}

.plotted-item__subtitle {
  font-size: 0.7rem;
  opacity: 0.65;
  margin-top: 1px;
}
</style>
