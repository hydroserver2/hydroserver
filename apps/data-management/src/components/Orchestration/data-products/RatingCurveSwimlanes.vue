<template>
  <div class="swimlanes-view">
    <div class="rc-mappings">
      <div class="rc-mappings-head">Input datastream</div>
      <div class="rc-mappings-head rc-mappings-head-target">
        Output datastream
      </div>

      <div
        v-for="(t, ti) in transformations"
        :key="ti"
        class="rc-mapping-row"
      >
        <div class="rc-mapping-source">
          <div class="etl-source-display">
            <span class="target-name">{{ t.inputDatastream?.name || '—' }}</span>
            <span v-if="t.ratingCurve?.name" class="target-thing">
              via {{ t.ratingCurve.name }}
            </span>
            <span class="target-id">{{ t.inputDatastream?.id || '—' }}</span>
          </div>
        </div>

        <div class="rc-mapping-arrow">
          <v-icon :icon="mdiArrowRight" size="22" />
        </div>

        <div class="rc-mapping-target">
          <div class="etl-target-display">
            <span class="target-name">{{ t.outputDatastream?.name || '—' }}</span>
            <span v-if="outputThingName(t)" class="target-thing">
              {{ outputThingName(t) }}
            </span>
            <span class="target-id">{{ t.outputDatastream?.id || '—' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { mdiArrowRight } from '@mdi/js'
import { useOrchestrationStore } from '@/store/orchestration'

type RatingCurveTransformation = {
  id?: string
  inputDatastream?: { id?: string; name?: string; thingId?: string }
  outputDatastream?: { id?: string; name?: string; thingId?: string }
  ratingCurve?: { id?: string; name?: string }
}

const props = defineProps<{
  transformations: RatingCurveTransformation[]
}>()

const { workspaceThings } = storeToRefs(useOrchestrationStore())

function outputThingName(t: RatingCurveTransformation) {
  const ds = t.outputDatastream as any
  const thingId = ds?.thingId ?? ds?.thing_id
  if (!thingId) return ''
  return workspaceThings.value.find((th) => th.id === String(thingId))?.name || ''
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
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  font-size: 0.68rem;
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
  border-radius: 10px;
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
</style>
