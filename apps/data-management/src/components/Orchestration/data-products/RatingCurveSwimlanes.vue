<template>
  <div class="swimlanes-view">
    <div class="rc-mappings">
      <div class="rc-mappings-head hs-label">Input datastream</div>
      <div class="rc-mappings-head rc-mappings-head-target hs-label">
        Output datastream
      </div>

      <div v-for="(t, ti) in transformations" :key="ti" class="rc-mapping-row">
        <div class="rc-mapping-source">
          <div class="etl-source-display datastream-display">
            <div class="datastream-display__content">
              <span class="target-name hs-title">{{
                inputDatastream(t)?.name || '—'
              }}</span>
              <small v-if="ratingCurveName(t)" class="target-monitoringSite">
                via {{ ratingCurveName(t) }}
              </small>
              <small class="target-id">{{ inputDatastreamId(t) || '—' }}</small>
            </div>
            <DatastreamSiteButton
              :datastream="inputDatastream(t)"
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
              <span class="target-name hs-title">{{
                outputDatastream(t)?.name || '—'
              }}</span>
              <small
                v-if="outputMonitoringSiteName(t)"
                class="target-monitoringSite"
              >
                {{ outputMonitoringSiteName(t) }}
              </small>
              <small class="target-id">{{
                outputDatastreamId(t) || '—'
              }}</small>
            </div>
            <DatastreamSiteButton
              :datastream="outputDatastream(t)"
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
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiArrowRight } from '@mdi/js'
import DatastreamSiteButton from '@/components/Orchestration/shared/DatastreamSiteButton.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'
import hs, { type RatingCurve } from '@hydroserver/client'

type DatastreamLike = {
  id?: string
  name?: string
  monitoringSiteId?: string
  monitoring_site_id?: string
  monitoringSite?: { id?: string }
} | null

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

const {
  workspaceMonitoringSites,
  workspaceDatastreams,
  linkedDatastreams,
  draftDatastreams,
} = storeToRefs(useOrchestrationStore())

const allKnownDatastreams = computed(() => [
  ...workspaceDatastreams.value,
  ...linkedDatastreams.value,
  ...draftDatastreams.value,
])

// `DataProductTransformationResponse` only carries flat ids -- unlike the
// datastreams (already loaded workspace-wide by the orchestration store),
// nothing else on this page loads rating curves, so this component fetches
// the ones for its own monitoring site to resolve `ratingCurveId` to a name.
const ratingCurves = ref<RatingCurve[]>([])

async function loadRatingCurves() {
  if (!props.monitoringSiteId) {
    ratingCurves.value = []
    return
  }
  ratingCurves.value = await hs.ratingCurves.listItemsForMonitoringSite(
    props.monitoringSiteId
  )
}

onMounted(loadRatingCurves)
watch(() => props.monitoringSiteId, loadRatingCurves)

function inputDatastreamId(t: RatingCurveTransformation) {
  return t.inputDatastreams?.[0]?.datastreamId ?? ''
}

function inputDatastream(t: RatingCurveTransformation): DatastreamLike {
  const id = inputDatastreamId(t)
  if (!id) return null
  return allKnownDatastreams.value.find((d) => String(d.id) === String(id)) ?? null
}

function outputDatastreamId(t: RatingCurveTransformation) {
  return t.outputDatastreamId ?? ''
}

function outputDatastream(t: RatingCurveTransformation): DatastreamLike {
  const id = outputDatastreamId(t)
  if (!id) return null
  return allKnownDatastreams.value.find((d) => String(d.id) === String(id)) ?? null
}

function ratingCurveName(t: RatingCurveTransformation) {
  if (!t.ratingCurveId) return ''
  return ratingCurves.value.find((rc) => rc.id === t.ratingCurveId)?.name ?? ''
}

function outputMonitoringSiteName(t: RatingCurveTransformation) {
  const datastream = outputDatastream(t)
  const monitoringSiteId =
    (datastream ? datastreamMonitoringSiteId(datastream as any) : '') ||
    props.monitoringSiteId
  if (!monitoringSiteId) return ''
  return (
    workspaceMonitoringSites.value.find(
      (th) => th.id === String(monitoringSiteId)
    )?.name || ''
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
  background: var(--hs-surface);
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
  background: var(--hs-surface);
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
</style>
