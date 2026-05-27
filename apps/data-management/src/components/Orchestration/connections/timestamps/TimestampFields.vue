<template>
  <v-card-item>
    <v-card-title>Timestamp</v-card-title>
  </v-card-item>

  <v-card-text class="pb-0">
    <v-row>
      <v-col>
        <v-text-field
          v-model="dataConnection.payload.timestampKey"
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
        >
          <template #append>
            <v-btn
              v-if="formatChoice === 'iso8601'"
              size="small"
              variant="text"
              color="grey"
              :icon="mdiHelpCircle"
              @click="openIso8601Help"
            />
            <v-btn
              v-else-if="formatChoice === 'custom'"
              size="small"
              variant="text"
              color="grey"
              :icon="mdiHelpCircle"
              @click="openStrftimeHelp"
            />
          </template>
        </v-select>
      </v-col>
    </v-row>

    <v-row v-if="formatChoice === 'custom'">
      <v-col>
        <v-text-field
          v-model="dataConnection.payload.timestampFormat"
          label="Custom timestamp format *"
          hint="Enter a strftime format string (e.g. %Y-%m-%d %H:%M:%S)"
          :rules="rules.required"
        />
      </v-col>
    </v-row>
  </v-card-text>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataConnectionStore } from '@/store/dataConnection'
import { rules } from '@/utils/rules'
import { mdiTableColumnWidth, mdiHelpCircle } from '@mdi/js'
import { IdentifierType } from '@hydroserver/client'

const props = defineProps<{
  identifierType?: IdentifierType
}>()

const { dataConnection } = storeToRefs(useDataConnectionStore())

const FORMAT_OPTIONS = [
  { title: 'ISO 8601', value: 'iso8601' },
  { title: 'Custom format', value: 'custom' },
] as const

// Track format choice independently so that selecting 'custom' before typing
// a format string doesn't snap back to 'iso8601' (empty string is falsy).
const formatChoice = ref<'iso8601' | 'custom'>(
  dataConnection.value.payload.timestampFormat ? 'custom' : 'iso8601'
)

watch(formatChoice, (choice) => {
  if (choice === 'iso8601') {
    dataConnection.value.payload.timestampFormat = null
  }
})

// Re-sync when the store's dataConnection is replaced.
watch(
  () => dataConnection.value,
  (dc) => {
    formatChoice.value = dc.payload.timestampFormat ? 'custom' : 'iso8601'
  }
)

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

const openStrftimeHelp = () =>
  window.open(
    'https://devhints.io/strftime',
    '_blank',
    'noreferrer'
  )

const openIso8601Help = () =>
  window.open(
    'https://www.iso.org/iso-8601-date-and-time-format.html',
    '_blank',
    'noreferrer'
  )
</script>
