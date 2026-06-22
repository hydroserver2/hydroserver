<template>
  <div
    data-testid="filter-range-panel"
    class="d-flex flex-column"
    style="min-height: 0"
  >
    <div class="px-3 py-2" style="min-height: 0">
      <RangeStager ref="stager" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef, watch, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import RangeStager from '@/components/FilterPoints/RangeStager.vue'
import { useUIStore } from '@/store/userInterface'

const stager = useTemplateRef<InstanceType<typeof RangeStager>>('stager')
const { filterRangeFromTs, filterRangeToTs } = storeToRefs(useUIStore())

const stop = ref<() => void>()
const wireMirrors = () => {
  stop.value = watch(
    [() => stager.value?.fromTs, () => stager.value?.toTs],
    ([from, to]) => {
      filterRangeFromTs.value =
        typeof from === 'number' && Number.isFinite(from) ? from : null
      filterRangeToTs.value =
        typeof to === 'number' && Number.isFinite(to) ? to : null
    },
    { immediate: true }
  )
}

// Stager ref isn't populated until after render flushes.
queueMicrotask(wireMirrors)

onBeforeUnmount(() => {
  stop.value?.()
  filterRangeFromTs.value = null
  filterRangeToTs.value = null
})
</script>
