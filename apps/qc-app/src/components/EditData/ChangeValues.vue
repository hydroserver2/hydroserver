<template>
  <v-card>
    <v-card-title>Change values</v-card-title>
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
      <div class="text-body-small text-medium-emphasis mb-2">Operator</div>
      <v-btn-toggle
        v-model="selectedOperator"
        color="primary"
        variant="outlined"
        divided
        mandatory
        density="comfortable"
        class="mb-3 d-flex"
      >
        <v-btn title="Add" class="flex-grow-1" style="min-width: 0">
          <v-icon color="green">mdi-plus</v-icon>
        </v-btn>
        <v-btn title="Subtract" class="flex-grow-1" style="min-width: 0">
          <v-icon color="red">mdi-minus</v-icon>
        </v-btn>
        <v-btn title="Multiply" class="flex-grow-1" style="min-width: 0">
          <v-icon color="blue">mdi-multiplication</v-icon>
        </v-btn>
        <v-btn title="Divide" class="flex-grow-1" style="min-width: 0">
          <v-icon color="orange">mdi-division</v-icon>
        </v-btn>
        <v-btn title="Assign" class="flex-grow-1" style="min-width: 0">
          <v-icon>mdi-equal</v-icon>
        </v-btn>
      </v-btn-toggle>

      <div class="text-body-small text-medium-emphasis mb-2">
        New value = old <b>{{ operators[selectedOperator] }}</b> input
      </div>
      <v-text-field
        label="Value"
        v-model="operationValue"
        step="0.1"
        type="number"
        density="comfortable"
        variant="outlined"
        hide-details="auto"
        :error-messages="valueError"
        @keyup.enter="canApply && onChangeValues()"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!canApply"
        @click="onChangeValues"
      >
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations, Operator } from '@uwrl/qc-utils'
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore } from '@/store/userInterface'

const { redraw } = usePlotlyStore()
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const { recordPostActionSelection } = useFilterDispatch()
const { operators } = useUIStore()
const { selectedOperator, operationValue } = storeToRefs(useUIStore())

const emit = defineEmits(['close'])

const operator = computed(
  () => Operator[operators[selectedOperator.value] as Operator]
)

// The field gives a string, and `+''` would quietly become 0.
const value = computed(() => {
  const raw = String(operationValue.value ?? '').trim()
  return raw === '' ? NaN : Number(raw)
})

const valueError = computed(() => {
  if (!Number.isFinite(value.value)) return 'Enter a number.'
  if (operator.value === Operator.DIV && value.value === 0)
    return 'Cannot divide by zero.'
  return ''
})

const canApply = computed(
  () => !isUpdating.value && !!selectedData.value?.length && !valueError.value
)

const onChangeValues = async () => {
  if (!canApply.value || !selectedData.value) return

  const op = operator.value
  const amount = value.value
  const indices = [...selectedData.value]

  isUpdating.value = true
  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.CHANGE_VALUES,
      op,
      amount
    )

    isUpdating.value = false
    await redraw()
    await recordPostActionSelection(indices)
    emit('close')
  })
}
</script>
