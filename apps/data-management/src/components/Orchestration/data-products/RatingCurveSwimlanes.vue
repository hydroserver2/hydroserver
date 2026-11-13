<template>
  <div class="swimlanes-view">
    <div class="rc-mappings">
      <div class="rc-mappings-head hs-label">Input datastream</div>
      <div class="rc-mappings-head rc-mappings-head-target hs-label">
        Output datastream
      </div>

      <div v-for="(t, ti) in transformations" :key="ti" class="rc-mapping-row">
        <div class="rc-mapping-source">
          <MappingDatastreamCard
            :datastream-id="inputDatastreamId(t)"
            :monitoring-site-id="props.monitoringSiteId"
          />
        </div>

        <div class="rc-mapping-arrow">
          <v-icon :icon="mdiArrowRight" size="22" />
        </div>

        <div class="rc-mapping-target">
          <MappingDatastreamCard
            class="etl-target-display"
            :datastream-id="outputDatastreamId(t)"
            :monitoring-site-id="props.monitoringSiteId"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { mdiArrowRight } from '@mdi/js'
import MappingDatastreamCard from '@/components/Orchestration/shared/MappingDatastreamCard.vue'
import { useMappingDatastreams } from '@/composables/orchestration/useMappingDatastreams'

type RatingCurveTransformation = {
  id?: string
  outputDatastreamId?: string
  ratingCurveId?: string | null
  inputDatastreams?: { datastreamId?: string; variableName?: string | null }[]
}

const props = defineProps<{
  transformations: RatingCurveTransformation[]
  monitoringSiteId?: string | null
}>()

useMappingDatastreams()

function inputDatastreamId(t: RatingCurveTransformation) {
  return t.inputDatastreams?.[0]?.datastreamId ?? ''
}

function outputDatastreamId(t: RatingCurveTransformation) {
  return t.outputDatastreamId ?? ''
}
</script>

<style scoped>
.swimlanes-view {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rc-mappings {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px minmax(0, 1fr);
  gap: 5px 5px;
  align-items: center;
}
.rc-mappings-head {
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  padding-bottom: 4px;
}
.rc-mappings-head:first-child {
  grid-column: 1 / 2;
}
.rc-mappings-head-target {
  grid-column: 3 / 4;
}
.rc-mapping-row {
  display: contents;
}
.rc-mapping-source,
.rc-mapping-target {
  min-width: 0;
  display: flex;
  align-items: center;
}
.rc-mapping-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0b8c9;
  min-height: 40px;
}
</style>
