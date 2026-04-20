<template>
  <div class="gap-finder">
    <!-- Shared range picker: date pickers, presets, plot overlay,
         data-bounds clamping, range warning. -->
    <RangeStager ref="stager" />

    <div class="text-caption text-medium-emphasis mt-4 mb-2">
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
      v-if="!rangeWarning"
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
              in the selected range.
            </slot>
          </template>
          <template v-else>
            No gaps match this threshold in the selected range.
          </template>
        </div>
      </div>
    </v-alert>
  </div>
</template>

<script setup lang="ts">
/**
 * Shared "find gaps" UI — used standalone by the Find Gaps
 * operation panel, and as the top half of the Fill Gaps panel.
 * Owns gap-detection-specific controls (threshold input, snap
 * chips, count alert, red gap bands) and delegates the date-range
 * picker / overlay / preset logic to `RangeStager`.
 *
 * When mounted with `autoSelectEndpoints`, each detection also
 * dispatches a point selection to the plot (Find Gaps' live-commit
 * behaviour). Without the prop the overlay bands render but the
 * plot's existing selection stays untouched (Fill Gaps' behaviour —
 * it owns the selection lifecycle through `dispatchAction`).
 */
import {
  computed,
  onBeforeUnmount,
  ref,
  useTemplateRef,
  watch,
} from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useDataSelection } from '@/composables/useDataSelection'
import {
  TimeUnit,
  timeUnitMultipliers,
} from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore, timeSpacingUnitToTimeUnitKey } from '@/store/userInterface'
import { saveOpParams } from '@/composables/useOperationParams'
import {
  clearGapBands,
  setGapBands,
} from '@/utils/plotting/staging'
import RangeStager from '@/components/FilterPoints/RangeStager.vue'

export interface GapPlan {
  leftTs: number
  rightTs: number
  leftIdx: number
  rightIdx: number
  leftY: number
  rightY: number
}

const props = defineProps<{
  /** Dispatch a live point selection of the gap endpoints on every
   *  detection. Find Gaps opts in; Fill Gaps leaves selection alone
   *  because its commit drives its own selection state. */
  autoSelectEndpoints?: boolean
  /** Override the "Updating gap preview…" line shown in the alert
   *  while the async Plotly writes settle. Handy when a parent
   *  bundles its own async work (ghost markers) under the same
   *  spinner window. */
  computingHint?: string
}>()

const { selectedSeries } = storeToRefs(usePlotlyStore())
const { gapAmount, gapUnits, selectedGapUnit } = storeToRefs(useUIStore())
const { qcDatastream } = storeToRefs(useDataVisStore())
const { dispatchSelection } = useDataSelection()

// Unwrap state exposed by RangeStager so downstream computeds can
// track the date-range without the parent having to thread it
// through props on every tick.
const stager = useTemplateRef<InstanceType<typeof RangeStager>>('stager')
const fromTs = computed(() => stager.value?.fromTs ?? 0)
const toTs = computed(() => stager.value?.toTs ?? 0)
const rangeWarning = computed<string | null>(
  () => stager.value?.rangeWarning ?? null
)
const rangeIndices = computed<[number, number] | null>(
  () => stager.value?.rangeIndices ?? null
)

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

// Client-side gap detection over the staged window. Mirrors
// `findGapsCore` in qc-utils (not re-exported from the package)
// but skips the worker path — we're detecting in-panel and the
// scan is small enough to run inline. Returns full `GapPlan`
// records so parents can build their own previews off a single
// shared pass.
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

/** Flat, sorted, de-duplicated list of every gap-endpoint index
 *  in the current scan. Matches the `_findGaps` return shape so
 *  `dispatchSelection` on it highlights the same points the
 *  committed filter would. */
const endpointIndices = computed<number[]>(() => {
  const out = new Set<number>()
  for (const p of gapPlans.value) {
    out.add(p.leftIdx)
    out.add(p.rightIdx)
  }
  return [...out].sort((a, b) => a - b)
})

// `isComputing` flips true for the duration of the async Plotly
// writes so the alert can show a spinner while relayouts settle.
const isComputing = ref(false)

watch(
  gapPlans,
  async (plans) => {
    isComputing.value = true
    try {
      await setGapBands(plans.map((p) => [p.leftTs, p.rightTs]))
      if (props.autoSelectEndpoints) {
        await dispatchSelection(endpointIndices.value)
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
watch(
  [gapAmount, selectedGapUnit, qcDatastream],
  () => {
    saveOpParams(qcDatastream.value?.id ?? null, {
      gapAmount: Number(gapAmount.value),
      gapUnit: selectedGapUnit.value,
    })
  },
  { flush: 'post' }
)

onBeforeUnmount(async () => {
  await clearGapBands()
})

defineExpose({
  gapPlans,
  endpointIndices,
  rangeWarning,
  isComputing,
  fromTs,
  toTs,
  thresholdMs,
  rangeIndices,
})
</script>
