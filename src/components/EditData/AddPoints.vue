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
                @click="dataPoints.splice(index, 1)"
              />
            </div>
            <v-text-field
              v-maska="options"
              label="Datetime"
              placeholder="YYYY-MM-DD HH:MM:SS"
              hint="e.g. 2024-12-30 18:00:00"
              v-model="point[0]"
              :rules="[...required, ...dateTimeFormat]"
              density="comfortable"
              variant="outlined"
              clearable
            />
            <v-text-field
              type="number"
              label="Value"
              :rules="requiredNumber"
              v-model.number="point[1]"
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
import { onMounted, reactive, Ref } from 'vue'
import type { MaskInputOptions } from 'maska'
import { vMaska } from 'maska/vue'
import { ref } from 'vue'
import { dateTimeFormat, required, requiredNumber } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import { storeToRefs } from 'pinia'
import { EnumEditOperations } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'

const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()

const form = ref<InstanceType<typeof VForm>>()

const dataPoints: Ref<
  [
    datetime: string,
    value: number,
    qualifier: Partial<{ resultQualifiers: string[] }>,
  ][]
> = ref([['', 0, { resultQualifiers: [] }]])
const options = reactive<MaskInputOptions>({
  mask: '####-##-## ##:##:##',
  eager: true,
})

const addRow = () => {
  dataPoints.value.push(['2023-01-01 12:00:00', 0, { resultQualifiers: [] }])
  form.value?.validate()
}

const emit = defineEmits(['close'])

const onAddDataPoints = async () => {
  if (!dataPoints.value || !dataPoints.value.length) {
    return
  }

  // Convert input localized datetimes to UTC
  const transformedDataPoints: [number, number][] = dataPoints.value.map(
    (point) => {
      const matches = point[0].match(
        /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/
      )
      if (matches) {
        const year = parseInt(matches[1] as string)
        const month = parseInt(matches[2] as string) - 1
        const day = parseInt(matches[3] as string)
        const hour = parseInt(matches[4] as string)
        const minute = parseInt(matches[5] as string)
        const second = parseInt(matches[6] as string)
        const date = new Date(year, month, day, hour, minute, second).getTime()
        return [date, point[1]]
        // return [date.toISOString().substring(0, 19) + 'Z', point[1], point[2]]
      } else {
        throw new Error('Invalid date format.')
      }
    }
  )

  isUpdating.value = true

  setTimeout(async () => {
    await selectedSeries.value?.data.dispatchAction(
      EnumEditOperations.ADD_POINTS,
      transformedDataPoints
    )

    isUpdating.value = false
    await redraw(true)
    emit('close')
  })
}

onMounted(() => {
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
