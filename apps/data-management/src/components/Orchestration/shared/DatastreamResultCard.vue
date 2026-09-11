<template>
  <div class="datastream-result-row">
    <div class="datastream-result-row__content">
      <div class="datastream-result-row__title">
        <span class="datastream-result-row__name">
          {{ datastream.name || 'Unnamed datastream' }}
        </span>
        <template v-if="showMonitoringSiteContext && monitoringSiteName">
          <span class="datastream-result-row__separator" aria-hidden="true">
            @
          </span>
          <span class="datastream-result-row__site">
            {{ monitoringSiteName }}
          </span>
        </template>
      </div>

      <div
        v-if="hasObservationInformation"
        class="datastream-result-row__observation-range hs-text-sm"
      >
        {{ observationRange }}
      </div>
    </div>

    <v-btn
      variant="text"
      size="small"
      color="primary"
      :append-icon="mdiChevronRight"
      :aria-label="`View details for ${datastream.name || 'datastream'}`"
      class="datastream-result-row__details"
      @mousedown.stop
      @click.stop="$emit('details')"
    >
      Details
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Datastream } from '@hydroserver/client'
import { mdiChevronRight } from '@mdi/js'
import { formatTime } from '@/utils/time'

const props = defineProps<{
  datastream: Datastream
  showMonitoringSiteContext?: boolean
}>()

defineEmits<{
  (e: 'details'): void
}>()

const monitoringSiteName = computed(() => {
  const datastream = props.datastream as Datastream & Record<string, any>
  return datastream.monitoringSite?.name || ''
})

const hasObservationInformation = computed(
  () =>
    props.datastream.valueCount !== null ||
    Boolean(props.datastream.phenomenonBeginTime) ||
    Boolean(props.datastream.phenomenonEndTime)
)

const observationRange = computed(() => {
  const count = Number(props.datastream.valueCount)
  const observationLabel = count === 1 ? 'observation' : 'observations'
  const formattedCount = Number.isFinite(count) ? count.toLocaleString() : '—'

  if (count === 0) return '0 observations'

  return [
    `${formattedCount} ${observationLabel} between`,
    formatTime(props.datastream.phenomenonBeginTime),
    'and',
    formatTime(props.datastream.phenomenonEndTime),
  ].join(' ')
})
</script>

<style scoped>
.datastream-result-row {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
  width: 100%;
  padding: var(--hs-space-12) var(--hs-space-16);
  background: var(--hs-surface);
  border-bottom: 1px solid var(--hs-border);
}

.datastream-result-row__content {
  flex: 1;
  min-width: 0;
}

.datastream-result-row__title {
  display: flex;
  gap: var(--hs-space-6);
  align-items: baseline;
  width: 100%;
}

.datastream-result-row__name {
  min-width: 0;
  overflow: hidden;
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.datastream-result-row__separator,
.datastream-result-row__site {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-regular);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.datastream-result-row__separator {
  flex: 0 0 auto;
}

.datastream-result-row__observation-range {
  margin-top: var(--hs-space-4);
  color: var(--hs-text-secondary);
  font-family: var(--hs-font-data);
  line-height: 1.4;
}

.datastream-result-row__details {
  flex: 0 0 auto;
  min-height: var(--hs-space-24);
}

@media (max-width: 760px) {
  .datastream-result-row {
    align-items: flex-start;
  }

  .datastream-result-row__title {
    align-items: flex-start;
  }

  .datastream-result-row__name,
  .datastream-result-row__site {
    white-space: normal;
  }
}
</style>
