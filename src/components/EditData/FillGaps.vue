<template>
  <v-card>
    <v-card-title>Fill gaps</v-card-title>

    <v-card-text>
      <!-- Top half: shared "find gaps" UX. `GapFinder` owns date
           pickers, presets, threshold, snap chips, overlay band,
           red gap bands, and the range warning; we read its exposed
           state via `gapFinder` below to drive the fill preview +
           commit. -->
      <GapFinder
        ref="gapFinder"
        auto-select-endpoints
        :record-history="false"
        computing-hint="Rebuilding fill preview…"
      />

      <!-- Fill-only controls start here. -->

      <div class="text-caption text-medium-emphasis mt-4 mb-2">
        Fill with a value every
      </div>
      <div class="d-flex gap-2">
        <v-text-field
          label="Amount"
          type="number"
          v-model.number="fillAmount"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
        <v-select
          label="Unit"
          :items="fillUnits"
          v-model="selectedFillUnit"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
      </div>

      <div class="d-flex gap-1 mt-2 flex-wrap">
        <v-chip
          v-if="hasIntendedCadence"
          size="x-small"
          variant="tonal"
          color="primary"
          :prepend-icon="matchesIntendedCadence ? 'mdi-check' : 'mdi-link-variant'"
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
        <div class="text-caption">{{ cadenceWarning.text }}</div>
      </v-alert>

      <v-alert
        class="mt-4"
        :color="plannedInsertions > 0 ? 'info' : 'success'"
        :icon="plannedInsertions > 0 ? 'mdi-magnify-scan' : 'mdi-check-circle-outline'"
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
              Rebuilding fill preview…
            </template>
            <template v-else-if="!thresholdMs || !fillDeltaMs">
              Pick a gap threshold and fill cadence to preview the edit.
            </template>
            <template v-else-if="plannedInsertions > 0">
              <b>{{ gapCount }}</b> gap{{ gapCount === 1 ? '' : 's' }}
              →
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
      <!-- Same "lost my selection" escape hatch as Find Gaps. Box-
           select / lasso gestures on the plot replace the gap
           endpoint selection and there's no built-in way to restore
           it; this button reapplies the currently-detected gap
           endpoints without having to retune anything. -->
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
          isUpdating ||
          isComputing ||
          plannedInsertions === 0 ||
          !!rangeWarning
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

// Template ref into the shared GapFinder. We expose its reactive
// refs via `defineExpose` over there; here we unwrap them with
// computed() so the fill-specific logic below (ghost markers,
// insertion counter, commit range) stays reactive.
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
// `range` arg for `FILL_GAPS` instead of the index-based
// `rangeIndices` so the operation is portable across datasets / data
// growth — qc-utils' `_fillGaps` snaps these timestamps back to
// indices internally.
const fromTs = computed<number | null>(
  () => gapFinder.value?.fromTs ?? null
)
const toTs = computed<number | null>(
  () => gapFinder.value?.toTs ?? null
)
const gapCount = computed(() => gapPlans.value.length)

// --- Fill cadence helpers -------------------------------------------

const fillDeltaMs = computed(() => {
  const amount = Number(fillAmount.value)
  if (!Number.isFinite(amount) || amount <= 0) return null
  // @ts-ignore
  const code = TimeUnit[selectedFillUnit.value as keyof typeof TimeUnit]
  const mult = timeUnitMultipliers[code]
  return mult ? amount * mult * 1000 : null
})

// Intended cadence from the QC datastream, translated into both our
// TimeUnit key space (for the Match button) and milliseconds (for
// the mismatch warning). Returns `null` when the datastream lacks
// the intended-spacing metadata.
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
  const ms = amount * timeUnitMultipliers[code] * 1000
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

// --- Insertion planning + ghost preview -----------------------------

interface FillFanout {
  xs: number[]
  ys: number[]
  count: number
}

/**
 * Expand each `GapPlan` into its synthesised fill positions so the
 * insertion counter, the ghost-marker preview, and the commit share
 * a single source of truth. Mirrors the count/fill loop in
 * `_fillGaps` byte-for-byte so what the user sees is exactly what
 * `dispatchAction` will write.
 */
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

// Local computing flag for the ghost-marker push. Union'd with the
// GapFinder's own `isComputing` so the alert + button report a
// single "busy" state across both panels.
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

// --- Warnings -------------------------------------------------------

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
      text:
        'Fill cadence is larger than the gap threshold — gaps just above the threshold will get no fill points. Choose a finer cadence if that matters.',
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

// --- Fill cadence snap chips ---------------------------------------

interface SnapChip {
  label: string
  amount: number
  unit: string
  active: boolean
}

const fillSnapChips = computed<SnapChip[]>(() => {
  const i = intendedCadence.value
  if (!i) return []
  // Fractional chips for finer-than-intended fill cadence, matching
  // the common case where users want to refill at the same grid but
  // also densify when data is missing.
  return [0.5, 1, 2].map((m) => {
    const amount = i.amount * m
    return {
      label: `${m}× intended (${amount} ${i.unit.toLowerCase()})`,
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

// --- Re-select gaps -------------------------------------------------

/**
 * Re-apply the current gap endpoint selection on the plot. Clears
 * whatever is selected first — including box-select / lasso
 * rectangles, which `setPlotSelection` alone can't wipe because
 * its underlying `setSelectedPoints` puts `selections: []` into the
 * data update instead of the layout update. Mirrors the same
 * escape hatch Find Gaps exposes.
 */
const reselectGaps = async () => {
  await clearSelected({ recordHistory: false })
  const indices = gapFinder.value?.endpointIndices ?? []
  await setPlotSelection(indices)
}

// --- Commit ---------------------------------------------------------

const emit = defineEmits(['close'])
const onFillGaps = async () => {
  isUpdating.value = true

  setTimeout(async () => {
    if (rangeWarning.value) {
      isUpdating.value = false
      return
    }
    // Datetime-addressed range — qc-utils converts to indices via
    // binary search internally. Only pass when the staged window is
    // valid (rangeIndices being non-null is the canonical "user has
    // a usable window" signal). Otherwise omit and `_fillGaps` runs
    // over the full extent.
    const dateRange: [number, number] | undefined =
      rangeIndices.value != null && fromTs.value != null && toTs.value != null
        ? [fromTs.value, toTs.value]
        : undefined

    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.FILL_GAPS,
      // @ts-ignore
      [+gapAmount.value, TimeUnit[selectedGapUnit.value]],
      // @ts-ignore
      [+fillAmount.value, TimeUnit[selectedFillUnit.value]],
      interpolateValues.value,
      +noDataValue.value,
      dateRange
    )

    opParamsStore.save(qcDatastream.value?.id ?? null, {
      gapAmount: Number(gapAmount.value),
      gapUnit: selectedGapUnit.value,
      fillAmount: Number(fillAmount.value),
      fillUnit: selectedFillUnit.value,
      noDataValue: Number(noDataValue.value),
    })

    // FILL_GAPS edit was just dispatched; the post-commit clear is
    // visual hygiene only — `recordHistory: false` keeps it from
    // adding an empty SELECTION below the FILL_GAPS entry.
    await clearSelected({ recordHistory: false })
    isUpdating.value = false
    await redraw()
    emit('close')
  })
}

// On open: switch the plot into pan mode so the staging band is
// visible + interactive (we hide it in zoom/select/lasso), then
// wipe any existing selection — including box-select / lasso
// rectangles — so a stale prior selection doesn't linger visually
// while the user is staging the fill. The explicit re-dispatch
// afterwards mirrors the fix in Find Gaps: GapFinder's
// `autoSelectEndpoints` watcher runs in the post-flush queue on
// mount and can interleave with `clearSelected`, so we apply the
// endpoints again here to make the end state deterministic.
onMounted(async () => {
  await enterPanMode()
  // Drop the previously visible selection from history — the panel's
  // internal Find Gaps step will immediately display a new selection
  // from the gaps it detects, so the prior selection-producing entry
  // (a user-click SELECTION or a selection-driving filter) is no
  // longer relevant context. `_selection`'s empty-case logic does
  // the pop: the dispatched empty SELECTION pops itself and (when
  // applicable) the preceding filter that was driving the cleared
  // selection.
  await clearSelected()
  const indices = gapFinder.value?.endpointIndices ?? []
  if (indices.length) {
    await setPlotSelection(indices)
  }
  // Explicitly seed the ghost-marker preview. The post-flush watcher
  // on `fillFanout` would normally handle this, but its
  // `immediate: true` fire happens during setup when `gapFinder.value`
  // is still null — so the watched value is empty and the initial
  // `setGhostFills([], [])` is a no-op. By the time we reach this
  // point in the parent's `onMounted`, RangeStager (a grandchild)
  // has run its own mount hook and seeded the date bounds, so
  // `fillFanout.value` reflects real gap data; pushing it now means
  // the preview is visible from the user's first frame instead of
  // waiting for whatever next reactivity tick happens to fire the
  // watcher.
  const { xs, ys } = fillFanout.value
  if (xs.length) {
    await setGhostFills(xs, ys)
  }
})

// Ghost-marker trace is owned by this panel (GapFinder handles the
// red bands + stage shape). Tear it down when the panel closes so
// the plot is clean if the user dismisses without committing.
onBeforeUnmount(async () => {
  await clearGhostFills()
})
</script>
