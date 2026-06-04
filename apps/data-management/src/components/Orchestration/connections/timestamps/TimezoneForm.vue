<template>
  <v-form ref="localForm" v-model="isValid" validate-on="input">
    <v-card
      class="mt-4"
      color="blue-grey-darken-2"
      variant="outlined"
      rounded="lg"
    >
      <v-toolbar color="blue-grey-darken-2">
        <v-row align="center" class="pt-0">
          <v-col cols="auto" class="pr-0">
            <v-card-item><v-card-title>Timezone</v-card-title></v-card-item>
          </v-col>
          <v-col class="pl-0">
            <v-icon
              :icon="mdiHelpCircleOutline"
              @click="showHelp = !showHelp"
              color="white"
              size="small"
            />
          </v-col>
        </v-row>
        <v-spacer />
        <v-select
          class="mx-4"
          v-model="timezoneMode"
          :items="TIMEZONE_OPTIONS"
          item-title="title"
          item-value="value"
          label="Timezone type"
          density="compact"
          rounded="lg"
          hide-details
          max-width="220px"
          variant="outlined"
        />
      </v-toolbar>

      <v-card-text v-if="showHelp" class="pt-4">
        The selected timezone applies to all timezone-unaware timestamps — both
        values substituted into query parameters (e.g. start and end time) and
        timestamps in the fetched payload. If your timestamps already include an
        embedded offset (e.g. an ISO 8601 string with <code>+05:30</code>), the
        embedded timezone takes precedence for payload data.
      </v-card-text>

      <v-card-text v-if="timezoneMode === 'fixedOffset' || timezoneMode === 'iana'">
        <v-row v-if="timezoneMode === 'fixedOffset'">
          <v-col>
            <v-autocomplete
              v-model="dataConnection.timezone"
              label="Fixed UTC offset *"
              hint="Select the fixed UTC offset for this data."
              :items="FIXED_OFFSET_TIMEZONES"
              :rules="rules.required"
            />
          </v-col>
        </v-row>

        <v-row v-if="timezoneMode === 'iana'">
          <v-col>
            <v-autocomplete
              v-model="dataConnection.timezone"
              label="IANA timezone *"
              hint="Select an IANA timezone for this data."
              :items="DST_AWARE_TIMEZONES"
              :rules="rules.required"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDataConnectionStore } from '@/store/dataConnection'
import { storeToRefs } from 'pinia'
import { VForm } from 'vuetify/lib/components/index.mjs'
import { FIXED_OFFSET_TIMEZONES, DST_AWARE_TIMEZONES } from '@/models/timestamp'
import { rules } from '@/utils/rules'
import { mdiHelpCircleOutline } from '@mdi/js'

const localForm = ref<VForm>()
const isValid = ref(true)
const showHelp = ref(false)

async function validate() {
  await localForm.value?.validate()
  return isValid.value
}

defineExpose({ validate })

const { dataConnection } = storeToRefs(useDataConnectionStore())

const TIMEZONE_OPTIONS = [
  { title: 'UTC (Default)', value: 'utc' },
  { title: 'Fixed UTC Offset', value: 'fixedOffset' },
  { title: 'IANA Timezone', value: 'iana' },
] as const

const timezoneMode = computed({
  get(): 'utc' | 'fixedOffset' | 'iana' {
    const tzType = dataConnection.value.timezoneType
    if (tzType === 'offset') return 'fixedOffset'
    if (tzType === 'iana') return 'iana'
    return 'utc'
  },
  set(mode: 'utc' | 'fixedOffset' | 'iana') {
    if (mode === 'utc') {
      dataConnection.value.timezoneType = null
      dataConnection.value.timezone = null
    } else if (mode === 'fixedOffset') {
      dataConnection.value.timezoneType = 'offset'
      dataConnection.value.timezone = '-0700'
    } else {
      dataConnection.value.timezoneType = 'iana'
      dataConnection.value.timezone = 'America/Denver'
    }
  },
})
</script>