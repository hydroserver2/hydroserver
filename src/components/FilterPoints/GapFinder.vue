<template>
  <div class="gap-finder">
    <div
      v-if="filterRangeActive"
      class="text-caption text-medium-emphasis mb-2"
    >
      Scan window: shared filter range (above).
    </div>
    <div v-else class="text-caption text-medium-emphasis mb-2">
      Scanning the full datastream.
      Toggle <b>Filter range</b> in the plot toolbar to restrict.
    </div>

    <div class="text-caption text-medium-emphasis mt-2 mb-2">
      Find gaps of at least
    </div>
    <div class="d-flex gap-2">
      <v-text-field
        label="Amount"
        type="number"
        v-model.number="gapAmount"
        density="comfortable"
        variant="outlined"
        hide-details
        style="flex: 1 1 0"
      />
      <v-select
        label="Unit"
        :items="gapUnits"
        v-model="selectedGapUnit"
        density="comfortable"
        variant="outlined"
        hide-details
        style="flex: 1 1 0"
      />
    </div>

    <div v-if="snapChips.length" class="d-flex gap-1 mt-2 flex-wrap">
      <v-chip
        v-for="chip in snapChips"
        :key="chip.label"
        size="x-small"
        variant="tonal"
        color="primary"
        :prepend-icon="chip.active ? 'mdi-check' : undefined"
        @click="applySnap(chip)"
      >
        {{ chip.label }}
      </v-chip>
    </div>

    <v-alert
      class="mt-4"
      :color="gapCount > 0 ? 'info' : 'success'"
      :icon="gapCount > 0 ? 'mdi-magnify-scan' : 'mdi-check-circle-outline'"
      variant="tonal"
      density="compact"
    >
      <div class="d-flex align-center gap-2">
        <v-progress-circular
          v-if="isComputing"
          size="14"
          width="2"
          indeterminate
          color="primary"
        />
        <div class="text-caption">
          <template v-if="isComputing">
            {{ props.computingHint ?? 'Updating gap preview…' }}
          </template>
          <template v-else-if="!thresholdMs">
            Choose a threshold to highlight gaps on the plot.
          </template>
          <template v-else-if="gapCount > 0">
            <slot name="gap-count-message" :count="gapCount">
              <b>{{ gapCount }}</b> gap{{ gapCount === 1 ? '' : 's' }}
              in the {{ filterRangeActive ? 'selected range' : 'datastream' }}.
            </slot>
          </template>
          <template v-else>
            No gaps match this threshold in the
            {{ filterRangeActive ? 'selected range' : 'datastream' }}.
          </template>
        </div>
      </div>
    </v-alert>
  </div>
</template>

<script setup lang="ts">
/**
 * Shared "find gaps" UI — used standalone by the Find Gaps
 * operation panel, and as the top half of the Fill Gaps panel. The
 * scan window is read from the shared "Filter range" toggle (plot
 * toolbar + sidebar `FilterRangePanel`); when off, the scan covers
 * the full datastream.
 *
 * When mounted with `autoSelectEndpoints`, each detection also
 * dispatches a point selection to the plot (Find Gaps' live-commit
 * behaviour). Without the prop the overlay bands render but the
 * plot's existing selection stays untouched (Fill Gaps' behaviour —
 * it owns the selection lifecycle through `dispatchAction`).
 */
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useDataSelection } from '@/composables/useDataSelection'
import {
  EnumFilterOperations,
  TimeUnit,
  timeUnitMultipliers,
  findFirstGreaterOrEqual,
  findLastLessOrEqual,
} from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore, timeSpacingUnitToTimeUnitKey } from '@/store/userInterface'
import { useOperationParamsStore } from '@/store/operationParams'
import { useFilterDispatch } from '@/composables/useFilterDispatch'

export interface GapPlan {
  leftTs: number
  rightTs: number
  leftIdx: number
  rightIdx: number
  leftY: number
  rightY: number
}

const props = withDefaults(
  defineProps<{
    /** Visually highlight the gap endpoints on the plot every time
     *  the local gap-detection re-runs. Find Gaps opts in (the
     *  detected gaps ARE its result); Fill Gaps opts in so the user
     *  can see what's about to be filled. */
    autoSelectEndpoints?: boolean
    /** When `autoSelectEndpoints` is true, also commit a `FIND_GAPS`
     *  entry to the ObservationRecord history (with `[amount, unit,
     *  range?]`) on every detection. Defaults to `true` so Find Gaps
     *  records its operation reproducibly. Fill Gaps disables this
     *  because the panel's commit dispatches `FILL_GAPS` directly —
     *  recording an extra `FIND_GAPS` before it (and another one
     *  after, when the post-fill data triggers a re-detection)
     *  produces three entries for what the user sees as one fill
     *  operation. */
    recordHistory?: boolean
    /** Override the "Updating gap preview…" line shown in the alert
     *  while the async Plotly writes settle. Handy when a parent
     *  bundles its own async work (ghost markers) under the same
     *  spinner window. */
    computingHint?: string
  }>(),
  {
    recordHistory: true,
  }
)

const { selectedSeries } = storeToRefs(usePlotlyStore())
const { gapAmount, gapUnits, selectedGapUnit, filterRangeActive } = storeToRefs(
  useUIStore()
)
const { qcDatastream } = storeToRefs(useDataVisStore())
const { setPlotSelection } = useDataSelection()
const { getActiveFilterRange } = useFilterDispatch()

const thresholdMs = computed(() => {
  const amount = Number(gapAmount.value)
  if (!Number.isFinite(amount) || amount <= 0) return null
  // @ts-ignore — selectedGapUnit is the enum key ("MINUTE");
  // TimeUnit maps it to the short code used by timeUnitMultipliers.
  const unitCode = TimeUnit[selectedGapUnit.value as keyof typeof TimeUnit]
  const mult = timeUnitMultipliers[unitCode]
  if (!mult) return null
  return amount * mult * 1000
})

/** Resolve the scan window's [startIdx, endIdx] inclusive index pair.
 *  Returns `null` when there's no data. */
const rangeIndices = computed<[number, number] | null>(() => {
  const dataX = selectedSeries.value?.data.dataX
  if (!dataX?.length) return null
  const range = getActiveFilterRange()
  if (!range) return [0, dataX.length - 1]
  const [from, to] = range
  const startIdx = findFirstGreaterOrEqual(dataX, from)
  const endIdx = findLastLessOrEqual(dataX, to)
  return endIdx >= startIdx ? [startIdx, endIdx] : null
})

// Client-side gap detection over the resolved window. Mirrors
// `findGapsCore` in qc-utils (not re-exported) but skips the worker
// path — the in-panel scan is small enough to run inline.
const gapPlans = computed<GapPlan[]>(() => {
  const threshold = thresholdMs.value
  const series = selectedSeries.value?.data
  const dataX = series?.dataX
  const dataY = series?.dataY
  const bounds = rangeIndices.value
  if (!threshold || !dataX?.length || !dataY || !bounds) return []
  const [startIdx, endIdx] = bounds
  if (endIdx <= startIdx) return []
  const plans: GapPlan[] = []
  for (let i = startIdx + 1; i <= endIdx; i++) {
    const span = dataX[i] - dataX[i - 1]
    if (span > threshold) {
      plans.push({
        leftTs: dataX[i - 1],
        rightTs: dataX[i],
        leftIdx: i - 1,
        rightIdx: i,
        leftY: dataY[i - 1],
        rightY: dataY[i],
      })
    }
  }
  return plans
})

const gapCount = computed(() => gapPlans.value.length)

/** Flat, sorted, de-duplicated list of every gap-endpoint index. */
const endpointIndices = computed<number[]>(() => {
  const out = new Set<number>()
  for (const p of gapPlans.value) {
    out.add(p.leftIdx)
    out.add(p.rightIdx)
  }
  return [...out].sort((a, b) => a - b)
})

const isComputing = ref(false)

watch(
  gapPlans,
  async () => {
    isComputing.value = true
    try {
      if (!props.autoSelectEndpoints) return

      const series = selectedSeries.value?.data
      const amount = Number(gapAmount.value)
      const unitCode = TimeUnit[selectedGapUnit.value as keyof typeof TimeUnit]
      const canRecord =
        props.recordHistory &&
        !!series &&
        Number.isFinite(amount) &&
        amount > 0 &&
        !!unitCode

      if (canRecord) {
        // Pull the active filter range straight from the helper so
        // the history entry's `range` argument matches what the user
        // sees on the plot. `undefined` when the toggle is off.
        const dateRange = getActiveFilterRange()
        const indices = await series!.dispatchFilter(
          EnumFilterOperations.FIND_GAPS,
          amount,
          unitCode,
          dateRange
        )
        await setPlotSelection(indices ?? [])
      } else {
        await setPlotSelection(endpointIndices.value)
      }
    } finally {
      isComputing.value = false
    }
  },
  { immediate: true, flush: 'post' }
)

// --- Snap chips -----------------------------------------------------

interface SnapChip {
  label: string
  amount: number
  unit: string
  active: boolean
}
const snapChips = computed<SnapChip[]>(() => {
  const ds = qcDatastream.value as {
    intendedTimeSpacing?: number
    intendedTimeSpacingUnit?: string | null
  } | null
  const n = Number(ds?.intendedTimeSpacing)
  const unitKey = timeSpacingUnitToTimeUnitKey(ds?.intendedTimeSpacingUnit)
  if (!Number.isFinite(n) || n <= 0 || !unitKey) return []
  const multipliers = [1, 2, 5]
  return multipliers.map((m) => {
    const amount = n * m
    return {
      label: `${m}× intended (${amount} ${unitKey.toLowerCase()})`,
      amount,
      unit: unitKey,
      active:
        Number(gapAmount.value) === amount &&
        selectedGapUnit.value === unitKey,
    }
  })
})

const applySnap = (chip: SnapChip) => {
  gapAmount.value = chip.amount
  selectedGapUnit.value = chip.unit
}

// Persist threshold per datastream so reopening either operation
// restores the last-used value without the user retyping.
const opParamsStore = useOperationParamsStore()
watch(
  [gapAmount, selectedGapUnit, qcDatastream],
  () => {
    opParamsStore.save(qcDatastream.value?.id ?? null, {
      gapAmount: Number(gapAmount.value),
      gapUnit: selectedGapUnit.value,
    })
  },
  { flush: 'post' }
)

// Re-exposed for parents (e.g. FillGaps) that need the wall-clock
// bounds of the active scan window. When the shared filter range is
// off these collapse to the full data extent so downstream consumers
// can use the same plumbing in either mode. `rangeWarning` stays
// null in both states because the shared panel maintains its own
// valid bounds.
const fromTs = computed<number | null>(() => {
  const range = getActiveFilterRange()
  if (range) return range[0]
  const dataX = selectedSeries.value?.data.dataX
  return dataX?.length ? (dataX[0] as number) : null
})
const toTs = computed<number | null>(() => {
  const range = getActiveFilterRange()
  if (range) return range[1]
  const dataX = selectedSeries.value?.data.dataX
  return dataX?.length ? (dataX[dataX.length - 1] as number) : null
})
const rangeWarning = computed<string | null>(() => {
  if (!selectedSeries.value?.data.dataX?.length) {
    return 'No data loaded for this datastream.'
  }
  return null
})

defineExpose({
  gapPlans,
  endpointIndices,
  isComputing,
  thresholdMs,
  rangeIndices,
  fromTs,
  toTs,
  rangeWarning,
})
</script>
