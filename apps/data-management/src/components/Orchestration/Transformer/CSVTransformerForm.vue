<template>
  <v-row>
    <v-col>
      <v-card-item>
        <v-card-title>Task structure</v-card-title>
      </v-card-item>
      <v-card-text>
        <v-row>
          <v-col>
            <v-radio-group class="mt-1" v-model="identifierType">
              <v-radio
                label="Identify columns by name (recommended)"
                :value="IdentifierType.Name"
              />
              <v-radio
                label="Identify columns by index"
                :value="IdentifierType.Index"
              />
            </v-radio-group>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-text-field
              ref="headerRowField"
              :disabled="identifierType === IdentifierType.Index"
              v-model.number="csvPayload.headerRow"
              label="File header row number *"
              hint="Enter the line number of the row that contains file headers (1-based)."
              type="number"
              clearable
              :rules="headerRowRules"
            />
          </v-col>
          <v-col>
            <v-text-field
              ref="dataStartRowField"
              v-model.number="csvPayload.dataStartRow"
              label="Data start row number *"
              hint="Enter the line number of the row the data starts on (1-based)."
              type="number"
              :rules="dataStartRowRules"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-select
              v-model="csvPayload.delimiter"
              label="File delimiter *"
              hint="Select the type of delimiter used for this data file."
              :items="CSV_DELIMITER_OPTIONS"
              variant="outlined"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-col>
    <v-col md="6">
      <TimestampFields :identifier-type="identifierType" />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataConnectionStore } from '@/store/dataConnection'
import { rules } from '@/utils/rules'
import {
  CSV_DELIMITER_OPTIONS,
  IdentifierType,
  type CSVPayload,
} from '@hydroserver/client'
import { VTextField } from 'vuetify/lib/components/index.mjs'
import TimestampFields from '@/components/Orchestration/Timestamp/TimestampFields.vue'

const { dataConnection } = storeToRefs(useDataConnectionStore())

const csvPayload = computed(() => dataConnection.value.payload as CSVPayload)
const DEFAULT_DELIMITER = ',' as const
const identifierType = ref<IdentifierType>(IdentifierType.Name)

const headerRowField = ref<InstanceType<typeof VTextField>>()
const dataStartRowField = ref<InstanceType<typeof VTextField>>()

watch(
  () => csvPayload.value.dataStartRow,
  () => nextTick(() => headerRowField.value?.validate())
)

watch(
  () => csvPayload.value.headerRow,
  () => nextTick(() => dataStartRowField.value?.validate())
)

const isUninitializedCsv = computed(
  () =>
    csvPayload.value.headerRow == null &&
    csvPayload.value.dataStartRow == null &&
    csvPayload.value.delimiter == null
)

watch(
  isUninitializedCsv,
  (shouldInitialize) => {
    if (!shouldInitialize) return

    csvPayload.value.headerRow = 1
    csvPayload.value.dataStartRow = 2
    csvPayload.value.delimiter = DEFAULT_DELIMITER

    if (!dataConnection.value.timestamp.key) {
      dataConnection.value.timestamp.key = 'timestamp'
    }
  },
  { immediate: true }
)

watch(
  () => dataConnection.value.payload,
  () => {
    identifierType.value =
      csvPayload.value.headerRow == null ? IdentifierType.Index : IdentifierType.Name
  },
  { immediate: true }
)

watch(
  identifierType,
  (newType) => {
    if (newType === IdentifierType.Name) {
      const headerRow = csvPayload.value.headerRow ?? 1
      csvPayload.value.headerRow = headerRow
      csvPayload.value.dataStartRow = Math.max(
        csvPayload.value.dataStartRow ?? headerRow + 1,
        headerRow + 1
      )
      if (
        !dataConnection.value.timestamp.key ||
        dataConnection.value.timestamp.key === '1'
      ) {
        dataConnection.value.timestamp.key = 'timestamp'
      }
      return
    }

    csvPayload.value.headerRow = null
    csvPayload.value.dataStartRow = Math.max(
      csvPayload.value.dataStartRow ?? 1,
      1
    )
    if (
      !dataConnection.value.timestamp.key ||
      dataConnection.value.timestamp.key === 'timestamp'
    ) {
      dataConnection.value.timestamp.key = '1'
    }
  }
)

const headerRowRules = computed(() => [
  ...(identifierType.value === IdentifierType.Name
    ? [
        ...rules.greaterThan(0),
        ...(csvPayload.value.dataStartRow != null
          ? rules.lessThan(csvPayload.value.dataStartRow, 'the data start row')
          : []),
      ]
    : []),
])

const dataStartRowRules = computed(() => [
  ...rules.greaterThan(0),
  ...(identifierType.value === IdentifierType.Name
    ? rules.greaterThan(csvPayload.value.headerRow || 0, 'the file header row')
    : []),
])
</script>
