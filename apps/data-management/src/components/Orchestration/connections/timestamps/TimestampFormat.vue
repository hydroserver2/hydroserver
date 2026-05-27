<template>
  <v-row>
    <v-col>
      <v-select
        v-model="target.format"
        :items="FORMAT_OPTIONS"
        item-title="title"
        item-value="value"
        label="Timestamp format *"
        hide-details
      >
        <template #append>
          <v-btn
            v-if="target.format === 'ISO8601'"
            size="small"
            variant="text"
            color="grey"
            :icon="mdiHelpCircle"
            @click="openIso8601Help"
          />
          <v-btn
            v-else-if="target.format === 'custom'"
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

  <v-row v-if="target.format === 'custom'">
    <v-col>
      <v-text-field
        v-model="target.customFormat"
        label="Custom timestamp format *"
        hint="Enter the timestamp format."
        :rules="rules.required"
      />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Timestamp } from '@/models/timestamp'
import { rules } from '@/utils/rules'
import { mdiHelpCircle } from '@mdi/js'

const { target } = defineProps<{ target: Timestamp; color: string }>()

const FORMAT_OPTIONS = [
  { title: 'ISO 8601', value: 'ISO8601' },
  { title: 'Custom Format', value: 'custom' },
] as const

const customFormatCache = ref(target.customFormat)
watch(
  () => target.format,
  (fmt) => {
    target.customFormat = fmt === 'custom' ? customFormatCache.value : undefined
  }
)

const openStrftimeHelp = () =>
  window.open('https://devhints.io/strftime', '_blank', 'noreferrer')

const openIso8601Help = () =>
  window.open(
    'https://www.iso.org/iso-8601-date-and-time-format.html',
    '_blank',
    'noreferrer'
  )
</script>
