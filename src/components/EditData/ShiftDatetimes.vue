<template>
  <v-card>
    <v-card-title>Shift datetimes</v-card-title>
    <v-card-subtitle>
      <span class="selected-count-badge">
        <v-icon icon="mdi-vector-selection" size="14" />
        {{ selectedData?.length }} point{{
          selectedData?.length === 1 ? '' : 's'
        }}
        selected
      </span>
    </v-card-subtitle>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">
        Shift selected timestamps by
      </div>
      <div class="d-flex gap-2">
        <v-text-field
          label="Amount"
          type="number"
          v-model.number="shiftAmount"
          density="comfortable"
          variant="outlined"
          hide-details
          style="flex: 1 1 0"
        />
        <v-select
          label="Unit"
          :items="shiftUnits"
          v-model="selectedShiftUnit"
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
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating || !selectedData?.length"
        @click="onShiftDatetimes"
      >
        Shift
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations, TimeUnit } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore, timeSpacingUnitToTimeUnitKey } from '@/store/userInterface'
import { useDataSelection } from '@/composables/useDataSelection'

const { selectedData, qcDatastream } = storeToRefs(useDataVisStore())
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedShiftUnit, shiftAmount } = storeToRefs(useUIStore())
const { redraw } = usePlotlyStore()
const { shiftUnits } = useUIStore()
const { clearSelected } = useDataSelection()

/**
 * Snap chips based on the QC datastream's intended cadence, mirroring
 * the Fill Gaps fill-cadence chips. The most common shift is a single
 * cadence step (users correcting an off-by-one misalignment), with
 * half- and double-cadence for the less frequent cases. Only rendered
 * when the datastream exposes intended-spacing metadata — otherwise
 * there's no anchor to snap against.
 */
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
  return [0.5, 1, 2].map((m) => {
    const amount = n * m
    return {
      label: `${m}× intended (${amount} ${unitKey.toLowerCase()})`,
      amount,
      unit: unitKey,
      active:
        Number(shiftAmount.value) === amount &&
        selectedShiftUnit.value === unitKey,
    }
  })
})

const applySnap = (chip: SnapChip) => {
  shiftAmount.value = chip.amount
  selectedShiftUnit.value = chip.unit
}

const emit = defineEmits(['close'])

const onShiftDatetimes = async () => {
  if (!selectedData.value?.length) {
    return
  }

  isUpdating.value = true

  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.SHIFT_DATETIMES,
      selectedData.value,
      +shiftAmount.value,
      // @ts-ignore
      TimeUnit[selectedShiftUnit.value]
    )

    await clearSelected()
    isUpdating.value = false
    await redraw(true)
    emit('close')
  })
}
</script>
