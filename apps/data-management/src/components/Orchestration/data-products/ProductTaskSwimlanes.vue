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
          <MappingDatastreamCard
            :datastream-id="row.sourceDatastreamId"
            :monitoring-site-id="props.monitoringSiteId"
          />
        </div>

        <div class="product-mapping-arrow">
          <v-icon :icon="mdiArrowRight" size="22" />
        </div>

        <div class="product-mapping-target">
          <MappingDatastreamCard
            class="etl-target-display"
            :datastream-id="row.targetDatastreamId"
            :monitoring-site-id="props.monitoringSiteId"
          />
        </div>
      </div>
    </div>

    <small v-else class="empty-mappings">No mappings configured.</small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { mdiArrowRight } from '@mdi/js'
import type { DataProductTransformation } from '@hydroserver/client'
import MappingDatastreamCard from '@/components/Orchestration/shared/MappingDatastreamCard.vue'
import { useMappingDatastreams } from '@/composables/orchestration/useMappingDatastreams'

type ProductTaskLabel = 'aggregation' | 'derivation'
type MappingRow = {
  key: string
  sourceDatastreamId: string
  targetDatastreamId: string
}

const props = defineProps<{
  transformations: DataProductTransformation[]
  taskLabel: ProductTaskLabel
  monitoringSiteId?: string | null
}>()

useMappingDatastreams()

const mappingRows = computed<MappingRow[]>(() => {
  const transformations = props.transformations ?? []

  if (props.taskLabel === 'aggregation') {
    return transformations.map((transformation, index) => ({
      key: `${transformation.id ?? index}`,
      sourceDatastreamId:
        transformation.inputDatastreams?.[0]?.datastreamId ?? '',
      targetDatastreamId: transformation.outputDatastreamId ?? '',
    }))
  }

  return transformations.flatMap((transformation, transformationIndex) =>
    (transformation.inputDatastreams ?? []).map((input, inputIndex) => ({
      key: `${transformation.id ?? transformationIndex}-${input.datastreamId ?? inputIndex}`,
      sourceDatastreamId: input.datastreamId ?? '',
      targetDatastreamId: transformation.outputDatastreamId ?? '',
    }))
  )
})
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
