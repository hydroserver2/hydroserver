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
        <div class="add-points__list d-flex flex-column gap-3">
          <div
            v-for="(point, index) of dataPoints"
            :key="index"
            class="add-points__row"
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
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!form?.isValid || isUpdating"
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
import { onMounted, ref, type Ref } from 'vue'
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

/** Default value for a new row — datastream's `noDataValue`. */
const defaultValue = () => Number(noDataValue.value) || 0

/**
 * Pick the seed datetime for the first row:
 *   - last selected point + intendedTimeSpacing, when there's a selection
 *   - last datapoint in the QC series + intendedTimeSpacing, otherwise
 *   - `now` if neither is available (shouldn't happen with a loaded series)
 *
 * `intendedTimeSpacing` is the datastream's declared cadence; falls back
 * to 0 (so the seed equals the anchor) when the metadata is missing.
 */
const pickFirstDatetime = (): Date => {
  const dt = intendedSpacingMs() ?? 0
  const dataX = selectedSeries.value?.data.dataX
  let anchor: number | null = null
  if (selectedData.value?.length && dataX) {
    const lastIdx = selectedData.value[selectedData.value.length - 1] as number
    const ts = dataX[lastIdx] as number | undefined
    if (Number.isFinite(ts)) anchor = ts as number
  }
  if (anchor == null && dataX?.length) {
    anchor = dataX[dataX.length - 1] as number
  }
  if (anchor == null) anchor = Date.now()
  return new Date(anchor + dt)
}

const addRow = () => {
  // Each new row sits exactly one cadence step past the previous row,
  // so a user adding several points in a row gets a sensible auto-
  // incremented timeline rather than typing each datetime by hand.
  const dt = intendedSpacingMs() ?? 0
  const last = dataPoints.value[dataPoints.value.length - 1]
  const nextDt = last ? new Date(last.dt.getTime() + dt) : pickFirstDatetime()
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
  // Seed the autopopulated first row.
  dataPoints.value = [{ dt: pickFirstDatetime(), value: defaultValue() }]
  form.value?.validate()
})
</script>

<style lang="scss" scoped>
.add-points__row {
  padding: 8px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 4px;
  background: rgba(var(--v-theme-primary), 0.02);
}
</style>
