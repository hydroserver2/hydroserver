<template>
  <div class="swimlanes-view">
    <template v-if="!isAggregationTask">
      <div class="etl-mappings">
        <div class="etl-mappings-head">Source field</div>
        <div class="etl-mappings-head etl-mappings-head-target">
          Target datastream
        </div>

        <template v-for="(m, mi) in (task.mappings as any[])" :key="mi">
          <template v-for="(p, pi) in (m as any).paths" :key="pi">
            <div class="etl-mapping-row">
              <div class="etl-mapping-source">
                <div class="etl-source-display">
                  {{ String(m.sourceIdentifier) || '—' }}
                </div>
              </div>

              <div class="etl-mapping-arrow">
                <v-icon :icon="mdiArrowRight" size="22" />
              </div>

              <div class="etl-mapping-target">
                <div class="etl-target-display">
                  <span class="target-id">{{
                    String(p.targetIdentifier) || '—'
                  }}</span>
                  <span class="target-name">
                    {{ datastreamNameById(p.targetIdentifier) }}
                  </span>
                </div>
              </div>
            </div>
          </template>
        </template>
      </div>
    </template>

    <template v-else>
      <div class="swimlanes swimlanes-aggregation">
        <div class="head">Source datastream</div>
        <div class="head">Aggregation statistic</div>
        <div class="head">Target datastream</div>

        <template v-for="(m, mi) in (task.mappings as any[])" :key="mi">
          <template v-for="(p, pi) in ((m as any).paths as any[])" :key="pi">
            <div class="cell aggregation-cell">
              <div class="target-selector-display">
                <v-icon :icon="mdiImport" size="16" class="mr-1" />
                <span class="target-selector-content">
                  <span class="target-id">
                    {{ String(m.sourceIdentifier) || '—' }}
                  </span>
                  <span class="target-name">
                    {{ datastreamNameById(m.sourceIdentifier) }}
                  </span>
                </span>
              </div>
            </div>

            <div class="aggregation-plain-cell">
              <div class="aggregation-stat-display">
                {{ aggregationStatisticLabel(p) }}
              </div>
            </div>

            <div class="cell aggregation-cell">
              <div class="target-selector-display">
                <v-icon :icon="mdiImport" size="16" class="mr-1" />
                <span class="target-selector-content">
                  <span class="target-id">
                    {{ String(p.targetIdentifier) || '—' }}
                  </span>
                  <span class="target-name">
                    {{ datastreamNameById(p.targetIdentifier) }}
                  </span>
                </span>
              </div>
            </div>
          </template>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import type { TaskExpanded } from '@hydroserver/client'
import { mdiArrowRight, mdiImport } from '@mdi/js'
import { useOrchestrationStore } from '@/store/orchestration'

const props = defineProps<{
  task: TaskExpanded
}>()

const { linkedDatastreams, workspaceDatastreams, draftDatastreams } =
  storeToRefs(useOrchestrationStore())

const isAggregationTask = computed(
  () => ((props.task as any)?.type ?? 'ETL') === 'Aggregation'
)

const aggregationStatisticTitles: Record<string, string> = {
  simple_mean: 'Simple mean',
  time_weighted_daily_mean: 'Time-weighted daily mean',
  last_value_of_day: 'Last value of day',
}

function aggregationStatisticLabel(path: any) {
  const transform = (path?.dataTransformations ?? []).find(
    (t: any) => t?.type === 'aggregation'
  )
  const statistic = transform?.aggregationStatistic
  if (!statistic) return '—'
  return aggregationStatisticTitles[statistic] ?? statistic
}

function datastreamNameById(id: string | number | undefined | null) {
  if (id === undefined || id === null || `${id}` === '') return ''
  const key = String(id)
  return (
    workspaceDatastreams.value.find((d) => d.id === key)?.name ||
    linkedDatastreams.value.find((d) => d.id === key)?.name ||
    draftDatastreams.value.find((d) => String(d.id) === key)?.name ||
    ''
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
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.etl-mappings-head {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  font-size: 0.68rem;
}
.etl-mappings-head-target {
  margin-left: calc(50% + 34px);
}
.etl-mapping-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px minmax(0, 1fr);
  gap: 5px;
  align-items: stretch;
}
.etl-mapping-source,
.etl-mapping-target {
  min-width: 0;
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
  overflow: hidden;
}

.swimlanes {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  column-gap: 12px;
  row-gap: 8px;
}
.swimlanes-aggregation {
  --aggregation-statistic-width: 18rem;
  grid-template-columns:
    minmax(0, 1fr)
    fit-content(var(--aggregation-statistic-width))
    minmax(0, 1fr);
  column-gap: 12px;
}
.head {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4f4b59;
  font-size: 0.68rem;
  padding-bottom: 6px;
}
.cell {
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  padding: 6px 8px;
  min-height: 40px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}
.aggregation-cell {
  background: transparent;
  border: none;
  padding: 0;
}
.aggregation-plain-cell {
  display: flex;
  align-items: center;
  max-width: var(--aggregation-statistic-width);
  width: var(--aggregation-statistic-width);
}
.aggregation-stat-display {
  width: 100%;
  border: 1px solid #d0c9d8;
  border-radius: 10px;
  padding: 8px 12px;
  background: #fdfdff;
  font-size: 0.86rem;
  color: #1c1b1f;
}
.target-selector-display {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  border: 1px solid #d0c9d8;
  border-radius: 10px;
  padding: 6px 12px;
  background: #f6f9ff;
  color: #1c1b1f;
  font-size: 0.86rem;
  min-height: 40px;
}
.target-selector-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}
.target-id {
  font-weight: 600;
  overflow-wrap: anywhere;
  white-space: normal;
}
.target-name {
  color: rgba(0, 0, 0, 0.66);
  overflow-wrap: anywhere;
  white-space: normal;
  font-size: 0.78rem;
}

@media (max-width: 960px) {
  .etl-mappings-head-target {
    margin-left: 0;
  }
  .etl-mapping-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .etl-mapping-arrow {
    justify-content: flex-start;
    min-height: 0;
  }
}
</style>
