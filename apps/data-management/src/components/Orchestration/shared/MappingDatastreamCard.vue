<template>
  <div
    class="mapping-datastream-card"
    :data-testid="`mapping-datastream-${datastreamId}`"
    :aria-busy="loading"
  >
    <div class="mapping-datastream-card__text">
      <v-skeleton-loader
        v-if="loading"
        type="sentences"
        loading-text="Loading datastream details"
        class="mapping-datastream-card__skeleton"
      />
      <template v-else>
        <span class="mapping-datastream-card__name hs-title">{{
          datastream?.name || '—'
        }}</span>
        <span v-if="siteName" class="mapping-datastream-card__site hs-text-sm"
          >@ {{ siteName }}</span
        >
        <span class="mapping-datastream-card__id hs-text-sm">{{
          datastreamId || '—'
        }}</span>
      </template>
    </div>
    <DatastreamSiteButton
      :datastream="datastream"
      :datastream-id="datastreamId"
      :fallback-monitoring-site-id="loading ? null : monitoringSiteId"
      show-menu
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import hs, {
  type Datastream,
  type DatastreamExtended,
} from '@hydroserver/client'
import DatastreamSiteButton from './DatastreamSiteButton.vue'

const props = defineProps<{
  datastreamId: string
  monitoringSiteId?: string | null
}>()

const datastream = ref<Datastream | null>(null)
const loading = ref(true)
watch(
  () => props.datastreamId,
  async (id, _, onCleanup) => {
    let active = true
    onCleanup(() => {
      active = false
    })
    loading.value = true
    datastream.value = null
    let result: Datastream | null = null
    try {
      if (id) {
        result = await hs.datastreams.getItem(id, { expand_related: true })
      }
    } catch (error) {
      console.error('Error fetching mapping datastream', error)
    }
    if (!active) return
    datastream.value = result
    loading.value = false
  },
  { immediate: true }
)
const siteName = computed(
  () =>
    (datastream.value as DatastreamExtended | null)?.monitoringSite?.name || ''
)
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
/* Reserves space for the name, site, and UUID while loading. */
.mapping-datastream-card__skeleton {
  height: calc(var(--hs-font-sm) * 4.25 + var(--hs-space-2) * 2);
}
.mapping-datastream-card__skeleton :deep(.v-skeleton-loader__sentences) {
  height: 100%;
  align-content: space-around;
}
.mapping-datastream-card__skeleton :deep(.v-skeleton-loader__text) {
  margin: 0;
}
.mapping-datastream-card__name {
  color: var(--hs-text-primary);
}
.mapping-datastream-card__site,
.mapping-datastream-card__id {
  color: var(--hs-text-secondary);
}
</style>
