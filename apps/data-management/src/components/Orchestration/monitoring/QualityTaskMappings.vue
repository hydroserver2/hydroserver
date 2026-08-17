<template>
  <div class="quality-mappings-view">
    <div v-if="mappingRows.length" class="quality-mappings">
      <div class="quality-mappings-head hs-label">Target datastream</div>

      <div
        v-for="row in mappingRows"
        :key="row.key"
        class="quality-mapping-target"
      >
        <div class="datastream-display">
          <div class="datastream-display__content">
            <span class="target-name hs-title">{{
              row.name
            }}</span>
            <small v-if="row.monitoringSiteName" class="target-monitoringSite">
              {{ row.monitoringSiteName }}
            </small>
            <small class="target-id">{{ row.id || '—' }}</small>
          </div>
          <DatastreamSiteButton
            :datastream="row.datastream"
            :datastream-id="row.id"
            :fallback-monitoring-site-id="row.monitoringSiteId"
          />
        </div>
      </div>
    </div>

    <small v-else class="empty-mappings">No mappings configured.</small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import DatastreamSiteButton from '@/components/Orchestration/shared/DatastreamSiteButton.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'

type DatastreamLike = {
  id?: string
  name?: string
  monitoringSiteId?: string
  monitoring_site_id?: string
  monitoringSite?: { id?: string; name?: string }
} | null

const props = defineProps<{
  task: any
  monitoringSiteId?: string | null
}>()

const {
  linkedDatastreams,
  workspaceDatastreams,
  draftDatastreams,
  workspaceMonitoringSites,
} = storeToRefs(useOrchestrationStore())

const allKnownDatastreams = computed(() => [
  ...workspaceDatastreams.value,
  ...linkedDatastreams.value,
  ...draftDatastreams.value,
])

const mappingRows = computed(() =>
  (props.task?.monitoredDatastreams ?? []).map(
    (monitoredDatastream: any, index: number) => {
      const includedDatastream =
        monitoredDatastream.datastream ?? monitoredDatastream
      const id = String(
        includedDatastream?.id ?? monitoredDatastream.datastreamId ?? ''
      )
      const datastream = resolveDatastream(includedDatastream, id)
      const monitoringSiteId =
        (datastream ? datastreamMonitoringSiteId(datastream as any) : '') ||
        props.monitoringSiteId ||
        ''

      return {
        key: id || `mapping-${index}`,
        id,
        datastream,
        name: datastream?.name || id || '—',
        monitoringSiteId,
        monitoringSiteName:
          (datastream as DatastreamLike)?.monitoringSite?.name ||
          workspaceMonitoringSites.value.find((monitoringSite) => monitoringSite.id === monitoringSiteId)?.name ||
          props.task?.monitoringSite?.name ||
          '',
      }
    }
  )
)

function resolveDatastream(datastream: DatastreamLike, id: string) {
  if (datastream?.name) return datastream
  if (!id) return datastream
  return (
    allKnownDatastreams.value.find(
      (candidate) => String(candidate.id) === id
    ) ?? datastream
  )
}
</script>

<style scoped>
.quality-mappings-view {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quality-mappings {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.quality-mappings-head {
  padding-bottom: 4px;
  color: #4f4b59;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.quality-mapping-target {
  min-width: 0;
}

.datastream-display {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 40px;
  overflow: hidden;
  padding: 6px 12px;
  border: 1px solid #d0c9d8;
  border-radius: 8px;
  background: #f6f9ff;
  color: #1c1b1f;
  text-align: left;
}

.datastream-display__content {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.target-name {
  color: #1c1b1f;
  overflow-wrap: anywhere;
}

.target-monitoringSite {
  margin-top: 2px;
  color: rgba(0, 0, 0, 0.66);
  overflow-wrap: anywhere;
}

.target-id {
  margin-top: 2px;
  color: rgba(0, 0, 0, 0.55);
  overflow-wrap: anywhere;
}

.empty-mappings {
  padding: 10px 0;
  color: rgba(0, 0, 0, 0.6);
}
</style>
