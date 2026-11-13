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

      <template v-for="(m, mi) in mappings" :key="mi">
        <div class="contents">
          <div class="min-w-0 flex items-center">
            <div
              class="etl-source-display w-full min-h-[40px] border rounded-[10px] px-3 py-2 hs-text-sm flex items-center [overflow-wrap:anywhere] [word-break:break-word]"
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
            <MappingDatastreamCard
              class="etl-target-display"
              :datastream-id="m.targetDatastreamId"
            />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { EtlMapping } from '@hydroserver/client'
import { mdiArrowRight } from '@mdi/js'
import MappingDatastreamCard from '@/components/Orchestration/shared/MappingDatastreamCard.vue'
import { useMappingDatastreams } from '@/composables/orchestration/useMappingDatastreams'

defineProps<{ mappings: EtlMapping[] }>()
useMappingDatastreams()
</script>

<style scoped>
.etl-source-display,
.etl-target-display {
  color: var(--hs-text-primary);
  background: var(--hs-surface);
  border-color: var(--hs-border);
}
</style>
