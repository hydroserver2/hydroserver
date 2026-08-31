<template>
  <div class="swimlanes-view">
    <div v-if="mappingRows.length" class="product-mappings">
      <div class="product-mappings-head hs-label">Source datastream</div>
      <div class="product-mappings-head product-mappings-head-target hs-label">
        Target datastream
      </div>

      <div
        v-for="row in mappingRows"
        :key="row.key"
        class="product-mapping-row"
      >
        <div class="product-mapping-source">
          <div class="etl-source-display datastream-display">
            <div class="datastream-display__content">
              <span class="target-name hs-title">
                {{
                  datastreamName(row.sourceDatastream, row.sourceDatastreamId)
                }}
              </span>
              <small v-if="row.sourceDetail" class="target-monitoringSite">
                {{ row.sourceDetail }}
              </small>
              <small
                v-if="monitoringSiteName(row.sourceDatastream)"
                class="target-monitoringSite"
              >
                {{ monitoringSiteName(row.sourceDatastream) }}
              </small>
              <small class="target-id">{{ row.sourceDatastreamId || '—' }}</small>
            </div>
            <DatastreamSiteButton
              :datastream="row.sourceDatastream"
              :datastream-id="row.sourceDatastreamId"
              :fallback-monitoring-site-id="
                monitoringSiteId(row.sourceDatastream) || props.monitoringSiteId
              "
            />
          </div>
        </div>

        <div class="product-mapping-arrow">
          <v-icon :icon="mdiArrowRight" size="22" />
        </div>

        <div class="product-mapping-target">
          <div class="etl-target-display datastream-display">
            <div class="datastream-display__content">
              <span class="target-name hs-title">
                {{
                  datastreamName(row.targetDatastream, row.targetDatastreamId)
                }}
              </span>
              <small
                v-if="monitoringSiteName(row.targetDatastream)"
                class="target-monitoringSite"
              >
                {{ monitoringSiteName(row.targetDatastream) }}
              </small>
              <small class="target-id">{{ row.targetDatastreamId || '—' }}</small>
            </div>
            <DatastreamSiteButton
              :datastream="row.targetDatastream"
              :datastream-id="row.targetDatastreamId"
              :fallback-monitoring-site-id="
                monitoringSiteId(row.targetDatastream) || props.monitoringSiteId
              "
            />
          </div>
        </div>
      </div>
    </div>

    <small v-else class="empty-mappings">No mappings configured.</small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiArrowRight } from '@mdi/js'
import DatastreamSiteButton from '@/components/Orchestration/shared/DatastreamSiteButton.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'

type ProductTaskLabel = 'aggregation' | 'derivation'
type DatastreamLike = {
  id?: string
  name?: string
  monitoringSiteId?: string
  monitoring_site_id?: string
  monitoringSite?: { id?: string }
} | null

type MappingRow = {
  key: string
  sourceDatastream: DatastreamLike
  sourceDatastreamId: string
  sourceDetail: string
  targetDatastream: DatastreamLike
  targetDatastreamId: string
}

const props = defineProps<{
  task: any
  taskLabel: ProductTaskLabel
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

const mappingRows = computed<MappingRow[]>(() => {
  if (props.taskLabel === 'aggregation') {
    return (props.task?.aggregationTransformations ?? []).map(
      (transformation: any, index: number) => {
        const sourceDatastream = resolveDatastream(
          transformation.inputDatastream,
          transformation.inputDatastreamId
        )
        const targetDatastream = resolveDatastream(
          transformation.outputDatastream,
          transformation.outputDatastreamId
        )

        return {
          key: `${transformation.id ?? index}`,
          sourceDatastream,
          sourceDatastreamId: datastreamId(
            sourceDatastream,
            transformation.inputDatastreamId
          ),
          sourceDetail: '',
          targetDatastream,
          targetDatastreamId: datastreamId(
            targetDatastream,
            transformation.outputDatastreamId
          ),
        }
      }
    )
  }

  // The derivation transformation type always carries a list of inputs
  // (one or more).
  return (props.task?.derivationTransformations ?? []).flatMap(
    (transformation: any, transformationIndex: number) => {
      const targetDatastream = resolveDatastream(
        transformation.outputDatastream,
        transformation.outputDatastreamId
      )
      const targetDatastreamId = datastreamId(
        targetDatastream,
        transformation.outputDatastreamId
      )

      return (transformation.inputDatastreams ?? []).map(
        (input: any, inputIndex: number) => {
          const sourceDatastream = resolveDatastream(
            input.datastream ?? input.inputDatastream,
            input.datastreamId ?? input.inputDatastreamId
          )

          return {
            key: `${transformation.id ?? transformationIndex}-${
              input.datastreamId ?? inputIndex
            }`,
            sourceDatastream,
            sourceDatastreamId: datastreamId(
              sourceDatastream,
              input.datastreamId ?? input.inputDatastreamId
            ),
            sourceDetail: input.variableName
              ? `Variable ${input.variableName}`
              : '',
            targetDatastream,
            targetDatastreamId,
          }
        }
      )
    }
  )
})

function resolveDatastream(datastream: DatastreamLike, id?: string | null) {
  if (datastream?.id || datastream?.name) return datastream
  if (!id) return null
  const key = String(id)
  return allKnownDatastreams.value.find((d) => String(d.id) === key) ?? null
}

function datastreamId(datastream: DatastreamLike, fallback?: string | null) {
  return String(datastream?.id ?? fallback ?? '')
}

function datastreamName(datastream: DatastreamLike, fallbackId: string) {
  if (datastream?.name) return datastream.name
  if (!fallbackId) return '—'
  return fallbackId
}

function monitoringSiteId(datastream: DatastreamLike) {
  return datastream ? datastreamMonitoringSiteId(datastream as any) : ''
}

function monitoringSiteName(datastream: DatastreamLike) {
  const id = monitoringSiteId(datastream)
  if (!id) return ''
  return (
    workspaceMonitoringSites.value.find((monitoringSite) => monitoringSite.id === String(id))?.name || ''
  )
}
</script>

<style scoped>
.swimlanes-view {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-mappings {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px minmax(0, 1fr);
  gap: 5px 5px;
  align-items: center;
}
.product-mappings-head {
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  padding-bottom: 4px;
}
.product-mappings-head:first-child {
  grid-column: 1 / 2;
}
.product-mappings-head-target {
  grid-column: 3 / 4;
}
.product-mapping-row {
  display: contents;
}
.product-mapping-source,
.product-mapping-target {
  min-width: 0;
  display: flex;
  align-items: center;
}
.product-mapping-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0b8c9;
  min-height: 40px;
}
.etl-source-display {
  width: 100%;
  min-height: 40px;
  border: 1px solid #d0c9d8;
  border-radius: 8px;
  padding: 6px 12px;
  background: #fdfdff;
  color: #1c1b1f;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: left;
  overflow: hidden;
}
.etl-target-display {
  width: 100%;
  min-height: 40px;
  border: 1px solid #d0c9d8;
  border-radius: 8px;
  padding: 6px 12px;
  background: #f6f9ff;
  color: #1c1b1f;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: left;
  overflow: hidden;
}
.datastream-display {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.datastream-display__content {
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.target-id {
  color: rgba(0, 0, 0, 0.55);
  overflow-wrap: anywhere;
  white-space: normal;
  margin-top: 2px;
}
.target-name {
  color: #1c1b1f;
  overflow-wrap: anywhere;
  white-space: normal;
}
.target-monitoringSite {
  color: rgba(0, 0, 0, 0.66);
  overflow-wrap: anywhere;
  white-space: normal;
  margin-top: 2px;
}
.empty-mappings {
  color: rgba(0, 0, 0, 0.6);
  padding: 10px 0;
}

@media (max-width: 960px) {
  .product-mappings {
    grid-template-columns: 1fr;
  }
  .product-mappings-head,
  .product-mappings-head:first-child,
  .product-mappings-head-target {
    grid-column: 1 / -1;
  }
  .product-mapping-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 5px;
  }
  .product-mapping-arrow {
    justify-content: flex-start;
    min-height: 0;
  }
}
</style>
