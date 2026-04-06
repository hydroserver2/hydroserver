<template>
  <v-card>
    <v-card-title>Change Values</v-card-title>
    <v-card-subtitle class="mb-4">
      <div>
        {{ selectedData?.length }} Data Point{{
          selectedData?.length === 1 ? '' : 's'
        }}
        selected
      </div>
    </v-card-subtitle>

    <v-divider></v-divider>

    <v-card-text>
      <div class="d-flex flex-column gap-2">
        <div>
          <v-label class="mb-2 d-block"
            >Operation: <b>{{ operators[selectedOperator] }}</b></v-label
          >
          <v-btn-toggle
            v-model="selectedOperator"
            variant="outlined"
            color="primary"
            mandatory
            divided
          >
            <v-btn title="Add">
              <v-icon color="green">mdi-plus</v-icon>
            </v-btn>

            <v-btn title="Subtract">
              <v-icon color="red">mdi-minus</v-icon>
            </v-btn>

            <v-btn title="Multiply">
              <v-icon color="blue">mdi-multiplication</v-icon>
            </v-btn>

            <v-btn title="Divide">
              <v-icon color="orange">mdi-division</v-icon>
            </v-btn>

            <v-btn title="Assign">
              <v-icon>mdi-equal</v-icon>
            </v-btn>
          </v-btn-toggle>
        </div>

        <v-text-field
          label="Value"
          v-model="operationValue"
          step="0.1"
          type="number"
          block
          hide-details
        >
        </v-text-field>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn :disabled="isUpdating" @click="onChangeValues"
        >Change Values</v-btn
      >
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
    await selectedSeries.value?.data.dispatch(
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
