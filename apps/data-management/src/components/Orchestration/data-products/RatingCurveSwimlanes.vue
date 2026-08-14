<template>
  <div class="swimlanes-view">
    <div class="rc-mappings">
      <div class="rc-mappings-head hs-text-2xs font-weight-bold">Input datastream</div>
      <div class="rc-mappings-head rc-mappings-head-target hs-text-2xs font-weight-bold">
        Output datastream
      </div>

      <div v-for="(t, ti) in transformations" :key="ti" class="rc-mapping-row">
        <div class="rc-mapping-source">
          <div class="etl-source-display datastream-display">
            <div class="datastream-display__content">
              <span class="target-name hs-text-sm font-weight-semibold">{{
                t.inputDatastream?.name || '—'
              }}</span>
              <small v-if="t.ratingCurve?.name" class="target-monitoringSite">
                via {{ t.ratingCurve.name }}
              </small>
              <small class="target-id">{{ inputDatastreamId(t) || '—' }}</small>
            </div>
            <DatastreamSiteButton
              :datastream="t.inputDatastream"
              :datastream-id="inputDatastreamId(t)"
              :fallback-monitoring-site-id="props.monitoringSiteId"
            />
          </div>
        </div>

        <div class="rc-mapping-arrow">
          <v-icon :icon="mdiArrowRight" size="22" />
        </div>

        <div class="rc-mapping-target">
          <div class="etl-target-display datastream-display">
            <div class="datastream-display__content">
              <span class="target-name hs-text-sm font-weight-semibold">{{
                t.outputDatastream?.name || '—'
              }}</span>
              <small
                v-if="outputMonitoringSiteName(t)"
                class="target-monitoringSite"
              >
                {{ outputMonitoringSiteName(t) }}
              </small>
              <small class="target-id">{{ outputDatastreamId(t) || '—' }}</small>
            </div>
            <DatastreamSiteButton
              :datastream="t.outputDatastream"
              :datastream-id="outputDatastreamId(t)"
              :fallback-monitoring-site-id="props.monitoringSiteId"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { mdiArrowRight } from '@mdi/js'
import DatastreamSiteButton from '@/components/Orchestration/shared/DatastreamSiteButton.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'

type RatingCurveTransformation = {
  id?: string
  inputDatastreamId?: string
  outputDatastreamId?: string
  inputDatastream?: {
    id?: string
    name?: string
    monitoringSiteId?: string
    monitoring_site_id?: string
    monitoringSite?: { id?: string }
  }
  outputDatastream?: {
    id?: string
    name?: string
    monitoringSiteId?: string
    monitoring_site_id?: string
    monitoringSite?: { id?: string }
  }
  ratingCurve?: { id?: string; name?: string }
}

const props = defineProps<{
  transformations: RatingCurveTransformation[]
  monitoringSiteId?: string | null
}>()

const { workspaceMonitoringSites } = storeToRefs(useOrchestrationStore())

function inputDatastreamId(t: RatingCurveTransformation) {
  return t.inputDatastream?.id || t.inputDatastreamId || ''
}

function outputDatastreamId(t: RatingCurveTransformation) {
  return t.outputDatastream?.id || t.outputDatastreamId || ''
}

function outputMonitoringSiteName(t: RatingCurveTransformation) {
  const monitoringSiteId =
    (t.outputDatastream ? datastreamMonitoringSiteId(t.outputDatastream as any) : '') ||
    props.monitoringSiteId
  if (!monitoringSiteId) return ''
  return (
    workspaceMonitoringSites.value.find((th) => th.id === String(monitoringSiteId))?.name || ''
  )
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
.etl-source-display {
  width: 100%;
  min-height: 40px;
  border: 1px solid #d0c9d8;
  border-radius: 10px;
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
  border-radius: 10px;
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
  line-height: 1.25;
  overflow-wrap: anywhere;
  white-space: normal;
}
.target-monitoringSite {
  color: rgba(0, 0, 0, 0.66);
  overflow-wrap: anywhere;
  white-space: normal;
  margin-top: 2px;
}
</style>
