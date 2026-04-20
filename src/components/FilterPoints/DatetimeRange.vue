<template>
  <v-card>
    <v-card-title class="text-body-1">Filter by datetime range</v-card-title>

    <v-card-text>
      <!-- Shared range picker owns the date pickers, presets, plot
           overlay, data-bounds clamping, and range warning. -->
      <RangeStager ref="stager" />

      <v-alert
        v-if="!rangeWarning"
        class="mt-4"
        :color="selectedCount > 0 ? 'info' : 'success'"
        :icon="
          selectedCount > 0
            ? 'mdi-selection-ellipse-arrow-inside'
            : 'mdi-check-circle-outline'
        "
        variant="tonal"
        density="compact"
      >
        <div class="d-flex align-center gap-2">
          <v-progress-circular
            v-if="isComputing"
            size="14"
            width="2"
            indeterminate
            color="primary"
          />
          <div class="text-caption">
            <template v-if="isComputing">Updating selection…</template>
            <template v-else-if="selectedCount > 0">
              <b>{{ selectedCount }}</b>
              point{{ selectedCount === 1 ? '' : 's' }} selected in range.
            </template>
            <template v-else>No points in the selected range.</template>
          </div>
        </div>
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
/**
 * Filter-by-datetime-range panel. Uses the shared `RangeStager`
 * for the range-picking UI (pickers, presets, plot overlay,
 * bounds clamping) and dispatches a live point selection every
 * time the range changes. The commit button is gone — the result
 * of the operation is the visible selection on the plot, exactly
 * like Find Gaps' live-commit behaviour.
 */
import { computed, ref, useTemplateRef, watch } from 'vue'
import { useDataSelection } from '@/composables/useDataSelection'
import RangeStager from '@/components/FilterPoints/RangeStager.vue'

const { dispatchSelection } = useDataSelection()

const stager = useTemplateRef<InstanceType<typeof RangeStager>>('stager')
const rangeIndices = computed<[number, number] | null>(
  () => stager.value?.rangeIndices ?? null
)
const rangeWarning = computed<string | null>(
  () => stager.value?.rangeWarning ?? null
)

const selectedCount = computed(() => {
  const r = rangeIndices.value
  return r ? r[1] - r[0] + 1 : 0
})

// Live "commit" — expand the index bounds into a flat selection
// list and push it to the plot. `flush: 'post'` keeps the Plotly
// restyle behind Vue's DOM reconciliation; `immediate: true` seeds
// the initial selection on open without waiting for the first
// interaction.
const isComputing = ref(false)
watch(
  rangeIndices,
  async (r) => {
    isComputing.value = true
    try {
      if (!r) {
        await dispatchSelection([])
        return
      }
      const [startIdx, endIdx] = r
      const selection: number[] = []
      for (let i = startIdx; i <= endIdx; i++) selection.push(i)
      await dispatchSelection(selection)
    } finally {
      isComputing.value = false
    }
  },
  { immediate: true, flush: 'post' }
)
</script>
