<template>
  <v-card-item>
    <v-card-title>Data ingestion window</v-card-title>
  </v-card-item>
  <v-card-text class="pt-0">
    <p class="hs-text-sm text-medium-emphasis mb-2">Data ingestion window start</p>
    <v-row align="center" dense>
      <v-col cols="12" sm="5">
        <v-select
          v-model="startAnchor"
          :items="ANCHOR_OPTIONS"
          item-title="title"
          item-value="value"
          label="Anchor"
          density="compact"
          variant="outlined"
          hide-details
        />
      </v-col>
      <template v-if="startAnchor !== 'fixed_timestamp'">
        <v-col cols="6" sm="4">
          <v-text-field
            v-model.number="startLookback"
            type="number"
            min="0"
            label="Lookback"
            density="compact"
            hide-details
            clearable
            placeholder="None"
          />
        </v-col>
        <v-col cols="6" sm="3">
          <v-select
            v-model="startLookbackUnits"
            :items="UNIT_OPTIONS"
            item-title="title"
            item-value="value"
            label="Unit"
            density="compact"
            variant="outlined"
            hide-details
            :disabled="!startLookback"
          />
        </v-col>
      </template>
      <template v-else>
        <v-col>
          <v-text-field
            :model-value="isoToInput(startTimestamp)"
            @update:model-value="startTimestamp = inputToIso($event) || null"
            type="datetime-local"
            :label="`Datetime (${timezoneLabel})`"
            density="compact"
            hide-details
          />
        </v-col>
      </template>
    </v-row>

    <p class="hs-text-sm text-medium-emphasis mt-4 mb-2">Data ingestion window end</p>
    <v-row align="center" dense>
      <v-col cols="12" sm="5">
        <v-select
          v-model="endAnchor"
          :items="ANCHOR_OPTIONS"
          item-title="title"
          item-value="value"
          label="Anchor"
          density="compact"
          variant="outlined"
          hide-details
        />
      </v-col>
      <template v-if="endAnchor !== 'fixed_timestamp'">
        <v-col cols="6" sm="4">
          <v-text-field
            v-model.number="endLookback"
            type="number"
            min="0"
            label="Lookback"
            density="compact"
            hide-details
            clearable
            placeholder="None"
          />
        </v-col>
        <v-col cols="6" sm="3">
          <v-select
            v-model="endLookbackUnits"
            :items="UNIT_OPTIONS"
            item-title="title"
            item-value="value"
            label="Unit"
            density="compact"
            variant="outlined"
            hide-details
            :disabled="!endLookback"
          />
        </v-col>
      </template>
      <template v-else>
        <v-col>
          <v-text-field
            :model-value="isoToInput(endTimestamp)"
            @update:model-value="endTimestamp = inputToIso($event) || null"
            type="datetime-local"
            :label="`Datetime (${timezoneLabel})`"
            density="compact"
            hide-details
          />
        </v-col>
      </template>
    </v-row>
  </v-card-text>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataConnectionStore } from '@/store/dataConnection'
import { getLocalTimeZone, inputToIso, isoToInput } from '@/utils/time'
import type { WindowAnchorType } from '@hydroserver/client'

const { dataConnection } = storeToRefs(useDataConnectionStore())

const timezoneLabel = getLocalTimeZone()

type LookbackUnits = 'minutes' | 'hours' | 'days'

const ANCHOR_OPTIONS = [
  { title: 'Latest observation timestamp', value: 'latest_observation_timestamp' },
  { title: 'Job execution time', value: 'run_time' },
  { title: 'Fixed datetime', value: 'fixed_timestamp' },
] as const

const UNIT_OPTIONS = [
  { title: 'Minutes', value: 'minutes' },
  { title: 'Hours', value: 'hours' },
  { title: 'Days', value: 'days' },
] as const

function initFromPayload() {
  const window = dataConnection.value.payload.dataIngestionWindow

  startAnchor.value = (window?.start?.anchor as WindowAnchorType) ?? 'latest_observation_timestamp'
  startLookback.value = window?.start?.lookback ?? null
  startLookbackUnits.value = (window?.start?.lookbackUnits as LookbackUnits) ?? 'hours'
  startTimestamp.value = window?.start?.timestamp ?? null

  endAnchor.value = (window?.end?.anchor as WindowAnchorType) ?? 'run_time'
  endLookback.value = window?.end?.lookback ?? null
  endLookbackUnits.value = (window?.end?.lookbackUnits as LookbackUnits) ?? 'hours'
  endTimestamp.value = window?.end?.timestamp ?? null
}

const existingWindow = dataConnection.value.payload.dataIngestionWindow

const startAnchor = ref<WindowAnchorType>(
  (existingWindow?.start?.anchor as WindowAnchorType) ?? 'latest_observation_timestamp',
)
const startLookback = ref<number | null>(existingWindow?.start?.lookback ?? null)
const startLookbackUnits = ref<LookbackUnits>(
  (existingWindow?.start?.lookbackUnits as LookbackUnits) ?? 'hours',
)
const startTimestamp = ref<string | null>(existingWindow?.start?.timestamp ?? null)

const endAnchor = ref<WindowAnchorType>(
  (existingWindow?.end?.anchor as WindowAnchorType) ?? 'run_time',
)
const endLookback = ref<number | null>(existingWindow?.end?.lookback ?? null)
const endLookbackUnits = ref<LookbackUnits>(
  (existingWindow?.end?.lookbackUnits as LookbackUnits) ?? 'hours',
)
const endTimestamp = ref<string | null>(existingWindow?.end?.timestamp ?? null)

function buildWindow() {
  const isDefaultStart =
    startAnchor.value === 'latest_observation_timestamp' && !startLookback.value
  const isDefaultEnd = endAnchor.value === 'run_time' && !endLookback.value

  if (isDefaultStart && isDefaultEnd) {
    dataConnection.value.payload.dataIngestionWindow = null
    return
  }

  dataConnection.value.payload.dataIngestionWindow = {
    start: {
      anchor: startAnchor.value,
      lookback: startAnchor.value !== 'fixed_timestamp' ? startLookback.value : null,
      lookbackUnits:
        startAnchor.value !== 'fixed_timestamp' && startLookback.value != null
          ? startLookbackUnits.value
          : null,
      timestamp: startAnchor.value === 'fixed_timestamp' ? startTimestamp.value : null,
    },
    end: {
      anchor: endAnchor.value,
      lookback: endAnchor.value !== 'fixed_timestamp' ? endLookback.value : null,
      lookbackUnits:
        endAnchor.value !== 'fixed_timestamp' && endLookback.value != null
          ? endLookbackUnits.value
          : null,
      timestamp: endAnchor.value === 'fixed_timestamp' ? endTimestamp.value : null,
    },
  }
}

watch(
  [startAnchor, startLookback, startLookbackUnits, startTimestamp, endAnchor, endLookback, endLookbackUnits, endTimestamp],
  buildWindow,
)

// Re-initialize when the payload object is replaced (e.g. CSV↔JSON switch or form reset)
watch(() => dataConnection.value.payload, initFromPayload)
</script>