<template>
  <div
    class="mapping-datastream-card"
    :data-testid="`mapping-datastream-${datastreamId}`"
  >
    <div class="mapping-datastream-card__text">
      <span class="mapping-datastream-card__name hs-title">{{
        datastream?.name || '—'
      }}</span>
      <span v-if="siteName" class="mapping-datastream-card__site hs-text-sm"
        >@ {{ siteName }}</span
      >
      <span class="mapping-datastream-card__id hs-text-sm">{{
        datastreamId || '—'
      }}</span>
    </div>
    <DatastreamSiteButton
      :datastream="datastream"
      :datastream-id="datastreamId"
      :fallback-monitoring-site-id="siteId"
      show-menu
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'
import DatastreamSiteButton from './DatastreamSiteButton.vue'

const props = defineProps<{
  datastreamId: string
  monitoringSiteId?: string | null
}>()

const {
  workspaceDatastreams,
  linkedDatastreams,
  draftDatastreams,
  workspaceMonitoringSites,
} = storeToRefs(useOrchestrationStore())

const datastream = computed(
  () =>
    [
      ...workspaceDatastreams.value,
      ...linkedDatastreams.value,
      ...draftDatastreams.value,
    ].find((item) => String(item.id) === props.datastreamId) ?? null
)
const siteId = computed(
  () =>
    (datastream.value
      ? datastreamMonitoringSiteId(datastream.value as any)
      : '') ||
    props.monitoringSiteId ||
    ''
)
const siteName = computed(() => {
  const expanded = datastream.value as {
    monitoringSite?: { name?: string }
  } | null
  return (
    expanded?.monitoringSite?.name ||
    workspaceMonitoringSites.value.find((site) => site.id === siteId.value)
      ?.name ||
    ''
  )
})
</script>

<style scoped>
.mapping-datastream-card {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
  width: 100%;
  min-width: 0;
  padding: var(--hs-space-6) var(--hs-space-12);
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-md);
  background: var(--hs-surface);
}
.mapping-datastream-card__text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  gap: var(--hs-space-2);
  overflow-wrap: anywhere;
}
.mapping-datastream-card__name {
  color: var(--hs-text-primary);
}
.mapping-datastream-card__site,
.mapping-datastream-card__id {
  color: var(--hs-text-secondary);
}
</style>
