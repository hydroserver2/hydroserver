<template>
  <div class="quality-mappings-view">
    <div v-if="mappingRows.length" class="quality-mappings">
      <div class="quality-mappings-head hs-label">Target datastream</div>

      <div
        v-for="row in mappingRows"
        :key="row.key"
        class="quality-mapping-target"
      >
        <MappingDatastreamCard
          :datastream-id="row.id"
          :monitoring-site-id="props.monitoringSiteId"
        />
      </div>
    </div>

    <small v-else class="empty-mappings">No mappings configured.</small>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import hs, { type MonitoringRule } from '@hydroserver/client'
import MappingDatastreamCard from '@/components/Orchestration/shared/MappingDatastreamCard.vue'
import { useMappingDatastreams } from '@/composables/orchestration/useMappingDatastreams'

const props = defineProps<{
  taskId: string
  monitoringSiteId?: string | null
}>()

useMappingDatastreams()

const rules = ref<MonitoringRule[]>([])

async function loadRules() {
  if (!props.taskId) {
    rules.value = []
    return
  }
  rules.value = await hs.monitoringRules.listAllItems({
    taskId: props.taskId,
  } as any)
}

watch(
  () => props.taskId,
  () => void loadRules(),
  { immediate: true }
)

defineExpose({ reload: loadRules })

const mappingRows = computed(() =>
  [...new Set(rules.value.map((rule) => String(rule.datastreamId ?? '')))]
    .filter(Boolean)
    .map((id) => ({ id, key: id }))
)
</script>

<style scoped>
.quality-mappings-view {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quality-mappings {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.quality-mappings-head {
  padding-bottom: 4px;
  color: #4f4b59;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.quality-mapping-target {
  min-width: 0;
}

.empty-mappings {
  padding: 10px 0;
  color: rgba(0, 0, 0, 0.6);
}
</style>
