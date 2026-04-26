<template>
  <v-card>
    <v-card-title class="text-body-1">Find time gaps</v-card-title>

    <v-card-text>
      <!-- `GapFinder` owns every bit of the detection UX. The
           `auto-select-endpoints` prop makes it commit a `FIND_GAPS`
           filter to history (with its threshold parameters) and
           live-select the gap endpoints on every change — the Find
           Gaps operation's "no button, result is the selection"
           contract. -->
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
      <!-- Re-apply the gap selection. Useful when the user has used
           box-select / lasso (or any other tool that replaced the
           selection) and wants to get back to the found gaps
           without retuning the threshold. -->
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
  // Switch the plot back to pan mode so the range overlay is
  // visible + interactive on open. If the user was last in zoom /
  // select / lasso the band would otherwise be hidden (staging
  // drops it outside pan mode so those tools aren't obstructed).
  await enterPanMode()
  // Wipe any existing selection (including box-select / lasso
  // rectangles) so the panel opens clean. `recordHistory: false`
  // because the watcher's FIND_GAPS dispatch will own the resulting
  // history entry — we don't want this mount-time clear to record a
  // SELECTION([]) that pops the previous panel's filter (cross-
  // filter replace handles that when the watcher fires).
  await clearSelected({ recordHistory: false })
  // GapFinder's `autoSelectEndpoints` watcher runs in the post-flush
  // queue and may interleave with the awaits above. If it lost the
  // race (its `setPlotSelection` ran first, our `clearSelected` ran
  // last), the gap-endpoint highlight would be wiped. Re-apply it
  // explicitly here — same indices as the watcher already pushed,
  // so this is just visual hygiene, no extra qc-utils round-trip.
  const indices = gapFinder.value?.endpointIndices ?? []
  if (indices.length) {
    await setPlotSelection(indices)
  }
})

const reselectGaps = async () => {
  // Wipe any prior selection first — including box-select / lasso
  // rectangles. `setPlotSelection` clears `selectedpoints` but not
  // saved selection shapes; `clearSelected` does a full layout-level
  // clear of both. `recordHistory: false` because re-selecting is
  // mechanically equivalent to "apply the same filter again" — we
  // shouldn't record a clear-then-set in history.
  await clearSelected({ recordHistory: false })
  const indices = gapFinder.value?.endpointIndices ?? []
  await setPlotSelection(indices)
}
</script>
