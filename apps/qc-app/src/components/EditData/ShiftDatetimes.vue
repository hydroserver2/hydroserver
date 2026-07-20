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
          hide-details
          @keyup.enter="
            !isUpdating && selectedData?.length && onShiftDatetimes()
          "
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
import { useFilterDispatch } from '@/composables/useFilterDispatch'

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
      label: `${m}Ã— intended (${amount} ${unitKey.toLowerCase()})`,
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
    const newIndices =
      ((await selectedSeries.value?.data.dispatchAction(
        EnumEditOperations.SHIFT_DATETIMES,
        +shiftAmount.value,
        // @ts-ignore
        TimeUnit[selectedShiftUnit.value]
      )) as number[] | undefined) ?? []

    isUpdating.value = false
    await redraw(true)
    await recordPostActionSelection(newIndices)
    emit('close')
  })
}
</script>
