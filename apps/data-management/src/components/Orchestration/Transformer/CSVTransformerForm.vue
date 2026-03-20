<template>
  <v-row>
    <v-col>
      <v-card-item>
        <v-card-title>Task structure</v-card-title>
      </v-card-item>
      <v-card-text>
        <v-row>
          <v-col>
            <v-radio-group
              class="mt-1"
              v-model="transformerWithTimestamp.settings.identifierType"
            >
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
              :disabled="
                transformerWithTimestamp.settings.identifierType ===
                IdentifierType.Index
              "
              v-model.number="transformerWithTimestamp.settings.headerRow"
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
              v-model.number="transformerWithTimestamp.settings.dataStartRow"
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
              v-model="transformerWithTimestamp.settings.delimiter"
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
      <TimestampFields />
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
  CSVTransformer,
  IdentifierType,
} from '@hydroserver/client'
import { VTextField } from 'vuetify/lib/components/index.mjs'
import TimestampFields from '@/components/Orchestration/Timestamp/TimestampFields.vue'

const { transformer } = storeToRefs(useDataConnectionStore())

const transformerWithTimestamp = computed(() => {
  const t: any = transformer.value ?? {}
  t.settings ??= {}
  t.settings.timestamp ??= {
    key: '',
    format: 'ISO8601',
    timezoneMode: 'embeddedOffset',
  }
  return t as CSVTransformer & {
    settings: CSVTransformer['settings'] & {
      timestamp: { key: string; format: string; timezoneMode: string }
    }
  }
})

const headerRowField = ref<InstanceType<typeof VTextField>>()
const dataStartRowField = ref<InstanceType<typeof VTextField>>()

watch(
  () => transformerWithTimestamp.value.settings.dataStartRow,
  () => {
    nextTick(() => {
      headerRowField.value?.validate()
    })
  }
)

watch(
  () => transformerWithTimestamp.value.settings.headerRow,
  () => {
    nextTick(() => {
      dataStartRowField.value?.validate()
    })
  }
)

const headerRowRules = computed(() => [
  ...rules.greaterThan(0),
  ...rules.lessThan(
    transformerWithTimestamp.value.settings.dataStartRow,
    'the data start row'
  ),
])

const dataStartRowRules = computed(() => [
  ...rules.greaterThan(0),
  ...rules.greaterThan(
    transformerWithTimestamp.value.settings.headerRow || 0,
    'the file header row'
  ),
])

watch(
  () => transformerWithTimestamp.value.settings.identifierType,
  (newType) => {
    transformerWithTimestamp.value.settings.timestamp.key =
      newType === IdentifierType.Name ? 'timestamp' : '1'
  }
)
</script>
