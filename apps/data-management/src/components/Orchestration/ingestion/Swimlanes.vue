<template>
  <div class="swimlanes-view">
    <div class="etl-mappings">
      <div class="etl-mappings-head">Source field</div>
      <div class="etl-mappings-head etl-mappings-head-target">
        Target datastream
      </div>

      <div
        v-for="(m, mi) in task.mappings"
        :key="mi"
        class="etl-mapping-row"
      >
        <div class="etl-mapping-source">
          <div class="etl-source-display">
            {{ m.sourceIdentifier || '—' }}
          </div>
        </div>

        <div class="etl-mapping-arrow">
          <v-icon :icon="mdiArrowRight" size="22" />
        </div>

        <div class="etl-mapping-target">
          <div class="etl-target-display">
            <span class="target-name">
              {{ resolveTargetName(m) || '—' }}
            </span>
            <span v-if="resolveThingName(m)" class="target-thing">
              {{ resolveThingName(m) }}
            </span>
            <span class="target-id">
              {{ targetDatastream(m)?.id || '—' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import type { TaskExpanded, TaskMapping } from '@hydroserver/client'
import { mdiArrowRight } from '@mdi/js'
import { useOrchestrationStore } from '@/store/orchestration'

const props = defineProps<{
  task: TaskExpanded
}>()

const {
  linkedDatastreams,
  workspaceDatastreams,
  draftDatastreams,
  workspaceThings,
} = storeToRefs(useOrchestrationStore())

function targetDatastream(mapping: TaskMapping) {
  return 'targetDatastream' in mapping ? mapping.targetDatastream : null
}

function resolveTargetName(mapping: TaskMapping) {
  const datastream = targetDatastream(mapping)
  if (datastream?.name) return datastream.name
  const id = datastream?.id
  if (!id) return ''
  const key = String(id)
  return (
    workspaceDatastreams.value.find((d) => d.id === key)?.name ||
    linkedDatastreams.value.find((d) => d.id === key)?.name ||
    draftDatastreams.value.find((d) => String(d.id) === key)?.name ||
    ''
  )
}

function resolveThingName(mapping: TaskMapping) {
  const ds = targetDatastream(mapping)
  const dsId = ds?.id
  const thingId =
    ds?.thingId ??
    ds?.thing_id ??
    (dsId
      ? workspaceDatastreams.value.find((d) => d.id === String(dsId))?.thingId
      : null)
  if (!thingId) return ''
  return (
    workspaceThings.value.find((t) => t.id === String(thingId))?.name || ''
  )
}
</script>

<style scoped>
.swimlanes-view {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.etl-mappings {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px minmax(0, 2fr);
  gap: 5px 5px;
  align-items: center;
}
.etl-mappings-head {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  font-size: 0.68rem;
  padding-bottom: 4px;
}
.etl-mappings-head:first-child {
  grid-column: 1 / 2;
}
.etl-mappings-head-target {
  grid-column: 3 / 4;
}
.etl-mapping-row {
  display: contents;
}
.etl-mapping-source,
.etl-mapping-target {
  min-width: 0;
  display: flex;
  align-items: center;
}
.etl-mapping-arrow {
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
  padding: 8px 12px;
  background: #fdfdff;
  font-size: 0.86rem;
  color: #1c1b1f;
  display: flex;
  align-items: center;
  text-align: left;
  overflow-wrap: anywhere;
  word-break: break-word;
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

@media (max-width: 960px) {
  .etl-mappings {
    grid-template-columns: 1fr;
  }
  .etl-mappings-head,
  .etl-mappings-head-target {
    grid-column: 1 / 2;
  }
  .etl-mapping-row {
    display: contents;
  }
  .etl-mapping-arrow {
    justify-content: flex-start;
    min-height: 0;
  }
}
</style>
