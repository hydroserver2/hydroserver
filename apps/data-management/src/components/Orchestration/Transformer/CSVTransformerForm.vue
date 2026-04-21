<template>
  <v-row>
    <v-col>
      <v-card-item>
        <v-card-title>CSV structure</v-card-title>
      </v-card-item>
      <v-card-text>
        <v-row>
          <v-col>
            <v-text-field
              ref="headerRowField"
              v-model.number="csvPayload.headerRow"
              label="File header row number"
              hint="Row number containing the headers (1-based)."
              type="number"
              clearable
              :rules="headerRowRules"
            />
          </v-col>
          <v-col>
            <v-text-field
              ref="dataStartRowField"
              v-model.number="csvPayload.dataStartRow"
              label="Data start row number"
              hint="Row number where data begins (1-based)."
              type="number"
              :rules="dataStartRowRules"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-select
              v-model="csvPayload.delimiter"
              label="File delimiter"
              hint="Delimiter used in the CSV file."
              :items="CSV_DELIMITER_OPTIONS"
              variant="outlined"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-col>
    <v-col md="6">
      <TimestampFields />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataConnectionStore } from '@/store/dataConnection'
import { rules } from '@/utils/rules'
import { CSV_DELIMITER_OPTIONS, type CSVPayload } from '@hydroserver/client'
import { VTextField } from 'vuetify/lib/components/index.mjs'
import TimestampFields from '@/components/Orchestration/Timestamp/TimestampFields.vue'

const { dataConnection } = storeToRefs(useDataConnectionStore())

const csvPayload = computed(() => dataConnection.value.payload as CSVPayload)

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

const headerRowRules = computed(() => [
  ...rules.greaterThan(0),
  ...(csvPayload.value.dataStartRow != null
    ? rules.lessThan(csvPayload.value.dataStartRow, 'the data start row')
    : []),
])

const dataStartRowRules = computed(() => [
  ...rules.greaterThan(0),
  ...rules.greaterThan(csvPayload.value.headerRow || 0, 'the file header row'),
])
</script>
