<template>
  <div class="quality-mappings-view">
    <div v-if="mappingRows.length" class="quality-mappings">
      <div class="quality-mappings-head">Target datastream</div>

      <div
        v-for="row in mappingRows"
        :key="row.key"
        class="quality-mapping-target"
      >
        <div class="datastream-display">
          <div class="datastream-display__content">
            <span class="target-name">{{ row.name }}</span>
            <span v-if="row.thingName" class="target-thing">
              {{ row.thingName }}
            </span>
            <span class="target-id">{{ row.id || '—' }}</span>
          </div>
          <DatastreamSiteButton
            :datastream="row.datastream"
            :datastream-id="row.id"
            :fallback-thing-id="row.thingId"
          />
        </div>
      </div>
    </div>

    <div v-else class="empty-mappings">No mappings configured.</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import DatastreamSiteButton from '@/components/Orchestration/shared/DatastreamSiteButton.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamThingId } from '@/utils/orchestration/datastreams'

type DatastreamLike = {
  id?: string
  name?: string
  thingId?: string
  thing_id?: string
  thing?: { id?: string; name?: string }
} | null

const props = defineProps<{
  task: any
  thingId?: string | null
}>()

const {
  linkedDatastreams,
  workspaceDatastreams,
  draftDatastreams,
  workspaceThings,
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
      const thingId =
        (datastream ? datastreamThingId(datastream as any) : '') ||
        props.thingId ||
        ''

      return {
        key: id || `mapping-${index}`,
        id,
        datastream,
        name: datastream?.name || id || '—',
        thingId,
        thingName:
          (datastream as DatastreamLike)?.thing?.name ||
          workspaceThings.value.find((thing) => thing.id === thingId)?.name ||
          props.task?.thing?.name ||
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
  font-size: 0.68rem;
  font-weight: 800;
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
  font-size: 0.86rem;
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
  font-size: 0.86rem;
  font-weight: 600;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.target-thing {
  margin-top: 2px;
  color: rgba(0, 0, 0, 0.66);
  font-size: 0.78rem;
  overflow-wrap: anywhere;
}

.target-id {
  margin-top: 2px;
  color: rgba(0, 0, 0, 0.55);
  font-size: 0.72rem;
  overflow-wrap: anywhere;
}

.empty-mappings {
  padding: 10px 0;
  color: rgba(0, 0, 0, 0.6);
  font-size: 0.86rem;
}
</style>
