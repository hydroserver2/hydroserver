<template>
  <v-row>
    <v-col>
      <v-select
        v-model="target.format"
        :items="TIMESTAMP_FORMATS"
        item-title="text"
        item-value="value"
        label="Timestamp format *"
        hide-details
      />
    </v-col>
  </v-row>

  <v-row v-if="target.format === 'custom'">
    <v-col>
      <v-text-field
        v-model="target.customFormat"
        label="Custom timestamp format *"
        hint="Enter the timestamp format."
        :rules="rules.required"
      >
        <template v-slot:append-inner>
          <v-btn
            size="lg"
            color="gray"
            :icon="mdiHelpCircle"
            @click="openStrftimeHelp"
          />
        </template>
      </v-text-field>
    </v-col>
  </v-row>

  <v-row v-if="target.format && target.format !== 'ISO8601'">
    <v-col>
      <label class="v-label">Timezone</label>
      <v-btn-toggle
        class="ml-4"
        v-model="target.timezoneMode"
        mandatory
        :rules="rules.required"
        variant="outlined"
        density="compact"
        :color="color"
      >
        <v-btn value="utc">UTC</v-btn>
        <v-btn value="fixedOffset">Fixed offset</v-btn>
        <v-btn value="daylightSavings">Daylight savings aware</v-btn>
      </v-btn-toggle>
    </v-col>
  </v-row>

  <v-row v-if="target.timezoneMode === 'fixedOffset'">
    <v-col>
      <v-autocomplete
        v-model="target.timezone"
        label="Fixed timezone offset *"
        hint="Enter a timezone offset to apply to the timestamp column."
        :items="FIXED_OFFSET_TIMEZONES"
        :rules="rules.required"
      ></v-autocomplete>
    </v-col>
  </v-row>

  <v-row v-if="target.timezoneMode === 'daylightSavings'">
    <v-col>
      <v-autocomplete
        v-model="target.timezone"
        label="Daylight savings aware timezone offset *"
        hint="Enter a timezone offset to apply to the timestamp column."
        :items="DST_AWARE_TIMEZONES"
        :rules="rules.required"
      ></v-autocomplete>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Timestamp,
  FIXED_OFFSET_TIMEZONES,
  DST_AWARE_TIMEZONES,
  TIMESTAMP_FORMATS,
} from '@/models/timestamp'
import { rules } from '@/utils/rules'
import { mdiHelpCircle } from '@mdi/js'

const { target, color } = defineProps<{ target: Timestamp; color: string }>()

const customFormatCache = ref(target.customFormat)
watch(
  () => target.format,
  (fmt) => {
    target.customFormat = fmt === 'custom' ? customFormatCache.value : undefined

    if (fmt === 'ISO8601') {
      target.timezoneMode = 'embeddedOffset'
      target.timezone = undefined
    } else {
      target.timezoneMode = 'utc'
    }
  }
)

watch(
  () => target.timezoneMode,
  (newMode) => {
    if (newMode === 'utc') target.timezone = undefined
    else if (newMode === 'fixedOffset') target.timezone = '-0700'
    else if (newMode === 'daylightSavings') target.timezone = 'America/Denver'
  }
)

const openStrftimeHelp = () =>
  window.open('https://devhints.io/strftime', '_blank', 'noreferrer')
</script>
