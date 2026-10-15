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
      <div class="text-body-small text-medium-emphasis mb-2">
        Shift selected timestamps by
      </div>
      <div class="d-flex ga-2">
        <v-text-field
          class="flex-grow-1"
          style="flex-basis: 0"
          label="Amount"
          type="number"
          v-model.number="shiftAmount"
          density="comfortable"
          variant="outlined"
          :error="!amountValid"
          hide-details
          data-testid="shift-amount"
          @keyup.enter="canShift && onShiftDatetimes()"
        />
        <v-select
          class="flex-grow-1"
          style="flex-basis: 0"
          label="Unit"
          :items="shiftUnits"
          v-model="selectedShiftUnit"
          density="comfortable"
          variant="outlined"
          hide-details
          data-testid="shift-unit"
        />
      </div>

      <div
        v-if="isCalendarUnit"
        class="text-body-small mt-2"
        :class="amountValid ? 'text-medium-emphasis' : 'text-error'"
        data-testid="shift-calendar-note"
      >
        {{
          amountValid
            ? `Months and years follow the calendar in ${zoneName()}, keeping the clock time. A day past the end of a month moves to its last day.`
            : 'Months and years shift by whole numbers.'
        }}
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
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!canShift"
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
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { zoneId, zoneName } from '@/utils/timeZone'

const { selectedData, qcDatastream } = storeToRefs(useDataVisStore())
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedShiftUnit, shiftAmount } = storeToRefs(useUIStore())
const { redraw } = usePlotlyStore()
const { shiftUnits } = useUIStore()
const { recordPostActionSelection } = useFilterDispatch()

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

const isCalendarUnit = computed(
  () => selectedShiftUnit.value === 'MONTH' || selectedShiftUnit.value === 'YEAR'
)
const amountValid = computed(() => {
  const n = Number(shiftAmount.value)
  return Number.isFinite(n) && (!isCalendarUnit.value || Number.isInteger(n))
})
const canShift = computed(
  () => !isUpdating.value && !!selectedData.value?.length && amountValid.value
)

const emit = defineEmits(['close'])

const onShiftDatetimes = async () => {
  if (!canShift.value) return

  isUpdating.value = true

  setTimeout(async () => {
    const newIndices =
      ((await selectedSeries.value?.data.dispatchAction(
        EnumEditOperations.SHIFT_DATETIMES,
        +shiftAmount.value,
        // @ts-ignore
        TimeUnit[selectedShiftUnit.value],
        zoneId()
      )) as number[] | undefined) ?? []

    isUpdating.value = false
    await redraw(true)
    await recordPostActionSelection(newIndices)
    emit('close')
  })
}
</script>
