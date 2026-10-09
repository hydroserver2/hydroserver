<template>
  <v-menu
    v-model="open"
    :close-on-content-click="false"
    location="right"
    offset="8"
  >
    <template #activator="{ props: menuProps }">
      <v-tooltip location="right" :open-delay="400">
        <template #activator="{ props: tipProps }">
          <button
            v-bind="{ ...menuProps, ...tipProps }"
            type="button"
            class="rail-btn rail-btn-secondary"
            data-testid="nav-rail-time-zone"
          >
            <span class="rail-pill rail-pill-secondary">
              <v-icon icon="mdi-earth" size="22" />
            </span>
            <span class="rail-label">{{ abbreviation }}</span>
          </button>
        </template>
        <span>Time zone: {{ description }}</span>
      </v-tooltip>
    </template>

    <v-card width="380" data-testid="time-zone-menu">
      <v-card-title class="text-title-medium d-flex align-center ga-2">
        <v-icon icon="mdi-earth" size="20" />
        Time zone
      </v-card-title>
      <v-card-text class="pt-1">
        <p class="text-body-small text-medium-emphasis mb-3">
          Every date the app shows or takes is in this zone: the plot, the
          table and the date pickers. Observations are stored in UTC either
          way.
        </p>

        <v-select
          :model-value="displayZone.mode"
          :items="ZONE_MODES"
          item-title="title"
          item-value="value"
          label="Time zone type"
          density="compact"
          variant="outlined"
          hide-details
          data-testid="time-zone-mode"
          @update:model-value="onModeChange"
        />

        <v-autocomplete
          v-if="displayZone.mode === 'fixedOffset'"
          :model-value="displayZone.zone"
          :items="FIXED_OFFSET_TIMEZONES"
          label="Fixed UTC offset"
          density="compact"
          variant="outlined"
          hide-details
          class="mt-3"
          data-testid="time-zone-offset"
          @update:model-value="onZoneChange"
        />

        <v-autocomplete
          v-if="displayZone.mode === 'iana'"
          :model-value="displayZone.zone"
          :items="DST_AWARE_TIMEZONES"
          label="IANA time zone"
          density="compact"
          variant="outlined"
          hide-details
          class="mt-3"
          data-testid="time-zone-iana"
          @update:model-value="onZoneChange"
        />
      </v-card-text>
      <v-card-actions class="px-4 pb-3 pt-0">
        <v-btn
          size="small"
          variant="text"
          prepend-icon="mdi-crosshairs-gps"
          :disabled="isBrowserZone"
          data-testid="time-zone-browser"
          @click="setZone(browserZone())"
        >
          Use my browser's zone ({{ browserZone().zone }})
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
/** The rail's time zone setting: UTC, a fixed UTC offset or an IANA zone,
 *  the same choice a data connection's timestamps offer. */

import { computed, ref } from 'vue'
import { DST_AWARE_TIMEZONES, FIXED_OFFSET_TIMEZONES } from '@uwrl/qc-utils'
import { useDisplayZone } from '@/composables/useDisplayZone'
import {
  browserZone,
  offsetMs,
  zoneAbbreviation,
  zoneDescription,
  type ZoneMode,
} from '@/utils/timeZone'

const ZONE_MODES: { title: string; value: ZoneMode }[] = [
  { title: 'UTC', value: 'utc' },
  { title: 'Fixed UTC offset', value: 'fixedOffset' },
  { title: 'IANA time zone', value: 'iana' },
]

const open = ref(false)
const { displayZone, setZone } = useDisplayZone()

const abbreviation = computed(() => zoneAbbreviation(Date.now(), displayZone.value))
const description = computed(() => zoneDescription(Date.now(), displayZone.value))

const isBrowserZone = computed(() => {
  const browser = browserZone()
  return displayZone.value.mode === browser.mode && displayZone.value.zone === browser.zone
})

/** The browser's offset right now, as a list value like `-0600`. */
function browserOffset(): string {
  const minutes = Math.round(offsetMs(Date.now(), browserZone()) / 60_000)
  const sign = minutes < 0 ? '-' : '+'
  const hh = String(Math.floor(Math.abs(minutes) / 60)).padStart(2, '0')
  const mm = String(Math.abs(minutes) % 60).padStart(2, '0')
  const value = `${sign}${hh}${mm}`
  return FIXED_OFFSET_TIMEZONES.some((o) => o.value === value) ? value : '+0000'
}

function onModeChange(mode: ZoneMode) {
  if (mode === 'utc') void setZone({ mode, zone: '' })
  else if (mode === 'fixedOffset') void setZone({ mode, zone: browserOffset() })
  else void setZone(browserZone())
}

function onZoneChange(zone: string | null) {
  if (zone) void setZone({ mode: displayZone.value.mode, zone })
}
</script>
