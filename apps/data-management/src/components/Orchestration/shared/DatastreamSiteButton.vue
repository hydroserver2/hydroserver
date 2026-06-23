<template>
  <div class="task-datastream-site-button">
    <v-tooltip
      :text="tooltipText"
      location="top"
      :open-delay="0"
      :close-delay="0"
    >
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          icon
          size="x-small"
          variant="text"
          color="primary"
          rounded="lg"
          :to="siteRoute"
          :disabled="!thingId"
          :aria-label="ariaLabel"
          :data-testid="testId"
        >
          <v-icon :icon="mdiMapMarker" size="16" />
        </v-btn>
      </template>
    </v-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { Datastream } from '@hydroserver/client'
import { mdiMapMarker } from '@mdi/js'
import { datastreamThingId } from '@/utils/orchestration/datastreams'

const props = withDefaults(
  defineProps<{
    datastream?: (Partial<Datastream> & Record<string, any>) | null
    datastreamId?: string | null
    fallbackThingId?: string | null
  }>(),
  {
    datastream: null,
    datastreamId: null,
    fallbackThingId: null,
  }
)

const datastreamId = computed(() => {
  const id = props.datastreamId ?? props.datastream?.id
  return id ? String(id) : ''
})

const thingId = computed(() => {
  const fromDatastream = props.datastream
    ? datastreamThingId(props.datastream as Datastream)
    : ''
  return fromDatastream || props.fallbackThingId || ''
})

const siteRoute = computed<RouteLocationRaw | undefined>(() =>
  thingId.value
    ? datastreamId.value
      ? {
          name: 'SiteDetails',
          params: { id: thingId.value },
          query: { datastream: datastreamId.value },
        }
      : { name: 'SiteDetails', params: { id: thingId.value } }
    : undefined
)

const tooltipText = computed(() =>
  thingId.value ? 'View site details' : 'Site details unavailable'
)

const ariaLabel = computed(() =>
  thingId.value
    ? `View site details for datastream ${datastreamId.value || 'mapping'}`
    : 'Site details unavailable'
)

const testId = computed(() =>
  datastreamId.value
    ? `view-site-for-datastream-${datastreamId.value}`
    : undefined
)
</script>

<style scoped>
.task-datastream-site-button {
  flex: 0 0 auto;
  margin-left: auto;
}
</style>
