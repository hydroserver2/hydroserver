<template>
  <div class="swimlanes-view">
    <div v-if="mappingRows.length" class="product-mappings">
      <div class="product-mappings-head">Source datastream</div>
      <div class="product-mappings-head product-mappings-head-target">
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
              <span class="target-name">
                {{
                  datastreamName(row.sourceDatastream, row.sourceDatastreamId)
                }}
              </span>
              <span v-if="row.sourceDetail" class="target-thing">
                {{ row.sourceDetail }}
              </span>
              <span v-if="thingName(row.sourceDatastream)" class="target-thing">
                {{ thingName(row.sourceDatastream) }}
              </span>
              <span class="target-id">{{ row.sourceDatastreamId || '—' }}</span>
            </div>
            <DatastreamSiteButton
              :datastream="row.sourceDatastream"
              :datastream-id="row.sourceDatastreamId"
              :fallback-thing-id="
                thingId(row.sourceDatastream) || props.thingId
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
              <span class="target-name">
                {{
                  datastreamName(row.targetDatastream, row.targetDatastreamId)
                }}
              </span>
              <span v-if="thingName(row.targetDatastream)" class="target-thing">
                {{ thingName(row.targetDatastream) }}
              </span>
              <span class="target-id">{{ row.targetDatastreamId || '—' }}</span>
            </div>
            <DatastreamSiteButton
              :datastream="row.targetDatastream"
              :datastream-id="row.targetDatastreamId"
              :fallback-thing-id="
                thingId(row.targetDatastream) || props.thingId
              "
            />
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-mappings">No mappings configured.</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiArrowRight } from '@mdi/js'
import DatastreamSiteButton from '@/components/Orchestration/shared/DatastreamSiteButton.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamThingId } from '@/utils/orchestration/datastreams'

type ProductTaskLabel = 'aggregation' | 'expression' | 'derivation'
type DatastreamLike = {
  id?: string
  name?: string
  thingId?: string
  thing_id?: string
  thing?: { id?: string }
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

const mappingRows = computed<MappingRow[]>(() => {
  if (props.taskLabel === 'derivation') {
    return (props.task?.compositeExpressionTransformations ?? []).flatMap(
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
  }

  const transformations =
    props.taskLabel === 'aggregation'
      ? props.task?.aggregationTransformations ?? []
      : props.task?.expressionTransformations ?? []

  return transformations.map((transformation: any, index: number) => {
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
  })
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

function thingId(datastream: DatastreamLike) {
  return datastream ? datastreamThingId(datastream as any) : ''
}

function thingName(datastream: DatastreamLike) {
  const id = thingId(datastream)
  if (!id) return ''
  return (
    workspaceThings.value.find((thing) => thing.id === String(id))?.name || ''
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
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  font-size: 0.68rem;
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
  font-size: 0.86rem;
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
  font-size: 0.86rem;
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
  font-size: 0.72rem;
  margin-top: 2px;
}
.target-name {
  font-weight: 600;
  color: #1c1b1f;
  font-size: 0.86rem;
  line-height: 1.25;
  overflow-wrap: anywhere;
  white-space: normal;
}
.target-thing {
  color: rgba(0, 0, 0, 0.66);
  overflow-wrap: anywhere;
  white-space: normal;
  font-size: 0.78rem;
  margin-top: 2px;
}
.empty-mappings {
  color: rgba(0, 0, 0, 0.6);
  font-size: 0.86rem;
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
