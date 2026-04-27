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
      <div class="text-caption text-medium-emphasis mb-2">Operator</div>
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

      <div class="text-caption text-medium-emphasis mb-2">
        New value = old <b>{{ operators[selectedOperator] }}</b> input
      </div>
      <v-text-field
        label="Value"
        v-model="operationValue"
        step="0.1"
        type="number"
        density="comfortable"
        variant="outlined"
        hide-details
        @keyup.enter="
          !isUpdating && selectedData?.length && onChangeValues()
        "
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating || !selectedData?.length"
        @click="onChangeValues"
      >
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations, Operator } from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import { usePlotlyStore } from '@/store/plotly'
import { useUIStore } from '@/store/userInterface'

const { redraw } = usePlotlyStore()
const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const { clearSelected } = useDataSelection()
const { operators } = useUIStore()
const { selectedOperator, operationValue } = storeToRefs(useUIStore())

const emit = defineEmits(['close'])

const onChangeValues = async () => {
  if (!selectedData.value?.length) {
    return
  }

  const operator = Operator[operators[selectedOperator.value] as Operator]

  isUpdating.value = true
  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.CHANGE_VALUES,
      operator,
      +operationValue.value
    )

    await clearSelected()
    isUpdating.value = false
    await redraw()
    emit('close')
  })
}
</script>
