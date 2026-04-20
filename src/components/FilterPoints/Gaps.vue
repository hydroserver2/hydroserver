<template>
  <v-card>
    <v-card-title class="text-body-1">Find time gaps</v-card-title>

    <v-card-text>
      <!-- `GapFinder` owns every bit of the detection UX. The
           `auto-select-endpoints` prop makes it live-commit the
           gap endpoints as a point selection on every change — the
           Find Gaps operation's "no button, result is the selection"
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

const { dispatchSelection, clearSelected } = useDataSelection()

// Wipe any existing selection (including box-select / lasso
// rectangles) when the panel opens. Find Gaps will seed its own
// gap-endpoint selection a tick later via the GapFinder's
// autoSelect watcher; starting from a clean slate avoids the
// confusing in-between state where the old unrelated selection
// lingers visually while the new scan hasn't produced any gaps
// yet (e.g. on first mount before a threshold is set).
onMounted(async () => {
  // Switch the plot back to pan mode so the range overlay is
  // visible + interactive on open. If the user was last in zoom /
  // select / lasso the band would otherwise be hidden (staging
  // drops it outside pan mode so those tools aren't obstructed).
  await enterPanMode()
  await clearSelected({ dispatchFilter: false })
  // The GapFinder's own `autoSelectEndpoints` watcher runs in the
  // post-flush queue on mount and can interleave with the
  // `clearSelected` above — whichever finishes last wins, and when
  // clearSelected loses we end up with an empty selection on
  // screen. Re-apply the gap-endpoint selection explicitly here so
  // the final state matches what the user expects regardless of
  // microtask ordering.
  const indices = gapFinder.value?.endpointIndices ?? []
  if (indices.length) {
    await dispatchSelection(indices)
  }
})

const gapFinder = useTemplateRef<InstanceType<typeof GapFinder>>('gapFinder')

const gapCount = computed<number>(
  () => gapFinder.value?.gapPlans.length ?? 0
)

const reselectGaps = async () => {
  // Wipe any prior selection first — including box-select / lasso
  // rectangles, which `dispatchSelection` alone doesn't clear
  // (its underlying `setSelectedPoints` puts `selections: []` into
  // the data update instead of the layout update, so any lasso'd
  // rectangle sticks around). `clearSelected({ dispatchFilter: false
  // })` does a full layout-level clear without the extra
  // ObservationRecord round-trip we don't need here.
  await clearSelected({ dispatchFilter: false })
  const indices = gapFinder.value?.endpointIndices ?? []
  await dispatchSelection(indices)
}
</script>
