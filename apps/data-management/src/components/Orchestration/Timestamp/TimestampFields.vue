<template>
  <v-card-item>
    <v-card-title>Timestamp</v-card-title>
  </v-card-item>

  <v-card-text class="pb-0">
    <v-row>
      <v-col>
        <v-text-field
          v-model="dataConnection.timestamp.key"
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
    <v-row>
      <v-col>
        <v-select
          v-model="formatChoice"
          :items="FORMAT_OPTIONS"
          item-title="title"
          item-value="value"
          label="Timestamp format *"
          hide-details
        />
      </v-col>
    </v-row>

    <v-row v-if="formatChoice === 'custom'">
      <v-col>
        <v-text-field
          v-model="dataConnection.timestamp.format"
          label="Custom timestamp format *"
          hint="Enter a strftime format string (e.g. %Y-%m-%d %H:%M:%S)"
          :rules="rules.required"
        >
          <template #append-inner>
            <v-btn
              size="small"
              variant="text"
              color="grey"
              :icon="mdiHelpCircle"
              @click="openStrftimeHelp"
            />
          </template>
        </v-text-field>
      </v-col>
    </v-row>

    <v-row v-if="formatChoice !== 'iso8601'">
      <v-col>
        <label class="v-label">Timezone</label>
        <v-btn-toggle
          class="ml-4"
          v-model="dataConnection.timestamp.timezoneType"
          mandatory
          variant="outlined"
          density="compact"
          color="green-darken-4"
        >
          <v-btn value="utc">UTC</v-btn>
          <v-btn value="offset">Fixed offset</v-btn>
          <v-btn value="iana">Daylight savings aware</v-btn>
        </v-btn-toggle>
      </v-col>
    </v-row>

    <v-row v-if="dataConnection.timestamp.timezoneType === 'offset'">
      <v-col>
        <v-autocomplete
          v-model="dataConnection.timestamp.timezone"
          label="Fixed timezone offset *"
          hint="Select the fixed UTC offset for this data."
          :items="FIXED_OFFSET_TIMEZONES"
          :rules="rules.required"
        />
      </v-col>
    </v-row>

    <v-row v-if="dataConnection.timestamp.timezoneType === 'iana'">
      <v-col>
        <v-autocomplete
          v-model="dataConnection.timestamp.timezone"
          label="Daylight savings aware timezone *"
          hint="Select an IANA timezone for this data."
          :items="DST_AWARE_TIMEZONES"
          :rules="rules.required"
        />
      </v-col>
    </v-row>
  </v-card-text>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataConnectionStore } from '@/store/dataConnection'
import { rules } from '@/utils/rules'
import { FIXED_OFFSET_TIMEZONES, DST_AWARE_TIMEZONES } from '@/models/timestamp'
import { mdiTableColumnWidth, mdiHelpCircle } from '@mdi/js'
import { IdentifierType } from '@hydroserver/client'

const props = defineProps<{
  identifierType?: IdentifierType
}>()

const { dataConnection } = storeToRefs(useDataConnectionStore())

const FORMAT_OPTIONS = [
  { title: 'ISO 8601 / embedded offset', value: 'iso8601' },
  { title: 'Naive (no timezone in string)', value: 'naive' },
  { title: 'Custom format', value: 'custom' },
] as const

const formatChoice = computed({
  get(): 'iso8601' | 'naive' | 'custom' {
    const fmt = dataConnection.value.timestamp.format
    const tzType = dataConnection.value.timestamp.timezoneType
    if (!fmt && !tzType) return 'iso8601'
    if (!fmt && tzType) return 'naive'
    return 'custom'
  },
  set(choice: 'iso8601' | 'naive' | 'custom') {
    const ts = dataConnection.value.timestamp
    if (choice === 'iso8601') {
      ts.format = null
      ts.timezoneType = null
      ts.timezone = null
    } else if (choice === 'naive') {
      ts.format = null
      ts.timezoneType = ts.timezoneType ?? 'utc'
    } else {
      ts.format = ts.format || ''
      ts.timezoneType = ts.timezoneType ?? 'utc'
    }
  },
})

const timestampKeyLabel = computed(() => {
  if (props.identifierType === IdentifierType.Name) {
    return 'Timestamp column name *'
  }
  if (props.identifierType === IdentifierType.Index) {
    return 'Timestamp column index *'
  }
  return 'Timestamp column *'
})

const timestampInputType = computed(() => {
  return props.identifierType === IdentifierType.Index ? 'number' : 'text'
})

const timestampKeyRules = computed(() => {
  return props.identifierType === IdentifierType.Index
    ? rules.requiredNumber
    : rules.requiredAndMaxLength150
})

watch(
  () => dataConnection.value.timestamp.timezoneType,
  (newType) => {
    const ts = dataConnection.value.timestamp
    if (!newType || newType === 'utc') {
      ts.timezone = null
    } else if (newType === 'offset' && !ts.timezone) {
      ts.timezone = '-0700'
    } else if (newType === 'iana' && !ts.timezone) {
      ts.timezone = 'America/Denver'
    }
  }
)

const openStrftimeHelp = () =>
  window.open('https://devhints.io/strftime', '_blank', 'noreferrer')
</script>
