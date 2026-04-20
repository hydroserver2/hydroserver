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
import { computed, useTemplateRef } from 'vue'
import { useDataSelection } from '@/composables/useDataSelection'
import GapFinder from '@/components/FilterPoints/GapFinder.vue'

const { dispatchSelection, clearSelected } = useDataSelection()

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
