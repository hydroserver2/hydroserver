<template>
  <v-card>
    <v-card-title class="text-body-large">Find time gaps</v-card-title>

    <v-card-text>
      <GapFinder
        ref="gapFinder"
        auto-select-endpoints
        computing-hint="Updating gap selection…"
      >
        <template #gap-count-message="{ count }">
          <b>{{ count }}</b> gap{{ count === 1 ? '' : 's' }}
          in the selected range. Endpoints are selected on the plot.
        </template>
      </GapFinder>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        variant="tonal"
        color="primary"
        prepend-icon="mdi-selection-ellipse-arrow-inside"
        :disabled="gapCount === 0"
        @click="reselectGaps"
      >
        Re-select gaps
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, useTemplateRef } from 'vue'
import { useDataSelection } from '@/composables/useDataSelection'
import GapFinder from '@/components/FilterPoints/GapFinder.vue'
import { enterPanMode } from '@/utils/plotting/staging'

const { setPlotSelection, clearSelected } = useDataSelection()
const gapFinder = useTemplateRef<InstanceType<typeof GapFinder>>('gapFinder')

const gapCount = computed<number>(
  () => gapFinder.value?.gapPlans.length ?? 0
)

onMounted(async () => {
  // Pan mode is required for the range overlay to be visible and interactive.
  await enterPanMode()
  // recordHistory false: the GapFinder watcher's FIND_GAPS dispatch owns the history entry.
  await clearSelected({ recordHistory: false })
  // Re-apply in case GapFinder's post-flush watcher lost the race with the awaits above.
  const indices = gapFinder.value?.endpointIndices ?? []
  if (indices.length) {
    await setPlotSelection(indices)
  }
})

const reselectGaps = async () => {
  // clearSelected wipes saved selection shapes (box/lasso) that setPlotSelection alone does not.
  await clearSelected({ recordHistory: false })
  const indices = gapFinder.value?.endpointIndices ?? []
  await setPlotSelection(indices)
}
</script>
