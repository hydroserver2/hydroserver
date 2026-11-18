<template>
  <v-form ref="form">
    <v-card>
      <v-card-title class="d-flex align-center">
        <span class="flex-grow-1">Add points</span>
        <v-btn
          size="x-small"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-plus"
          @click="addRow"
        >
          Row
        </v-btn>
      </v-card-title>

      <v-card-text>
        <div class="d-flex flex-column ga-3">
          <div
            v-for="(point, index) of dataPoints"
            :key="index"
            class="add-points__row pa-2 rounded border"
          >
            <div class="d-flex align-center mb-1">
              <v-chip size="x-small" color="primary" variant="tonal" label>
                #{{ index + 1 }}
              </v-chip>
              <v-spacer />
              <v-btn
                icon="mdi-close"
                size="x-small"
                variant="text"
                color="error"
                density="comfortable"
                title="Remove row"
                @click="removeRow(index)"
              />
            </div>
            <div class="mb-2">
              <DatePickerField
                :model-value="point.dt"
                seconds
                placeholder="Datetime"
                @update:model-value="(d: Date) => (point.dt = d)"
              />
            </div>
            <v-text-field
              type="number"
              label="Value"
              :rules="requiredNumber"
              v-model.number="point.value"
              density="comfortable"
              variant="outlined"
              hide-details
            />
          </div>
        </div>
        <div
          v-if="takenTime !== null"
          class="text-body-small text-error mt-3"
          data-testid="add-points-collision"
        >
          A point already exists at {{ formatDateTime(takenTime) }}. Pick a
          different datetime.
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!form?.isValid || isUpdating || takenTime !== null"
          @click="onAddDataPoints"
        >
          Add {{ dataPoints.length }} point{{
            dataPoints.length === 1 ? '' : 's'
          }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Ref } from 'vue'
import { requiredNumber } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import { storeToRefs } from 'pinia'
import { EnumEditOperations } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import { useUIStore } from '@/store/userInterface'
import DatePickerField from '@/components/VisualizeData/DatePickerField.vue'
import { intendedSpacingMs } from '@/utils/plotting/plotly'
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { formatDateTime } from '@/utils/time'

const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const { redraw } = usePlotlyStore()
const { noDataValue } = storeToRefs(useUIStore())
const { recordPostActionSelection } = useFilterDispatch()

const form = ref<InstanceType<typeof VForm>>()

interface NewPoint {
  dt: Date
  value: number
}

const dataPoints: Ref<NewPoint[]> = ref([])

const defaultValue = () => Number(noDataValue.value) || 0

// Without an intended spacing, step by the gap before the anchor point so
// the proposed time isn't the anchor's own.
const spacingAt = (index: number | null): number => {
  const intended = intendedSpacingMs()
  if (intended) return intended
  const dataX = selectedSeries.value?.data.dataX
  if (dataX && index != null && index > 0) {
    const gap = (dataX[index] as number) - (dataX[index - 1] as number)
    if (gap > 0) return gap
  }
  return 60_000
}

const pickFirstDatetime = (): Date => {
  const dataX = selectedSeries.value?.data.dataX
  let anchorIdx: number | null = null
  if (selectedData.value?.length && dataX) {
    const lastIdx = selectedData.value[selectedData.value.length - 1] as number
    if (Number.isFinite(dataX[lastIdx])) anchorIdx = lastIdx
  }
  if (anchorIdx == null && dataX?.length) anchorIdx = dataX.length - 1
  if (anchorIdx == null || !dataX) return new Date()
  return new Date((dataX[anchorIdx] as number) + spacingAt(anchorIdx))
}

// The first taken timestamp among the rows, or null.
const takenTime = computed(() => {
  const record = selectedSeries.value?.data
  if (!record || !dataPoints.value.length) return null
  return record.findTimeCollision(dataPoints.value.map((p) => p.dt.getTime()))
})

const addRow = () => {
  const last = dataPoints.value[dataPoints.value.length - 1]
  const nextDt = last
    ? new Date(last.dt.getTime() + spacingAt(null))
    : pickFirstDatetime()
  dataPoints.value.push({ dt: nextDt, value: defaultValue() })
  form.value?.validate()
}

const removeRow = (index: number) => {
  dataPoints.value.splice(index, 1)
}

const emit = defineEmits(['close'])

const onAddDataPoints = async () => {
  if (!dataPoints.value.length) return

  const transformedDataPoints: [number, number][] = dataPoints.value.map(
    (p) => [p.dt.getTime(), p.value]
  )

  isUpdating.value = true

  setTimeout(async () => {
    const insertedIndices =
      ((await selectedSeries.value?.data.dispatchAction(
        EnumEditOperations.ADD_POINTS,
        transformedDataPoints
      )) as number[] | undefined) ?? []

    isUpdating.value = false
    await redraw(true)
    await recordPostActionSelection(insertedIndices)
    emit('close')
  })
}

onMounted(() => {
  dataPoints.value = [{ dt: pickFirstDatetime(), value: defaultValue() }]
  form.value?.validate()
})
</script>

<style lang="scss" scoped>
.add-points__row {
  background: rgba(var(--v-theme-primary), 0.02);
}
</style>
