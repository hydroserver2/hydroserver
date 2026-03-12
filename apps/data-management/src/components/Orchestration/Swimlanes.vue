<template>
  <div class="swimlanes">
    <div class="task-header">
      <span class="task-name">{{ task.name }}</span>
      <div class="actions" v-if="showActions">
        <v-btn
          variant="text"
          color="green"
          :icon="mdiPencil"
          @click.stop="$emit('edit', task)"
        />
        <v-btn
          variant="text"
          color="red-darken-3"
          :icon="mdiDelete"
          @click.stop="$emit('delete', task)"
        />
      </div>
    </div>
    <div class="head">
      {{ isAggregationTask ? 'Source datastream' : 'Source' }}
    </div>
    <div class="head">
      {{ isAggregationTask ? 'Aggregation statistic' : 'Data transformations' }}
    </div>
    <div class="head">
      {{ isAggregationTask ? 'Target datastream' : 'Target' }}
    </div>

    <template v-for="(m, mi) in task.mappings" :key="mi">
      <template v-for="(p, pi) in m.paths" :key="pi">
        <div class="cell source" :class="{ 'source-empty': pi !== 0 }">
          <template v-if="pi === 0">
            <v-chip size="small" color="primary" variant="flat" class="mr-2">
              <template v-if="isAggregationTask">
                {{ sourceDatastreamLabel(m.sourceIdentifier) }}
              </template>
              <template v-else>
                {{ String(m.sourceIdentifier) }}
              </template>
            </v-chip>
          </template>
        </div>

        <div class="cell transforms">
          <div class="transform-row">
            <v-chip
              v-if="!p.dataTransformations?.length"
              size="small"
              variant="tonal"
              color="grey"
            >
              no transform
            </v-chip>
            <TransformChip
              v-for="(t, ti) in p.dataTransformations"
              :key="ti"
              :t="t"
              class="mr-1 mb-1"
            />
          </div>
        </div>

        <div class="cell">
          <div class="text-caption">
            <span class="font-weight-medium">{{
              String(p.targetIdentifier)
            }}</span
            >&nbsp;&ndash;&nbsp;
            <span class="text-medium-emphasis">
              {{
                linkedDatastreams.find((d) => d.id == p.targetIdentifier)?.name
              }}
            </span>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import TransformChip from './TransformChip.vue'
import type { Task, TaskExpanded } from '@hydroserver/client'
import { mdiDelete, mdiPencil } from '@mdi/js'
import { useOrchestrationStore } from '@/store/orchestration'

const props = defineProps<{
  task: TaskExpanded
  showActions?: boolean
}>()

const { linkedDatastreams, workspaceDatastreams } = storeToRefs(
  useOrchestrationStore()
)
const isAggregationTask = computed(
  () => ((props.task as any)?.type ?? 'ETL') === 'Aggregation'
)
defineEmits<{
  (e: 'edit', task: TaskExpanded): void
  (e: 'delete', task: TaskExpanded): void
}>()

function sourceDatastreamLabel(sourceIdentifier: string | number) {
  const id = String(sourceIdentifier)
  const match =
    linkedDatastreams.value.find((d) => d.id === id) ||
    workspaceDatastreams.value.find((d) => d.id === id)
  return match?.name ? `${id} - ${match.name}` : id
}
</script>

<style scoped>
.task-name {
  grid-column: 1 / -1;
  font-weight: 600;
  font-size: 1rem;
  padding: 4px 0 8px;
  color: rgba(0, 0, 0, 0.8);
}
.task-header {
  grid-column: 1 / -1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0 8px;
}
.target-wrap {
  white-space: normal; /* enable wrapping */
  overflow-wrap: anywhere; /* break long tokens if needed */
  text-overflow: clip;
  line-height: 1.25;
}
:deep(.chip-wrap .v-chip__content) {
  white-space: normal !important; /* override Vuetify’s nowrap */
  overflow-wrap: anywhere; /* break very long tokens */
  text-overflow: clip;
  line-height: 1.25;
}
.swimlanes {
  display: grid;
  grid-template-columns: 1fr 2fr 4fr;
  column-gap: 12px;
  row-gap: 8px;
  margin-bottom: 12px;
}
.head {
  font-weight: 600;
  color: rgba(0, 0, 0, 0.6);
  padding-bottom: 6px;
}
.cell {
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  padding: 6px 8px;
  min-height: 34px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
.source {
  background: transparent;
  border: none;
  padding-left: 0;
}
.source-empty {
  min-height: 0;
}
.transforms.trunk {
  position: relative;
}
.transform-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.target {
  justify-content: space-between;
}
</style>
