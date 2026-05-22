<template>
  <div>
    <div
      v-if="filterRangeActive"
      class="text-body-small text-medium-emphasis mb-2"
    >
      Scan window: shared filter range (above).
    </div>
    <div v-else class="text-body-small text-medium-emphasis mb-2">
      Scanning the full datastream.
      Toggle <b>Filter range</b> in the plot toolbar to restrict.
    </div>

    <div class="text-body-small text-medium-emphasis mt-2 mb-2">
      Find gaps of at least
    </div>
    <div class="d-flex ga-2">
      <v-text-field
        label="Amount"
        type="number"
        v-model.number="gapAmount"
        density="comfortable"
        variant="outlined"
        hide-details
        class="flex-1-1-0"
      />
      <v-select
        label="Unit"
        :items="gapUnits"
        v-model="selectedGapUnit"
        density="comfortable"
        variant="outlined"
        hide-details
        class="flex-1-1-0"
      />
    </div>

    <div v-if="snapChips.length" class="d-flex ga-1 mt-2 flex-wrap">
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
      <div class="d-flex align-center ga-2">
        <v-progress-circular
          v-if="isComputing"
          size="14"
          width="2"
          indeterminate
          color="primary"
        />
        <div class="text-body-small">
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
    autoSelectEndpoints?: boolean
    recordHistory?: boolean
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
  // @ts-ignore
  const unitCode = TimeUnit[selectedGapUnit.value as keyof typeof TimeUnit]
  const mult = timeUnitMultipliers[unitCode]
  if (!mult) return null
  return amount * mult * 1000
})

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
    const leftTs = dataX[i - 1]
    const rightTs = dataX[i]
    const leftY = dataY[i - 1]
    const rightY = dataY[i]
    if (
      leftTs === undefined ||
      rightTs === undefined ||
      leftY === undefined ||
      rightY === undefined
    ) continue
    const span = rightTs - leftTs
    if (span > threshold) {
      plans.push({
        leftTs,
        rightTs,
        leftIdx: i - 1,
        rightIdx: i,
        leftY,
        rightY,
      })
    }
  }
  return plans
})

const gapCount = computed(() => gapPlans.value.length)

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
      label: `${m}Ã— intended (${amount} ${unitKey.toLowerCase()})`,
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
