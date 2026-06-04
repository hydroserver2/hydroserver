<template>
  <div class="flex flex-col gap-1">
    <div
      class="grid grid-cols-[minmax(0,1fr)_42px_minmax(0,2fr)] gap-[5px] items-center max-[960px]:grid-cols-1"
    >
      <div class="font-extrabold uppercase tracking-[0.04em] text-[#4f4b59] text-[0.68rem] pb-1 col-start-1 col-end-2 max-[960px]:col-span-full">
        Source field
      </div>
      <div class="font-extrabold uppercase tracking-[0.04em] text-[#4f4b59] text-[0.68rem] pb-1 col-start-3 col-end-4 max-[960px]:col-span-full">
        Target datastream
      </div>

      <template v-for="(m, mi) in task.mappings" :key="mi">
        <div class="contents">
          <div class="min-w-0 flex items-center">
            <div
              class="etl-source-display w-full min-h-[40px] border border-[#d0c9d8] rounded-[10px] px-3 py-2 bg-[#fdfdff] text-[0.86rem] text-[#1c1b1f] flex items-center [overflow-wrap:anywhere] [word-break:break-word]"
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
              class="etl-target-display w-full min-h-[40px] border border-[#d0c9d8] rounded-[10px] px-3 py-[6px] bg-[#f6f9ff] text-[0.86rem] text-[#1c1b1f] flex flex-col justify-center overflow-hidden"
            >
              <span class="font-semibold text-[#1c1b1f] text-[0.86rem] leading-[1.25] [overflow-wrap:anywhere] whitespace-normal">
                {{ resolveTargetName(m) || '—' }}
              </span>
              <span
                v-if="resolveThingName(m)"
                class="text-[rgba(0,0,0,0.66)] text-[0.78rem] mt-0.5 [overflow-wrap:anywhere] whitespace-normal"
              >
                {{ resolveThingName(m) }}
              </span>
              <span class="text-[rgba(0,0,0,0.55)] text-[0.72rem] mt-0.5 [overflow-wrap:anywhere] whitespace-normal">
                {{ targetDatastream(m)?.id || '—' }}
              </span>
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
