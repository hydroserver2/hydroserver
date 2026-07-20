<template>
  <v-card>
    <v-card-title class="text-body-large">Filter by datetime range</v-card-title>

    <v-card-text>
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
        <div class="d-flex align-center ga-2">
          <v-progress-circular
            v-if="isComputing"
            size="14"
            width="2"
            indeterminate
            color="primary"
          />
          <div class="text-body-small">
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
import { computed, ref, useTemplateRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useDataSelection } from '@/composables/useDataSelection'
import RangeStager from '@/components/FilterPoints/RangeStager.vue'

const { selectedSeries } = storeToRefs(usePlotlyStore())
const { setPlotSelection } = useDataSelection()

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

// flush 'post' keeps the Plotly restyle behind Vue's DOM reconciliation.
const isComputing = ref(false)
watch(
  rangeIndices,
  async (r) => {
    isComputing.value = true
    try {
      if (!r) {
        await setPlotSelection([])
        return
      }
      const from = stager.value?.fromTs
      const to = stager.value?.toTs
      const bounds = stager.value?.dataBounds
      const isAll =
        bounds != null &&
        from != null &&
        to != null &&
        Math.abs(from - bounds.min) < 1000 &&
        Math.abs(to - bounds.max) < 1000

      if (isAll) {
        await selectedSeries.value?.data.dispatchFilter(EnumFilterOperations.DATETIME_RANGE)
      } else {
        await selectedSeries.value?.data.dispatchFilter(
          EnumFilterOperations.DATETIME_RANGE,
          from,
          to,
        )
      }

      const [startIdx, endIdx] = r
      const selection: number[] = []
      for (let i = startIdx; i <= endIdx; i++) selection.push(i)
      await setPlotSelection(selection)
    } finally {
      isComputing.value = false
    }
  },
  { immediate: true, flush: 'post' },
)
</script>
