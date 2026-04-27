<template>
  <div class="filter-range-panel d-flex flex-column bg-surface">
    <!-- Header mirrors OperationPanel's so the two panels read as
         siblings stacked in the sidebar. The close button flips the
         shared `filterRangeActive` flag — the same flag the plot-
         header toggle drives, so closing here also restores the
         toggle to its inactive state. -->
    <div
      class="filter-range-panel__header px-3 py-2 d-flex align-center gap-2"
    >
      <v-avatar color="primary" variant="flat" size="24">
        <v-icon icon="mdi-arrow-expand-horizontal" color="white" size="14" />
      </v-avatar>
      <div class="d-flex flex-column flex-grow-1" style="min-width: 0">
        <span class="text-body-2 font-weight-bold text-truncate">
          Filter range
        </span>
        <span class="text-caption text-medium-emphasis text-truncate">
          Restrict filter operations to this datetime window.
        </span>
      </div>
      <v-tooltip location="start" text="Disable filter range">
        <template #activator="{ props: tp }">
          <v-btn
            v-bind="tp"
            size="x-small"
            variant="text"
            density="comfortable"
            icon="mdi-close"
            @click="filterRangeActive = false"
          />
        </template>
      </v-tooltip>
    </div>

    <v-divider />

    <div class="filter-range-panel__body px-3 py-3">
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
const { filterRangeActive, filterRangeFromTs, filterRangeToTs } = storeToRefs(
  useUIStore()
)

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
  overflow: hidden;
}

.filter-range-panel__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 40px;
}

.filter-range-panel__body {
  min-height: 0;
}
</style>
