<template>
  <v-card-item>
    <v-card-title>Task timestamp</v-card-title>
  </v-card-item>
  <v-card-text class="pb-0">
    <v-row>
      <v-col>
        <v-text-field
          v-model="transformerWithTimestamp.settings.timestamp.key"
          placeholder="timestamp"
          :label="timestampKeyLabel"
          density="compact"
          rounded="lg"
          :type="timestampInputType"
          :prepend-inner-icon="mdiTableColumnWidth"
          :rules="timestampKeyRules"
        />
      </v-col>
    </v-row>
  </v-card-text>
  <v-card-text>
    <TimestampFormat
      :target="transformerWithTimestamp.settings.timestamp"
      color="green-darken-4"
    />
  </v-card-text>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CSVTransformer, IdentifierType } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { useDataConnectionStore } from '@/store/dataConnection'

import { rules } from '@/utils/rules'
import TimestampFormat from './TimestampFormat.vue'
import { mdiTableColumnWidth } from '@mdi/js'

const { transformer } = storeToRefs(useDataConnectionStore())

const transformerWithTimestamp = computed(() => {
  const t: any = transformer.value ?? {}
  t.settings ??= {}
  t.settings.timestamp ??= {
    key: '',
    format: 'ISO8601',
    timezoneMode: 'embeddedOffset',
  }
  return t
})

const isCSV = (t?: any | null) => !!t && t.type === 'CSV'

const timestampKeyLabel = computed(() => {
  const t = transformerWithTimestamp.value
  if (isCSV(t)) {
    return `Timestamp column ${
      (t as CSVTransformer).settings.identifierType === IdentifierType.Name
        ? 'name'
        : 'index'
    } *`
  }
  return 'Timestamp key *'
})

const timestampInputType = computed(() => {
  if (isCSV(transformerWithTimestamp.value)) {
    return (transformerWithTimestamp.value as CSVTransformer).settings
      .identifierType === IdentifierType.Index
      ? 'number'
      : 'text'
  }
  return 'text'
})

const timestampKeyRules = computed(() => {
  const t = transformerWithTimestamp.value
  if (isCSV(t)) {
    return (t as CSVTransformer).settings.identifierType === IdentifierType.Name
      ? rules.requiredAndMaxLength150
      : rules.requiredNumber
  }
  return rules.requiredAndMaxLength150
})
</script>
