<template>
  <div class="filter-range-panel d-flex flex-column">
    <div class="filter-range-panel__body px-3 py-2">
      <RangeStager ref="stager" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Filter range — sidebar panel rendered above OperationPanel when the
 * plot header's "Filter range" toggle is on. Wraps the existing
 * `RangeStager` (date pickers, presets, blue plot overlay, bounds
 * clamping) and mirrors its window into the UI store so every filter
 * operation can pick the active range up via `filterRangeFromTs` /
 * `filterRangeToTs`.
 */
import { ref, useTemplateRef, watch, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import RangeStager from '@/components/FilterPoints/RangeStager.vue'
import { useUIStore } from '@/store/userInterface'

const stager = useTemplateRef<InstanceType<typeof RangeStager>>('stager')
const { filterRangeFromTs, filterRangeToTs } = storeToRefs(useUIStore())

// Keep the store mirrors of fromTs/toTs in sync so other components
// (each filter panel) can react without holding a ref to this
// component. Watching the unwrapped numbers means the watcher only
// fires when the values actually change — not on every render of
// the stager.
const stop = ref<() => void>()
const wireMirrors = () => {
  // `useTemplateRef` resolves to the component instance; .fromTs /
  // .toTs come from RangeStager.defineExpose.
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

// `onMounted` would only run once. The stager ref needs to exist
// first; using a microtask after the render flushes is enough.
queueMicrotask(wireMirrors)

onBeforeUnmount(() => {
  stop.value?.()
  // Closing the panel must clear the published range so filter
  // operations downstream stop seeing a stale window.
  filterRangeFromTs.value = null
  filterRangeToTs.value = null
})
</script>

<style scoped>
.filter-range-panel {
  min-height: 0;
}

.filter-range-panel__body {
  min-height: 0;
}
</style>
