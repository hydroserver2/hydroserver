<template>
  <div class="task-datastream-site-button">
    <v-menu v-if="showMenu" location="bottom end" attach="body">
      <template #activator="{ props: menuProps }">
        <v-btn-icon
          v-bind="menuProps"
          :icon="mdiDotsVertical"
          size="small"
          class="task-datastream-site-button__button"
          :disabled="!monitoringSiteId"
          :aria-label="menuAriaLabel"
          :data-testid="menuTestId"
        />
      </template>

      <v-list>
        <v-list-item
          :prepend-icon="mdiMapMarkerOutline"
          title="View on site details page"
          :to="siteRoute"
          :data-testid="testId"
        />
        <v-list-item
          :prepend-icon="mdiChartLine"
          title="View on visualize data page"
          :to="visualizeRoute"
          :disabled="!visualizeRoute"
          :data-testid="visualizeLinkTestId"
        />
      </v-list>
    </v-menu>

    <v-tooltip
      v-else
      :text="tooltipText"
      location="top"
      :open-delay="0"
      :close-delay="0"
    >
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          icon
          size="small"
          variant="text"
          color="primary"
          rounded="lg"
          class="task-datastream-site-button__button"
          :to="siteRoute"
          :disabled="!monitoringSiteId"
          :aria-label="ariaLabel"
          :data-testid="testId"
        >
          <v-icon
            :icon="mdiOpenInNew"
            size="18"
            class="task-datastream-site-button__icon"
          />
        </v-btn>
      </template>
    </v-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { Datastream } from '@hydroserver/client'
import {
  mdiChartLine,
  mdiDotsVertical,
  mdiMapMarkerOutline,
  mdiOpenInNew,
} from '@mdi/js'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'

const props = withDefaults(
  defineProps<{
    datastream?: (Partial<Datastream> & Record<string, any>) | null
    datastreamId?: string | null
    fallbackMonitoringSiteId?: string | null
    showMenu?: boolean
  }>(),
  {
    datastream: null,
    datastreamId: null,
    fallbackMonitoringSiteId: null,
    showMenu: false,
  }
)

const datastreamId = computed(() => {
  const id = props.datastreamId ?? props.datastream?.id
  return id ? String(id) : ''
})

const monitoringSiteId = computed(() => {
  const fromDatastream = props.datastream
    ? datastreamMonitoringSiteId(props.datastream as Datastream)
    : ''
  return fromDatastream || props.fallbackMonitoringSiteId || ''
})

const siteRoute = computed<RouteLocationRaw | undefined>(() =>
  monitoringSiteId.value
    ? datastreamId.value
      ? {
          name: 'SiteDetails',
          params: { id: monitoringSiteId.value },
          query: { datastream: datastreamId.value },
        }
      : { name: 'SiteDetails', params: { id: monitoringSiteId.value } }
    : undefined
)

const visualizeRoute = computed<RouteLocationRaw | undefined>(() =>
  monitoringSiteId.value && datastreamId.value
    ? {
        name: 'VisualizeData',
        query: {
          sites: monitoringSiteId.value,
          datastreams: datastreamId.value,
        },
      }
    : undefined
)

const tooltipText = computed(() =>
  monitoringSiteId.value
    ? 'Go to site details page'
    : 'Site details unavailable'
)

const ariaLabel = computed(() =>
  monitoringSiteId.value
    ? `Go to site details page for datastream ${datastreamId.value || 'mapping'}`
    : 'Site details unavailable'
)

const testId = computed(() =>
  datastreamId.value
    ? `view-site-for-datastream-${datastreamId.value}`
    : undefined
)

const menuAriaLabel = computed(() =>
  datastreamId.value
    ? `Actions for datastream ${datastreamId.value}`
    : 'Datastream actions'
)

const menuTestId = computed(() =>
  datastreamId.value ? `datastream-links-${datastreamId.value}` : undefined
)

const visualizeLinkTestId = computed(() =>
  datastreamId.value ? `visualize-datastream-${datastreamId.value}` : undefined
)
</script>

<style scoped>
.task-datastream-site-button {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
  margin-left: auto;
}

.task-datastream-site-button__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 28px;
  width: 28px;
  min-width: 28px;
  height: 28px;
  padding: 0;
}

.task-datastream-site-button__button :deep(.v-btn__content) {
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.task-datastream-site-button__icon {
  flex: 0 0 18px;
  width: 18px;
  height: 18px;
}
</style>
