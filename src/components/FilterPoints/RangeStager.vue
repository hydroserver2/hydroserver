<template>
  <div class="range-stager">
    <div class="text-caption text-medium-emphasis mb-2">Date range</div>
    <DatePickerField
      placeholder="From"
      :modelValue="fromDate"
      @update:modelValue="onFromDateChange"
      class="mb-2"
    />
    <DatePickerField
      placeholder="To"
      :modelValue="toDate"
      @update:modelValue="onToDateChange"
      class="mb-2"
    />

    <div v-if="rangePresets.length" class="d-flex gap-1 flex-wrap mb-2">
      <v-chip
        v-for="preset in rangePresets"
        :key="preset.label"
        size="x-small"
        variant="tonal"
        :color="preset.active ? 'primary' : undefined"
        :prepend-icon="preset.active ? 'mdi-check' : undefined"
        @click="applyPreset(preset)"
      >
        {{ preset.label }}
      </v-chip>
    </div>

    <div class="text-caption text-medium-emphasis">
      Drag the blue band on the plot to resize, or edit the dates above.
    </div>

    <!-- When the user switches to zoom / select / lasso we drop the
         stage shape off the plot so those tools can draw freely over
         the plot area (see the staging module for why). This hint
         keeps the hidden-state discoverable — without it the band
         just disappears and the affordance to drag it back feels
         lost. -->
    <v-alert
      v-if="!stagePanMode"
      class="mt-3"
      color="info"
      variant="tonal"
      density="compact"
      icon="mdi-cursor-move"
    >
      <div class="text-caption">
        Range overlay hidden while the zoom, box-select, or lasso tool is
        active. Switch back to pan to resize it on the plot.
      </div>
    </v-alert>

    <v-alert
      v-if="rangeWarning"
      class="mt-4"
      color="warning"
      variant="tonal"
      density="compact"
      icon="mdi-alert-outline"
    >
      <div class="text-caption">{{ rangeWarning }}</div>
    </v-alert>
  </div>
</template>

<script setup lang="ts">
/**
 * Shared "pick a date range" UI — date pickers, preset chips, the
 * editable blue band on the plot, data-bounds clamping, and a
 * one-line range warning for degenerate windows. Parents read the
 * resulting state via `defineExpose` (`fromTs`, `toTs`,
 * `rangeWarning`, `rangeIndices`) and do whatever they need with
 * it: Find Gaps scans for gaps, Fill Gaps computes a fill preview,
 * Datetime Range selects every point inside.
 *
 * Keeping the range UX in one component means a single fix for
 * edge cases (clamping, invalid windows, drag gestures) lands in
 * every operation that opts into it.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlotlyStore } from '@/store/plotly'
import {
  findFirstGreaterOrEqual,
  findLastLessOrEqual,
} from '@uwrl/qc-utils'
import {
  subtractDays,
  subtractMonths,
  subtractYears,
} from '@/utils/dateMath'
import {
  clearStageShape,
  onStageDrag,
  setStageShape,
  stagePanMode,
} from '@/utils/plotting/staging'
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'

const { selectedSeries } = storeToRefs(usePlotlyStore())

// Data-driven min/max for the picker + overlay. Read off the live
// `dataX` Float64Array so the bounds track whatever is actually
// plotted, not the (sometimes stale) datastream metadata. `null`
// when the series hasn't loaded yet — callers fall back to
// unclamped behaviour in that case so the panel stays usable
// during load.
const dataBounds = computed<{ min: number; max: number } | null>(() => {
  const dataX = selectedSeries.value?.data.dataX
  if (!dataX?.length) return null
  return { min: dataX[0], max: dataX[dataX.length - 1] }
})

const clampTs = (ts: number): number => {
  const b = dataBounds.value
  if (!b) return Number.isFinite(ts) ? ts : Date.now()
  if (!Number.isFinite(ts)) return b.min
  return Math.min(Math.max(ts, b.min), b.max)
}

// Initialise to placeholders; `onMounted` rewrites these from
// `dataBounds` so the panel always opens on the full data extent
// rather than inheriting whatever selection-bound dates were in
// scope (see the Find→Fill switchover bug for why).
const fromDate = ref<Date>(new Date())
const toDate = ref<Date>(new Date())

const onFromDateChange = (date: Date) => {
  const next = clampTs(date.getTime())
  fromDate.value = new Date(next)
  if (fromDate.value.getTime() > toDate.value.getTime()) {
    toDate.value = new Date(next)
  }
}
const onToDateChange = (date: Date) => {
  const next = clampTs(date.getTime())
  toDate.value = new Date(next)
  if (toDate.value.getTime() < fromDate.value.getTime()) {
    fromDate.value = new Date(next)
  }
}

const fromTs = computed(() => fromDate.value.getTime())
const toTs = computed(() => toDate.value.getTime())

// Keep the editable range shape on the plot in sync with the
// picker values. Pushing from here means both the pickers and the
// drag handle on the plot write through the same local refs.
watch(
  [fromTs, toTs],
  async ([from, to]) => {
    if (Number.isFinite(from) && Number.isFinite(to) && from < to) {
      await setStageShape(from, to)
    }
  },
  { immediate: false }
)

const rangeWarning = computed<string | null>(() => {
  if (!selectedSeries.value?.data.dataX?.length) {
    return 'No data loaded for this datastream.'
  }
  if (!Number.isFinite(fromTs.value) || !Number.isFinite(toTs.value)) {
    return 'Pick a valid From and To date.'
  }
  if (fromTs.value >= toTs.value) return 'From must come before To.'
  return null
})

/** Start / end indices in the QC series corresponding to the
 *  staged `[fromTs, toTs]` window. `null` when the window is
 *  empty or the series hasn't loaded. */
const rangeIndices = computed<[number, number] | null>(() => {
  const dataX = selectedSeries.value?.data.dataX
  if (!dataX?.length || rangeWarning.value) return null
  const startIdx = findFirstGreaterOrEqual(dataX, fromTs.value)
  const endIdx = findLastLessOrEqual(dataX, toTs.value)
  return endIdx >= startIdx ? [startIdx, endIdx] : null
})

// --- Range presets --------------------------------------------------

interface RangePreset {
  label: string
  compute: (bounds: { min: number; max: number }) => [number, number] | null
  active: boolean
}

const approxEqual = (a: number, b: number) => Math.abs(a - b) < 1000

const rangePresets = computed<RangePreset[]>(() => {
  const bounds = dataBounds.value
  if (!bounds) return []

  const defs: Array<{
    label: string
    compute: (b: { min: number; max: number }) => [number, number] | null
  }> = [
      {
        label: '1W',
        compute: (b) => [
          Math.max(subtractDays(new Date(b.max), 7).getTime(), b.min),
          b.max,
        ],
      },
      {
        label: '1M',
        compute: (b) => [
          Math.max(subtractMonths(new Date(b.max), 1).getTime(), b.min),
          b.max,
        ],
      },
      {
        label: '3M',
        compute: (b) => [
          Math.max(subtractMonths(new Date(b.max), 3).getTime(), b.min),
          b.max,
        ],
      },
      {
        label: '6M',
        compute: (b) => [
          Math.max(subtractMonths(new Date(b.max), 6).getTime(), b.min),
          b.max,
        ],
      },
      {
        label: '1Y',
        compute: (b) => [
          Math.max(subtractYears(new Date(b.max), 1).getTime(), b.min),
          b.max,
        ],
      },
      {
        label: 'YTD',
        compute: (b) => {
          const jan1 = new Date(new Date().getFullYear(), 0, 1).getTime()
          const start = Math.max(jan1, b.min)
          if (start >= b.max) return null
          return [start, b.max]
        },
      },
      { label: 'All', compute: (b) => [b.min, b.max] },
    ]

  return defs
    .map((d) => {
      const range = d.compute(bounds)
      if (!range) return null
      const [from, to] = range
      return {
        label: d.label,
        compute: d.compute,
        active:
          approxEqual(fromTs.value, from) && approxEqual(toTs.value, to),
      } as RangePreset
    })
    .filter((p): p is RangePreset => p !== null)
})

const applyPreset = (preset: RangePreset) => {
  const bounds = dataBounds.value
  if (!bounds) return
  const range = preset.compute(bounds)
  if (!range) return
  const [from, to] = range
  fromDate.value = new Date(clampTs(from))
  toDate.value = new Date(clampTs(to))
}

// --- Overlay lifecycle ---------------------------------------------

let stopDragListener: (() => void) | null = null

onMounted(async () => {
  // Default the staged window to the full data extent on every
  // open. We deliberately don't inherit from
  // `useDataSelection.startDate / endDate` — those collapse to the
  // live point selection's extent, which can be a near-zero range
  // right after a filter operation committed.
  const b = dataBounds.value
  if (b) {
    fromDate.value = new Date(b.min)
    toDate.value = new Date(b.max)
  }

  await setStageShape(fromTs.value, toTs.value)
  stopDragListener = onStageDrag((from, to) => {
    fromDate.value = new Date(clampTs(from))
    toDate.value = new Date(clampTs(to))
  })
})

onBeforeUnmount(async () => {
  stopDragListener?.()
  stopDragListener = null
  await clearStageShape()
})

defineExpose({
  fromTs,
  toTs,
  fromDate,
  toDate,
  rangeWarning,
  rangeIndices,
  dataBounds,
})
</script>
