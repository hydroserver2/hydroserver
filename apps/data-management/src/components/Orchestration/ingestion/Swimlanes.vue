<template>
  <div class="flex flex-col gap-1">
    <div
      class="grid grid-cols-[minmax(0,1fr)_42px_minmax(0,2fr)] gap-[5px] items-center max-[960px]:grid-cols-1"
    >
      <div
        class="font-weight-bold uppercase tracking-[0.04em] text-[#4f4b59] hs-text-2xs pb-1 col-start-1 col-end-2 max-[960px]:col-span-full"
      >
        Source field
      </div>
      <div
        class="font-weight-bold uppercase tracking-[0.04em] text-[#4f4b59] hs-text-2xs pb-1 col-start-3 col-end-4 max-[960px]:col-span-full"
      >
        Target datastream
      </div>

      <template v-for="(m, mi) in task.mappings" :key="mi">
        <div class="contents">
          <div class="min-w-0 flex items-center">
            <div
              class="etl-source-display w-full min-h-[40px] border border-[#d0c9d8] rounded-[10px] px-3 py-2 bg-[#fdfdff] hs-text-sm text-[#1c1b1f] flex items-center [overflow-wrap:anywhere] [word-break:break-word]"
            >
              {{ m.sourceIdentifier || '—' }}
            </div>
          </div>

          <div
            class="flex items-center justify-center text-[#c0b8c9] min-h-[40px] max-[960px]:justify-start max-[960px]:min-h-0"
          >
            <v-icon :icon="mdiArrowRight" size="22" />
          </div>

          <div class="min-w-0 flex items-center">
            <div
              class="etl-target-display w-full min-h-[40px] border border-[#d0c9d8] rounded-[10px] px-3 py-[6px] bg-[#f6f9ff] hs-text-sm text-[#1c1b1f] flex items-center gap-2 overflow-hidden"
            >
              <div class="min-w-0 flex flex-1 flex-col justify-center">
                <span
                  class="font-weight-semibold text-[#1c1b1f] hs-text-sm leading-[1.25] [overflow-wrap:anywhere] whitespace-normal"
                >
                  {{ resolveTargetName(m) || '—' }}
                </span>
                <span
                  v-if="resolveMonitoringSiteName(m)"
                  class="text-[rgba(0,0,0,0.66)] hs-text-sm mt-0.5 [overflow-wrap:anywhere] whitespace-normal"
                >
                  {{ resolveMonitoringSiteName(m) }}
                </span>
                <span
                  class="text-[rgba(0,0,0,0.55)] hs-text-sm mt-0.5 [overflow-wrap:anywhere] whitespace-normal"
                >
                  {{ targetDatastreamId(m) || '—' }}
                </span>
              </div>
              <DatastreamSiteButton
                :datastream="targetDatastream(m)"
                :datastream-id="targetDatastreamId(m)"
                :fallback-monitoring-site-id="resolveMonitoringSiteId(m)"
              />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import type { TaskExpanded, TaskMapping } from '@hydroserver/client'
import { mdiArrowRight } from '@mdi/js'
import DatastreamSiteButton from '@/components/Orchestration/shared/DatastreamSiteButton.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'

const props = defineProps<{
  task: TaskExpanded
}>()

const {
  linkedDatastreams,
  workspaceDatastreams,
  draftDatastreams,
  workspaceMonitoringSites,
} = storeToRefs(useOrchestrationStore())

function targetDatastream(mapping: TaskMapping) {
  return 'targetDatastream' in mapping ? mapping.targetDatastream : null
}

function targetDatastreamId(mapping: TaskMapping) {
  const datastream = targetDatastream(mapping)
  return datastream?.id || (mapping as any).targetDatastreamId || ''
}

function resolveTargetName(mapping: TaskMapping) {
  const datastream = targetDatastream(mapping)
  if (datastream?.name) return datastream.name
  const id = targetDatastreamId(mapping)
  if (!id) return ''
  const key = String(id)
  return (
    workspaceDatastreams.value.find((d) => d.id === key)?.name ||
    linkedDatastreams.value.find((d) => d.id === key)?.name ||
    draftDatastreams.value.find((d) => String(d.id) === key)?.name ||
    ''
  )
}

function resolveMonitoringSiteName(mapping: TaskMapping) {
  const monitoringSiteId = resolveMonitoringSiteId(mapping)
  if (!monitoringSiteId) return ''
  return workspaceMonitoringSites.value.find((t) => t.id === String(monitoringSiteId))?.name || ''
}

function resolveMonitoringSiteId(mapping: TaskMapping) {
  const ds = targetDatastream(mapping)
  const dsId = targetDatastreamId(mapping)
  const monitoringSiteId = ds ? datastreamMonitoringSiteId(ds as any) : ''
  if (monitoringSiteId) return monitoringSiteId
  if (!dsId) return ''
  const key = String(dsId)
  const relatedDatastream =
    workspaceDatastreams.value.find((d) => d.id === key) ||
    linkedDatastreams.value.find((d) => d.id === key) ||
    draftDatastreams.value.find((d) => String(d.id) === key)
  return relatedDatastream ? datastreamMonitoringSiteId(relatedDatastream as any) : ''
}
</script>
