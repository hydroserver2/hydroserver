<template>
  <v-card>
    <v-card-title>Fill gaps</v-card-title>

    <v-card-text>
      <GapFinder
        ref="gapFinder"
        auto-select-endpoints
        :record-history="false"
        computing-hint="Rebuilding fill preview…"
      />

      <div class="text-body-small text-medium-emphasis mt-4 mb-2">
        Fill with a value every
      </div>
      <div class="d-flex ga-2">
        <v-text-field
          class="flex-grow-1"
          style="flex-basis: 0"
          label="Amount"
          type="number"
          v-model.number="fillAmount"
          density="comfortable"
          variant="outlined"
          hide-details
        />
        <v-select
          class="flex-grow-1"
          style="flex-basis: 0"
          label="Unit"
          :items="fillUnits"
          v-model="selectedFillUnit"
          density="comfortable"
          variant="outlined"
          hide-details
        />
      </div>

      <div class="d-flex ga-1 mt-2 flex-wrap">
        <v-chip
          v-if="hasIntendedCadence"
          size="x-small"
          variant="tonal"
          color="primary"
          :prepend-icon="
            matchesIntendedCadence ? 'mdi-check' : 'mdi-link-variant'
          "
          @click="applyIntendedCadence"
        >
          Match intended cadence
        </v-chip>
        <v-chip
          v-for="chip in fillSnapChips"
          :key="`fill-${chip.label}`"
          size="x-small"
          variant="tonal"
          color="primary"
          :prepend-icon="chip.active ? 'mdi-check' : undefined"
          @click="applyFillSnap(chip)"
        >
          {{ chip.label }}
        </v-chip>
      </div>

      <v-checkbox
        v-model="interpolateValues"
        label="Interpolate fill values"
        :hint="
          interpolateValues
            ? 'Values between endpoints will be linearly interpolated.'
            : 'The NoData value below will be inserted for every filled point.'
        "
        persistent-hint
        density="compact"
        class="mt-2"
      />

      <v-text-field
        v-if="!interpolateValues"
        v-model.number="noDataValue"
        label="NoData value"
        type="number"
        density="comfortable"
        variant="outlined"
        hide-details
        class="mt-4"
      />

      <v-alert
        v-if="cadenceWarning"
        class="mt-4"
        color="warning"
        variant="tonal"
        density="compact"
        :icon="cadenceWarning.icon"
      >
        <div class="text-body-small">{{ cadenceWarning.text }}</div>
      </v-alert>

      <v-alert
        class="mt-4"
        :color="plannedInsertions > 0 ? 'info' : 'success'"
        :icon="
          plannedInsertions > 0
            ? 'mdi-magnify-scan'
            : 'mdi-check-circle-outline'
        "
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
            <template v-if="isComputing"> Rebuilding fill preview… </template>
            <template v-else-if="!thresholdMs || !fillDeltaMs">
              Pick a gap threshold and fill cadence to preview the edit.
            </template>
            <template v-else-if="plannedInsertions > 0">
              <b>{{ gapCount }}</b> gap{{ gapCount === 1 ? '' : 's' }}
              â†’
              <b>{{ plannedInsertions }}</b>
              point{{ plannedInsertions === 1 ? '' : 's' }} to insert.
            </template>
            <template v-else>
              No points would be inserted with this threshold and cadence.
            </template>
          </div>
        </div>
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-btn
        variant="tonal"
        color="primary"
        prepend-icon="mdi-selection-ellipse-arrow-inside"
        :disabled="gapCount === 0"
        @click="reselectGaps"
      >
        Re-select gaps
      </v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="
          isUpdating || isComputing || plannedInsertions === 0 || !!rangeWarning
        "
        @click="onFillGaps"
      >
        Fill gaps
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch,
} from 'vue'
import { useUIStore, timeSpacingUnitToTimeUnitKey } from '@/store/userInterface'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import {
  EnumEditOperations,
  TimeUnit,
  timeUnitMultipliers,
} from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { usePlotlyStore } from '@/store/plotly'
import { useOperationParamsStore } from '@/store/operationParams'
import {
  clearGhostFills,
  enterPanMode,
  setGhostFills,
} from '@/utils/plotting/staging'
import GapFinder from '@/components/FilterPoints/GapFinder.vue'
import type { GapPlan } from '@/components/FilterPoints/GapFinder.vue'

const { fillUnits } = useUIStore()
const {
  interpolateValues,
  selectedFillUnit,
  fillAmount,
  noDataValue,
  gapAmount,
  selectedGapUnit,
} = storeToRefs(useUIStore())
const opParamsStore = useOperationParamsStore()

const { redraw } = usePlotlyStore()
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { qcDatastream } = storeToRefs(useDataVisStore())
const { clearSelected, setPlotSelection } = useDataSelection()
const { recordPostActionSelection } = useFilterDispatch()

const gapFinder = useTemplateRef<InstanceType<typeof GapFinder>>('gapFinder')

const gapPlans = computed<GapPlan[]>(() => gapFinder.value?.gapPlans ?? [])
const rangeWarning = computed<string | null>(
  () => gapFinder.value?.rangeWarning ?? null
)
const thresholdMs = computed<number | null>(
  () => gapFinder.value?.thresholdMs ?? null
)
const rangeIndices = computed<[number, number] | null>(
  () => gapFinder.value?.rangeIndices ?? null
)
// Wall-clock bounds of the staged window (epoch ms). Used as the
// `range` arg for FILL_GAPS so the operation is portable across
// datasets and data growth; qc-utils snaps timestamps back to
// indices internally.
const fromTs = computed<number | null>(() => gapFinder.value?.fromTs ?? null)
const toTs = computed<number | null>(() => gapFinder.value?.toTs ?? null)
const gapCount = computed(() => gapPlans.value.length)

const fillDeltaMs = computed(() => {
  const amount = Number(fillAmount.value)
  if (!Number.isFinite(amount) || amount <= 0) return null
  // @ts-ignore
  const code = TimeUnit[selectedFillUnit.value as keyof typeof TimeUnit]
  const mult = timeUnitMultipliers[code]
  return mult ? amount * mult * 1000 : null
})

const intendedCadence = computed<{
  amount: number
  unit: string
  ms: number
} | null>(() => {
  const ds = qcDatastream.value as {
    intendedTimeSpacing?: number
    intendedTimeSpacingUnit?: string | null
  } | null
  const amount = Number(ds?.intendedTimeSpacing)
  const unit = timeSpacingUnitToTimeUnitKey(ds?.intendedTimeSpacingUnit)
  if (!Number.isFinite(amount) || amount <= 0 || !unit) return null
  // @ts-ignore
  const code = TimeUnit[unit as keyof typeof TimeUnit]
  const multiplier = timeUnitMultipliers[code]
  if (multiplier === undefined) return null
  const ms = amount * multiplier * 1000
  return { amount, unit, ms }
})

const hasIntendedCadence = computed(() => intendedCadence.value !== null)
const matchesIntendedCadence = computed(() => {
  const i = intendedCadence.value
  if (!i) return false
  return (
    Number(fillAmount.value) === i.amount && selectedFillUnit.value === i.unit
  )
})

const applyIntendedCadence = () => {
  const i = intendedCadence.value
  if (!i) return
  fillAmount.value = i.amount
  selectedFillUnit.value = i.unit
}

interface FillFanout {
  xs: number[]
  ys: number[]
  count: number
}

// Mirrors the count/fill loop in qc-utils' _fillGaps so the preview
// matches exactly what the dispatch will write.
const fillFanout = computed<FillFanout>(() => {
  const delta = fillDeltaMs.value
  if (!delta || !gapPlans.value.length) return { xs: [], ys: [], count: 0 }
  const xs: number[] = []
  const ys: number[] = []
  for (const p of gapPlans.value) {
    let t = p.leftTs + delta
    const span = p.rightTs - p.leftTs
    const valueSpan = p.rightY - p.leftY
    while (t < p.rightTs) {
      xs.push(t)
      ys.push(p.leftY + ((t - p.leftTs) * valueSpan) / span)
      t += delta
    }
  }
  return { xs, ys, count: xs.length }
})

const plannedInsertions = computed(() => fillFanout.value.count)

const ghostComputing = ref(false)
const isComputing = computed(
  () => ghostComputing.value || (gapFinder.value?.isComputing ?? false)
)

watch(
  fillFanout,
  async ({ xs, ys }) => {
    ghostComputing.value = true
    try {
      await setGhostFills(xs, ys)
    } finally {
      ghostComputing.value = false
    }
  },
  { immediate: true, flush: 'post' }
)

interface CadenceWarning {
  icon: string
  text: string
}

const cadenceWarning = computed<CadenceWarning | null>(() => {
  const t = thresholdMs.value
  const d = fillDeltaMs.value
  if (t && d && d > t) {
    return {
      icon: 'mdi-alert-outline',
      text: 'Fill cadence is larger than the gap threshold: gaps just above the threshold will get no fill points. Choose a finer cadence if that matters.',
    }
  }
  const i = intendedCadence.value
  if (i && d) {
    const ratio = i.ms / d
    const isCleanRatio = Math.abs(ratio - Math.round(ratio)) < 1e-6
    if (!isCleanRatio) {
      return {
        icon: 'mdi-alert-circle-outline',
        text: `Fill cadence doesn't divide evenly into the datastream's intended spacing (${i.amount} ${i.unit.toLowerCase()}). Inserted points won't align to the existing grid.`,
      }
    }
  }
  return null
})

interface SnapChip {
  label: string
  amount: number
  unit: string
  active: boolean
}

const fillSnapChips = computed<SnapChip[]>(() => {
  const i = intendedCadence.value
  if (!i) return []
  return [0.5, 1, 2].map((m) => {
    const amount = i.amount * m
    return {
      label: `${m}Ã— intended (${amount} ${i.unit.toLowerCase()})`,
      amount,
      unit: i.unit,
      active:
        Number(fillAmount.value) === amount &&
        selectedFillUnit.value === i.unit,
    }
  })
})

const applyFillSnap = (chip: SnapChip) => {
  fillAmount.value = chip.amount
  selectedFillUnit.value = chip.unit
}

// Clear before reselecting because setPlotSelection alone can't wipe
// box-select / lasso rectangles: setSelectedPoints puts selections:[]
// into the data update instead of the layout update.
const reselectGaps = async () => {
  await clearSelected({ recordHistory: false })
  const indices = gapFinder.value?.endpointIndices ?? []
  await setPlotSelection(indices)
}

const emit = defineEmits(['close'])
const onFillGaps = async () => {
  isUpdating.value = true

  setTimeout(async () => {
    if (rangeWarning.value) {
      isUpdating.value = false
      return
    }
    // Pass a datetime range only when the staged window is valid;
    // otherwise omit and _fillGaps runs over the full extent.
    const dateRange: [number, number] | undefined =
      rangeIndices.value != null && fromTs.value != null && toTs.value != null
        ? [fromTs.value, toTs.value]
        : undefined

    const insertedIndices =
      ((await selectedSeries.value?.data.dispatchAction(
        EnumEditOperations.FILL_GAPS,
        // @ts-ignore
        [+gapAmount.value, TimeUnit[selectedGapUnit.value]],
        // @ts-ignore
        [+fillAmount.value, TimeUnit[selectedFillUnit.value]],
        interpolateValues.value,
        +noDataValue.value,
        dateRange
      )) as number[] | undefined) ?? []

    opParamsStore.save(qcDatastream.value?.id ?? null, {
      gapAmount: Number(gapAmount.value),
      gapUnit: selectedGapUnit.value,
      fillAmount: Number(fillAmount.value),
      fillUnit: selectedFillUnit.value,
      noDataValue: Number(noDataValue.value),
    })

    isUpdating.value = false
    await redraw()
    await recordPostActionSelection(insertedIndices)
    emit('close')
  })
}

// Pan mode keeps the staging band visible (hidden in zoom/select/lasso).
// Re-dispatch endpoints after clearSelected because GapFinder's
// autoSelectEndpoints watcher runs in the post-flush queue and can
// interleave with the clear.
onMounted(async () => {
  await enterPanMode()
  await clearSelected()
  const indices = gapFinder.value?.endpointIndices ?? []
  if (indices.length) {
    await setPlotSelection(indices)
  }
  // Seed the ghost-marker preview manually: the immediate fire of the
  // post-flush watcher on fillFanout runs while gapFinder.value is
  // still null, so its initial setGhostFills is a no-op.
  const { xs, ys } = fillFanout.value
  if (xs.length) {
    await setGhostFills(xs, ys)
  }
})

onBeforeUnmount(async () => {
  await clearGhostFills()
})
</script>
